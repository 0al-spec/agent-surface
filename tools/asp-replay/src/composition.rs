use std::sync::OnceLock;

use asp_manifest_linter::lint_manifest_value;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use specification_core::{DecisionSpecification, FirstMatch, Specification};

use crate::hash::object_hash;
use crate::strict_json::parse_strict;
use crate::surface_provider::{self, SurfaceVerdict};
use crate::{ReplayError, TOOL_NAME, TOOL_VERSION, verify};

pub(crate) const COMPOSITION_REPORT_DOMAIN: &str =
    "https://github.com/0al-spec/agent-surface/hash/replay-composition-report/v1";
const COMPOSITION_POLICY_VERSION: &str = "1.0.0";
const MAX_SUPPLEMENTAL_LINT_NODES: usize = 4096;
static COMPOSITION_SCHEMA_VALIDATOR: OnceLock<Result<jsonschema::Validator, String>> =
    OnceLock::new();

const NATIVE_SURFACE: &str = "native_surface";
const NATIVE_GRANT: &str = "native_grant";
const NATIVE_CLOUDEVENT: &str = "native_cloudevent";
const NATIVE_EVENT_ACK: &str = "native_event_ack";
const NATIVE_EVENT_GAP: &str = "native_event_gap";
const NATIVE_RECEIPT: &str = "native_receipt";
const NATIVE_RECEIPT_SIGNATURE: &str = "native_receipt_signature";

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct CompositionTool {
    pub name: String,
    pub version: String,
    pub policy_profile: String,
    pub policy_version: String,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct CompositionInput {
    pub source_sha256: String,
    pub bundle_id: Option<String>,
    pub bundle_hash: Option<String>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct BoundedReplayCoverage {
    pub report_hash: String,
    pub evaluation_state: String,
    pub integrity_verdict: String,
    pub replay_completeness: String,
    pub bounded_verdict: String,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct NativeProviderEvidence {
    pub ruleset_id: String,
    pub ruleset_version: String,
    pub ruleset_sha256: String,
    pub subject_bundle_hash: String,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct NativeProviderCoverage {
    pub provider_id: String,
    pub object_profile: String,
    pub applicability: String,
    pub status: String,
    pub reason: String,
    pub provider_name: Option<String>,
    pub provider_version: Option<String>,
    pub evidence: Option<NativeProviderEvidence>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct SupplementalCoverage {
    pub check_id: String,
    pub status: String,
    pub reason: String,
    pub tool_name: String,
    pub tool_version: String,
    pub ruleset_id: Option<String>,
    pub ruleset_version: Option<String>,
    pub errors: usize,
    pub warnings: usize,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct CompositionReport {
    #[serde(rename = "$schema")]
    pub schema: String,
    pub schema_version: u64,
    pub report_profile: String,
    pub claim_effect: String,
    pub tool: CompositionTool,
    pub input: CompositionInput,
    pub bounded_replay: BoundedReplayCoverage,
    pub composition_state: String,
    pub complete_claim_eligible: bool,
    pub providers: Vec<NativeProviderCoverage>,
    pub supplemental_checks: Vec<SupplementalCoverage>,
    pub report_hash: String,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum CompositionState {
    Rejected,
    Blocked,
    EligibleIncomplete,
    EligibleValid,
}

impl CompositionState {
    const fn as_str(self) -> &'static str {
        match self {
            Self::Rejected => "rejected",
            Self::Blocked => "blocked",
            Self::EligibleIncomplete => "eligible_incomplete",
            Self::EligibleValid => "eligible_valid",
        }
    }

    const fn complete_claim_eligible(self) -> bool {
        matches!(self, Self::EligibleIncomplete | Self::EligibleValid)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Applicability {
    Required,
    NotApplicable,
}

impl Applicability {
    const fn as_str(self) -> &'static str {
        match self {
            Self::Required => "required",
            Self::NotApplicable => "not_applicable",
        }
    }
}

#[derive(Clone, Copy)]
struct ProviderDefinition {
    provider_id: &'static str,
    object_profile: &'static str,
}

const PROVIDERS: [ProviderDefinition; 7] = [
    ProviderDefinition {
        provider_id: NATIVE_SURFACE,
        object_profile: "agent_surface_manifest",
    },
    ProviderDefinition {
        provider_id: NATIVE_GRANT,
        object_profile: "semantic_agent_grant",
    },
    ProviderDefinition {
        provider_id: NATIVE_CLOUDEVENT,
        object_profile: "asp_cloudevent",
    },
    ProviderDefinition {
        provider_id: NATIVE_EVENT_ACK,
        object_profile: "event_acknowledgement",
    },
    ProviderDefinition {
        provider_id: NATIVE_EVENT_GAP,
        object_profile: "event_gap",
    },
    ProviderDefinition {
        provider_id: NATIVE_RECEIPT,
        object_profile: "receipt",
    },
    ProviderDefinition {
        provider_id: NATIVE_RECEIPT_SIGNATURE,
        object_profile: "receipt_signature",
    },
];

enum ProviderOutcome {
    Passed {
        provider_name: &'static str,
        provider_version: &'static str,
        ruleset_id: &'static str,
        ruleset_version: &'static str,
        ruleset_sha256: &'static str,
    },
    Failed {
        provider_name: &'static str,
        provider_version: &'static str,
        ruleset_id: &'static str,
        ruleset_version: &'static str,
        ruleset_sha256: &'static str,
    },
    Unavailable {
        reason: &'static str,
        provider_name: Option<&'static str>,
        provider_version: Option<&'static str>,
    },
}

trait NativeProviderSet {
    fn evaluate(&self, provider_id: &str, bundle: &Value) -> ProviderOutcome;
}

struct BuiltInProviders;

impl NativeProviderSet for BuiltInProviders {
    fn evaluate(&self, provider_id: &str, bundle: &Value) -> ProviderOutcome {
        if provider_id == NATIVE_SURFACE {
            return match surface_provider::evaluate(bundle) {
                SurfaceVerdict::Passed => ProviderOutcome::Passed {
                    provider_name: surface_provider::PROVIDER_NAME,
                    provider_version: surface_provider::PROVIDER_VERSION,
                    ruleset_id: surface_provider::RULESET_ID,
                    ruleset_version: surface_provider::RULESET_VERSION,
                    ruleset_sha256: surface_provider::RULESET_SHA256,
                },
                SurfaceVerdict::Failed => ProviderOutcome::Failed {
                    provider_name: surface_provider::PROVIDER_NAME,
                    provider_version: surface_provider::PROVIDER_VERSION,
                    ruleset_id: surface_provider::RULESET_ID,
                    ruleset_version: surface_provider::RULESET_VERSION,
                    ruleset_sha256: surface_provider::RULESET_SHA256,
                },
                SurfaceVerdict::Unavailable => ProviderOutcome::Unavailable {
                    reason: "provider_error",
                    provider_name: Some(surface_provider::PROVIDER_NAME),
                    provider_version: Some(surface_provider::PROVIDER_VERSION),
                },
            };
        }
        ProviderOutcome::Unavailable {
            reason: "provider_not_implemented",
            provider_name: None,
            provider_version: None,
        }
    }
}

#[derive(Clone, Copy)]
struct CompositionFacts<'a> {
    bounded_verdict: &'a str,
    required_failed: usize,
    required_unavailable: usize,
}

struct BoundedRejected;

impl Specification<CompositionFacts<'_>> for BoundedRejected {
    fn is_satisfied_by(&self, candidate: &CompositionFacts<'_>) -> bool {
        candidate.bounded_verdict == "invalid"
    }
}

struct RequiredProviderFailed;

impl Specification<CompositionFacts<'_>> for RequiredProviderFailed {
    fn is_satisfied_by(&self, candidate: &CompositionFacts<'_>) -> bool {
        candidate.required_failed > 0
    }
}

struct RequiredProviderUnavailable;

impl Specification<CompositionFacts<'_>> for RequiredProviderUnavailable {
    fn is_satisfied_by(&self, candidate: &CompositionFacts<'_>) -> bool {
        candidate.required_unavailable > 0
    }
}

struct AllRequiredProvidersPassed;

impl Specification<CompositionFacts<'_>> for AllRequiredProvidersPassed {
    fn is_satisfied_by(&self, candidate: &CompositionFacts<'_>) -> bool {
        candidate.required_failed == 0 && candidate.required_unavailable == 0
    }
}

struct BoundedIncomplete;

impl Specification<CompositionFacts<'_>> for BoundedIncomplete {
    fn is_satisfied_by(&self, candidate: &CompositionFacts<'_>) -> bool {
        candidate.bounded_verdict == "incomplete"
    }
}

struct BoundedValid;

impl Specification<CompositionFacts<'_>> for BoundedValid {
    fn is_satisfied_by(&self, candidate: &CompositionFacts<'_>) -> bool {
        candidate.bounded_verdict == "valid"
    }
}

fn decide_composition(facts: &CompositionFacts<'_>) -> CompositionState {
    let mut policy = FirstMatch::new();
    policy.push(
        BoundedRejected.or(RequiredProviderFailed),
        CompositionState::Rejected,
    );
    policy.push(RequiredProviderUnavailable, CompositionState::Blocked);
    policy.push(
        AllRequiredProvidersPassed.and(BoundedIncomplete),
        CompositionState::EligibleIncomplete,
    );
    policy.push(
        AllRequiredProvidersPassed.and(BoundedValid),
        CompositionState::EligibleValid,
    );
    policy
        .decide(facts)
        .copied()
        .unwrap_or(CompositionState::Blocked)
}

fn record_exists(bundle: &Value, kind: &str) -> bool {
    bundle
        .get("records")
        .and_then(Value::as_array)
        .is_some_and(|records| {
            records
                .iter()
                .any(|record| record.get("kind").and_then(Value::as_str) == Some(kind))
        })
}

fn receipt_signature_validation_required(bundle: &Value) -> bool {
    if !record_exists(bundle, "receipt") {
        return false;
    }
    let carried_signature =
        bundle
            .get("records")
            .and_then(Value::as_array)
            .is_some_and(|records| {
                records.iter().any(|record| {
                    record.get("kind").and_then(Value::as_str) == Some("receipt")
                        && record
                            .get("body")
                            .and_then(Value::as_object)
                            .is_some_and(|body| body.contains_key("receipt_signatures"))
                })
            });
    let grant_requires_signature = bundle
        .pointer("/context/grant/audit/receipt_signing/required_signers")
        .and_then(Value::as_array)
        .is_some_and(|signers| !signers.is_empty());
    carried_signature || grant_requires_signature
}

fn applicability(provider_id: &str, bundle: &Value) -> Applicability {
    match provider_id {
        NATIVE_SURFACE | NATIVE_GRANT => Applicability::Required,
        NATIVE_CLOUDEVENT if record_exists(bundle, "event_delivery") => Applicability::Required,
        NATIVE_EVENT_ACK if record_exists(bundle, "event_ack") => Applicability::Required,
        NATIVE_EVENT_GAP if record_exists(bundle, "event_gap") => Applicability::Required,
        NATIVE_RECEIPT if record_exists(bundle, "receipt") => Applicability::Required,
        NATIVE_RECEIPT_SIGNATURE if receipt_signature_validation_required(bundle) => {
            Applicability::Required
        }
        _ => Applicability::NotApplicable,
    }
}

fn provider_coverage(
    providers: &impl NativeProviderSet,
    bundle: &Value,
    evaluate: bool,
    _subject_bundle_hash: Option<&str>,
) -> Vec<NativeProviderCoverage> {
    PROVIDERS
        .iter()
        .map(|definition| {
            let applicability = applicability(definition.provider_id, bundle);
            let (status, reason, provider_name, provider_version, evidence) = match applicability {
                Applicability::NotApplicable => {
                    ("not_applicable", "not_applicable", None, None, None)
                }
                Applicability::Required if !evaluate => {
                    ("not_evaluated", "bounded_replay_rejected", None, None, None)
                }
                Applicability::Required => match providers.evaluate(definition.provider_id, bundle)
                {
                    ProviderOutcome::Passed {
                        provider_name,
                        provider_version,
                        ruleset_id,
                        ruleset_version,
                        ruleset_sha256,
                    } => (
                        "passed",
                        "validated",
                        Some(provider_name.to_owned()),
                        Some(provider_version.to_owned()),
                        _subject_bundle_hash.map(|bundle_hash| NativeProviderEvidence {
                            ruleset_id: ruleset_id.to_owned(),
                            ruleset_version: ruleset_version.to_owned(),
                            ruleset_sha256: ruleset_sha256.to_owned(),
                            subject_bundle_hash: bundle_hash.to_owned(),
                        }),
                    ),
                    ProviderOutcome::Failed {
                        provider_name,
                        provider_version,
                        ruleset_id,
                        ruleset_version,
                        ruleset_sha256,
                    } => (
                        "failed",
                        "provider_rejected",
                        Some(provider_name.to_owned()),
                        Some(provider_version.to_owned()),
                        _subject_bundle_hash.map(|bundle_hash| NativeProviderEvidence {
                            ruleset_id: ruleset_id.to_owned(),
                            ruleset_version: ruleset_version.to_owned(),
                            ruleset_sha256: ruleset_sha256.to_owned(),
                            subject_bundle_hash: bundle_hash.to_owned(),
                        }),
                    ),
                    ProviderOutcome::Unavailable {
                        reason,
                        provider_name,
                        provider_version,
                    } => (
                        "unavailable",
                        reason,
                        provider_name.map(str::to_owned),
                        provider_version.map(str::to_owned),
                        None,
                    ),
                },
            };
            let (status, reason, provider_name, provider_version, evidence) =
                if matches!(status, "passed" | "failed") && evidence.is_none() {
                    (
                        "unavailable",
                        "provider_error",
                        provider_name,
                        provider_version,
                        None,
                    )
                } else {
                    (status, reason, provider_name, provider_version, evidence)
                };
            NativeProviderCoverage {
                provider_id: definition.provider_id.to_owned(),
                object_profile: definition.object_profile.to_owned(),
                applicability: applicability.as_str().to_owned(),
                status: status.to_owned(),
                reason: reason.to_owned(),
                provider_name,
                provider_version,
                evidence,
            }
        })
        .collect()
}

fn within_node_budget(value: &Value, remaining: &mut usize) -> bool {
    if *remaining == 0 {
        return false;
    }
    *remaining -= 1;
    match value {
        Value::Array(values) => values
            .iter()
            .all(|value| within_node_budget(value, remaining)),
        Value::Object(object) => object
            .values()
            .all(|value| within_node_budget(value, remaining)),
        _ => true,
    }
}

fn supplemental_surface_lint(bundle: &Value) -> SupplementalCoverage {
    let Some(surface) = bundle.pointer("/context/surface") else {
        return SupplementalCoverage {
            check_id: "surface_manifest_lint".to_owned(),
            status: "error".to_owned(),
            reason: "tool_error".to_owned(),
            tool_name: asp_manifest_linter::TOOL_NAME.to_owned(),
            tool_version: asp_manifest_linter::TOOL_VERSION.to_owned(),
            ruleset_id: None,
            ruleset_version: None,
            errors: 0,
            warnings: 0,
        };
    };
    let mut remaining = MAX_SUPPLEMENTAL_LINT_NODES;
    if !within_node_budget(surface, &mut remaining) {
        return SupplementalCoverage {
            check_id: "surface_manifest_lint".to_owned(),
            status: "not_evaluated".to_owned(),
            reason: "resource_limit".to_owned(),
            tool_name: asp_manifest_linter::TOOL_NAME.to_owned(),
            tool_version: asp_manifest_linter::TOOL_VERSION.to_owned(),
            ruleset_id: None,
            ruleset_version: None,
            errors: 0,
            warnings: 0,
        };
    }
    let result = lint_manifest_value("<embedded-surface>", surface).map_err(|_| ());
    match result {
        Ok(report) => SupplementalCoverage {
            check_id: "surface_manifest_lint".to_owned(),
            status: if report.summary.errors == 0 && report.summary.warnings == 0 {
                "pass"
            } else {
                "findings"
            }
            .to_owned(),
            reason: "evaluated".to_owned(),
            tool_name: report.tool.name,
            tool_version: report.tool.version,
            ruleset_id: Some(report.tool.ruleset_id),
            ruleset_version: Some(report.tool.ruleset_version),
            errors: report.summary.errors,
            warnings: report.summary.warnings,
        },
        Err(()) => SupplementalCoverage {
            check_id: "surface_manifest_lint".to_owned(),
            status: "error".to_owned(),
            reason: "tool_error".to_owned(),
            tool_name: asp_manifest_linter::TOOL_NAME.to_owned(),
            tool_version: asp_manifest_linter::TOOL_VERSION.to_owned(),
            ruleset_id: None,
            ruleset_version: None,
            errors: 0,
            warnings: 0,
        },
    }
}

fn unevaluated_surface_lint() -> SupplementalCoverage {
    SupplementalCoverage {
        check_id: "surface_manifest_lint".to_owned(),
        status: "not_evaluated".to_owned(),
        reason: "bounded_replay_rejected".to_owned(),
        tool_name: asp_manifest_linter::TOOL_NAME.to_owned(),
        tool_version: asp_manifest_linter::TOOL_VERSION.to_owned(),
        ruleset_id: None,
        ruleset_version: None,
        errors: 0,
        warnings: 0,
    }
}

fn compose_with_providers(
    source: &str,
    document: &[u8],
    providers: &impl NativeProviderSet,
) -> Result<CompositionReport, ReplayError> {
    let bounded = verify(source, document)?;
    let bundle = parse_strict(document)?;
    let bounded_rejected = bounded.verdict == "invalid";
    let provider_results = provider_coverage(
        providers,
        &bundle,
        !bounded_rejected,
        bounded.input.bundle_hash.as_deref(),
    );
    let facts = CompositionFacts {
        bounded_verdict: &bounded.verdict,
        required_failed: provider_results
            .iter()
            .filter(|provider| provider.applicability == "required" && provider.status == "failed")
            .count(),
        required_unavailable: provider_results
            .iter()
            .filter(|provider| {
                provider.applicability == "required" && provider.status == "unavailable"
            })
            .count(),
    };
    let state = decide_composition(&facts);
    let mut report = CompositionReport {
        schema: "./composition-report.schema.json".to_owned(),
        schema_version: 1,
        report_profile: crate::COMPOSITION_REPORT_PROFILE.to_owned(),
        claim_effect: "descriptive_only".to_owned(),
        tool: CompositionTool {
            name: TOOL_NAME.to_owned(),
            version: TOOL_VERSION.to_owned(),
            policy_profile: crate::COMPOSITION_POLICY_PROFILE.to_owned(),
            policy_version: COMPOSITION_POLICY_VERSION.to_owned(),
        },
        input: CompositionInput {
            source_sha256: bounded.input.source_sha256.clone(),
            bundle_id: bounded.input.bundle_id.clone(),
            bundle_hash: bounded.input.bundle_hash.clone(),
        },
        bounded_replay: BoundedReplayCoverage {
            report_hash: bounded.report_hash.clone(),
            evaluation_state: bounded.evaluation_state.clone(),
            integrity_verdict: bounded.integrity_verdict.clone(),
            replay_completeness: bounded.replay_completeness.clone(),
            bounded_verdict: bounded.verdict.clone(),
        },
        composition_state: state.as_str().to_owned(),
        complete_claim_eligible: state.complete_claim_eligible(),
        providers: provider_results,
        supplemental_checks: vec![if bounded_rejected {
            unevaluated_surface_lint()
        } else {
            supplemental_surface_lint(&bundle)
        }],
        report_hash: String::new(),
    };
    let value =
        serde_json::to_value(&report).map_err(|error| ReplayError::Canonical(error.to_string()))?;
    report.report_hash = object_hash(COMPOSITION_REPORT_DOMAIN, &value, &["report_hash"])?;
    Ok(report)
}

/// Compose bounded replay with the statically linked native-profile providers.
///
/// The built-in provider set is intentionally fail-closed. Until an
/// authoritative native provider exists for every applicable profile, this
/// function emits a `blocked` coverage report rather than a complete-profile
/// conformance verdict.
pub fn compose(source: &str, document: &[u8]) -> Result<CompositionReport, ReplayError> {
    compose_with_providers(source, document, &BuiltInProviders)
}

fn composition_schema_validator() -> Result<&'static jsonschema::Validator, ReplayError> {
    COMPOSITION_SCHEMA_VALIDATOR
        .get_or_init(|| {
            let schema: Value = serde_json::from_str(crate::COMPOSITION_REPORT_SCHEMA)
                .map_err(|error| error.to_string())?;
            jsonschema::draft202012::options()
                .should_validate_formats(true)
                .build(&schema)
                .map_err(|error| error.to_string())
        })
        .as_ref()
        .map_err(|error| ReplayError::Composition(format!("report schema: {error}")))
}

/// Validate one composition report against the exact replay bundle it describes.
///
/// This validates the report schema and digest, re-runs bounded replay for the
/// supplied bytes, derives native-provider applicability from that bundle, and
/// checks every evaluated provider's subject binding. It does not establish
/// trust in a provider or its ruleset; callers must make that authority decision
/// separately.
pub fn validate_composition_report(
    document: &[u8],
    report: &CompositionReport,
) -> Result<(), ReplayError> {
    let value =
        serde_json::to_value(report).map_err(|error| ReplayError::Canonical(error.to_string()))?;
    if let Some(error) = composition_schema_validator()?.iter_errors(&value).next() {
        return Err(ReplayError::Composition(format!(
            "report schema rejected {}",
            error.instance_path()
        )));
    }
    let expected_hash = object_hash(COMPOSITION_REPORT_DOMAIN, &value, &["report_hash"])?;
    if report.report_hash != expected_hash {
        return Err(ReplayError::Composition(
            "report_hash does not match the report body".to_owned(),
        ));
    }

    let bounded = verify("<composition-report-validation>", document)?;
    let expected_input = CompositionInput {
        source_sha256: bounded.input.source_sha256.clone(),
        bundle_id: bounded.input.bundle_id.clone(),
        bundle_hash: bounded.input.bundle_hash.clone(),
    };
    if report.input != expected_input {
        return Err(ReplayError::Composition(
            "input identity does not match the supplied bundle".to_owned(),
        ));
    }
    let expected_bounded = BoundedReplayCoverage {
        report_hash: bounded.report_hash.clone(),
        evaluation_state: bounded.evaluation_state.clone(),
        integrity_verdict: bounded.integrity_verdict.clone(),
        replay_completeness: bounded.replay_completeness.clone(),
        bounded_verdict: bounded.verdict.clone(),
    };
    if report.bounded_replay != expected_bounded {
        return Err(ReplayError::Composition(
            "bounded replay coverage does not match the supplied bundle".to_owned(),
        ));
    }

    let bundle = parse_strict(document)?;
    for (definition, coverage) in PROVIDERS.iter().zip(&report.providers) {
        let expected_applicability = applicability(definition.provider_id, &bundle).as_str();
        if coverage.provider_id != definition.provider_id
            || coverage.object_profile != definition.object_profile
            || coverage.applicability != expected_applicability
        {
            return Err(ReplayError::Composition(format!(
                "provider coverage does not match derived applicability for {}",
                definition.provider_id
            )));
        }
        match coverage.status.as_str() {
            "passed" | "failed" => {
                let Some(evidence) = coverage.evidence.as_ref() else {
                    return Err(ReplayError::Composition(format!(
                        "{} is missing provider evidence",
                        definition.provider_id
                    )));
                };
                if Some(evidence.subject_bundle_hash.as_str())
                    != report.input.bundle_hash.as_deref()
                {
                    return Err(ReplayError::Composition(format!(
                        "{} evidence is bound to a different bundle",
                        definition.provider_id
                    )));
                }
            }
            _ if coverage.evidence.is_some() => {
                return Err(ReplayError::Composition(format!(
                    "{} carries evidence without an evaluated result",
                    definition.provider_id
                )));
            }
            _ => {}
        }
    }

    let facts = CompositionFacts {
        bounded_verdict: &report.bounded_replay.bounded_verdict,
        required_failed: report
            .providers
            .iter()
            .filter(|provider| provider.applicability == "required" && provider.status == "failed")
            .count(),
        required_unavailable: report
            .providers
            .iter()
            .filter(|provider| {
                provider.applicability == "required" && provider.status == "unavailable"
            })
            .count(),
    };
    let expected_state = decide_composition(&facts);
    if report.composition_state != expected_state.as_str()
        || report.complete_claim_eligible != expected_state.complete_claim_eligible()
    {
        return Err(ReplayError::Composition(
            "composition decision does not match bounded and provider coverage".to_owned(),
        ));
    }
    Ok(())
}

#[cfg(any(test, fuzzing))]
struct SyntheticProviders<'a> {
    outcomes: &'a [u8; PROVIDERS.len()],
}

#[cfg(any(test, fuzzing))]
impl NativeProviderSet for SyntheticProviders<'_> {
    fn evaluate(&self, provider_id: &str, _bundle: &Value) -> ProviderOutcome {
        let Some(index) = PROVIDERS
            .iter()
            .position(|definition| definition.provider_id == provider_id)
        else {
            return ProviderOutcome::Unavailable {
                reason: "provider_error",
                provider_name: Some("fuzz-native-provider"),
                provider_version: Some("1.0.0"),
            };
        };
        match self.outcomes[index] % 3 {
            0 => ProviderOutcome::Passed {
                provider_name: "fuzz-native-provider",
                provider_version: "1.0.0",
                ruleset_id: "fuzz-native-ruleset",
                ruleset_version: "1.0.0",
                ruleset_sha256: "sha-256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            },
            1 => ProviderOutcome::Failed {
                provider_name: "fuzz-native-provider",
                provider_version: "1.0.0",
                ruleset_id: "fuzz-native-ruleset",
                ruleset_version: "1.0.0",
                ruleset_sha256: "sha-256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            },
            _ => ProviderOutcome::Unavailable {
                reason: "provider_error",
                provider_name: Some("fuzz-native-provider"),
                provider_version: Some("1.0.0"),
            },
        }
    }
}

#[cfg(any(test, fuzzing))]
pub(crate) fn compose_with_provider_plan(
    source: &str,
    document: &[u8],
    outcomes: &[u8; PROVIDERS.len()],
) -> Result<CompositionReport, ReplayError> {
    compose_with_providers(source, document, &SyntheticProviders { outcomes })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::COMPOSITION_REPORT_SCHEMA;

    const COMPLETE_SESSION: &[u8] = include_bytes!("../tests/fixtures/complete-session.json");
    const EVENT_RECEIPT_FLOW: &[u8] = include_bytes!("../tests/fixtures/event-receipt-flow.json");
    const INVALID: &[u8] = include_bytes!("../tests/fixtures/invalid-empty.json");
    const TEST_RULESET_DIGEST: &str = "sha-256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";

    fn passed_outcome() -> ProviderOutcome {
        ProviderOutcome::Passed {
            provider_name: "test-authoritative-provider",
            provider_version: "1.0.0",
            ruleset_id: "test-ruleset",
            ruleset_version: "1.0.0",
            ruleset_sha256: TEST_RULESET_DIGEST,
        }
    }

    struct PassingProviders;

    impl NativeProviderSet for PassingProviders {
        fn evaluate(&self, _provider_id: &str, _bundle: &Value) -> ProviderOutcome {
            passed_outcome()
        }
    }

    struct FailingSurfaceProvider;

    impl NativeProviderSet for FailingSurfaceProvider {
        fn evaluate(&self, provider_id: &str, _bundle: &Value) -> ProviderOutcome {
            if provider_id == NATIVE_SURFACE {
                ProviderOutcome::Failed {
                    provider_name: "test-authoritative-provider",
                    provider_version: "1.0.0",
                    ruleset_id: "test-ruleset",
                    ruleset_version: "1.0.0",
                    ruleset_sha256: TEST_RULESET_DIGEST,
                }
            } else {
                passed_outcome()
            }
        }
    }

    struct ErroringSurfaceProvider;

    impl NativeProviderSet for ErroringSurfaceProvider {
        fn evaluate(&self, provider_id: &str, _bundle: &Value) -> ProviderOutcome {
            if provider_id == NATIVE_SURFACE {
                ProviderOutcome::Unavailable {
                    reason: "provider_error",
                    provider_name: Some("test-authoritative-provider"),
                    provider_version: Some("1.0.0"),
                }
            } else {
                passed_outcome()
            }
        }
    }

    fn validate_report_schema(report: &CompositionReport) {
        let schema: Value =
            serde_json::from_str(COMPOSITION_REPORT_SCHEMA).expect("composition report schema");
        let validator = jsonschema::validator_for(&schema).expect("compiled report schema");
        let value = serde_json::to_value(report).expect("composition report value");
        let errors = validator
            .iter_errors(&value)
            .map(|error| error.to_string())
            .collect::<Vec<_>>();
        assert!(errors.is_empty(), "schema errors: {errors:?}");
    }

    fn assert_report_contract(document: &[u8], report: &CompositionReport) {
        validate_report_schema(report);
        let value = serde_json::to_value(report).expect("composition report value");
        assert_eq!(
            object_hash(COMPOSITION_REPORT_DOMAIN, &value, &["report_hash"])
                .expect("composition report hash"),
            report.report_hash
        );
        validate_composition_report(document, report).expect("bound composition report");
    }

    fn schema_rejects(value: &Value) -> bool {
        let schema: Value =
            serde_json::from_str(COMPOSITION_REPORT_SCHEMA).expect("composition report schema");
        !jsonschema::validator_for(&schema)
            .expect("compiled report schema")
            .is_valid(value)
    }

    fn refresh_report_hash(report: &mut CompositionReport) {
        report.report_hash.clear();
        let value = serde_json::to_value(&*report).expect("composition report value");
        report.report_hash = object_hash(COMPOSITION_REPORT_DOMAIN, &value, &["report_hash"])
            .expect("composition report hash");
    }

    #[test]
    fn built_in_composition_is_deterministic_blocked_and_schema_valid() {
        let first = compose("<test>", COMPLETE_SESSION).expect("composition report");
        let second = compose("<different-source>", COMPLETE_SESSION).expect("composition report");

        assert_eq!(first, second);
        assert_eq!(first.composition_state, "blocked");
        assert!(!first.complete_claim_eligible);
        assert_eq!(first.providers.len(), PROVIDERS.len());
        assert_eq!(first.providers[0].provider_id, NATIVE_SURFACE);
        assert_eq!(first.providers[0].status, "passed");
        assert_eq!(
            first.providers[0].provider_name.as_deref(),
            Some(surface_provider::PROVIDER_NAME)
        );
        assert!(first.providers[0].evidence.is_some());
        assert_eq!(first.providers[1].provider_id, NATIVE_GRANT);
        assert!(
            first
                .providers
                .iter()
                .skip(1)
                .filter(|provider| provider.applicability == "required")
                .all(|provider| provider.status == "unavailable")
        );
        let value = serde_json::to_value(&first).expect("composition report value");
        assert!(value.get("verdict").is_none());
        assert_report_contract(COMPLETE_SESSION, &first);
    }

    #[test]
    fn composition_schema_rejects_claim_upgrades_and_unknown_verdicts() {
        let report = compose("<test>", COMPLETE_SESSION).expect("composition report");
        let mut value = serde_json::to_value(report).expect("composition report value");

        value["complete_claim_eligible"] = Value::Bool(true);
        assert!(schema_rejects(&value));

        value["complete_claim_eligible"] = Value::Bool(false);
        value["composition_state"] = Value::String("eligible_valid".to_owned());
        assert!(schema_rejects(&value));

        value["composition_state"] = Value::String("blocked".to_owned());
        value["verdict"] = Value::String("valid".to_owned());
        assert!(schema_rejects(&value));

        value
            .as_object_mut()
            .expect("report object")
            .remove("verdict");
        value["input"]["bundle_id"] = Value::Null;
        value["input"]["bundle_hash"] = Value::Null;
        assert!(schema_rejects(&value));
    }

    #[test]
    fn composition_schema_closes_provider_and_supplemental_lifecycles() {
        let valid = compose("<test>", COMPLETE_SESSION).expect("valid bounded composition");
        let mut value = serde_json::to_value(valid).expect("composition report value");

        value["providers"][0]["status"] = Value::String("not_evaluated".to_owned());
        value["providers"][0]["reason"] = Value::String("bounded_replay_rejected".to_owned());
        value["providers"][0]["provider_name"] = Value::Null;
        value["providers"][0]["provider_version"] = Value::Null;
        value["providers"][0]["evidence"] = Value::Null;
        assert!(schema_rejects(&value));

        let valid = compose("<test>", COMPLETE_SESSION).expect("valid bounded composition");
        let mut value = serde_json::to_value(valid).expect("composition report value");
        value["supplemental_checks"][0]["status"] = Value::String("not_evaluated".to_owned());
        value["supplemental_checks"][0]["reason"] =
            Value::String("bounded_replay_rejected".to_owned());
        value["supplemental_checks"][0]["ruleset_id"] = Value::Null;
        value["supplemental_checks"][0]["ruleset_version"] = Value::Null;
        value["supplemental_checks"][0]["errors"] = Value::from(0);
        value["supplemental_checks"][0]["warnings"] = Value::from(0);
        assert!(schema_rejects(&value));

        let rejected = compose("<test>", INVALID).expect("bounded rejection report");
        let mut value = serde_json::to_value(rejected).expect("composition report value");
        value["providers"][0]["status"] = Value::String("passed".to_owned());
        value["providers"][0]["reason"] = Value::String("validated".to_owned());
        value["providers"][0]["provider_name"] =
            Value::String("test-authoritative-provider".to_owned());
        value["providers"][0]["provider_version"] = Value::String("1.0.0".to_owned());
        value["providers"][0]["evidence"] = serde_json::json!({
            "ruleset_id": "test-ruleset",
            "ruleset_version": "1.0.0",
            "ruleset_sha256": TEST_RULESET_DIGEST,
            "subject_bundle_hash": TEST_RULESET_DIGEST
        });
        assert!(schema_rejects(&value));

        let rejected = compose("<test>", INVALID).expect("bounded rejection report");
        let mut value = serde_json::to_value(rejected).expect("composition report value");
        value["supplemental_checks"][0]["status"] = Value::String("pass".to_owned());
        value["supplemental_checks"][0]["reason"] = Value::String("evaluated".to_owned());
        value["supplemental_checks"][0]["ruleset_id"] = Value::String("test-ruleset".to_owned());
        value["supplemental_checks"][0]["ruleset_version"] = Value::String("1.0.0".to_owned());
        assert!(schema_rejects(&value));
    }

    #[test]
    fn bound_validator_rejects_cross_bundle_evidence_and_derived_applicability_drift() {
        let mut wrong_subject =
            compose_with_providers("<test>", COMPLETE_SESSION, &PassingProviders)
                .expect("eligible composition");
        wrong_subject.providers[0]
            .evidence
            .as_mut()
            .expect("provider evidence")
            .subject_bundle_hash = "sha-256:EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE".to_owned();
        refresh_report_hash(&mut wrong_subject);
        validate_report_schema(&wrong_subject);
        let error = validate_composition_report(COMPLETE_SESSION, &wrong_subject)
            .expect_err("cross-bundle evidence must fail");
        assert!(
            matches!(error, ReplayError::Composition(message) if message.contains("different bundle"))
        );

        let mut wrong_applicability =
            compose_with_providers("<test>", EVENT_RECEIPT_FLOW, &PassingProviders)
                .expect("eligible event composition");
        let event = wrong_applicability
            .providers
            .iter_mut()
            .find(|provider| provider.provider_id == NATIVE_CLOUDEVENT)
            .expect("CloudEvent provider");
        event.applicability = "not_applicable".to_owned();
        event.status = "not_applicable".to_owned();
        event.reason = "not_applicable".to_owned();
        event.provider_name = None;
        event.provider_version = None;
        event.evidence = None;
        refresh_report_hash(&mut wrong_applicability);
        validate_report_schema(&wrong_applicability);
        let error = validate_composition_report(EVENT_RECEIPT_FLOW, &wrong_applicability)
            .expect_err("derived applicability drift must fail");
        assert!(
            matches!(error, ReplayError::Composition(message) if message.contains("derived applicability"))
        );
    }

    #[test]
    fn complete_native_coverage_enables_only_bounded_outcome() {
        let valid = compose_with_providers("<test>", COMPLETE_SESSION, &PassingProviders)
            .expect("valid composition");
        assert_eq!(valid.composition_state, "eligible_valid");
        assert!(valid.complete_claim_eligible);
        assert_report_contract(COMPLETE_SESSION, &valid);
        let bundle_hash = valid
            .input
            .bundle_hash
            .as_deref()
            .expect("evaluated bundle hash");
        assert!(
            valid
                .providers
                .iter()
                .filter(|provider| provider.applicability == "required")
                .all(|provider| provider
                    .evidence
                    .as_ref()
                    .is_some_and(|evidence| evidence.subject_bundle_hash == bundle_hash))
        );
        let mut missing_evidence =
            serde_json::to_value(&valid).expect("eligible composition report value");
        missing_evidence["providers"][0]["evidence"] = Value::Null;
        assert!(schema_rejects(&missing_evidence));

        let mut partial: Value = serde_json::from_slice(COMPLETE_SESSION).expect("valid fixture");
        partial["capture"]["completeness"] = Value::String("partial".to_owned());
        partial["records"]
            .as_array_mut()
            .expect("records")
            .push(serde_json::json!({
                "ordinal": 2,
                "record_id": "capture-gap",
                "recorded_at": "2026-06-24T12:02:00Z",
                "kind": "capture_gap",
                "name": "capture.gap",
                "representation": "exact",
                "elisions": [],
                "body": {
                    "reason": "not_captured",
                    "started_at": "2026-06-24T12:01:30Z",
                    "ended_at": "2026-06-24T12:01:45Z"
                },
                "previous_record_hash": "sha-256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                "record_hash": "sha-256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            }));
        crate::rehash::rehash_bundle(&mut partial).expect("rehash partial fixture");
        let bytes = serde_json::to_vec(&partial).expect("partial fixture bytes");
        let incomplete = compose_with_providers("<test>", &bytes, &PassingProviders)
            .expect("incomplete composition");
        assert_eq!(incomplete.composition_state, "eligible_incomplete");
        assert!(incomplete.complete_claim_eligible);
        assert_report_contract(&bytes, &incomplete);
    }

    #[test]
    fn bounded_or_native_failure_rejects_before_unavailable_coverage() {
        let bounded = compose("<test>", INVALID).expect("bounded rejection report");
        assert_eq!(bounded.composition_state, "rejected");
        assert!(
            bounded
                .providers
                .iter()
                .filter(|provider| provider.applicability == "required")
                .all(|provider| provider.status == "not_evaluated")
        );
        assert_eq!(bounded.supplemental_checks[0].status, "not_evaluated");
        assert_eq!(
            bounded.supplemental_checks[0].reason,
            "bounded_replay_rejected"
        );
        assert_report_contract(INVALID, &bounded);

        let native = compose_with_providers("<test>", COMPLETE_SESSION, &FailingSurfaceProvider)
            .expect("native rejection report");
        assert_eq!(native.composition_state, "rejected");
        assert!(!native.complete_claim_eligible);
        assert_report_contract(COMPLETE_SESSION, &native);
    }

    #[test]
    fn provider_error_is_unavailable_and_blocks() {
        let report = compose_with_providers("<test>", COMPLETE_SESSION, &ErroringSurfaceProvider)
            .expect("blocked report");
        assert_eq!(report.composition_state, "blocked");
        let surface = report
            .providers
            .iter()
            .find(|provider| provider.provider_id == NATIVE_SURFACE)
            .expect("surface provider");
        assert_eq!(surface.status, "unavailable");
        assert_eq!(surface.reason, "provider_error");
        assert!(surface.evidence.is_none());
        assert_report_contract(COMPLETE_SESSION, &report);
    }

    #[test]
    fn supplemental_lint_stops_before_unbounded_diagnostic_amplification() {
        let mut bundle: Value =
            serde_json::from_slice(COMPLETE_SESSION).expect("valid replay fixture");
        bundle["context"]["surface"]["actions"] = Value::Array(
            (0..MAX_SUPPLEMENTAL_LINT_NODES)
                .map(|_| serde_json::json!({}))
                .collect(),
        );
        crate::rehash::rehash_bundle(&mut bundle).expect("rehash bounded fixture");
        let document = serde_json::to_vec(&bundle).expect("serialize bounded fixture");

        let report = compose("<test>", &document).expect("bounded composition report");

        assert_eq!(report.bounded_replay.bounded_verdict, "valid");
        assert_eq!(report.composition_state, "blocked");
        assert_eq!(report.supplemental_checks[0].status, "not_evaluated");
        assert_eq!(report.supplemental_checks[0].reason, "resource_limit");
        assert_report_contract(&document, &report);
    }

    #[test]
    fn applicability_tracks_only_carried_native_objects() {
        let session = compose("<test>", COMPLETE_SESSION).expect("session composition");
        assert_eq!(
            session
                .providers
                .iter()
                .filter(|provider| provider.applicability == "required")
                .map(|provider| provider.provider_id.as_str())
                .collect::<Vec<_>>(),
            vec![NATIVE_SURFACE, NATIVE_GRANT]
        );

        let flow = compose("<test>", EVENT_RECEIPT_FLOW).expect("event composition");
        let required = flow
            .providers
            .iter()
            .filter(|provider| provider.applicability == "required")
            .map(|provider| provider.provider_id.as_str())
            .collect::<Vec<_>>();
        assert!(required.contains(&NATIVE_CLOUDEVENT));
        assert!(required.contains(&NATIVE_EVENT_ACK));
        assert!(required.contains(&NATIVE_RECEIPT));
        assert!(!required.contains(&NATIVE_RECEIPT_SIGNATURE));
    }

    #[test]
    fn decision_policy_is_total_and_ordered() {
        let cases = [
            (
                CompositionFacts {
                    bounded_verdict: "invalid",
                    required_failed: 0,
                    required_unavailable: 1,
                },
                CompositionState::Rejected,
            ),
            (
                CompositionFacts {
                    bounded_verdict: "valid",
                    required_failed: 1,
                    required_unavailable: 1,
                },
                CompositionState::Rejected,
            ),
            (
                CompositionFacts {
                    bounded_verdict: "valid",
                    required_failed: 0,
                    required_unavailable: 1,
                },
                CompositionState::Blocked,
            ),
            (
                CompositionFacts {
                    bounded_verdict: "incomplete",
                    required_failed: 0,
                    required_unavailable: 0,
                },
                CompositionState::EligibleIncomplete,
            ),
            (
                CompositionFacts {
                    bounded_verdict: "valid",
                    required_failed: 0,
                    required_unavailable: 0,
                },
                CompositionState::EligibleValid,
            ),
            (
                CompositionFacts {
                    bounded_verdict: "unexpected",
                    required_failed: 0,
                    required_unavailable: 0,
                },
                CompositionState::Blocked,
            ),
        ];
        for (facts, expected) in cases {
            assert_eq!(decide_composition(&facts), expected);
        }
    }
}
