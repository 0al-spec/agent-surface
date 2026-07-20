//! Fuzz and test entry points for exercising the private replay pipeline.

use serde_json::Value;

use crate::composition::compose_with_provider_plan;
use crate::rehash::rehash_bundle;
use crate::{CompositionReport, ReplayError, Report, compose, validate_composition_report, verify};

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

/// Compose a previously rehashed structured bundle through the production policy.
pub fn compose_rehashed(bundle: &Value) -> Result<CompositionReport, ReplayError> {
    let document =
        serde_json::to_vec(bundle).map_err(|error| ReplayError::Canonical(error.to_string()))?;
    compose("<fuzz>", &document)
}

/// Compose a rehashed bundle with a synthetic provider outcome for each native role.
pub fn compose_rehashed_with_plan(
    bundle: &Value,
    outcomes: &[u8; 7],
) -> Result<CompositionReport, ReplayError> {
    let document =
        serde_json::to_vec(bundle).map_err(|error| ReplayError::Canonical(error.to_string()))?;
    compose_with_provider_plan("<fuzz>", &document, outcomes)
}

/// Check the machine-readable schema, report digest, and evidence binding contract.
pub fn composition_contract_holds(bundle: &Value, report: &CompositionReport) -> bool {
    let Ok(document) = serde_json::to_vec(bundle) else {
        return false;
    };
    validate_composition_report(&document, report).is_ok()
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
        let composition = compose_rehashed(&bundle).expect("composition coverage");
        assert_eq!(composition.composition_state, "rejected");
        assert!(!composition.complete_claim_eligible);
    }

    #[test]
    fn synthetic_provider_matrix_reaches_every_composition_state() {
        let complete: Value =
            serde_json::from_slice(include_bytes!("../tests/fixtures/complete-session.json"))
                .expect("valid complete replay fixture");
        let incomplete: Value = serde_json::from_slice(include_bytes!(
            "../tests/fixtures/explicit-capture-gap.json"
        ))
        .expect("valid incomplete replay fixture");
        let invalid: Value =
            serde_json::from_slice(include_bytes!("../tests/fixtures/invalid-empty.json"))
                .expect("valid JSON invalid replay fixture");

        let eligible_valid =
            compose_rehashed_with_plan(&complete, &[0; 7]).expect("eligible valid composition");
        assert_eq!(eligible_valid.providers[0].status, "passed");
        assert_eq!(eligible_valid.composition_state, "eligible_valid");
        assert!(composition_contract_holds(&complete, &eligible_valid));

        let eligible_incomplete =
            compose_rehashed_with_plan(&incomplete, &[0; 7]).expect("eligible incomplete report");
        assert_eq!(eligible_incomplete.providers[0].status, "passed");
        assert_eq!(eligible_incomplete.composition_state, "eligible_incomplete");
        assert!(composition_contract_holds(
            &incomplete,
            &eligible_incomplete
        ));

        let rejected =
            compose_rehashed_with_plan(&complete, &[1, 0, 0, 0, 0, 0, 0]).expect("rejection");
        assert_eq!(rejected.providers[0].status, "failed");
        assert_eq!(rejected.composition_state, "rejected");
        assert!(composition_contract_holds(&complete, &rejected));

        let blocked =
            compose_rehashed_with_plan(&complete, &[2, 0, 0, 0, 0, 0, 0]).expect("blocked");
        assert_eq!(blocked.providers[0].status, "unavailable");
        assert_eq!(blocked.composition_state, "blocked");
        assert!(composition_contract_holds(&complete, &blocked));

        let bounded_rejected =
            compose_rehashed_with_plan(&invalid, &[0; 7]).expect("bounded rejection");
        assert_eq!(bounded_rejected.providers[0].status, "not_evaluated");
        assert_eq!(bounded_rejected.composition_state, "rejected");
        assert!(composition_contract_holds(&invalid, &bounded_rejected));
    }
}
