use std::collections::HashMap;

use serde_json::Value;

use crate::ReplayError;
use crate::hash::{
    ACTUAL_EFFECTS_DOMAIN, BUNDLE_DOMAIN, EVENT_DOMAIN, EXECUTION_DOMAIN, GRANT_DOMAIN,
    IDENTITY_EVIDENCE_DOMAIN, MANIFEST_DOMAIN, POLICY_DOMAIN, RECEIPT_DOMAIN, RECORD_DOMAIN,
    object_hash,
};
use crate::value::{member, string};

fn set_string(value: &mut Value, name: &str, new_value: String) {
    if let Some(object) = value.as_object_mut() {
        object.insert(name.to_owned(), Value::String(new_value));
    }
}

/// Recompute every derived hash in one mutable replay bundle.
///
/// This helper is pure with respect to process state: it only mutates the
/// supplied JSON value and never reads files, resolves URIs, or performs
/// network operations.
pub(crate) fn rehash_bundle(bundle: &mut Value) -> Result<(), ReplayError> {
    let identity_evidence_hash = {
        let evidence = bundle
            .pointer("/context/grant/delegate/identity_evidence")
            .ok_or_else(|| {
                ReplayError::SelfCheck(
                    "rehash requires context.grant.delegate.identity_evidence".to_owned(),
                )
            })?;
        object_hash(IDENTITY_EVIDENCE_DOMAIN, evidence, &[])?
    };
    set_string(
        bundle
            .pointer_mut("/scope")
            .ok_or_else(|| ReplayError::SelfCheck("rehash requires scope".to_owned()))?,
        "identity_evidence_hash",
        identity_evidence_hash.clone(),
    );

    let surface_hash = {
        let surface = bundle
            .pointer("/context/surface")
            .ok_or_else(|| ReplayError::SelfCheck("rehash requires context.surface".to_owned()))?;
        object_hash(MANIFEST_DOMAIN, surface, &["surface_hash"])?
    };
    set_string(
        bundle
            .pointer_mut("/context/surface")
            .expect("surface was resolved"),
        "surface_hash",
        surface_hash.clone(),
    );
    set_string(
        bundle
            .pointer_mut("/context/grant/resource_server")
            .ok_or_else(|| {
                ReplayError::SelfCheck("rehash requires Grant resource_server".to_owned())
            })?,
        "surface_hash",
        surface_hash.clone(),
    );
    set_string(
        bundle
            .pointer_mut("/scope")
            .ok_or_else(|| ReplayError::SelfCheck("rehash requires scope".to_owned()))?,
        "surface_hash",
        surface_hash.clone(),
    );

    let grant_hash = {
        let grant = bundle
            .pointer("/context/grant")
            .ok_or_else(|| ReplayError::SelfCheck("rehash requires context.grant".to_owned()))?;
        let mut hash_view = grant.clone();
        if let Some(object) = hash_view.as_object_mut() {
            object.remove("grant_hash");
            if object.get("type").and_then(Value::as_str)
                == Some(
                    "https://github.com/0al-spec/agent-surface/authorization-details/agent-grant",
                )
            {
                object.remove("type");
            }
        }
        object_hash(GRANT_DOMAIN, &hash_view, &[])?
    };
    set_string(
        bundle
            .pointer_mut("/context/grant")
            .expect("grant was resolved"),
        "grant_hash",
        grant_hash.clone(),
    );
    set_string(
        bundle.pointer_mut("/scope").expect("scope was resolved"),
        "grant_hash",
        grant_hash.clone(),
    );

    let mut prior_record_hash: Option<String> = None;
    let mut receipt_hash_replacements = HashMap::new();
    let records = member(bundle, "records")
        .and_then(Value::as_array)
        .ok_or_else(|| ReplayError::SelfCheck("rehash requires records".to_owned()))?
        .len();
    for index in 0..records {
        let record_path = format!("/records/{index}");
        let kind = bundle
            .pointer(&record_path)
            .and_then(|record| string(record, "kind"))
            .unwrap_or_default()
            .to_owned();
        let body_path = format!("{record_path}/body");
        if let Some(body) = bundle.pointer_mut(&body_path) {
            match kind.as_str() {
                "event_delivery" => {
                    set_string(body, "aspsurfacehash", surface_hash.clone());
                    let hash = object_hash(
                        EVENT_DOMAIN,
                        body,
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
                    )?;
                    set_string(body, "aspeventhash", hash);
                }
                "receipt" => {
                    set_string(body, "grant_hash", grant_hash.clone());
                    set_string(body, "surface_hash", surface_hash.clone());
                    if let Some(actor_agent) = body.get_mut("actor_agent") {
                        set_string(
                            actor_agent,
                            "identity_evidence_hash",
                            identity_evidence_hash.clone(),
                        );
                    }
                    if let Some(parent) = string(body, "parent_receipt_hash")
                        .and_then(|hash| receipt_hash_replacements.get(hash))
                        .cloned()
                    {
                        set_string(body, "parent_receipt_hash", parent);
                    }
                    if let Some(links) =
                        member(body, "approval_receipt_hashes").and_then(Value::as_object)
                    {
                        let replacements: Vec<(String, String)> = links
                            .iter()
                            .filter_map(|(role, value)| {
                                let old = value.as_str()?;
                                Some((role.clone(), receipt_hash_replacements.get(old)?.clone()))
                            })
                            .collect();
                        if let Some(links) = body
                            .get_mut("approval_receipt_hashes")
                            .and_then(Value::as_object_mut)
                        {
                            for (role, hash) in replacements {
                                links.insert(role, Value::String(hash));
                            }
                        }
                    }
                    if let Some(target) = body
                        .get("execution")
                        .and_then(|execution| string(execution, "target_receipt_hash"))
                        .and_then(|hash| receipt_hash_replacements.get(hash))
                        .cloned()
                        && let Some(execution) = body.get_mut("execution")
                    {
                        set_string(execution, "target_receipt_hash", target);
                    }
                    if let Some(policy) = body.get_mut("policy_decision") {
                        let hash = object_hash(POLICY_DOMAIN, policy, &["policy_decision_hash"])?;
                        set_string(policy, "policy_decision_hash", hash.clone());
                        set_string(body, "policy_decision_hash", hash);
                    }
                    if let Some(execution) = member(body, "execution") {
                        let hash = object_hash(EXECUTION_DOMAIN, execution, &["execution_token"])?;
                        set_string(body, "execution_hash", hash);
                    }
                    if let Some(effects) = member(body, "actual_effects") {
                        let hash = object_hash(ACTUAL_EFFECTS_DOMAIN, effects, &[])?;
                        set_string(body, "actual_effects_hash", hash);
                    }
                    let old_hash = string(body, "receipt_hash").map(str::to_owned);
                    let hash = object_hash(
                        RECEIPT_DOMAIN,
                        body,
                        &["receipt_hash", "receipt_signatures"],
                    )?;
                    set_string(body, "receipt_hash", hash.clone());
                    if let Some(old_hash) = old_hash {
                        receipt_hash_replacements.insert(old_hash, hash);
                    }
                }
                _ => {}
            }
        }
        let record = bundle
            .pointer_mut(&record_path)
            .expect("record index was resolved");
        if let Some(object) = record.as_object_mut() {
            match &prior_record_hash {
                Some(hash) => {
                    object.insert(
                        "previous_record_hash".to_owned(),
                        Value::String(hash.clone()),
                    );
                }
                None => {
                    object.remove("previous_record_hash");
                }
            }
        }
        let hash = object_hash(RECORD_DOMAIN, record, &["record_hash"])?;
        set_string(record, "record_hash", hash.clone());
        prior_record_hash = Some(hash);
    }
    let hash = object_hash(BUNDLE_DOMAIN, bundle, &["bundle_hash"])?;
    set_string(bundle, "bundle_hash", hash);
    Ok(())
}
