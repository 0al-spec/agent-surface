use std::collections::HashSet;

use asp_manifest_linter::lint_manifest_value;
use serde_json::Value;

use crate::hash::{MANIFEST_DOMAIN, object_hash};

pub(crate) const PROVIDER_NAME: &str = "asp-replay-native-surface";
pub(crate) const PROVIDER_VERSION: &str = env!("CARGO_PKG_VERSION");
pub(crate) const RULESET_ID: &str =
    "https://github.com/0al-spec/agent-surface/rules/native-surface/v1";
pub(crate) const RULESET_VERSION: &str = "1.0.0";
pub(crate) const RULESET_SHA256: &str = "sha-256:9m666CQobLkG_9GSCii-LhiKGKFO8UuMEyUJbTAIJG8";

const MAX_SURFACE_NODES: usize = 4096;
const REQUIRED_STRING_MEMBERS: [&str; 7] = [
    "protocol",
    "app_id",
    "issuer",
    "surface_mode",
    "surface_version",
    "surface_hash",
    "surface_url",
];
const REQUIRED_OBJECT_MEMBERS: [&str; 4] = ["auth", "agent_api", "audit", "revocation"];
const REQUIRED_ARRAY_MEMBERS: [&str; 5] =
    ["scopes", "data_classes", "resources", "actions", "events"];
const FORBIDDEN_PROPOSAL_COMPANIONS: [&str; 7] = [
    "commit_action",
    "dry_run_action",
    "proposal_action",
    "reservation_action",
    "recovery_actions",
    "target_actions",
    "reservation",
];

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum SurfaceVerdict {
    Passed,
    Failed,
    Unavailable,
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

fn is_https_uri(value: &str) -> bool {
    value.strip_prefix("https://").is_some_and(|remainder| {
        !remainder.is_empty()
            && !remainder.starts_with('/')
            && !remainder.chars().any(char::is_whitespace)
    })
}

fn required_shape_is_valid(surface: &Value) -> bool {
    REQUIRED_STRING_MEMBERS
        .iter()
        .all(|name| surface.get(name).and_then(Value::as_str).is_some())
        && REQUIRED_OBJECT_MEMBERS
            .iter()
            .all(|name| surface.get(name).and_then(Value::as_object).is_some())
        && REQUIRED_ARRAY_MEMBERS
            .iter()
            .all(|name| surface.get(name).and_then(Value::as_array).is_some())
}

fn ids_are_unique(surface: &Value) -> bool {
    REQUIRED_ARRAY_MEMBERS.iter().all(|name| {
        let mut ids = HashSet::new();
        surface
            .get(name)
            .and_then(Value::as_array)
            .is_some_and(|members| {
                members.iter().all(|member| {
                    member
                        .get("id")
                        .and_then(Value::as_str)
                        .is_some_and(|id| !id.is_empty() && ids.insert(id))
                })
            })
    })
}

fn endpoints_are_https(surface: &Value) -> bool {
    if !["issuer", "surface_url"].iter().all(|name| {
        surface
            .get(name)
            .and_then(Value::as_str)
            .is_some_and(is_https_uri)
    }) {
        return false;
    }
    ["auth", "agent_api"].iter().all(|section| {
        surface
            .get(section)
            .and_then(Value::as_object)
            .is_some_and(|object| {
                object.iter().all(|(name, value)| {
                    !name.ends_with("_url") || value.as_str().is_some_and(is_https_uri)
                })
            })
    })
}

fn proposal_only_is_valid(surface: &Value) -> bool {
    if surface.get("surface_mode").and_then(Value::as_str) != Some("proposal_only") {
        return true;
    }
    let Some(actions) = surface.get("actions").and_then(Value::as_array) else {
        return false;
    };
    let mut has_proposal = false;
    for action in actions {
        let Some(action) = action.as_object() else {
            return false;
        };
        let Some(execution) = action.get("execution").and_then(Value::as_object) else {
            return false;
        };
        let Some(mode) = execution.get("mode").and_then(Value::as_str) else {
            return false;
        };
        has_proposal |= mode == "propose";
        if !matches!(mode, "read" | "propose")
            || action.get("side_effect").and_then(Value::as_bool) != Some(false)
            || action.contains_key("effects")
            || FORBIDDEN_PROPOSAL_COMPANIONS
                .iter()
                .any(|name| action.contains_key(*name) || execution.contains_key(*name))
        {
            return false;
        }
        if mode == "propose"
            && execution.get("persisted").and_then(Value::as_bool) == Some(true)
            && (action.get("idempotency").and_then(Value::as_str) != Some("required")
                || action
                    .get("idempotency_normalization")
                    .and_then(Value::as_str)
                    != Some("asp-json-normalization-v1")
                || action.get("input_hash_profile").and_then(Value::as_str)
                    != Some("asp-jcs-sha-256"))
        {
            return false;
        }
    }
    has_proposal
}

pub(crate) fn evaluate(bundle: &Value) -> SurfaceVerdict {
    let Some(surface) = bundle.pointer("/context/surface") else {
        return SurfaceVerdict::Failed;
    };
    let mut remaining = MAX_SURFACE_NODES;
    if !within_node_budget(surface, &mut remaining) {
        return SurfaceVerdict::Unavailable;
    }
    if !required_shape_is_valid(surface)
        || surface.get("protocol").and_then(Value::as_str) != Some("agent-surface/0.1")
        || !matches!(
            surface.get("surface_mode").and_then(Value::as_str),
            Some("standard" | "proposal_only")
        )
        || !ids_are_unique(surface)
        || !endpoints_are_https(surface)
        || !proposal_only_is_valid(surface)
    {
        return SurfaceVerdict::Failed;
    }
    let Some(expected_hash) = surface.get("surface_hash").and_then(Value::as_str) else {
        return SurfaceVerdict::Failed;
    };
    let Ok(actual_hash) = object_hash(MANIFEST_DOMAIN, surface, &["surface_hash"]) else {
        return SurfaceVerdict::Unavailable;
    };
    if expected_hash != actual_hash {
        return SurfaceVerdict::Failed;
    }
    match lint_manifest_value("<embedded-surface>", surface) {
        Ok(report) if report.summary.errors == 0 => SurfaceVerdict::Passed,
        Ok(_) => SurfaceVerdict::Failed,
        Err(_) => SurfaceVerdict::Unavailable,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rehash::rehash_bundle;

    fn complete_bundle() -> Value {
        serde_json::from_slice(include_bytes!("../tests/fixtures/complete-session.json"))
            .expect("complete bundle")
    }

    fn rehash(bundle: &mut Value) {
        rehash_bundle(bundle).expect("rehashed bundle");
    }

    #[test]
    fn accepts_complete_hash_bound_surface_snapshot() {
        assert_eq!(evaluate(&complete_bundle()), SurfaceVerdict::Passed);
    }

    #[test]
    fn rejects_non_https_endpoint_even_when_rehashed() {
        let mut bundle = complete_bundle();
        bundle["context"]["surface"]["surface_url"] =
            Value::String("http://code.example.com/agent-surface.json".to_owned());
        rehash(&mut bundle);
        assert_eq!(evaluate(&bundle), SurfaceVerdict::Failed);
    }

    #[test]
    fn rejects_duplicate_inventory_ids_even_when_rehashed() {
        let mut bundle = complete_bundle();
        let scope = serde_json::json!({"id": "tasks.read"});
        bundle["context"]["surface"]["scopes"] = Value::Array(vec![scope.clone(), scope]);
        rehash(&mut bundle);
        assert_eq!(evaluate(&bundle), SurfaceVerdict::Failed);
    }

    #[test]
    fn rejects_proposal_only_surface_without_a_proposal_action() {
        let mut bundle = complete_bundle();
        bundle["context"]["surface"]["surface_mode"] = Value::String("proposal_only".to_owned());
        rehash(&mut bundle);
        assert_eq!(evaluate(&bundle), SurfaceVerdict::Failed);
    }

    #[test]
    fn rejects_ruleset_digest_drift() {
        use base64::Engine as _;
        use sha2::{Digest, Sha256};

        let digest = Sha256::digest(include_bytes!("../rules/v1/native-surface.json"));
        let encoded = base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(digest);
        assert_eq!(RULESET_SHA256, format!("sha-256:{encoded}"));
    }
}
