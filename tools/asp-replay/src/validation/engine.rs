use std::collections::HashMap;

use crate::hash::{
    BUNDLE_DOMAIN, REPORT_DOMAIN, object_hash, raw_sha256, valid_bundle_id, valid_digest,
};
use crate::registry::registry;
use crate::strict_json::parse_strict;
use crate::value::{member, string, timestamp_shape};
use crate::{
    Assurance, CHECK_REGISTRY, CheckResult, PROFILE, REPORT_PROFILE, ReplayError, ReplaySummary,
    Report, ReportInput, ReportTool, TOOL_NAME, TOOL_VERSION,
};

use super::context::check_context;
use super::records::{validate_record_integrity, validate_records};
use super::schema::validate_schema;
use super::secrets::scan_secrets;
use super::state::Validator;

fn report_hash(report: &Report) -> Result<String, ReplayError> {
    let value =
        serde_json::to_value(report).map_err(|error| ReplayError::Canonical(error.to_string()))?;
    object_hash(REPORT_DOMAIN, &value, &["report_hash"])
}

/// Verify one exact replay bundle and produce a deterministic, payload-minimized report.
pub(crate) fn verify_document(_source: &str, document: &[u8]) -> Result<Report, ReplayError> {
    let bundle = parse_strict(document)?;
    let capture_partial = member(&bundle, "capture")
        .and_then(|capture| string(capture, "completeness"))
        == Some("partial");
    let mut validator = Validator::new(capture_partial);
    validate_schema(&bundle, &mut validator)?;

    if string(&bundle, "profile") != Some(PROFILE)
        || string(&bundle, "protocol_version") != Some("agent-surface/0.1")
        || string(&bundle, "claim_effect") != Some("descriptive_only")
        || string(&bundle, "created_at").is_none_or(|time| !timestamp_shape(time))
    {
        validator.error(
            "ASP-REPLAY-SCHEMA-001",
            0,
            "",
            "bundle profile metadata is not canonical",
        );
    }
    if let Some(capture) = member(&bundle, "capture") {
        for member_name in ["started_at", "ended_at"] {
            if string(capture, member_name).is_none_or(|time| !timestamp_shape(time)) {
                validator.error(
                    "ASP-REPLAY-SCHEMA-001",
                    0,
                    format!("/capture/{member_name}"),
                    "capture timestamp is not a real supported RFC 3339 UTC instant",
                );
            }
        }
    }
    if let Some(expected) = string(&bundle, "bundle_hash") {
        if !valid_digest(expected) {
            validator.error(
                "ASP-REPLAY-CONTEXT-001",
                0,
                "/bundle_hash",
                "bundle hash is not a canonical SHA-256 value",
            );
        } else {
            let actual = object_hash(BUNDLE_DOMAIN, &bundle, &["bundle_hash"])?;
            if expected != actual {
                validator.error(
                    "ASP-REPLAY-CONTEXT-001",
                    0,
                    "/bundle_hash",
                    "bundle hash does not match the exact bundle",
                );
            }
        }
    }
    check_context(&bundle, &mut validator)?;
    scan_secrets(&bundle, "", 0, &mut validator);
    validate_record_integrity(&bundle, &mut validator)?;
    let preflight_failed = validator.has_errors;
    if !preflight_failed {
        validate_records(&bundle, &mut validator)?;
    }

    let check_registry = registry()?;
    let order: HashMap<&str, usize> = check_registry
        .checks
        .iter()
        .enumerate()
        .map(|(index, check)| (check.check_id.as_str(), index))
        .collect();
    validator.diagnostics.sort_by(|left, right| {
        (
            left.ordinal,
            order
                .get(left.check_id.as_str())
                .copied()
                .unwrap_or(usize::MAX),
            left.path.as_str(),
            left.message.as_str(),
        )
            .cmp(&(
                right.ordinal,
                order
                    .get(right.check_id.as_str())
                    .copied()
                    .unwrap_or(usize::MAX),
                right.path.as_str(),
                right.message.as_str(),
            ))
    });
    let has_errors = validator.has_errors;
    let evaluation_state = if preflight_failed {
        "preflight_failed"
    } else if has_errors {
        "semantic_invalid"
    } else if validator.incomplete {
        "incomplete"
    } else {
        "valid"
    };
    let integrity_verdict = if has_errors { "invalid" } else { "valid" };
    let replay_completeness = if has_errors {
        "not_evaluated"
    } else if validator.incomplete {
        "incomplete"
    } else {
        "complete"
    };
    let verdict = if has_errors {
        "invalid"
    } else if validator.incomplete {
        "incomplete"
    } else {
        "valid"
    };
    let checks = check_registry
        .checks
        .iter()
        .map(|definition| {
            let summary = validator
                .finding_summaries
                .get(&definition.check_id)
                .cloned()
                .unwrap_or_default();
            let semantic = ![
                "ASP-REPLAY-SCHEMA-001",
                "ASP-REPLAY-CONTEXT-001",
                "ASP-REPLAY-ORDER-001",
                "ASP-REPLAY-SECRETS-001",
            ]
            .contains(&definition.check_id.as_str());
            let status = if preflight_failed && semantic {
                "not_evaluated"
            } else if summary.errors > 0 {
                "fail"
            } else if summary.incomplete > 0 {
                "incomplete"
            } else {
                "pass"
            };
            CheckResult {
                check_id: definition.check_id.clone(),
                title: definition.title.clone(),
                status: status.to_owned(),
                findings: summary.errors + summary.incomplete,
            }
        })
        .collect::<Vec<_>>();
    let check_passes = |check_id: &str| {
        checks
            .iter()
            .find(|check| check.check_id == check_id)
            .is_some_and(|check| check.status == "pass")
    };
    let mut verified = Vec::new();
    if !has_errors {
        if [
            "ASP-REPLAY-SCHEMA-001",
            "ASP-REPLAY-ORDER-001",
            "ASP-REPLAY-RECEIPT-HASH-001",
        ]
        .iter()
        .all(|check| check_passes(check))
        {
            verified.push("canonical_integrity".to_owned());
        }
        if check_passes("ASP-REPLAY-CONTEXT-001") {
            verified.push("historical_context_consistency".to_owned());
        }
        if ["ASP-REPLAY-SESSION-001", "ASP-REPLAY-GAP-001"]
            .iter()
            .all(|check| check_passes(check))
        {
            verified.push("recorded_lifecycle".to_owned());
        }
        if [
            "ASP-REPLAY-EVENT-001",
            "ASP-REPLAY-DELIVERY-001",
            "ASP-REPLAY-ACK-001",
            "ASP-REPLAY-GAP-001",
            "ASP-REPLAY-RECEIPT-CHAIN-001",
            "ASP-REPLAY-RECEIPT-LINK-001",
        ]
        .iter()
        .all(|check| check_passes(check))
        {
            verified.push("recorded_linkage".to_owned());
        }
    }
    let heads = validator
        .receipt_hashes
        .iter()
        .filter(|hash| !validator.receipt_parents.contains(*hash))
        .count();
    let source_hash = raw_sha256(document);
    let bundle_id = string(&bundle, "bundle_id")
        .filter(|value| valid_bundle_id(value))
        .map(str::to_owned);
    let bundle_hash = string(&bundle, "bundle_hash")
        .filter(|value| valid_digest(value))
        .map(str::to_owned);
    let replay = if has_errors {
        ReplaySummary {
            status: "not_evaluated".to_owned(),
            final_session_state: "unknown".to_owned(),
            session_generation: 0,
            session_transitions: 0,
            event_occurrences: 0,
            event_deliveries: 0,
            event_attempts: 0,
            event_acknowledgements: 0,
            event_gaps: 0,
            capture_gaps: 0,
            receipts: 0,
            receipt_roots: 0,
            receipt_heads: 0,
        }
    } else {
        ReplaySummary {
            status: "evaluated".to_owned(),
            final_session_state: validator.session_state,
            session_generation: validator.session_generation,
            session_transitions: validator.session_transitions,
            event_occurrences: validator.occurrence_hashes.len(),
            event_deliveries: validator.deliveries.len(),
            event_attempts: validator.event_attempts,
            event_acknowledgements: validator.event_acknowledgements,
            event_gaps: validator.event_gaps,
            capture_gaps: validator.capture_gaps,
            receipts: validator.receipt_hashes.len(),
            receipt_roots: validator.receipt_roots.len(),
            receipt_heads: heads,
        }
    };
    let mut report = Report {
        schema: "./report.schema.json".to_owned(),
        schema_version: 1,
        report_profile: REPORT_PROFILE.to_owned(),
        claim_effect: "descriptive_only".to_owned(),
        tool: ReportTool {
            name: TOOL_NAME.to_owned(),
            version: TOOL_VERSION.to_owned(),
            check_profile: check_registry.profile.clone(),
            check_version: check_registry.version.clone(),
            check_registry_sha256: raw_sha256(CHECK_REGISTRY.as_bytes()),
        },
        input: ReportInput {
            source_sha256: source_hash,
            bundle_id,
            bundle_hash,
        },
        evaluation_state: evaluation_state.to_owned(),
        integrity_verdict: integrity_verdict.to_owned(),
        replay_completeness: replay_completeness.to_owned(),
        verdict: verdict.to_owned(),
        checks,
        diagnostics: validator.diagnostics,
        diagnostics_truncated: validator.diagnostics_truncated,
        diagnostics_omitted: validator.diagnostics_omitted,
        replay,
        assurance: Assurance {
            verified,
            not_verified: vec![
                "producer_authentication".to_owned(),
                "signature_validity".to_owned(),
                "current_authority".to_owned(),
                "trusted_time".to_owned(),
                "effect_occurrence".to_owned(),
                "remote_schemas".to_owned(),
                "complete_native_object_semantics".to_owned(),
            ],
        },
        report_hash: String::new(),
    };
    report.report_hash = report_hash(&report)?;
    Ok(report)
}
