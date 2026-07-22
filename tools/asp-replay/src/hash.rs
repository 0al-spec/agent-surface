use base64::Engine;
use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use serde_json::Value;
use sha2::{Digest, Sha256};
use specification_core::Specification;

use crate::ReplayError;
use crate::specifications::{BundleId, CanonicalDigest};

pub(crate) const MANIFEST_DOMAIN: &str =
    "https://github.com/0al-spec/agent-surface/hash/manifest/v1";
pub(crate) const GRANT_DOMAIN: &str = "https://github.com/0al-spec/agent-surface/hash/grant/v1";
pub(crate) const IDENTITY_EVIDENCE_DOMAIN: &str =
    "https://github.com/0al-spec/agent-surface/hash/agent-identity-evidence/v1";
pub(crate) const EVENT_DOMAIN: &str = "https://github.com/0al-spec/agent-surface/hash/event/v1";
pub(crate) const POLICY_DOMAIN: &str =
    "https://github.com/0al-spec/agent-surface/hash/policy-decision/v1";
pub(crate) const EXECUTION_DOMAIN: &str =
    "https://github.com/0al-spec/agent-surface/hash/action-execution/v1";
pub(crate) const ACTUAL_EFFECTS_DOMAIN: &str =
    "https://github.com/0al-spec/agent-surface/hash/actual-effects/v1";
pub(crate) const RECEIPT_DOMAIN: &str = "https://github.com/0al-spec/agent-surface/hash/receipt/v1";
pub(crate) const RECORD_DOMAIN: &str =
    "https://github.com/0al-spec/agent-surface/hash/replay-record/v1";
pub(crate) const BUNDLE_DOMAIN: &str =
    "https://github.com/0al-spec/agent-surface/hash/replay-bundle/v1";
pub(crate) const REPORT_DOMAIN: &str =
    "https://github.com/0al-spec/agent-surface/hash/replay-report/v1";

pub(crate) fn raw_sha256(bytes: &[u8]) -> String {
    format!("sha-256:{}", URL_SAFE_NO_PAD.encode(Sha256::digest(bytes)))
}

pub(crate) fn object_hash(
    domain: &str,
    value: &Value,
    exclusions: &[&str],
) -> Result<String, ReplayError> {
    let mut view = value.clone();
    if let Some(object) = view.as_object_mut() {
        for member in exclusions {
            object.remove(*member);
        }
    }
    let wrapper = serde_json::json!({"domain": domain, "object": view});
    let bytes = serde_json_canonicalizer::to_vec(&wrapper)
        .map_err(|error| ReplayError::Canonical(error.to_string()))?;
    Ok(raw_sha256(&bytes))
}

pub(crate) fn valid_digest(value: &str) -> bool {
    CanonicalDigest.is_satisfied_by(value)
}

pub(crate) fn valid_bundle_id(value: &str) -> bool {
    BundleId.is_satisfied_by(value)
}
