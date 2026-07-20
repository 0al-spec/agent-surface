//! Fuzz-only entry points for exercising the private replay pipeline.

use serde_json::Value;

use crate::rehash::rehash_bundle;
use crate::{ReplayError, Report, verify};

/// Parse and verify one arbitrary byte sequence through the production entry point.
pub fn parse_verify(document: &[u8]) -> Result<Report, ReplayError> {
    verify("<fuzz>", document)
}

/// Recompute all derived bundle hashes, serialize the value, and verify it.
pub fn rehash_and_verify(bundle: &mut Value) -> Result<Report, ReplayError> {
    rehash_bundle(bundle)?;
    let document =
        serde_json::to_vec(bundle).map_err(|error| ReplayError::Canonical(error.to_string()))?;
    verify("<fuzz>", &document)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rehash_bridge_reaches_semantic_validation() {
        let mut bundle: Value =
            serde_json::from_slice(include_bytes!("../tests/fixtures/event-receipt-flow.json"))
                .expect("valid replay fixture");
        bundle["records"][2]["body"]["payload"]["outcome"] = Value::String("retry".to_owned());

        let report = rehash_and_verify(&mut bundle).expect("rehash and verification");

        assert_eq!(report.evaluation_state, "semantic_invalid");
        assert!(
            report
                .checks
                .iter()
                .any(|check| check.check_id == "ASP-REPLAY-DELIVERY-001" && check.status == "fail")
        );
    }
}
