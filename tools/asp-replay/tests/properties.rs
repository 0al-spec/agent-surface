use std::sync::OnceLock;

use asp_replay::{
    MAX_DIAGNOSTIC_MESSAGE_CHARS, MAX_DIAGNOSTIC_PATH_CHARS, MAX_DIAGNOSTICS, REPORT_SCHEMA,
    ReplayError, Report, verify,
};
use proptest::collection::vec;
use proptest::prelude::*;
use proptest::test_runner::{Config, RngAlgorithm, TestCaseResult, TestRng, TestRunner};
use serde_json::Value;

const COMPLETE_SESSION: &[u8] = include_bytes!("fixtures/complete-session.json");
const EVENT_RECEIPT_FLOW: &[u8] = include_bytes!("fixtures/event-receipt-flow.json");

fn deterministic_runner(seed_tag: u8, cases: u32) -> TestRunner {
    let mut seed = [0_u8; 32];
    for (index, byte) in seed.iter_mut().enumerate() {
        *byte = seed_tag.wrapping_add((index as u8).wrapping_mul(29));
    }
    let config = Config {
        cases,
        failure_persistence: None,
        max_shrink_iters: 4096,
        ..Config::default()
    };
    TestRunner::new_with_rng(config, TestRng::from_seed(RngAlgorithm::ChaCha, &seed))
}

fn report_validator() -> &'static jsonschema::Validator {
    static VALIDATOR: OnceLock<jsonschema::Validator> = OnceLock::new();
    VALIDATOR.get_or_init(|| {
        let schema: Value = serde_json::from_str(REPORT_SCHEMA).expect("embedded report schema");
        jsonschema::validator_for(&schema).expect("compiled report schema")
    })
}

fn assert_report_contract(report: &Report) -> TestCaseResult {
    let report_value = serde_json::to_value(report).expect("Report is serializable");
    let schema_errors: Vec<String> = report_validator()
        .iter_errors(&report_value)
        .map(|error| error.to_string())
        .collect();
    prop_assert!(
        schema_errors.is_empty(),
        "emitted report violates its schema: {}",
        schema_errors.join("; ")
    );

    prop_assert_eq!(report.checks.len(), 12);
    prop_assert!(report.diagnostics.len() <= MAX_DIAGNOSTICS);
    prop_assert!(
        report.diagnostics.iter().all(|diagnostic| {
            diagnostic.path.chars().count() <= MAX_DIAGNOSTIC_PATH_CHARS
                && diagnostic.message.chars().count() <= MAX_DIAGNOSTIC_MESSAGE_CHARS
        }),
        "diagnostic path or message exceeds its bound"
    );

    let findings: usize = report.checks.iter().map(|check| check.findings).sum();
    prop_assert_eq!(
        findings,
        report.diagnostics.len() + report.diagnostics_omitted
    );
    if report.diagnostics_omitted > 0 {
        prop_assert!(report.diagnostics_truncated);
    }
    if !report.diagnostics_truncated {
        prop_assert_eq!(report.diagnostics_omitted, 0);
    }

    match report.evaluation_state.as_str() {
        "preflight_failed" | "semantic_invalid" => {
            prop_assert_eq!(report.integrity_verdict.as_str(), "invalid");
            prop_assert_eq!(report.replay_completeness.as_str(), "not_evaluated");
            prop_assert_eq!(report.verdict.as_str(), "invalid");
            prop_assert_eq!(report.replay.status.as_str(), "not_evaluated");
            prop_assert!(report.assurance.verified.is_empty());
        }
        "incomplete" => {
            prop_assert_eq!(report.integrity_verdict.as_str(), "valid");
            prop_assert_eq!(report.replay_completeness.as_str(), "incomplete");
            prop_assert_eq!(report.verdict.as_str(), "incomplete");
            prop_assert_eq!(report.replay.status.as_str(), "evaluated");
        }
        "valid" => {
            prop_assert_eq!(report.integrity_verdict.as_str(), "valid");
            prop_assert_eq!(report.replay_completeness.as_str(), "complete");
            prop_assert_eq!(report.verdict.as_str(), "valid");
            prop_assert_eq!(report.replay.status.as_str(), "evaluated");
            prop_assert!(report.diagnostics.is_empty());
            prop_assert!(!report.diagnostics_truncated);
            prop_assert_eq!(report.diagnostics_omitted, 0);
        }
        state => prop_assert!(false, "unknown evaluation state {state:?}"),
    }
    Ok(())
}

fn normalized_semantic_report(mut report: Report) -> Report {
    report.input.source_sha256.clear();
    report.report_hash.clear();
    report
}

#[derive(Clone, Debug)]
enum BundleMutation {
    RemoveTopLevel(u8),
    ReplaceTopLevelString(u8, String),
    ReplaceRecordOrdinal(u16, u64),
    ReplaceCaptureTimestamp(bool, String),
    AddSecret(u32),
}

fn mutation_strategy() -> impl Strategy<Value = BundleMutation> {
    prop_oneof![
        any::<u8>().prop_map(BundleMutation::RemoveTopLevel),
        (
            any::<u8>(),
            proptest::string::string_regex("[A-Za-z0-9._:/-]{0,48}")
                .expect("static mutation regex"),
        )
            .prop_map(|(member, value)| BundleMutation::ReplaceTopLevelString(member, value)),
        (any::<u16>(), 0_u64..5000)
            .prop_map(|(record, ordinal)| BundleMutation::ReplaceRecordOrdinal(record, ordinal)),
        (
            any::<bool>(),
            proptest::string::string_regex("[0-9TZ:.-]{0,32}").expect("static timestamp regex"),
        )
            .prop_map(|(start, value)| BundleMutation::ReplaceCaptureTimestamp(start, value)),
        any::<u32>().prop_map(BundleMutation::AddSecret),
    ]
}

fn apply_mutations(bundle: &mut Value, mutations: &[BundleMutation]) -> Vec<String> {
    const TOP_LEVEL: [&str; 12] = [
        "$schema",
        "schema_version",
        "profile",
        "protocol_version",
        "claim_effect",
        "bundle_id",
        "created_at",
        "scope",
        "context",
        "capture",
        "records",
        "bundle_hash",
    ];
    const STRING_MEMBERS: [&str; 6] = [
        "$schema",
        "profile",
        "protocol_version",
        "claim_effect",
        "bundle_id",
        "bundle_hash",
    ];

    let mut secrets = Vec::new();
    for mutation in mutations {
        match mutation {
            BundleMutation::RemoveTopLevel(member) => {
                if let Some(object) = bundle.as_object_mut() {
                    object.remove(TOP_LEVEL[usize::from(*member) % TOP_LEVEL.len()]);
                }
            }
            BundleMutation::ReplaceTopLevelString(member, value) => {
                if let Some(object) = bundle.as_object_mut() {
                    object.insert(
                        STRING_MEMBERS[usize::from(*member) % STRING_MEMBERS.len()].to_owned(),
                        Value::String(value.clone()),
                    );
                }
            }
            BundleMutation::ReplaceRecordOrdinal(record, ordinal) => {
                if let Some(records) = bundle.get_mut("records").and_then(Value::as_array_mut)
                    && !records.is_empty()
                {
                    let index = usize::from(*record) % records.len();
                    if let Some(object) = records[index].as_object_mut() {
                        object.insert("ordinal".to_owned(), Value::from(*ordinal));
                    }
                }
            }
            BundleMutation::ReplaceCaptureTimestamp(start, value) => {
                if let Some(capture) = bundle.get_mut("capture").and_then(Value::as_object_mut) {
                    capture.insert(
                        if *start { "started_at" } else { "ended_at" }.to_owned(),
                        Value::String(value.clone()),
                    );
                }
            }
            BundleMutation::AddSecret(id) => {
                let secret = format!("property-secret-{id:08x}");
                if let Some(body) = bundle
                    .pointer_mut("/records/0/body")
                    .and_then(Value::as_object_mut)
                {
                    body.insert("execution_token".to_owned(), Value::String(secret.clone()));
                    secrets.push(secret);
                }
            }
        }
    }
    secrets
}

#[test]
fn arbitrary_bytes_only_produce_strict_parse_errors_or_schema_valid_reports() {
    let strategy = vec(any::<u8>(), 0..2048);
    deterministic_runner(0x21, 512)
        .run(&strategy, |document| {
            match verify("<property>", &document) {
                Ok(report) => assert_report_contract(&report),
                Err(ReplayError::StrictJson(_)) => Ok(()),
                Err(error) => {
                    prop_assert!(false, "arbitrary input reached an internal error: {error}");
                    Ok(())
                }
            }
        })
        .expect("deterministic arbitrary-byte property");
}

#[test]
fn source_labels_and_repeated_verification_do_not_change_reports() {
    let labels =
        proptest::string::string_regex("[A-Za-z0-9_./:-]{0,64}").expect("static source regex");
    deterministic_runner(0x43, 128)
        .run(&labels, |label| {
            let first = verify(&label, COMPLETE_SESSION).expect("valid fixture");
            let second =
                verify("a different inert source", COMPLETE_SESSION).expect("valid fixture");
            prop_assert_eq!(first, second);
            Ok(())
        })
        .expect("deterministic source-label property");
}

#[test]
fn insignificant_json_presentation_preserves_semantic_report_fields() {
    let whitespace = vec(
        prop_oneof![Just(' '), Just('\n'), Just('\r'), Just('\t')],
        0..24,
    );
    let strategy = (any::<bool>(), whitespace.clone(), whitespace);
    let value: Value = serde_json::from_slice(EVENT_RECEIPT_FLOW).expect("valid fixture JSON");
    let compact = serde_json::to_vec(&value).expect("compact fixture");
    let baseline = verify("<compact>", &compact).expect("valid compact fixture");

    deterministic_runner(0x65, 128)
        .run(&strategy, |(pretty, prefix, suffix)| {
            let serialized = if pretty {
                serde_json::to_string_pretty(&value).expect("pretty fixture")
            } else {
                serde_json::to_string(&value).expect("compact fixture")
            };
            let document = format!(
                "{}{serialized}{}",
                prefix.into_iter().collect::<String>(),
                suffix.into_iter().collect::<String>()
            );
            let report = verify("<presentation>", document.as_bytes()).expect("valid presentation");
            assert_report_contract(&report)?;
            prop_assert_eq!(
                normalized_semantic_report(report),
                normalized_semantic_report(baseline.clone())
            );
            Ok(())
        })
        .expect("deterministic presentation property");
}

#[test]
fn schema_shaped_mutations_keep_reports_closed_bounded_and_secret_free() {
    let mutations = vec(mutation_strategy(), 0..16);
    deterministic_runner(0x87, 192)
        .run(&mutations, |mutations| {
            let mut bundle: Value =
                serde_json::from_slice(EVENT_RECEIPT_FLOW).expect("valid fixture JSON");
            let secrets = apply_mutations(&mut bundle, &mutations);
            let document = serde_json::to_vec(&bundle).expect("mutated bundle serialization");
            let report = verify("<mutated>", &document).map_err(|error| {
                TestCaseError::fail(format!("internal verifier error: {error}"))
            })?;
            assert_report_contract(&report)?;

            let serialized_report = serde_json::to_string(&report).expect("report serialization");
            for secret in secrets {
                prop_assert!(
                    !serialized_report.contains(&secret),
                    "diagnostics echoed an injected secret"
                );
            }
            Ok(())
        })
        .expect("deterministic structured-mutation property");
}
