//! Application-side implementation used by the independent reference slice.
//!
//! The conformance entry points consume only the closed stimulus view supplied
//! by the suite. They do not read vector expectations, fixture labels, or the
//! mock implementation.

use base64::Engine as _;
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::io::{self, Read};
use thiserror::Error;

pub const SUBJECT_PROTOCOL: &str = "asp-reference-subject/1";
pub const SP: &str = "https://github.com/0al-spec/agent-surface/conformance/surface-publisher/v1";
pub const GI: &str = "https://github.com/0al-spec/agent-surface/conformance/grant-issuer/v1";
pub const AE: &str = "https://github.com/0al-spec/agent-surface/conformance/action-executor/v1";
pub const RP: &str = "https://github.com/0al-spec/agent-surface/conformance/receipt-producer/v1";

#[derive(Debug, Error)]
pub enum AppError {
    #[error("cannot read JSON input: {0}")]
    Io(#[from] io::Error),
    #[error("invalid JSON input: {0}")]
    Json(#[from] serde_json::Error),
    #[error("invalid subject invocation: {0}")]
    Invalid(String),
}

#[derive(Debug, Deserialize)]
pub struct SubjectInvocation {
    pub subject_protocol: String,
    pub case: Case,
}

#[derive(Debug, Deserialize)]
pub struct Case {
    pub profile_id: String,
    #[serde(default)]
    pub producer_role: Option<String>,
    pub initial_state: Vec<InitialState>,
    pub stimulus: Stimulus,
}

#[derive(Debug, Deserialize)]
pub struct InitialState {
    pub state: String,
    pub value: Value,
}

#[derive(Debug, Deserialize)]
pub struct Stimulus {
    pub operation: String,
    pub fixture: Fixture,
}

#[derive(Debug, Deserialize)]
pub struct Fixture {
    pub document: Value,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct StateDelta {
    pub state: String,
    pub before: Value,
    pub after: Value,
}

#[derive(Debug, Serialize, PartialEq)]
pub struct SubjectResult {
    pub schema_version: u8,
    pub decision: String,
    pub tokens: Vec<String>,
    pub state_deltas: Vec<StateDelta>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub asp_error: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub policy_reason: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub match_reason: Option<String>,
}

struct Transition {
    before: BTreeMap<String, Value>,
    after: BTreeMap<String, Value>,
}

impl Transition {
    fn new(initial: Vec<InitialState>) -> Result<Self, AppError> {
        let mut before = BTreeMap::new();
        for item in initial {
            if before.insert(item.state.clone(), item.value).is_some() {
                return Err(AppError::Invalid(format!(
                    "duplicate initial state: {}",
                    item.state
                )));
            }
        }
        Ok(Self {
            after: before.clone(),
            before,
        })
    }

    fn increment(&mut self, name: &str) -> Result<(), AppError> {
        let value = self
            .after
            .get_mut(name)
            .ok_or_else(|| AppError::Invalid(format!("missing initial state: {name}")))?;
        let number = value
            .as_i64()
            .ok_or_else(|| AppError::Invalid(format!("state is not an integer: {name}")))?;
        *value = Value::from(number + 1);
        Ok(())
    }

    fn set(&mut self, name: &str, value: Value) -> Result<(), AppError> {
        let slot = self
            .after
            .get_mut(name)
            .ok_or_else(|| AppError::Invalid(format!("missing initial state: {name}")))?;
        *slot = value;
        Ok(())
    }

    fn result(
        self,
        decision: &str,
        tokens: &[&str],
        asp_error: Option<&str>,
        policy_reason: Option<&str>,
        match_reason: Option<&str>,
    ) -> SubjectResult {
        let state_deltas = self
            .before
            .into_iter()
            .map(|(state, before)| StateDelta {
                after: self.after[&state].clone(),
                state,
                before,
            })
            .collect();
        SubjectResult {
            schema_version: 1,
            decision: decision.to_owned(),
            tokens: tokens.iter().map(|item| (*item).to_owned()).collect(),
            state_deltas,
            asp_error: asp_error.map(str::to_owned),
            policy_reason: policy_reason.map(str::to_owned),
            match_reason: match_reason.map(str::to_owned),
        }
    }
}

fn object<'a>(value: &'a Value, name: &str) -> Result<&'a Map<String, Value>, AppError> {
    value
        .get(name)
        .and_then(Value::as_object)
        .ok_or_else(|| AppError::Invalid(format!("missing object section: {name}")))
}

fn string<'a>(object: &'a Map<String, Value>, name: &str) -> Option<&'a str> {
    object.get(name).and_then(Value::as_str)
}

fn strings<'a>(object: &'a Map<String, Value>, name: &str) -> Option<Vec<&'a str>> {
    object
        .get(name)?
        .as_array()?
        .iter()
        .map(Value::as_str)
        .collect()
}

fn finish(
    transition: Transition,
    decision: &str,
    tokens: &[&str],
) -> Result<SubjectResult, AppError> {
    Ok(transition.result(decision, tokens, None, None, None))
}

fn finish_error(
    transition: Transition,
    decision: &str,
    tokens: &[&str],
    asp_error: &str,
) -> Result<SubjectResult, AppError> {
    Ok(transition.result(decision, tokens, Some(asp_error), None, None))
}

fn evaluate_surface(
    document: &Value,
    mut state: Transition,
    operation: &str,
) -> Result<SubjectResult, AppError> {
    if operation != "publish_manifest" {
        return Err(AppError::Invalid(format!(
            "Surface Publisher does not support {operation}"
        )));
    }
    let surface = object(document, "surface")?;
    let incompatible = string(surface, "references") != Some("complete")
        || string(surface, "candidate_hash") != string(surface, "retained_hash")
        || (string(surface, "mode") == Some("proposal_only")
            && string(surface, "action_semantics") != Some("closed_read_propose"));
    if incompatible {
        return finish_error(
            state,
            "rejected",
            &["manifest_rejected"],
            "surface_incompatible",
        );
    }
    state.increment("manifest.accepted_count")?;
    state.increment("surface.version_binding_count")?;
    finish(state, "accepted", &["manifest_published"])
}

fn evaluate_grant(
    document: &Value,
    mut state: Transition,
    operation: &str,
) -> Result<SubjectResult, AppError> {
    let surface = object(document, "surface")?;
    let grant = object(document, "grant")?;
    match operation {
        "issue_grant" => {
            if string(surface, "status") != Some("current") {
                return finish(
                    state,
                    "rejected",
                    &["grant_rejected", "current_state_checked"],
                );
            }
            let requested = strings(grant, "requested_actions")
                .ok_or_else(|| AppError::Invalid("requested_actions is not an array".into()))?;
            let issued = strings(grant, "issued_actions")
                .ok_or_else(|| AppError::Invalid("issued_actions is not an array".into()))?;
            if !issued.iter().all(|item| requested.contains(item)) {
                return finish(state, "rejected", &["grant_rejected"]);
            }
            if string(grant, "companion_closure") != Some("closed") {
                return finish(state, "rejected", &["grant_rejected"]);
            }
            if string(grant, "passport_status") != Some("current") {
                return finish(
                    state,
                    "rejected",
                    &["grant_rejected", "current_state_checked"],
                );
            }
            state.increment("grant.issued_count")?;
            state.increment("credential.issued_count")?;
            finish(state, "accepted", &["grant_issued", "tuple_checked"])
        }
        "revoke_grant" => {
            if string(grant, "revocation_request_hash")
                != string(grant, "recorded_revocation_request_hash")
            {
                return Err(AppError::Invalid(
                    "revocation request does not match its record".into(),
                ));
            }
            if string(grant, "status") == Some("revoked")
                || string(grant, "revocation_state") == Some("revoked")
            {
                return finish(
                    state,
                    "replayed",
                    &[
                        "grant_revoked",
                        "original_revocation_replayed",
                        "revocation_confirmed",
                    ],
                );
            }
            state.set("grant.lifecycle", Value::from("revoked"))?;
            for name in [
                "grant.child_active_count",
                "credential.active_count",
                "proof_session.active_count",
                "execution_token.active_count",
                "reservation.active_count",
            ] {
                state.set(name, Value::from(0))?;
            }
            for name in [
                "control_event.emitted_count",
                "revocation.effective_count",
                "revocation.confirmed_count",
                "revocation.fence_count",
            ] {
                state.increment(name)?;
            }
            state.set("revocation.confirmed_after_effective", Value::from(true))?;
            finish(
                state,
                "accepted",
                &[
                    "grant_revoked",
                    "child_grant_revoked",
                    "credential_invalidated",
                    "proof_session_invalidated",
                    "execution_token_invalidated",
                    "reservation_invalidated",
                    "control_event_emitted",
                    "revocation_fence_established",
                    "revocation_confirmed",
                ],
            )
        }
        _ => Err(AppError::Invalid(format!(
            "Grant Issuer does not support {operation}"
        ))),
    }
}

fn evaluate_action(
    document: &Value,
    mut state: Transition,
    operation: &str,
) -> Result<SubjectResult, AppError> {
    let grant = object(document, "grant")?;
    let execution = object(document, "execution")?;
    match operation {
        "replay_action" => {
            if string(execution, "input_schema_hash")
                != string(execution, "recorded_input_schema_hash")
            {
                return finish_error(
                    state,
                    "rejected",
                    &[
                        "input_schema_checked",
                        "normalization_checked",
                        "action_rejected",
                        "approval_not_reopened",
                    ],
                    "idempotency_conflict",
                );
            }
            if string(execution, "normalization") != Some("fixed_point") {
                return finish_error(
                    state,
                    "rejected",
                    &[
                        "input_schema_checked",
                        "normalization_checked",
                        "action_rejected",
                    ],
                    "input_not_normalized",
                );
            }
            let conflict = [
                ("input_hash", "recorded_input_hash"),
                ("execution_hash", "recorded_execution_hash"),
                ("approval_hash", "recorded_approval_hash"),
            ]
            .iter()
            .any(|(current, recorded)| string(execution, current) != string(execution, recorded));
            if conflict {
                return finish_error(
                    state,
                    "rejected",
                    &["action_rejected", "approval_not_reopened"],
                    "idempotency_conflict",
                );
            }
            finish(
                state,
                "replayed",
                &["original_result_replayed", "same_receipt_replayed"],
            )
        }
        "invoke_action" => {
            if string(execution, "normalization") != Some("fixed_point") {
                return finish_error(
                    state,
                    "rejected",
                    &[
                        "input_schema_checked",
                        "normalization_checked",
                        "action_rejected",
                    ],
                    "input_not_normalized",
                );
            }
            if string(execution, "sender_credential_audience")
                != string(execution, "bound_credential_audience")
            {
                return finish_error(
                    state,
                    "rejected",
                    &["credential_rejected", "tuple_checked", "action_rejected"],
                    "grant_proof_invalid",
                );
            }
            if string(execution, "proof_session_binding")
                != string(execution, "bound_session_binding")
            {
                return finish_error(
                    state,
                    "rejected",
                    &["proof_rejected", "tuple_checked", "action_rejected"],
                    "grant_proof_invalid",
                );
            }
            if string(grant, "claimed_issuer") != string(grant, "issuer") {
                return finish_error(
                    state,
                    "rejected",
                    &["action_rejected", "tuple_checked"],
                    "integrity_mismatch",
                );
            }
            if string(grant, "status") != Some("active")
                || string(grant, "revocation_state") == Some("revoked")
            {
                return finish_error(
                    state,
                    "rejected",
                    &["action_rejected", "current_state_checked"],
                    "grant_revoked",
                );
            }
            if string(execution, "runtime_identity") != string(execution, "bound_runtime_identity")
                || string(execution, "attestation") != Some("current")
            {
                return finish_error(
                    state,
                    "rejected",
                    &["action_rejected", "current_state_checked"],
                    "runtime_untrusted",
                );
            }
            if string(execution, "policy") != Some("allow") {
                state.increment("receipt.application_count")?;
                return finish_error(
                    state,
                    "rejected",
                    &[
                        "action_rejected",
                        "denial_recorded",
                        "application_receipt_emitted",
                    ],
                    "risk_denied",
                );
            }
            for name in [
                "action.dispatch_count",
                "action.effect_count",
                "idempotency.record_count",
                "budget.application_charge",
                "receipt.application_count",
            ] {
                state.increment(name)?;
            }
            finish(
                state,
                "accepted",
                &[
                    "action_accepted",
                    "tuple_checked",
                    "current_state_checked",
                    "application_receipt_emitted",
                ],
            )
        }
        _ => Err(AppError::Invalid(format!(
            "Action Executor does not support {operation}"
        ))),
    }
}

fn evaluate_receipt(
    document: &Value,
    mut state: Transition,
    operation: &str,
    producer_role: Option<&str>,
) -> Result<SubjectResult, AppError> {
    if producer_role != Some("application") {
        return Err(AppError::Invalid(
            "this entry point only produces application receipts".into(),
        ));
    }
    let receipt = object(document, "receipt")?;
    if operation == "verify_receipt" {
        if string(receipt, "integrity") != Some("valid") {
            return finish_error(
                state,
                "rejected",
                &["receipt_rejected"],
                "integrity_mismatch",
            );
        }
        return finish(state, "accepted", &["receipt_verified"]);
    }
    if operation != "produce_receipt" {
        return Err(AppError::Invalid(format!(
            "Receipt Producer does not support {operation}"
        )));
    }
    if string(receipt, "authority_use") != Some("prohibited") {
        return finish(state, "rejected", &["receipt_rejected"]);
    }
    if string(receipt, "claimed_observation") != Some("application_effect")
        || string(receipt, "integrity") != Some("valid")
        || string(receipt, "origin") != Some("observed")
    {
        return finish_error(
            state,
            "rejected",
            &["receipt_rejected"],
            "integrity_mismatch",
        );
    }
    state.increment("receipt.application_count")?;
    finish(
        state,
        "accepted",
        &["application_receipt_emitted", "receipt_verified"],
    )
}

pub fn evaluate(invocation: SubjectInvocation) -> Result<SubjectResult, AppError> {
    if invocation.subject_protocol != SUBJECT_PROTOCOL {
        return Err(AppError::Invalid("unsupported subject protocol".into()));
    }
    let case = invocation.case;
    let state = Transition::new(case.initial_state)?;
    let document = &case.stimulus.fixture.document;
    match case.profile_id.as_str() {
        SP => evaluate_surface(document, state, &case.stimulus.operation),
        GI => evaluate_grant(document, state, &case.stimulus.operation),
        AE => evaluate_action(document, state, &case.stimulus.operation),
        RP => evaluate_receipt(
            document,
            state,
            &case.stimulus.operation,
            case.producer_role.as_deref(),
        ),
        profile => Err(AppError::Invalid(format!(
            "unsupported application profile: {profile}"
        ))),
    }
}

pub fn run_subject(allowed_profiles: &[&str]) -> Result<(), AppError> {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input)?;
    let invocation: SubjectInvocation = serde_json::from_str(&input)?;
    if !allowed_profiles.contains(&invocation.case.profile_id.as_str()) {
        return Err(AppError::Invalid(format!(
            "profile is outside this artifact boundary: {}",
            invocation.case.profile_id
        )));
    }
    let result = evaluate(invocation)?;
    serde_json::to_writer(io::stdout(), &result)?;
    Ok(())
}

pub fn canonical_digest(domain: &str, value: &Value) -> Result<String, AppError> {
    let bytes = serde_json_canonicalizer::to_vec(value)
        .map_err(|error| AppError::Invalid(format!("cannot canonicalize value: {error}")))?;
    let mut hash = Sha256::new();
    hash.update(domain.as_bytes());
    hash.update([0]);
    hash.update(bytes);
    Ok(format!(
        "sha-256:{}",
        base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(hash.finalize())
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn invocation(profile: &str, operation: &str, document: Value) -> SubjectInvocation {
        SubjectInvocation {
            subject_protocol: SUBJECT_PROTOCOL.to_owned(),
            case: Case {
                profile_id: profile.to_owned(),
                producer_role: None,
                initial_state: vec![
                    InitialState {
                        state: "manifest.accepted_count".to_owned(),
                        value: json!(0),
                    },
                    InitialState {
                        state: "surface.version_binding_count".to_owned(),
                        value: json!(0),
                    },
                ],
                stimulus: Stimulus {
                    operation: operation.to_owned(),
                    fixture: Fixture { document },
                },
            },
        }
    }

    #[test]
    fn publisher_accepts_exact_surface() {
        let result = evaluate(invocation(
            SP,
            "publish_manifest",
            json!({
                "surface": {
                    "references": "complete",
                    "candidate_hash": "same",
                    "retained_hash": "same",
                    "mode": "standard",
                    "action_semantics": "closed_read_propose"
                }
            }),
        ))
        .expect("surface should be accepted");
        assert_eq!(result.decision, "accepted");
        assert_eq!(result.tokens, vec!["manifest_published"]);
        assert_eq!(result.state_deltas[0].after, json!(1));
    }

    #[test]
    fn digest_is_domain_separated() {
        let left = canonical_digest("A", &json!({"x": 1})).unwrap();
        let right = canonical_digest("B", &json!({"x": 1})).unwrap();
        assert_ne!(left, right);
    }
}
