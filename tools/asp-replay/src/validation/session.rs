use serde_json::Value;

use crate::value::{has_only, string, uint};

use super::state::Validator;
use super::support::require_members;

pub(super) fn transition(body: &Value, ordinal: usize, validator: &mut Validator) {
    let path = format!("/records/{ordinal}/body");
    if !require_members(
        body,
        &["session_generation", "prior_state", "next_state", "reason"],
        "ASP-REPLAY-SESSION-001",
        ordinal,
        &path,
        "session transition is missing a required member",
        validator,
    ) {
        return;
    }
    let Some(object) = body.as_object() else {
        return;
    };
    if !has_only(
        object,
        &["session_generation", "prior_state", "next_state", "reason"],
    ) {
        validator.error(
            "ASP-REPLAY-SESSION-001",
            ordinal,
            &path,
            "session transition contains an unknown member",
        );
    }
    let (Some(prior), Some(next), Some(generation), Some(_reason)) = (
        string(body, "prior_state"),
        string(body, "next_state"),
        uint(body, "session_generation"),
        string(body, "reason"),
    ) else {
        validator.error(
            "ASP-REPLAY-SESSION-001",
            ordinal,
            &path,
            "session transition members have invalid JSON types",
        );
        return;
    };
    if generation != validator.session_generation {
        validator.error(
            "ASP-REPLAY-SESSION-001",
            ordinal,
            &path,
            "session transition generation conflicts with the replay scope",
        );
        return;
    }
    let first = validator.session_transitions == 0;
    let terminal_observed = matches!(
        validator.session_state.as_str(),
        "cancelled" | "completed" | "failed"
    );
    if validator.session_gap_pending && !terminal_observed {
        validator.session_state = prior.to_owned();
    }
    if validator.session_state != prior {
        validator.error(
            "ASP-REPLAY-SESSION-001",
            ordinal,
            &path,
            "session transition does not continue the replayed state",
        );
        return;
    }
    let legal = if first {
        (generation == 1 && prior == "absent" && next == "active")
            || (generation > 1 && prior == "interrupted" && next == "active")
            || (validator.session_gap_pending
                && matches!(
                    (prior, next),
                    (
                        "active",
                        "interrupted" | "cancelled" | "completed" | "failed"
                    ) | ("interrupted", "cancelled")
                ))
    } else {
        matches!(
            (prior, next),
            (
                "active",
                "interrupted" | "cancelled" | "completed" | "failed"
            ) | ("interrupted", "cancelled")
        )
    };
    if !legal {
        validator.error(
            "ASP-REPLAY-SESSION-001",
            ordinal,
            &path,
            "session transition is not legal for the recorded generation",
        );
        return;
    }
    validator.session_state = next.to_owned();
    validator.session_transitions += 1;
    validator.session_gap_pending = false;
}
