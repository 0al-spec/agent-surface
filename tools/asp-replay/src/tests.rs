use std::collections::{BTreeMap, HashSet};

use serde_json::Value;

use crate::hash::{EVENT_DOMAIN, RECORD_DOMAIN, object_hash};
use crate::rehash::rehash_bundle;
use crate::selfcheck::validate_instance;
use crate::strict_json::parse_strict;
use crate::{
    CASE_REGISTRY, CASES_SCHEMA, MAX_DIAGNOSTIC_MESSAGE_CHARS, MAX_DIAGNOSTIC_PATH_CHARS,
    MAX_DIAGNOSTICS, REPORT_SCHEMA, Report, verify,
};

use super::events::{check_ack, check_event, check_gap};
use super::receipts::{
    validate_approval_decision, validate_approval_target, validate_parent_projection,
    validate_recovery_target,
};
use super::records::reconcile_pending_references;
use super::secrets::scan_secrets;
use super::state::{PendingReference, PendingReferenceKind, ReceiptProjection, Validator};

#[test]
fn jcs_uses_utf16_member_order_and_finite_binary64() {
    let value = parse_strict(br#"{"data":{"\uE000":2,"\uD800\uDC00":1,"value":0.1}}"#).unwrap();
    let canonical = serde_json_canonicalizer::to_string(&value).unwrap();
    assert_eq!(canonical, r#"{"data":{"value":0.1,"𐀀":1,"":2}}"#);
}

#[test]
fn strict_parser_rejects_ijson_hazards() {
    for document in [
        br#"{"value":-0}"#.as_slice(),
        br#"{"value":-0.0}"#,
        br#"{"value":9007199254740992}"#,
        br#"{"value":1,"value":2}"#,
        br#"{"value":1e400}"#,
        br#"{"value":"\uFDD0"}"#,
    ] {
        assert!(parse_strict(document).is_err());
    }
}

#[test]
fn hash_exclusion_is_stable() {
    let first = serde_json::json!({"ordinal":0,"record_hash":"old","body":{"x":1}});
    let second = serde_json::json!({"ordinal":0,"record_hash":"new","body":{"x":1}});
    assert_eq!(
        object_hash(RECORD_DOMAIN, &first, &["record_hash"]).unwrap(),
        object_hash(RECORD_DOMAIN, &second, &["record_hash"]).unwrap()
    );
}

#[test]
fn diagnostics_never_include_values_from_secret_fields() {
    let mut validator = Validator::new(false);
    scan_secrets(
        &serde_json::json!({"execution_token":"do-not-print"}),
        "/body",
        0,
        &mut validator,
    );
    let serialized = serde_json::to_string(&validator.diagnostics).unwrap();
    assert!(!serialized.contains("do-not-print"));
}

fn event_fixture(delivery_id: &str, event_id: &str, attempt: u64, sequence: u64) -> Value {
    let mut event = serde_json::json!({
        "specversion": "1.0",
        "id": event_id,
        "source": "https://code.example.com",
        "type": "task.created",
        "time": "2026-07-20T10:00:00Z",
        "dataschema": "https://code.example.com/schemas/task-created.json",
        "datacontenttype": "application/json",
        "data": {"score": 0.1},
        "aspscope": "task.read",
        "aspcontrol": false,
        "aspsurfacehash": "sha-256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "aspeventhash": "",
        "aspsubid": "sub_1",
        "aspdeliveryid": delivery_id,
        "aspattempt": attempt,
        "aspstream": "stream_1",
        "aspsequence": sequence,
        "aspcursor": format!("cursor_{sequence}"),
        "aspsessionid": "sess_1",
        "aspsessiongen": 1
    });
    let hash = object_hash(
        EVENT_DOMAIN,
        &event,
        &[
            "aspeventhash",
            "aspsubid",
            "aspdeliveryid",
            "aspattempt",
            "aspstream",
            "aspsequence",
            "aspcursor",
            "traceparent",
            "tracestate",
        ],
    )
    .unwrap();
    event["aspeventhash"] = Value::String(hash);
    event
}

fn event_fixture_for(
    delivery_id: &str,
    event_id: &str,
    attempt: u64,
    sequence: u64,
    subscription_id: &str,
    stream: &str,
) -> Value {
    let mut event = event_fixture(delivery_id, event_id, attempt, sequence);
    event["aspsubid"] = Value::String(subscription_id.to_owned());
    event["aspstream"] = Value::String(stream.to_owned());
    event
}

fn event_scope() -> (Value, Value, Value) {
    (
        serde_json::json!({
            "issuer": "https://code.example.com",
            "surface_hash": "sha-256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "session_id": "sess_1",
            "session_generation": 1
        }),
        serde_json::json!({
            "events": [{
                "id": "task.created",
                "scope": "task.read",
                "schema": "https://code.example.com/schemas/task-created.json"
            }]
        }),
        serde_json::json!({"scopes":["task.read"]}),
    )
}

fn terminal_ack(delivery_id: &str, cursor: &str, ordinal: usize, validator: &mut Validator) {
    check_ack(
        &serde_json::json!({
            "type":"event.ack",
            "payload":{
                "subscription_id":"sub_1",
                "delivery_id":delivery_id,
                "cursor":cursor,
                "outcome":"processed",
                "reason":"durably_recorded"
            }
        }),
        ordinal,
        validator,
    );
}

#[test]
fn stream_sequence_requires_terminal_acknowledgement() {
    let scope = serde_json::json!({
        "issuer": "https://code.example.com",
        "surface_hash": "sha-256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "session_id": "sess_1",
        "session_generation": 1
    });
    let surface = serde_json::json!({
        "events": [{
            "id": "task.created",
            "scope": "task.read",
            "schema": "https://code.example.com/schemas/task-created.json"
        }]
    });
    let grant = serde_json::json!({"scopes":["task.read"]});
    let mut validator = Validator::new(false);
    validator.session_generation = 1;
    validator.session_state = "active".to_owned();
    check_event(
        &event_fixture("delivery_1", "event_1", 1, 1),
        0,
        &scope,
        &surface,
        &grant,
        &mut validator,
    )
    .unwrap();
    check_event(
        &event_fixture("delivery_2", "event_2", 1, 2),
        1,
        &scope,
        &surface,
        &grant,
        &mut validator,
    )
    .unwrap();
    assert!(validator.diagnostics.iter().any(|diagnostic| {
        diagnostic.check_id == "ASP-REPLAY-DELIVERY-001" && diagnostic.severity == "error"
    }));
}

#[test]
fn capture_gap_can_cover_a_missing_terminal_acknowledgement() {
    let (scope, surface, grant) = event_scope();
    let mut validator = Validator::new(true);
    validator.session_generation = 1;
    validator.session_state = "active".to_owned();
    check_event(
        &event_fixture("delivery_1", "event_1", 1, 1),
        0,
        &scope,
        &surface,
        &grant,
        &mut validator,
    )
    .unwrap();
    validator.capture_gap_epoch += 1;
    check_event(
        &event_fixture("delivery_2", "event_2", 1, 2),
        2,
        &scope,
        &surface,
        &grant,
        &mut validator,
    )
    .unwrap();
    assert!(!validator.has_errors);
    assert!(validator.diagnostics.iter().any(|diagnostic| {
        diagnostic.check_id == "ASP-REPLAY-DELIVERY-001"
            && diagnostic.severity == "incomplete"
            && diagnostic.message.contains("terminal acknowledgement")
    }));
    assert_eq!(
        validator
            .streams
            .get(&("sub_1".to_owned(), "stream_1".to_owned()))
            .map(|progress| progress.sequence),
        Some(2)
    );
}

#[test]
fn protocol_gap_does_not_cover_a_known_missing_terminal_acknowledgement() {
    let (scope, surface, grant) = event_scope();
    let mut validator = Validator::new(false);
    validator.session_generation = 1;
    validator.session_state = "active".to_owned();
    check_event(
        &event_fixture("delivery_1", "event_1", 1, 1),
        0,
        &scope,
        &surface,
        &grant,
        &mut validator,
    )
    .unwrap();
    check_gap(
        &serde_json::json!({
            "type":"event.gap",
            "payload":{
                "subscription_id":"sub_1",
                "last_accepted_cursor":"cursor_1",
                "earliest_available_cursor":"cursor_2",
                "reason":"retention_expired"
            }
        }),
        1,
        &mut validator,
    );
    check_event(
        &event_fixture("delivery_2", "event_2", 1, 2),
        2,
        &scope,
        &surface,
        &grant,
        &mut validator,
    )
    .unwrap();
    assert!(validator.diagnostics.iter().any(|diagnostic| {
        diagnostic.check_id == "ASP-REPLAY-DELIVERY-001"
            && diagnostic.severity == "error"
            && diagnostic.message.contains("terminal acknowledgement")
    }));
}

#[test]
fn terminal_ack_allows_the_next_stream_sequence() {
    let scope = serde_json::json!({
        "issuer": "https://code.example.com",
        "surface_hash": "sha-256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "session_id": "sess_1",
        "session_generation": 1
    });
    let surface = serde_json::json!({
        "events": [{
            "id": "task.created",
            "scope": "task.read",
            "schema": "https://code.example.com/schemas/task-created.json"
        }]
    });
    let grant = serde_json::json!({"scopes":["task.read"]});
    let mut validator = Validator::new(false);
    validator.session_generation = 1;
    validator.session_state = "active".to_owned();
    check_event(
        &event_fixture("delivery_1", "event_1", 1, 1),
        0,
        &scope,
        &surface,
        &grant,
        &mut validator,
    )
    .unwrap();
    check_ack(
        &serde_json::json!({
            "type":"event.ack",
            "payload":{
                "subscription_id":"sub_1",
                "delivery_id":"delivery_1",
                "cursor":"cursor_1",
                "outcome":"processed",
                "reason":"durably_recorded"
            }
        }),
        1,
        &mut validator,
    );
    check_event(
        &event_fixture("delivery_2", "event_2", 1, 2),
        2,
        &scope,
        &surface,
        &grant,
        &mut validator,
    )
    .unwrap();
    assert!(validator.diagnostics.is_empty());
}

#[test]
fn protocol_gap_epoch_covers_each_stream_once() {
    let (scope, surface, grant) = event_scope();
    let mut validator = Validator::new(false);
    validator.session_generation = 1;
    validator.session_state = "active".to_owned();
    for (ordinal, stream) in ["stream_1", "stream_2"].iter().enumerate() {
        let delivery_id = format!("delivery_{}", ordinal + 1);
        check_event(
            &event_fixture_for(
                &delivery_id,
                &format!("event_{}", ordinal + 1),
                1,
                1,
                "sub_1",
                stream,
            ),
            ordinal * 2,
            &scope,
            &surface,
            &grant,
            &mut validator,
        )
        .unwrap();
        terminal_ack(&delivery_id, "cursor_1", ordinal * 2 + 1, &mut validator);
    }
    check_gap(
        &serde_json::json!({
            "type":"event.gap",
            "payload":{
                "subscription_id":"sub_1",
                "last_accepted_cursor":"cursor_1",
                "earliest_available_cursor":"cursor_3",
                "reason":"retention_expired"
            }
        }),
        4,
        &mut validator,
    );
    for (offset, stream) in ["stream_1", "stream_2"].iter().enumerate() {
        check_event(
            &event_fixture_for(
                &format!("delivery_{}", offset + 3),
                &format!("event_{}", offset + 3),
                1,
                3,
                "sub_1",
                stream,
            ),
            5 + offset,
            &scope,
            &surface,
            &grant,
            &mut validator,
        )
        .unwrap();
    }
    assert_eq!(
        validator
            .diagnostics
            .iter()
            .filter(|diagnostic| {
                diagnostic.check_id == "ASP-REPLAY-DELIVERY-001"
                    && diagnostic.severity == "incomplete"
            })
            .count(),
        2
    );
    assert!(!validator.has_errors);
}

#[test]
fn exact_post_gap_position_observes_epoch_for_that_stream() {
    let (scope, surface, grant) = event_scope();
    let mut validator = Validator::new(false);
    validator.session_generation = 1;
    validator.session_state = "active".to_owned();
    check_event(
        &event_fixture("delivery_1", "event_1", 1, 1),
        0,
        &scope,
        &surface,
        &grant,
        &mut validator,
    )
    .unwrap();
    terminal_ack("delivery_1", "cursor_1", 1, &mut validator);
    check_gap(
        &serde_json::json!({
            "type":"event.gap",
            "payload":{
                "subscription_id":"sub_1",
                "last_accepted_cursor":"cursor_1",
                "earliest_available_cursor":"cursor_2",
                "reason":"retention_expired"
            }
        }),
        2,
        &mut validator,
    );
    check_event(
        &event_fixture("delivery_2", "event_2", 1, 2),
        3,
        &scope,
        &surface,
        &grant,
        &mut validator,
    )
    .unwrap();
    terminal_ack("delivery_2", "cursor_2", 4, &mut validator);
    check_event(
        &event_fixture("delivery_4", "event_4", 1, 4),
        5,
        &scope,
        &surface,
        &grant,
        &mut validator,
    )
    .unwrap();
    assert!(validator.diagnostics.iter().any(|diagnostic| {
        diagnostic.check_id == "ASP-REPLAY-DELIVERY-001" && diagnostic.severity == "error"
    }));
}

#[test]
fn protocol_gap_does_not_cover_another_subscription_or_attempt_gap() {
    let (scope, surface, grant) = event_scope();
    let mut validator = Validator::new(false);
    validator.session_generation = 1;
    validator.session_state = "active".to_owned();
    check_gap(
        &serde_json::json!({
            "type":"event.gap",
            "payload":{
                "subscription_id":"sub_1",
                "last_accepted_cursor":"cursor_1",
                "earliest_available_cursor":"cursor_2",
                "reason":"retention_expired"
            }
        }),
        0,
        &mut validator,
    );
    check_event(
        &event_fixture_for("delivery_2", "event_2", 1, 2, "sub_2", "stream_1"),
        1,
        &scope,
        &surface,
        &grant,
        &mut validator,
    )
    .unwrap();
    check_event(
        &event_fixture("delivery_retry", "event_retry", 2, 1),
        2,
        &scope,
        &surface,
        &grant,
        &mut validator,
    )
    .unwrap();
    assert!(
        validator
            .finding_summaries
            .get("ASP-REPLAY-DELIVERY-001")
            .is_some_and(|summary| summary.errors == 2)
    );
}

#[test]
fn pending_ack_known_only_later_is_invalid() {
    let (scope, surface, grant) = event_scope();
    let mut validator = Validator::new(false);
    validator.session_generation = 1;
    validator.session_state = "active".to_owned();
    terminal_ack("delivery_1", "cursor_1", 0, &mut validator);
    check_event(
        &event_fixture("delivery_1", "event_1", 1, 1),
        1,
        &scope,
        &surface,
        &grant,
        &mut validator,
    )
    .unwrap();
    reconcile_pending_references(&mut validator);
    assert!(validator.diagnostics.iter().any(|diagnostic| {
        diagnostic.check_id == "ASP-REPLAY-ACK-001"
            && diagnostic.severity == "error"
            && diagnostic.message.contains("later delivery")
    }));
}

fn receipt_projection_fixture(
    ordinal: usize,
    receipt_type: &str,
    action_id: &str,
) -> ReceiptProjection {
    ReceiptProjection {
        ordinal,
        receipt_type: receipt_type.to_owned(),
        grant_hash: "sha-256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA".to_owned(),
        surface_hash: "sha-256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB".to_owned(),
        surface_version: "2026-07-20".to_owned(),
        session_id: "sess_1".to_owned(),
        session_generation: 1,
        trace_id: "4bf92f3577b34da6a3ce929d0e0e4736".to_owned(),
        linked_trace_id: None,
        action_id: action_id.to_owned(),
        idempotency_key: "idem_1".to_owned(),
        input_hash: "sha-256:CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC".to_owned(),
        execution: Some(serde_json::json!({
            "mode":"commit",
            "execution_id":"exec_1"
        })),
        execution_hash: Some("sha-256:DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD".to_owned()),
        timestamp: "2026-07-20T10:00:00Z".to_owned(),
        result: "success".to_owned(),
        effect_outcome: None,
        actual_effect_ids: HashSet::new(),
        approval_role: None,
        approval_receipt_hashes: BTreeMap::new(),
        target_receipt_hash: None,
    }
}

#[test]
fn receipt_parent_projection_rejects_invocation_and_trace_substitution() {
    let parent = receipt_projection_fixture(0, "runtime", "comment.create");
    let mut child = receipt_projection_fixture(1, "app", "comment.update");
    child.trace_id = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa".to_owned();
    let mut validator = Validator::new(false);
    validate_parent_projection(&child, &parent, &mut validator);
    assert!(
        validator
            .finding_summaries
            .get("ASP-REPLAY-RECEIPT-CHAIN-001")
            .is_some_and(|summary| summary.errors == 2)
    );
}

#[test]
fn pending_receipt_references_known_only_later_are_invalid() {
    let parent_hash = "sha-256:EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE";
    let approval_hash = "sha-256:FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF";
    let mut validator = Validator::new(true);
    validator.validated_capture_gaps = 1;
    validator.pending_references.extend([
        PendingReference {
            check_id: "ASP-REPLAY-RECEIPT-CHAIN-001",
            ordinal: 1,
            path: "/records/1/body/parent_receipt_hash".to_owned(),
            target: parent_hash.to_owned(),
            kind: PendingReferenceKind::ReceiptParent,
        },
        PendingReference {
            check_id: "ASP-REPLAY-RECEIPT-LINK-001",
            ordinal: 2,
            path: "/records/2/body/approval_receipt_hashes/runtime".to_owned(),
            target: approval_hash.to_owned(),
            kind: PendingReferenceKind::ApprovalSideLink {
                role: "runtime".to_owned(),
            },
        },
    ]);
    validator.receipts_by_hash.insert(
        parent_hash.to_owned(),
        receipt_projection_fixture(3, "runtime", "comment.create"),
    );
    validator.receipts_by_hash.insert(
        approval_hash.to_owned(),
        receipt_projection_fixture(4, "approval", "comment.create"),
    );
    reconcile_pending_references(&mut validator);
    assert_eq!(
        validator
            .diagnostics
            .iter()
            .filter(|diagnostic| {
                diagnostic.severity == "error" && diagnostic.message.contains("later receipt")
            })
            .count(),
        2
    );
    assert!(
        !validator
            .diagnostics
            .iter()
            .any(|diagnostic| { diagnostic.severity == "incomplete" })
    );
}

#[test]
fn approval_side_link_requires_approved_role_matched_invocation() {
    let source = receipt_projection_fixture(1, "app", "comment.create");
    let mut target = receipt_projection_fixture(0, "approval", "comment.create");
    target.result = "approved".to_owned();
    target.approval_role = Some("runtime".to_owned());
    let mut valid = Validator::new(false);
    validate_approval_target(&source, "runtime", &target, &mut valid);
    assert!(valid.diagnostics.is_empty());

    target.approval_role = Some("application".to_owned());
    target.input_hash = "sha-256:EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE".to_owned();
    let mut invalid = Validator::new(false);
    validate_approval_target(&source, "runtime", &target, &mut invalid);
    assert!(invalid.has_errors);
}

#[test]
fn recovery_target_requires_exact_reciprocal_relationship() {
    let mut source = receipt_projection_fixture(2, "app", "payment.refund");
    source.execution = Some(serde_json::json!({
        "mode":"compensate",
        "execution_id":"exec_refund",
        "target_receipt_hash":"sha-256:FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    }));
    source.target_receipt_hash =
        Some("sha-256:FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF".to_owned());
    source.timestamp = "2026-07-20T11:00:00Z".to_owned();
    let mut target = receipt_projection_fixture(0, "app", "payment.capture");
    target.effect_outcome = Some("applied".to_owned());
    target.actual_effect_ids.insert("charge".to_owned());
    let surface = serde_json::json!({
        "actions":[
            {
                "id":"payment.capture",
                "execution":{
                    "mode":"commit",
                    "operation_id":"payment.capture",
                    "recovery_actions":[{
                        "mode":"compensate",
                        "action_id":"payment.refund",
                        "effect_ids":["charge"],
                        "recovery_window_seconds":3600
                    }]
                }
            },
            {
                "id":"payment.refund",
                "execution":{
                    "mode":"compensate",
                    "operation_id":"payment.capture",
                    "target_actions":[{
                        "action_id":"payment.capture",
                        "effect_ids":["charge"],
                        "recovery_window_seconds":3600
                    }]
                }
            }
        ]
    });
    let mut valid = Validator::new(false);
    validate_recovery_target(&source, &target, &surface, &mut valid);
    assert!(valid.diagnostics.is_empty());

    let mut broken = surface.clone();
    broken["actions"][1]["execution"]["target_actions"][0]["recovery_window_seconds"] =
        Value::from(1800);
    let mut invalid = Validator::new(false);
    validate_recovery_target(&source, &target, &broken, &mut invalid);
    assert!(invalid.has_errors);

    let mut expired = source.clone();
    expired.timestamp = "2026-07-20T11:00:01Z".to_owned();
    let mut expired_validator = Validator::new(false);
    validate_recovery_target(&expired, &target, &surface, &mut expired_validator);
    assert!(
        expired_validator
            .diagnostics
            .iter()
            .any(|diagnostic| { diagnostic.message.contains("recovery window") })
    );

    let mut reversed = source;
    reversed.timestamp = "2026-07-20T09:59:59Z".to_owned();
    let mut reversed_validator = Validator::new(false);
    validate_recovery_target(&reversed, &target, &surface, &mut reversed_validator);
    assert!(
        reversed_validator
            .diagnostics
            .iter()
            .any(|diagnostic| { diagnostic.message.contains("recovery window") })
    );
}

fn approval_decision_fixture(
    role: &str,
    result: &str,
    decided_by: &str,
    outcome: &str,
    reason_code: &str,
    valid_until: Option<&str>,
) -> Value {
    let enforcer = if role == "runtime" {
        serde_json::json!({"type":"runtime","id":"runtime_456"})
    } else {
        serde_json::json!({"type":"application","id":"code.example.com"})
    };
    let mut approval = serde_json::json!({
        "approval_id":"approval_1",
        "role":role,
        "decided_by":decided_by
    });
    if let Some(valid_until) = valid_until {
        approval["valid_until"] = Value::String(valid_until.to_owned());
    }
    serde_json::json!({
        "action_id":"comment.create",
        "timestamp":"2026-07-20T10:00:00Z",
        "result":result,
        "approval":approval,
        "policy_decision":{
            "enforcer":enforcer,
            "outcome":outcome,
            "reason_code":reason_code,
            "evaluated_at":"2026-07-20T10:00:00Z"
        }
    })
}

fn approval_scope_and_grant(max_age_seconds: u64, expires_at: &str) -> (Value, Value) {
    (
        serde_json::json!({
            "runtime_id":"runtime_456",
            "app_id":"code.example.com"
        }),
        serde_json::json!({
            "constraints":{"expires_at":expires_at},
            "audit":{
                "approval_receipt":{
                    "profile":"https://github.com/0al-spec/agent-surface/profiles/approval-receipt/v1",
                    "requirements":[{
                        "action_id":"comment.create",
                        "accepted_roles":["application","runtime"],
                        "max_age_seconds":max_age_seconds
                    }]
                }
            }
        }),
    )
}

#[test]
fn approval_decision_accepts_exact_six_row_semantics() {
    let (scope, grant) = approval_scope_and_grant(300, "2026-07-20T10:10:00Z");
    let rows = [
        ("runtime", "approved", "user", "allow", "approval_satisfied"),
        ("runtime", "denied", "user", "deny", "approval_denied"),
        ("runtime", "denied", "policy", "deny", "local_policy_denied"),
        (
            "application",
            "approved",
            "user",
            "allow",
            "approval_satisfied",
        ),
        ("application", "denied", "user", "deny", "approval_denied"),
        (
            "application",
            "denied",
            "policy",
            "deny",
            "app_policy_denied",
        ),
    ];
    for (ordinal, (role, result, decided_by, outcome, reason)) in rows.into_iter().enumerate() {
        let mut validator = Validator::new(false);
        validate_approval_decision(
            &approval_decision_fixture(
                role,
                result,
                decided_by,
                outcome,
                reason,
                (result == "approved").then_some("2026-07-20T10:04:59Z"),
            ),
            ordinal,
            &scope,
            &grant,
            &mut validator,
        );
        assert!(
            validator.diagnostics.is_empty(),
            "valid row {ordinal} produced {:?}",
            validator.diagnostics
        );
    }
}

#[test]
fn approval_decision_rejects_denied_expiry_and_excessive_age() {
    let (scope, grant) = approval_scope_and_grant(300, "2026-07-20T10:03:00Z");
    let mut denied = Validator::new(false);
    validate_approval_decision(
        &approval_decision_fixture(
            "runtime",
            "denied",
            "user",
            "deny",
            "approval_denied",
            Some("2026-07-20T10:01:00Z"),
        ),
        0,
        &scope,
        &grant,
        &mut denied,
    );
    assert!(denied.has_errors);

    let mut approved = Validator::new(false);
    validate_approval_decision(
        &approval_decision_fixture(
            "application",
            "approved",
            "policy",
            "allow",
            "approval_satisfied",
            Some("2026-07-20T10:06:00Z"),
        ),
        0,
        &scope,
        &grant,
        &mut approved,
    );
    assert!(
        approved
            .finding_summaries
            .get("ASP-REPLAY-RECEIPT-LINK-001")
            .is_some_and(|summary| summary.errors >= 2)
    );

    let mut invalid_combination = Validator::new(false);
    validate_approval_decision(
        &approval_decision_fixture(
            "runtime",
            "approved",
            "policy",
            "allow",
            "approval_satisfied",
            Some("2026-07-20T10:01:00Z"),
        ),
        0,
        &scope,
        &grant,
        &mut invalid_combination,
    );
    assert!(invalid_combination.has_errors);
}

#[test]
fn diagnostics_are_bounded_without_hiding_failure_state() {
    let mut validator = Validator::new(false);
    let long_path = format!("/{}", "x".repeat(MAX_DIAGNOSTIC_PATH_CHARS + 100));
    let long_message = "m".repeat(MAX_DIAGNOSTIC_MESSAGE_CHARS + 100);
    for ordinal in 0..(MAX_DIAGNOSTICS + 44) {
        validator.error("ASP-REPLAY-SCHEMA-001", ordinal, &long_path, &long_message);
    }
    assert!(validator.has_errors);
    assert_eq!(validator.diagnostics.len(), MAX_DIAGNOSTICS);
    assert_eq!(validator.diagnostics_omitted, 44);
    assert!(validator.diagnostics_truncated);
    assert_eq!(
        validator
            .finding_summaries
            .get("ASP-REPLAY-SCHEMA-001")
            .map(|summary| summary.errors),
        Some(MAX_DIAGNOSTICS + 44)
    );
    assert!(validator.diagnostics.iter().all(|diagnostic| {
        diagnostic.path.chars().count() <= MAX_DIAGNOSTIC_PATH_CHARS
            && diagnostic.path.starts_with('/')
            && !diagnostic.path.ends_with('~')
            && diagnostic.message.chars().count() <= MAX_DIAGNOSTIC_MESSAGE_CHARS
    }));
    assert_eq!(validator.diagnostics[0].path, "/<truncated>");
}

fn verify_rehashed_event_flow_mutation(pointer: &str, replacement: Value) -> Report {
    let mut bundle =
        parse_strict(include_bytes!("../tests/fixtures/event-receipt-flow.json")).unwrap();
    *bundle
        .pointer_mut(pointer)
        .expect("test mutation pointer must resolve") = replacement;
    rehash_bundle(&mut bundle).unwrap();
    verify("mutated-event-flow", &serde_json::to_vec(&bundle).unwrap()).unwrap()
}

#[test]
fn non_integer_event_attempt_is_a_delivery_error_after_rehashing() {
    let report = verify_rehashed_event_flow_mutation(
        "/records/1/body/aspattempt",
        Value::String("1".to_owned()),
    );
    assert_eq!(report.evaluation_state, "semantic_invalid");
    assert!(report.checks.iter().any(|check| {
        check.check_id == "ASP-REPLAY-DELIVERY-001" && check.status == "fail" && check.findings >= 1
    }));
    assert!(report.diagnostics.iter().any(|diagnostic| {
        diagnostic.check_id == "ASP-REPLAY-DELIVERY-001"
            && diagnostic.path == "/records/1/body/aspattempt"
    }));
}

#[test]
fn non_string_event_id_is_an_event_error_after_rehashing() {
    let report = verify_rehashed_event_flow_mutation("/records/1/body/id", Value::from(123));
    assert_eq!(report.evaluation_state, "semantic_invalid");
    assert!(report.checks.iter().any(|check| {
        check.check_id == "ASP-REPLAY-EVENT-001" && check.status == "fail" && check.findings >= 1
    }));
    assert!(report.diagnostics.iter().any(|diagnostic| {
        diagnostic.check_id == "ASP-REPLAY-EVENT-001" && diagnostic.path == "/records/1/body/id"
    }));
}

#[test]
fn malformed_event_occurrence_identity_members_are_rejected() {
    let (scope, surface, grant) = event_scope();
    for name in ["source", "id", "aspeventhash"] {
        let mut event = event_fixture("delivery_1", "event_1", 1, 1);
        event[name] = Value::from(123);
        let mut validator = Validator::new(false);
        validator.session_generation = 1;
        validator.session_state = "active".to_owned();
        check_event(&event, 1, &scope, &surface, &grant, &mut validator).unwrap();
        assert!(
            validator.diagnostics.iter().any(|diagnostic| {
                diagnostic.check_id == "ASP-REPLAY-EVENT-001"
                    && diagnostic.path == format!("/records/1/body/{name}")
            }),
            "malformed event occurrence member {name:?} must be rejected"
        );
    }
}

#[test]
fn malformed_acknowledgement_delivery_id_is_an_ack_error_after_rehashing() {
    let report = verify_rehashed_event_flow_mutation(
        "/records/2/body/payload/delivery_id",
        Value::from(123),
    );
    assert_eq!(report.evaluation_state, "semantic_invalid");
    assert!(report.checks.iter().any(|check| {
        check.check_id == "ASP-REPLAY-ACK-001" && check.status == "fail" && check.findings >= 1
    }));
    assert!(report.diagnostics.iter().any(|diagnostic| {
        diagnostic.check_id == "ASP-REPLAY-ACK-001"
            && diagnostic.path == "/records/2/body/payload/delivery_id"
    }));
}

#[test]
fn preflight_report_nulls_noncanonical_input_identity() {
    let mut bundle =
        parse_strict(include_bytes!("../tests/fixtures/complete-session.json")).unwrap();
    bundle["bundle_id"] = Value::String("x".repeat(257));
    bundle["bundle_hash"] = Value::String("not-a-digest".to_owned());
    let bytes = serde_json::to_vec(&bundle).unwrap();
    let report = verify("invalid-identity", &bytes).unwrap();
    assert_eq!(report.evaluation_state, "preflight_failed");
    assert_eq!(report.input.bundle_id, None);
    assert_eq!(report.input.bundle_hash, None);
    let schema: Value = serde_json::from_str(REPORT_SCHEMA).unwrap();
    validate_instance(
        &schema,
        &serde_json::to_value(report).unwrap(),
        "preflight report",
    )
    .unwrap();
}

#[test]
fn retained_diagnostics_and_omission_count_account_for_every_finding() {
    let report = verify(
        "invalid-empty",
        include_bytes!("../tests/fixtures/invalid-empty.json"),
    )
    .unwrap();
    let findings: usize = report.checks.iter().map(|check| check.findings).sum();
    assert_eq!(
        findings,
        report.diagnostics.len() + report.diagnostics_omitted
    );
    assert!(
        report
            .diagnostics
            .iter()
            .any(|diagnostic| diagnostic.path.is_empty())
    );
}

#[test]
fn report_schema_rejects_a_truncated_or_fabricated_check_profile() {
    let report_schema: Value = serde_json::from_str(REPORT_SCHEMA).unwrap();
    let report = verify(
        "complete-session",
        include_bytes!("../tests/fixtures/complete-session.json"),
    )
    .unwrap();
    let mut value = serde_json::to_value(report).unwrap();
    value["checks"].as_array_mut().unwrap().truncate(1);
    assert!(validate_instance(&report_schema, &value, "truncated report").is_err());
}

#[test]
fn report_schema_rejects_unknown_diagnostic_checks_and_invalid_json_pointers() {
    let report_schema: Value = serde_json::from_str(REPORT_SCHEMA).unwrap();
    let report = verify(
        "invalid-empty",
        include_bytes!("../tests/fixtures/invalid-empty.json"),
    )
    .unwrap();
    let value = serde_json::to_value(report).unwrap();

    let mut unknown_check = value.clone();
    unknown_check["diagnostics"][0]["check_id"] =
        Value::String("ASP-REPLAY-UNKNOWN-001".to_owned());
    assert!(validate_instance(&report_schema, &unknown_check, "unknown diagnostic check").is_err());

    for invalid_path in ["not/a/pointer", "/~2bad"] {
        let mut bad_pointer = value.clone();
        bad_pointer["diagnostics"][0]["path"] = Value::String(invalid_path.to_owned());
        assert!(
            validate_instance(&report_schema, &bad_pointer, "invalid diagnostic path").is_err(),
            "invalid RFC 6901 diagnostic path {invalid_path:?} must be rejected"
        );
    }
}

#[test]
fn case_schema_rejects_an_impossible_report_truth_tuple() {
    let cases_schema: Value = serde_json::from_str(CASES_SCHEMA).unwrap();
    let mut cases = parse_strict(CASE_REGISTRY.as_bytes()).unwrap();
    let first = &mut cases["cases"][0];
    first["integrity_verdict"] = Value::String("invalid".to_owned());
    first["replay_completeness"] = Value::String("not_evaluated".to_owned());
    first["verdict"] = Value::String("incomplete".to_owned());
    assert!(validate_instance(&cases_schema, &cases, "impossible case tuple").is_err());
}
