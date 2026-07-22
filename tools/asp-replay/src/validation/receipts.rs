use std::collections::{BTreeMap, HashSet};

use serde_json::Value;

use crate::ReplayError;
use crate::hash::{
    ACTUAL_EFFECTS_DOMAIN, EXECUTION_DOMAIN, POLICY_DOMAIN, RECEIPT_DOMAIN, object_hash,
    valid_digest,
};
use crate::value::{
    has_only, member, string, timestamp_elapsed_within, timestamp_not_after, timestamp_shape,
    timestamp_within_seconds, uint,
};

use super::state::{
    ApprovalRequirement, PendingReference, PendingReferenceKind, ReceiptProjection, Validator,
};
use super::support::require_members;

pub(super) fn action_available(surface: &Value, grant: &Value, action_id: &str) -> bool {
    let declared = member(surface, "actions")
        .and_then(Value::as_array)
        .is_some_and(|actions| {
            actions
                .iter()
                .any(|action| string(action, "id") == Some(action_id))
        });
    let granted = member(grant, "actions")
        .and_then(Value::as_array)
        .is_some_and(|actions| {
            actions
                .iter()
                .any(|action| action.as_str() == Some(action_id))
        });
    declared && granted
}

pub(super) fn action_declaration<'a>(surface: &'a Value, action_id: &str) -> Option<&'a Value> {
    member(surface, "actions")?
        .as_array()?
        .iter()
        .find(|action| string(action, "id") == Some(action_id))
}

pub(super) fn approval_requirement(grant: &Value, action_id: &str) -> Option<ApprovalRequirement> {
    let approval_receipt =
        member(grant, "audit").and_then(|audit| member(audit, "approval_receipt"))?;
    if string(approval_receipt, "profile")
        != Some("https://github.com/0al-spec/agent-surface/profiles/approval-receipt/v1")
    {
        return None;
    }
    let requirement = member(approval_receipt, "requirements")?
        .as_array()?
        .iter()
        .find(|requirement| string(requirement, "action_id") == Some(action_id))?;
    Some(ApprovalRequirement {
        accepted_roles: member(requirement, "accepted_roles")?
            .as_array()?
            .iter()
            .map(|role| role.as_str().map(str::to_owned))
            .collect::<Option<HashSet<_>>>()?,
        max_age_seconds: uint(requirement, "max_age_seconds")?,
    })
}

pub(super) fn approval_links(receipt: &Value) -> Option<BTreeMap<String, String>> {
    let links = member(receipt, "approval_receipt_hashes")?.as_object()?;
    Some(
        links
            .iter()
            .filter_map(|(role, hash)| Some((role.clone(), hash.as_str()?.to_owned())))
            .collect(),
    )
}

pub(super) fn receipt_projection(receipt: &Value, ordinal: usize) -> Option<ReceiptProjection> {
    let execution = member(receipt, "execution").cloned();
    let actual_effect_ids = member(receipt, "actual_effects")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .filter_map(|effect| string(effect, "effect_id"))
        .map(str::to_owned)
        .collect();
    Some(ReceiptProjection {
        ordinal,
        receipt_type: string(receipt, "receipt_type")?.to_owned(),
        grant_hash: string(receipt, "grant_hash")?.to_owned(),
        surface_hash: string(receipt, "surface_hash")?.to_owned(),
        surface_version: string(receipt, "surface_version")?.to_owned(),
        session_id: string(receipt, "session_id")?.to_owned(),
        session_generation: uint(receipt, "session_generation")?,
        trace_id: string(receipt, "trace_id")?.to_owned(),
        linked_trace_id: string(receipt, "linked_trace_id").map(str::to_owned),
        action_id: string(receipt, "action_id")?.to_owned(),
        idempotency_key: string(receipt, "idempotency_key")?.to_owned(),
        input_hash: string(receipt, "input_hash")?.to_owned(),
        execution_hash: string(receipt, "execution_hash").map(str::to_owned),
        timestamp: string(receipt, "timestamp")?.to_owned(),
        target_receipt_hash: execution
            .as_ref()
            .and_then(|value| string(value, "target_receipt_hash"))
            .map(str::to_owned),
        execution,
        result: string(receipt, "result")?.to_owned(),
        effect_outcome: string(receipt, "effect_outcome").map(str::to_owned),
        actual_effect_ids,
        approval_role: member(receipt, "approval")
            .and_then(|approval| string(approval, "role"))
            .map(str::to_owned),
        approval_receipt_hashes: approval_links(receipt).unwrap_or_default(),
    })
}

pub(super) fn same_invocation_projection(
    left: &ReceiptProjection,
    right: &ReceiptProjection,
) -> bool {
    left.grant_hash == right.grant_hash
        && left.surface_hash == right.surface_hash
        && left.surface_version == right.surface_version
        && left.session_id == right.session_id
        && left.session_generation == right.session_generation
        && left.action_id == right.action_id
        && left.idempotency_key == right.idempotency_key
        && left.input_hash == right.input_hash
        && left.execution == right.execution
        && left.execution_hash == right.execution_hash
}

pub(super) fn validate_parent_projection(
    child: &ReceiptProjection,
    parent: &ReceiptProjection,
    validator: &mut Validator,
) {
    let path = format!("/records/{}/body/parent_receipt_hash", child.ordinal);
    if child.receipt_type == "approval" || parent.receipt_type == "approval" {
        validator.error(
            "ASP-REPLAY-RECEIPT-CHAIN-001",
            child.ordinal,
            &path,
            "approval receipt cannot participate in the parent chain",
        );
        return;
    }
    if !same_invocation_projection(child, parent) {
        validator.error(
            "ASP-REPLAY-RECEIPT-CHAIN-001",
            child.ordinal,
            &path,
            "receipt parent does not preserve the exact invocation projection",
        );
    }
    if child.trace_id != parent.trace_id
        && child.linked_trace_id.as_deref() != Some(parent.trace_id.as_str())
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-CHAIN-001",
            child.ordinal,
            &path,
            "receipt parent trace is neither preserved nor explicitly linked",
        );
    }
    if parent.receipt_type == "runtime" && child.receipt_type == "app" {
        let parent_runtime = parent.approval_receipt_hashes.get("runtime");
        let child_runtime = child.approval_receipt_hashes.get("runtime");
        if parent_runtime != child_runtime || (parent_runtime.is_none() && child_runtime.is_some())
        {
            validator.error(
                "ASP-REPLAY-RECEIPT-LINK-001",
                child.ordinal,
                format!("/records/{}/body/approval_receipt_hashes", child.ordinal),
                "application receipt did not preserve the runtime approval side link",
            );
        }
    }
}

pub(super) fn validate_approval_decision(
    receipt: &Value,
    ordinal: usize,
    scope: &Value,
    grant: &Value,
    validator: &mut Validator,
) {
    let path = format!("/records/{ordinal}/body");
    let Some(approval) = member(receipt, "approval") else {
        return;
    };
    let role = string(approval, "role").unwrap_or_default();
    let decided_by = string(approval, "decided_by").unwrap_or_default();
    let result = string(receipt, "result").unwrap_or_default();
    let policy = member(receipt, "policy_decision");
    let outcome = policy
        .and_then(|value| string(value, "outcome"))
        .unwrap_or_default();
    let reason = policy
        .and_then(|value| string(value, "reason_code"))
        .unwrap_or_default();
    let expected = match (role, result, decided_by) {
        ("runtime", "approved", "user") => Some(("allow", "approval_satisfied")),
        ("runtime", "denied", "user") => Some(("deny", "approval_denied")),
        ("runtime", "denied", "policy") => Some(("deny", "local_policy_denied")),
        ("application", "approved", "user" | "policy") => Some(("allow", "approval_satisfied")),
        ("application", "denied", "user") => Some(("deny", "approval_denied")),
        ("application", "denied", "policy") => Some(("deny", "app_policy_denied")),
        _ => None,
    };
    if expected != Some((outcome, reason)) {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            ordinal,
            format!("{path}/approval"),
            "approval receipt role, result, decision source, and policy outcome are inconsistent",
        );
    }
    let enforcer = policy.and_then(|value| member(value, "enforcer"));
    let expected_enforcer = match role {
        "runtime" => Some(("runtime", string(scope, "runtime_id"))),
        "application" => Some(("application", string(scope, "app_id"))),
        _ => None,
    };
    if expected_enforcer.is_none_or(|(kind, id)| {
        enforcer.and_then(|value| string(value, "type")) != Some(kind)
            || enforcer.and_then(|value| string(value, "id")) != id
    }) {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            ordinal,
            format!("{path}/policy_decision/enforcer"),
            "approval receipt enforcer does not match its producer role",
        );
    }
    if policy.and_then(|value| string(value, "evaluated_at")) != string(receipt, "timestamp") {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            ordinal,
            format!("{path}/policy_decision/evaluated_at"),
            "approval policy decision time does not equal receipt timestamp",
        );
    }
    let requirement =
        string(receipt, "action_id").and_then(|action_id| approval_requirement(grant, action_id));
    if requirement
        .as_ref()
        .is_none_or(|requirement| !requirement.accepted_roles.contains(role))
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            ordinal,
            format!("{path}/approval/role"),
            "approval receipt role is not accepted by the historical Grant requirement",
        );
    }
    let valid_until = string(approval, "valid_until");
    if result == "denied" && valid_until.is_some() {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            ordinal,
            format!("{path}/approval/valid_until"),
            "denied approval receipt must omit valid_until",
        );
    }
    if result == "approved"
        && let (Some(timestamp), Some(valid_until), Some(requirement)) = (
            string(receipt, "timestamp"),
            valid_until,
            requirement.as_ref(),
        )
        && !timestamp_within_seconds(timestamp, valid_until, requirement.max_age_seconds)
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            ordinal,
            format!("{path}/approval/valid_until"),
            "approved receipt validity exceeds the historical Grant maximum age",
        );
    }
    if result == "approved"
        && let (Some(valid_until), Some(grant_expiry)) = (
            valid_until,
            member(grant, "constraints").and_then(|value| string(value, "expires_at")),
        )
        && !timestamp_not_after(valid_until, grant_expiry)
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            ordinal,
            format!("{path}/approval/valid_until"),
            "approved receipt validity exceeds the historical Grant expiry",
        );
    }
}

pub(super) fn validate_approval_map_shape(
    source: &ReceiptProjection,
    surface: &Value,
    grant: &Value,
    validator: &mut Validator,
) {
    let Some(action) = action_declaration(surface, &source.action_id) else {
        return;
    };
    let mode = string(action, "approval").unwrap_or("none");
    let accepted_roles = approval_requirement(grant, &source.action_id)
        .map(|requirement| requirement.accepted_roles);
    let actual: HashSet<&str> = source
        .approval_receipt_hashes
        .keys()
        .map(String::as_str)
        .collect();
    let valid = match (source.receipt_type.as_str(), mode, accepted_roles.as_ref()) {
        ("approval", _, _) => actual.is_empty(),
        (_, "none", _) => actual.is_empty(),
        (_, _, None) => actual.is_empty(),
        ("runtime", "app", Some(_)) => actual.is_empty(),
        ("runtime", "runtime" | "runtime_and_app", Some(roles)) => {
            roles.contains("runtime") && actual == HashSet::from(["runtime"])
        }
        ("runtime", "user_or_app", Some(roles)) => {
            (roles.contains("runtime") && actual == HashSet::from(["runtime"]))
                || (roles.contains("application") && actual.is_empty())
        }
        ("app", "runtime", Some(roles)) => {
            roles.contains("runtime") && actual == HashSet::from(["runtime"])
        }
        ("app", "app", Some(roles)) => {
            roles.contains("application") && actual == HashSet::from(["application"])
        }
        ("app", "runtime_and_app", Some(roles)) => {
            roles.contains("runtime")
                && roles.contains("application")
                && actual == HashSet::from(["application", "runtime"])
        }
        ("app", "user_or_app", Some(roles)) => {
            actual.len() == 1 && actual.iter().all(|role| roles.contains(*role))
        }
        _ => false,
    };
    if !valid {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            source.ordinal,
            format!("/records/{}/body/approval_receipt_hashes", source.ordinal),
            "approval side-link role map does not satisfy the manifest mode and Grant requirement",
        );
    }
}

pub(super) fn validate_approval_target(
    source: &ReceiptProjection,
    role: &str,
    target: &ReceiptProjection,
    validator: &mut Validator,
) {
    let path = format!(
        "/records/{}/body/approval_receipt_hashes/{role}",
        source.ordinal
    );
    if target.receipt_type != "approval"
        || target.result != "approved"
        || target.approval_role.as_deref() != Some(role)
        || !same_invocation_projection(source, target)
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            source.ordinal,
            path,
            "approval side link does not resolve to an approved role-matched invocation projection",
        );
    }
}

pub(super) fn relationship_projection(
    entries: Option<&Value>,
    action_id: &str,
    mode: Option<&str>,
) -> Option<(Vec<String>, u64)> {
    entries?.as_array()?.iter().find_map(|entry| {
        if string(entry, "action_id") != Some(action_id)
            || mode.is_some_and(|expected| string(entry, "mode") != Some(expected))
        {
            return None;
        }
        let mut effects: Vec<String> = member(entry, "effect_ids")?
            .as_array()?
            .iter()
            .map(|value| value.as_str().map(str::to_owned))
            .collect::<Option<Vec<_>>>()?;
        effects.sort();
        effects.dedup();
        Some((effects, uint(entry, "recovery_window_seconds")?))
    })
}

pub(super) fn validate_recovery_target(
    source: &ReceiptProjection,
    target: &ReceiptProjection,
    surface: &Value,
    validator: &mut Validator,
) {
    let path = format!(
        "/records/{}/body/execution/target_receipt_hash",
        source.ordinal
    );
    let mode = source
        .execution
        .as_ref()
        .and_then(|execution| string(execution, "mode"));
    if target.receipt_type != "app" || !matches!(mode, Some("compensate" | "revert")) {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            source.ordinal,
            &path,
            "recovery target must be an earlier application receipt for compensate or revert",
        );
        return;
    }
    if !matches!(
        target.effect_outcome.as_deref(),
        Some("applied" | "partially_applied")
    ) {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            source.ordinal,
            &path,
            "recovery target does not carry a recoverable effect outcome",
        );
    }
    let Some(source_action) = action_declaration(surface, &source.action_id) else {
        return;
    };
    let Some(target_action) = action_declaration(surface, &target.action_id) else {
        return;
    };
    let source_execution = member(source_action, "execution");
    let target_execution = member(target_action, "execution");
    let source_operation = source_execution.and_then(|value| string(value, "operation_id"));
    let target_operation = target_execution.and_then(|value| string(value, "operation_id"));
    let outbound = relationship_projection(
        target_execution.and_then(|value| member(value, "recovery_actions")),
        &source.action_id,
        mode,
    );
    let reciprocal = relationship_projection(
        source_execution.and_then(|value| member(value, "target_actions")),
        &target.action_id,
        None,
    );
    if string(target_execution.unwrap_or(&Value::Null), "mode") != Some("commit")
        || target
            .execution
            .as_ref()
            .and_then(|execution| string(execution, "mode"))
            != Some("commit")
        || string(source_execution.unwrap_or(&Value::Null), "mode") != mode
        || source_operation.is_none()
        || source_operation != target_operation
        || outbound.is_none()
        || outbound != reciprocal
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            source.ordinal,
            &path,
            "recovery target lacks an exact reciprocal manifest relationship",
        );
        return;
    }
    if let Some((effect_ids, _)) = reciprocal
        && effect_ids
            .iter()
            .any(|effect_id| !target.actual_effect_ids.contains(effect_id))
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            source.ordinal,
            path,
            "recovery relationship names an effect absent from the target receipt",
        );
    } else if let Some((_, recovery_window_seconds)) = outbound
        && !timestamp_elapsed_within(
            &target.timestamp,
            &source.timestamp,
            recovery_window_seconds,
        )
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            source.ordinal,
            path,
            "recovery target timestamp falls outside the declared recovery window",
        );
    }
}

pub(super) fn check_receipt(
    receipt: &Value,
    ordinal: usize,
    scope: &Value,
    surface: &Value,
    grant: &Value,
    validator: &mut Validator,
) -> Result<(), ReplayError> {
    let path = format!("/records/{ordinal}/body");
    let common = [
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
    if !require_members(
        receipt,
        &common,
        "ASP-REPLAY-RECEIPT-HASH-001",
        ordinal,
        &path,
        "receipt is missing a required identity, trace, decision, input, or result member",
        validator,
    ) {
        return Ok(());
    }
    let typed_strings = [
        "receipt_id",
        "receipt_type",
        "receipt_hash",
        "grant_id",
        "grant_hash",
        "session_id",
        "trace_id",
        "span_id",
        "action_id",
        "app_id",
        "surface_version",
        "surface_hash",
        "idempotency_key",
        "input_hash",
        "policy_decision_hash",
        "timestamp",
        "result",
    ];
    let typed = typed_strings
        .iter()
        .all(|name| string(receipt, name).is_some())
        && uint(receipt, "session_generation").is_some()
        && ["runtime", "actor_agent", "subject", "policy_decision"]
            .iter()
            .all(|name| member(receipt, name).and_then(Value::as_object).is_some());
    if !typed {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            &path,
            "receipt required members have invalid JSON types",
        );
        return Ok(());
    }
    let Some(receipt_id) = string(receipt, "receipt_id") else {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            &path,
            "receipt identity members have invalid types",
        );
        return Ok(());
    };
    let Some(receipt_type) = string(receipt, "receipt_type") else {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            &path,
            "receipt identity members have invalid types",
        );
        return Ok(());
    };
    let Some(receipt_hash) = string(receipt, "receipt_hash") else {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            &path,
            "receipt identity members have invalid types",
        );
        return Ok(());
    };
    if !valid_digest(receipt_hash) {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            format!("{path}/receipt_hash"),
            "receipt hash is not a canonical SHA-256 digest",
        );
        return Ok(());
    }
    if !["runtime", "app", "approval"].contains(&receipt_type) {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            &path,
            "receipt type is not supported by the replay profile",
        );
    }
    if string(receipt, "timestamp").is_none_or(|time| !timestamp_shape(time)) {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            format!("{path}/timestamp"),
            "receipt timestamp must be a real RFC 3339 UTC instant without leap seconds",
        );
    }
    let action_requires_execution = string(receipt, "action_id")
        .and_then(|action_id| {
            member(surface, "actions")?
                .as_array()?
                .iter()
                .find(|action| string(action, "id") == Some(action_id))
        })
        .and_then(|action| member(action, "execution"))
        .and_then(|execution| string(execution, "mode"))
        .is_some_and(|mode| ["reserve", "commit", "compensate", "revert"].contains(&mode));
    let execution_pair = (
        member(receipt, "execution").is_some(),
        member(receipt, "execution_hash").is_some(),
    );
    if execution_pair.0 != execution_pair.1 || (action_requires_execution && !execution_pair.0) {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            &path,
            "receipt execution and execution_hash must appear together when applicable",
        );
    }
    let effects_pair = (
        member(receipt, "actual_effects").is_some(),
        member(receipt, "actual_effects_hash").is_some(),
    );
    if effects_pair.0 != effects_pair.1 {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            &path,
            "receipt actual_effects and actual_effects_hash must appear together",
        );
    }
    if receipt_type == "approval" {
        let mut required = common.to_vec();
        required.extend(["execution", "execution_hash", "approval"]);
        if !require_members(
            receipt,
            &required,
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            &path,
            "approval receipt is missing a required closed-shape member",
            validator,
        ) {
            return Ok(());
        }
        let allowed = [
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
            "execution",
            "execution_hash",
            "policy_decision_hash",
            "policy_decision",
            "approval",
            "timestamp",
            "result",
            "receipt_signatures",
        ];
        if !receipt
            .as_object()
            .is_some_and(|object| has_only(object, &allowed))
        {
            validator.error(
                "ASP-REPLAY-RECEIPT-HASH-001",
                ordinal,
                &path,
                "approval receipt contains a member outside its closed wire shape",
            );
        }
        let approval_required: &[&str] = if string(receipt, "result") == Some("approved") {
            &["approval_id", "role", "decided_by", "valid_until"]
        } else {
            &["approval_id", "role", "decided_by"]
        };
        let Some(approval) = member(receipt, "approval") else {
            return Ok(());
        };
        if !require_members(
            approval,
            approval_required,
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            &format!("{path}/approval"),
            "approval projection is missing a required closed-shape member",
            validator,
        ) {
            return Ok(());
        }
        let approval_allowed = ["approval_id", "role", "decided_by", "valid_until"];
        if !approval
            .as_object()
            .is_some_and(|object| has_only(object, &approval_allowed))
        {
            validator.error(
                "ASP-REPLAY-RECEIPT-HASH-001",
                ordinal,
                format!("{path}/approval"),
                "approval projection contains a member outside its closed wire shape",
            );
        }
        if let Some(valid_until) = string(approval, "valid_until")
            && (string(receipt, "timestamp").is_none_or(|timestamp| {
                !timestamp_shape(valid_until)
                    || !timestamp_not_after(timestamp, valid_until)
                    || timestamp == valid_until
            }))
        {
            validator.error(
                "ASP-REPLAY-RECEIPT-HASH-001",
                ordinal,
                format!("{path}/approval/valid_until"),
                "approved receipt validity must be a real UTC instant not before its timestamp",
            );
        }
        validate_approval_decision(receipt, ordinal, scope, grant, validator);
    }
    let actual = object_hash(
        RECEIPT_DOMAIN,
        receipt,
        &["receipt_hash", "receipt_signatures"],
    )?;
    if receipt_hash != actual {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            format!("{path}/receipt_hash"),
            "receipt hash does not match the exact receipt",
        );
    }
    if let Some(policy) = member(receipt, "policy_decision")
        && let Some(expected) = string(receipt, "policy_decision_hash")
    {
        let actual = object_hash(POLICY_DOMAIN, policy, &["policy_decision_hash"])?;
        if expected != actual || string(policy, "policy_decision_hash") != Some(expected) {
            validator.error(
                "ASP-REPLAY-RECEIPT-HASH-001",
                ordinal,
                format!("{path}/policy_decision_hash"),
                "receipt Policy Decision hash binding is invalid",
            );
        }
    }
    if let Some(execution) = member(receipt, "execution")
        && let Some(expected) = string(receipt, "execution_hash")
    {
        let actual = object_hash(EXECUTION_DOMAIN, execution, &["execution_token"])?;
        if expected != actual {
            validator.error(
                "ASP-REPLAY-RECEIPT-HASH-001",
                ordinal,
                format!("{path}/execution_hash"),
                "receipt execution hash binding is invalid",
            );
        }
    }
    if let Some(effects) = member(receipt, "actual_effects")
        && let Some(expected) = string(receipt, "actual_effects_hash")
    {
        let actual = object_hash(ACTUAL_EFFECTS_DOMAIN, effects, &[])?;
        if expected != actual {
            validator.error(
                "ASP-REPLAY-RECEIPT-HASH-001",
                ordinal,
                format!("{path}/actual_effects_hash"),
                "receipt actual-effects hash binding is invalid",
            );
        }
    }
    for (member_name, scope_name) in [
        ("grant_id", "grant_id"),
        ("grant_hash", "grant_hash"),
        ("session_id", "session_id"),
        ("surface_version", "surface_version"),
        ("surface_hash", "surface_hash"),
    ] {
        if let Some(value) = string(receipt, member_name)
            && Some(value) != string(scope, scope_name)
        {
            validator.error(
                "ASP-REPLAY-RECEIPT-CHAIN-001",
                ordinal,
                format!("{path}/{member_name}"),
                "receipt conflicts with the replay scope",
            );
        }
    }
    if uint(receipt, "session_generation") != uint(scope, "session_generation") {
        validator.error(
            "ASP-REPLAY-RECEIPT-CHAIN-001",
            ordinal,
            format!("{path}/session_generation"),
            "receipt generation conflicts with the replay scope",
        );
    }
    let nested_bindings = [
        (string(receipt, "app_id"), string(scope, "app_id"), "app_id"),
        (
            member(receipt, "subject").and_then(|value| string(value, "user")),
            string(scope, "subject_user"),
            "subject/user",
        ),
        (
            member(receipt, "runtime").and_then(|value| string(value, "runtime_id")),
            string(scope, "runtime_id"),
            "runtime/runtime_id",
        ),
        (
            member(receipt, "actor_agent").and_then(|value| string(value, "agent_id")),
            string(scope, "agent_id"),
            "actor_agent/agent_id",
        ),
        (
            member(receipt, "actor_agent")
                .and_then(|value| string(value, "identity_evidence_hash")),
            string(scope, "identity_evidence_hash"),
            "actor_agent/identity_evidence_hash",
        ),
    ];
    for (actual, expected, member_path) in nested_bindings {
        if actual != expected {
            validator.error(
                "ASP-REPLAY-RECEIPT-CHAIN-001",
                ordinal,
                format!("{path}/{member_path}"),
                "receipt participant binding conflicts with the replay scope",
            );
        }
    }
    if let Some(action_id) = string(receipt, "action_id")
        && !action_available(surface, grant, action_id)
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-CHAIN-001",
            ordinal,
            format!("{path}/action_id"),
            "receipt action is absent from the historical Surface or Grant",
        );
    }
    if let Some(previous) = validator.receipts_by_id.get(receipt_id) {
        if previous != receipt_hash {
            validator.error(
                "ASP-REPLAY-RECEIPT-CHAIN-001",
                ordinal,
                format!("{path}/receipt_id"),
                "receipt id was reused for another receipt hash",
            );
        }
    } else {
        validator
            .receipts_by_id
            .insert(receipt_id.to_owned(), receipt_hash.to_owned());
    }
    if let Some(links) = member(receipt, "approval_receipt_hashes")
        && !links.as_object().is_some_and(|object| {
            object.keys().all(|role| {
                matches!(role.as_str(), "runtime" | "application")
                    && object
                        .get(role)
                        .and_then(Value::as_str)
                        .is_some_and(valid_digest)
            })
        })
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            ordinal,
            format!("{path}/approval_receipt_hashes"),
            "approval side-link map must be closed and contain canonical role hashes",
        );
    }
    let execution_mode = member(receipt, "execution").and_then(|value| string(value, "mode"));
    let nested_target =
        member(receipt, "execution").and_then(|value| string(value, "target_receipt_hash"));
    if matches!(execution_mode, Some("compensate" | "revert")) != nested_target.is_some() {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            ordinal,
            format!("{path}/execution/target_receipt_hash"),
            "recovery execution and target receipt hash must appear together",
        );
    }
    let Some(projection) = receipt_projection(receipt, ordinal) else {
        validator.error(
            "ASP-REPLAY-RECEIPT-CHAIN-001",
            ordinal,
            &path,
            "receipt linkage projection contains invalid member types",
        );
        validator.receipt_hashes.insert(receipt_hash.to_owned());
        return Ok(());
    };
    validate_approval_map_shape(&projection, surface, grant, validator);
    if let Some(parent) = string(receipt, "parent_receipt_hash") {
        if !valid_digest(parent) {
            validator.error(
                "ASP-REPLAY-RECEIPT-CHAIN-001",
                ordinal,
                format!("{path}/parent_receipt_hash"),
                "receipt parent reference is not a canonical SHA-256 digest",
            );
        } else {
            validator.receipt_parents.insert(parent.to_owned());
            if let Some(parent_projection) = validator.receipts_by_hash.get(parent).cloned() {
                validate_parent_projection(&projection, &parent_projection, validator);
            } else {
                validator.pending_references.push(PendingReference {
                    check_id: "ASP-REPLAY-RECEIPT-CHAIN-001",
                    ordinal,
                    path: format!("{path}/parent_receipt_hash"),
                    target: parent.to_owned(),
                    kind: PendingReferenceKind::ReceiptParent,
                });
            }
        }
    } else {
        validator.receipt_roots.insert(receipt_hash.to_owned());
    }
    if receipt_type == "approval" && member(receipt, "parent_receipt_hash").is_some() {
        validator.error(
            "ASP-REPLAY-RECEIPT-CHAIN-001",
            ordinal,
            format!("{path}/parent_receipt_hash"),
            "approval receipt must be a root",
        );
    }
    for (role, hash) in &projection.approval_receipt_hashes {
        if let Some(target) = validator.receipts_by_hash.get(hash).cloned() {
            validate_approval_target(&projection, role, &target, validator);
        } else {
            validator.pending_references.push(PendingReference {
                check_id: "ASP-REPLAY-RECEIPT-LINK-001",
                ordinal,
                path: format!("{path}/approval_receipt_hashes/{role}"),
                target: hash.clone(),
                kind: PendingReferenceKind::ApprovalSideLink { role: role.clone() },
            });
        }
    }
    if let Some(target_hash) = &projection.target_receipt_hash {
        if !valid_digest(target_hash) {
            validator.error(
                "ASP-REPLAY-RECEIPT-LINK-001",
                ordinal,
                format!("{path}/execution/target_receipt_hash"),
                "recovery target is not a canonical SHA-256 digest",
            );
        } else if let Some(target) = validator.receipts_by_hash.get(target_hash).cloned() {
            validate_recovery_target(&projection, &target, surface, validator);
        } else {
            validator.pending_references.push(PendingReference {
                check_id: "ASP-REPLAY-RECEIPT-LINK-001",
                ordinal,
                path: format!("{path}/execution/target_receipt_hash"),
                target: target_hash.clone(),
                kind: PendingReferenceKind::RecoveryTarget,
            });
        }
    }
    validator.receipt_hashes.insert(receipt_hash.to_owned());
    if let Some(previous) = validator
        .receipts_by_hash
        .insert(receipt_hash.to_owned(), projection)
        && previous.ordinal != ordinal
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-CHAIN-001",
            ordinal,
            format!("{path}/receipt_hash"),
            "receipt hash was repeated by another replay record",
        );
    }
    Ok(())
}
