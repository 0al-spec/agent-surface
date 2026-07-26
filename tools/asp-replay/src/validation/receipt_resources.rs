use serde::Serialize;
use serde_json::{Value, json};
use std::collections::HashSet;

use crate::hash::valid_digest;
use crate::strict_json::parse_strict;
use crate::value::{has_only, member, string, uint};
use crate::{Diagnostic, ReplayError};

use super::receipts::check_receipt;
use super::state::Validator;

pub(crate) const RECEIPT_RESOURCE_REQUEST_PROFILE: &str =
    "https://github.com/0al-spec/agent-surface/tools/asp-replay/receipt-resource-request/v1";
pub(crate) const RECEIPT_RESOURCE_REPORT_PROFILE: &str =
    "https://github.com/0al-spec/agent-surface/tools/asp-replay/receipt-resource-report/v1";

const EXPECTED_BINDING_MEMBERS: &[&str] = &[
    "session_id",
    "session_generation",
    "trace_id",
    "grant_id",
    "grant_hash",
    "app_id",
    "surface_hash",
    "surface_version",
    "action_id",
    "idempotency_key",
    "input_hash",
    "runtime",
    "actor_agent",
    "subject",
    "execution",
    "execution_hash",
];

const REQUIRED_BINDING_MEMBERS: &[&str] = &[
    "session_id",
    "session_generation",
    "trace_id",
    "grant_id",
    "grant_hash",
    "app_id",
    "surface_hash",
    "surface_version",
    "action_id",
    "idempotency_key",
    "input_hash",
    "runtime",
    "actor_agent",
    "subject",
];

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct ReceiptResourceReport {
    pub profile: String,
    pub validation_scope: String,
    pub verdict: String,
    pub resources: usize,
    pub signatures_verified: bool,
    pub diagnostics: Vec<Diagnostic>,
}

fn receipt_string(receipt: &Value, name: &str) -> String {
    string(receipt, name).unwrap_or_default().to_owned()
}

fn approval_roles(receipt: &Value) -> Vec<String> {
    let mut roles = member(receipt, "approval_receipt_hashes")
        .and_then(Value::as_object)
        .map(|links| links.keys().cloned().collect::<Vec<_>>())
        .unwrap_or_default();
    if string(receipt, "receipt_type") == Some("approval")
        && let Some(role) = member(receipt, "approval").and_then(|value| string(value, "role"))
        && !roles.iter().any(|candidate| candidate == role)
    {
        roles.push(role.to_owned());
    }
    roles.sort();
    roles.dedup();
    roles
}

fn approval_mode(receipt_type: &str, roles: &[String]) -> &'static str {
    if receipt_type == "approval" {
        return match roles.first().map(String::as_str) {
            Some("runtime") => "runtime",
            Some("application") => "app",
            _ => "none",
        };
    }
    match (
        roles.iter().any(|role| role == "runtime"),
        roles.iter().any(|role| role == "application"),
    ) {
        (true, true) => "runtime_and_app",
        (true, false) => "runtime",
        (false, true) => "app",
        (false, false) => "none",
    }
}

fn synthetic_context(receipt: &Value) -> (Value, Value, Value) {
    let receipt_type = string(receipt, "receipt_type").unwrap_or_default();
    let action_id = receipt_string(receipt, "action_id");
    let roles = approval_roles(receipt);
    let mut action = json!({
        "id": action_id,
        "approval": approval_mode(receipt_type, &roles),
    });
    if let Some(mode) = member(receipt, "execution").and_then(|value| string(value, "mode")) {
        action["execution"] = json!({"mode": mode});
    }
    let scope = json!({
        "grant_id": receipt_string(receipt, "grant_id"),
        "grant_hash": receipt_string(receipt, "grant_hash"),
        "session_id": receipt_string(receipt, "session_id"),
        "session_generation": uint(receipt, "session_generation").unwrap_or_default(),
        "surface_version": receipt_string(receipt, "surface_version"),
        "surface_hash": receipt_string(receipt, "surface_hash"),
        "app_id": receipt_string(receipt, "app_id"),
        "subject_user": member(receipt, "subject")
            .and_then(|value| string(value, "user"))
            .unwrap_or_default(),
        "runtime_id": member(receipt, "runtime")
            .and_then(|value| string(value, "runtime_id"))
            .unwrap_or_default(),
        "agent_id": member(receipt, "actor_agent")
            .and_then(|value| string(value, "agent_id"))
            .unwrap_or_default(),
        "identity_evidence_hash": member(receipt, "actor_agent")
            .and_then(|value| string(value, "identity_evidence_hash"))
            .unwrap_or_default(),
    });
    let surface = json!({"actions": [action]});
    let requirements = if roles.is_empty() {
        Vec::new()
    } else {
        vec![json!({
            "action_id": receipt_string(receipt, "action_id"),
            "accepted_roles": roles,
            "max_age_seconds": u64::MAX,
        })]
    };
    let grant = json!({
        "actions": [receipt_string(receipt, "action_id")],
        "constraints": {},
        "audit": {
            "approval_receipt": {
                "profile": "https://github.com/0al-spec/agent-surface/profiles/approval-receipt/v1",
                "requirements": requirements,
            }
        }
    });
    (scope, surface, grant)
}

fn validate_expected_binding(
    receipt: &Value,
    expected: &Value,
    ordinal: usize,
    validator: &mut Validator,
) {
    let path = format!("/resources/{ordinal}/expected");
    let Some(expected_object) = expected.as_object() else {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            &path,
            "receipt resource expectation must be an object",
        );
        return;
    };
    if !has_only(
        expected_object,
        &[
            "receipt_id",
            "receipt_hash",
            "receipt_type",
            "approval_role",
            "binding",
            "signature_required",
        ],
    ) || [
        "receipt_id",
        "receipt_hash",
        "receipt_type",
        "approval_role",
        "binding",
        "signature_required",
    ]
    .iter()
    .any(|name| member(expected, name).is_none())
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            &path,
            "receipt resource expectation is not the exact closed shape",
        );
        return;
    }
    for name in ["receipt_id", "receipt_hash", "receipt_type"] {
        if string(expected, name) != string(receipt, name) {
            validator.error(
                "ASP-REPLAY-RECEIPT-HASH-001",
                ordinal,
                format!("{path}/{name}"),
                "receipt resource identity differs from its authenticated reference",
            );
        }
    }
    let expected_approval_role = member(expected, "approval_role");
    let actual_approval_role = member(receipt, "approval")
        .and_then(|approval| string(approval, "role"))
        .map(Value::from)
        .unwrap_or(Value::Null);
    if expected_approval_role != Some(&actual_approval_role) {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            ordinal,
            format!("{path}/approval_role"),
            "receipt approval role differs from the authenticated outer role",
        );
    }
    if member(expected, "signature_required").and_then(Value::as_bool) != Some(false)
        || member(receipt, "receipt_signatures").is_some()
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            format!("{path}/signature_required"),
            "receipt signatures require an independently verified provider result",
        );
    }
    let Some(binding) = member(expected, "binding") else {
        return;
    };
    let Some(binding_object) = binding.as_object() else {
        validator.error(
            "ASP-REPLAY-RECEIPT-CHAIN-001",
            ordinal,
            format!("{path}/binding"),
            "receipt resource binding must be an object",
        );
        return;
    };
    if !has_only(binding_object, EXPECTED_BINDING_MEMBERS)
        || REQUIRED_BINDING_MEMBERS
            .iter()
            .any(|name| member(binding, name).is_none())
        || (member(binding, "execution").is_some() != member(binding, "execution_hash").is_some())
        || (member(binding, "execution").is_some() != member(receipt, "execution").is_some())
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-CHAIN-001",
            ordinal,
            format!("{path}/binding"),
            "receipt resource binding is not the exact complete invocation shape",
        );
    }
    for (name, expected_value) in binding_object {
        if member(receipt, name) != Some(expected_value) {
            validator.error(
                "ASP-REPLAY-RECEIPT-CHAIN-001",
                ordinal,
                format!("{path}/binding/{name}"),
                "receipt resource differs from the correlated action tuple",
            );
        }
    }
}

fn validate_receipt_wire_shape(receipt: &Value, ordinal: usize, validator: &mut Validator) {
    const COMMON: &[&str] = &[
        "receipt_id",
        "receipt_type",
        "receipt_hash",
        "grant_id",
        "grant_hash",
        "session_id",
        "session_generation",
        "trace_id",
        "span_id",
        "action_id",
        "app_id",
        "surface_version",
        "surface_hash",
        "runtime",
        "actor_agent",
        "subject",
        "idempotency_key",
        "input_hash",
        "policy_decision_hash",
        "policy_decision",
        "timestamp",
        "result",
    ];
    const RUNTIME_ALLOWED: &[&str] = &[
        "receipt_id",
        "receipt_type",
        "receipt_hash",
        "parent_receipt_hash",
        "grant_id",
        "grant_hash",
        "session_id",
        "session_generation",
        "trace_id",
        "linked_trace_id",
        "span_id",
        "action_id",
        "app_id",
        "surface_version",
        "surface_hash",
        "runtime",
        "actor_agent",
        "subject",
        "idempotency_key",
        "approval_receipt_hashes",
        "input_hash",
        "execution",
        "execution_hash",
        "policy_decision_hash",
        "policy_decision",
        "budget_charges",
        "timestamp",
        "result",
        "error",
        "receipt_signatures",
    ];
    const APP_ALLOWED: &[&str] = &[
        "receipt_id",
        "receipt_type",
        "receipt_hash",
        "parent_receipt_hash",
        "grant_id",
        "grant_hash",
        "session_id",
        "session_generation",
        "trace_id",
        "linked_trace_id",
        "span_id",
        "action_id",
        "app_id",
        "surface_version",
        "surface_hash",
        "runtime",
        "actor_agent",
        "subject",
        "idempotency_key",
        "approval_receipt_hashes",
        "input_hash",
        "execution",
        "execution_hash",
        "reservation_result",
        "output_hash",
        "actual_effects",
        "actual_effects_hash",
        "effect_outcome",
        "revert_evidence",
        "policy_decision_hash",
        "policy_decision",
        "resource",
        "budget_charges",
        "error",
        "timestamp",
        "result",
        "receipt_signatures",
    ];
    let path = format!("/records/{ordinal}/body");
    let allowed = match string(receipt, "receipt_type") {
        Some("runtime") => Some(RUNTIME_ALLOWED),
        Some("app") => Some(APP_ALLOWED),
        Some("approval") => None,
        _ => Some(&[][..]),
    };
    if let Some(allowed) = allowed
        && (!receipt
            .as_object()
            .is_some_and(|object| has_only(object, allowed))
            || COMMON.iter().any(|name| member(receipt, name).is_none()))
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            &path,
            "ordinary receipt is not its exact closed producer wire shape",
        );
    }
    let participant_shapes = [
        ("runtime", &["runtime_id"][..]),
        ("actor_agent", &["agent_id", "identity_evidence_hash"][..]),
        ("subject", &["user"][..]),
    ];
    for (name, members) in participant_shapes {
        let nested = member(receipt, name);
        if !nested.is_some_and(|value| {
            value
                .as_object()
                .is_some_and(|object| has_only(object, members))
                && members.iter().all(|member_name| {
                    string(value, member_name).is_some_and(|item| !item.is_empty())
                })
        }) {
            validator.error(
                "ASP-REPLAY-RECEIPT-HASH-001",
                ordinal,
                format!("{path}/{name}"),
                "receipt participant projection is not its exact closed shape",
            );
        }
    }
    if member(receipt, "actor_agent")
        .and_then(|value| string(value, "identity_evidence_hash"))
        .is_none_or(|value| !valid_digest(value))
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            format!("{path}/actor_agent/identity_evidence_hash"),
            "receipt actor identity evidence hash is invalid",
        );
    }
    if member(receipt, "execution")
        .and_then(|value| member(value, "execution_token"))
        .is_some()
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            format!("{path}/execution/execution_token"),
            "receipt must not contain a raw execution token",
        );
    }
}

pub(crate) fn verify_receipt_resources(
    document: &[u8],
) -> Result<ReceiptResourceReport, ReplayError> {
    let request = parse_strict(document)?;
    let mut validator = Validator::new(false);
    let root_valid = request.as_object().is_some_and(|object| {
        has_only(object, &["profile", "resources"])
            && string(&request, "profile") == Some(RECEIPT_RESOURCE_REQUEST_PROFILE)
            && member(&request, "resources")
                .and_then(Value::as_array)
                .is_some_and(|resources| !resources.is_empty() && resources.len() <= 64)
    });
    if !root_valid {
        validator.error(
            "ASP-REPLAY-SCHEMA-001",
            0,
            "",
            "receipt resource request is not the exact bounded batch shape",
        );
    }
    let resources = member(&request, "resources")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();
    let mut uris = HashSet::new();
    let mut receipt_ids = HashSet::new();
    let mut receipt_hashes = HashSet::new();
    let mut validated_entries = Vec::new();
    for (ordinal, entry) in resources.iter().enumerate() {
        let path = format!("/resources/{ordinal}");
        let entry_valid = entry.as_object().is_some_and(|object| {
            has_only(object, &["uri", "receipt", "expected"])
                && string(entry, "uri").is_some_and(|uri| !uri.is_empty())
                && member(entry, "receipt")
                    .and_then(Value::as_object)
                    .is_some()
                && member(entry, "expected")
                    .and_then(Value::as_object)
                    .is_some()
        });
        if !entry_valid {
            validator.error(
                "ASP-REPLAY-SCHEMA-001",
                ordinal,
                &path,
                "receipt resource entry is not the exact closed shape",
            );
            continue;
        }
        let receipt = member(entry, "receipt").expect("entry shape checked");
        let expected = member(entry, "expected").expect("entry shape checked");
        let unique = [
            ("uri", string(entry, "uri").unwrap_or_default(), &mut uris),
            (
                "receipt_id",
                string(receipt, "receipt_id").unwrap_or_default(),
                &mut receipt_ids,
            ),
            (
                "receipt_hash",
                string(receipt, "receipt_hash").unwrap_or_default(),
                &mut receipt_hashes,
            ),
        ];
        for (name, value, seen) in unique {
            if value.is_empty() || !seen.insert(value.to_owned()) {
                validator.error(
                    "ASP-REPLAY-RECEIPT-CHAIN-001",
                    ordinal,
                    format!("{path}/{name}"),
                    "receipt resource batch identity is empty or duplicated",
                );
            }
        }
        validate_receipt_wire_shape(receipt, ordinal, &mut validator);
        validate_expected_binding(receipt, expected, ordinal, &mut validator);
        validated_entries.push((ordinal, receipt));
    }
    // Approval receipts are prerequisite evidence. Validate them before the
    // ordinary receipts that link to them so side-link semantics are checked
    // even when ResourceLink order places the application receipt first.
    validated_entries.sort_by_key(|(_, receipt)| {
        if string(receipt, "receipt_type") == Some("approval") {
            0
        } else {
            1
        }
    });
    for (ordinal, receipt) in validated_entries {
        let (scope, surface, grant) = synthetic_context(receipt);
        check_receipt(receipt, ordinal, &scope, &surface, &grant, &mut validator)?;
    }
    validator.diagnostics.sort_by(|left, right| {
        (
            left.path.as_str(),
            left.check_id.as_str(),
            left.message.as_str(),
        )
            .cmp(&(
                right.path.as_str(),
                right.check_id.as_str(),
                right.message.as_str(),
            ))
    });
    Ok(ReceiptResourceReport {
        profile: RECEIPT_RESOURCE_REPORT_PROFILE.to_owned(),
        validation_scope: "local_structure_semantics_hashes_and_correlated_binding".to_owned(),
        verdict: if validator.has_errors {
            "invalid"
        } else {
            "valid"
        }
        .to_owned(),
        resources: resources.len(),
        signatures_verified: false,
        diagnostics: validator.diagnostics,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::hash::{POLICY_DOMAIN, RECEIPT_DOMAIN, object_hash};

    fn runtime_receipt() -> Value {
        let fixture: Value =
            serde_json::from_str(include_str!("../../tests/fixtures/event-receipt-flow.json"))
                .expect("fixture parses");
        member(&fixture, "records")
            .and_then(Value::as_array)
            .expect("records")
            .iter()
            .filter_map(|record| member(record, "body"))
            .find(|body| string(body, "receipt_type") == Some("runtime"))
            .expect("runtime receipt")
            .clone()
    }

    fn binding(receipt: &Value) -> Value {
        let mut binding = json!({
            "session_id": member(receipt, "session_id").unwrap(),
            "session_generation": member(receipt, "session_generation").unwrap(),
            "trace_id": member(receipt, "trace_id").unwrap(),
            "grant_id": member(receipt, "grant_id").unwrap(),
            "grant_hash": member(receipt, "grant_hash").unwrap(),
            "app_id": member(receipt, "app_id").unwrap(),
            "surface_hash": member(receipt, "surface_hash").unwrap(),
            "surface_version": member(receipt, "surface_version").unwrap(),
            "action_id": member(receipt, "action_id").unwrap(),
            "idempotency_key": member(receipt, "idempotency_key").unwrap(),
            "input_hash": member(receipt, "input_hash").unwrap(),
            "runtime": member(receipt, "runtime").unwrap(),
            "actor_agent": member(receipt, "actor_agent").unwrap(),
            "subject": member(receipt, "subject").unwrap(),
        });
        if let Some(execution) = member(receipt, "execution") {
            binding["execution"] = execution.clone();
            binding["execution_hash"] = member(receipt, "execution_hash")
                .expect("execution hash")
                .clone();
        }
        binding
    }

    fn request(receipt: &Value) -> Value {
        json!({
            "profile": RECEIPT_RESOURCE_REQUEST_PROFILE,
            "resources": [{
                "uri": "asp://receipt/runtime-1",
                "receipt": receipt,
                "expected": {
                    "receipt_id": member(receipt, "receipt_id").unwrap(),
                    "receipt_hash": member(receipt, "receipt_hash").unwrap(),
                    "receipt_type": "runtime",
                    "approval_role": null,
                    "binding": binding(receipt),
                    "signature_required": false,
                }
            }]
        })
    }

    #[test]
    fn authentic_unsigned_receipt_resource_is_valid() {
        let report = verify_receipt_resources(
            &serde_json::to_vec(&request(&runtime_receipt())).expect("serialize request"),
        )
        .expect("validation runs");
        assert_eq!(report.verdict, "valid", "{:?}", report.diagnostics);
        assert!(!report.signatures_verified);
    }

    #[test]
    fn binding_substitution_and_signatures_fail_closed() {
        let receipt = runtime_receipt();
        let mut substituted = request(&receipt);
        substituted["resources"][0]["expected"]["binding"]["app_id"] =
            Value::String("evil.example".to_owned());
        let report = verify_receipt_resources(
            &serde_json::to_vec(&substituted).expect("serialize substitution"),
        )
        .expect("validation runs");
        assert_eq!(report.verdict, "invalid");

        let mut signed = request(&receipt);
        signed["resources"][0]["receipt"]["receipt_signatures"] = json!([]);
        let report = verify_receipt_resources(
            &serde_json::to_vec(&signed).expect("serialize signature case"),
        )
        .expect("validation runs");
        assert_eq!(report.verdict, "invalid");
    }

    #[test]
    fn duplicate_resource_identity_and_partial_policy_fail_closed() {
        let receipt = runtime_receipt();
        let mut duplicated = request(&receipt);
        let duplicate = duplicated["resources"][0].clone();
        duplicated["resources"]
            .as_array_mut()
            .unwrap()
            .push(duplicate);
        let report = verify_receipt_resources(
            &serde_json::to_vec(&duplicated).expect("serialize duplicate"),
        )
        .expect("validation runs");
        assert_eq!(report.verdict, "invalid");

        let mut partial = request(&receipt);
        partial["resources"][0]["receipt"]["policy_decision"]
            .as_object_mut()
            .unwrap()
            .remove("matched_rules");
        let report = verify_receipt_resources(
            &serde_json::to_vec(&partial).expect("serialize partial policy"),
        )
        .expect("validation runs");
        assert_eq!(report.verdict, "invalid");
    }

    #[test]
    fn unregistered_extension_policy_reason_fails_closed() {
        let mut receipt = runtime_receipt();
        let policy = receipt["policy_decision"]
            .as_object_mut()
            .expect("policy decision");
        policy.insert(
            "reason_code".to_owned(),
            Value::String("https://example.com/reasons/deny-only".to_owned()),
        );
        let policy_hash = object_hash(
            POLICY_DOMAIN,
            &Value::Object(policy.clone()),
            &["policy_decision_hash"],
        )
        .expect("policy hash");
        policy.insert(
            "policy_decision_hash".to_owned(),
            Value::String(policy_hash.clone()),
        );
        receipt["policy_decision_hash"] = Value::String(policy_hash);
        receipt["receipt_hash"] = Value::String(
            object_hash(
                RECEIPT_DOMAIN,
                &receipt,
                &["receipt_hash", "receipt_signatures"],
            )
            .expect("receipt hash"),
        );

        let report = verify_receipt_resources(
            &serde_json::to_vec(&request(&receipt)).expect("serialize request"),
        )
        .expect("validation runs");
        assert_eq!(report.verdict, "invalid");
        assert!(
            report
                .diagnostics
                .iter()
                .any(|diagnostic| { diagnostic.path.ends_with("/policy_decision/reason_code") })
        );
    }

    #[test]
    fn runtime_closed_shape_accepts_optional_parent_and_error() {
        let mut receipt = runtime_receipt();
        receipt["parent_receipt_hash"] =
            Value::String("sha-256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA".to_owned());
        receipt["error"] = json!({
            "code": "local_policy_denied",
            "description": "The runtime denied forwarding.",
            "retryable": false,
        });
        receipt["receipt_hash"] = Value::String(
            object_hash(
                RECEIPT_DOMAIN,
                &receipt,
                &["receipt_hash", "receipt_signatures"],
            )
            .expect("receipt hash"),
        );
        let report = verify_receipt_resources(
            &serde_json::to_vec(&request(&receipt)).expect("serialize request"),
        )
        .expect("validation runs");
        assert_eq!(report.verdict, "valid", "{:?}", report.diagnostics);
    }
}
