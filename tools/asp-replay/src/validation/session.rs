use serde_json::Value;
use specification_core::DecisionSpecification;

use crate::value::{has_only, string, uint};

use super::state::Validator;
use super::support::require_members;

#[derive(Clone, Copy)]
struct SessionTransitionInput<'a> {
    generation: u64,
    prior: &'a str,
    next: &'a str,
    replay_state: &'a str,
    first: bool,
    gap_pending: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum SessionTransitionDecision {
    StateMismatch,
    Illegal,
    Accepted,
}

struct SessionTransitionPolicy;

impl DecisionSpecification<SessionTransitionInput<'_>> for SessionTransitionPolicy {
    type Decision = SessionTransitionDecision;

    fn decide(&self, candidate: &SessionTransitionInput<'_>) -> Option<&Self::Decision> {
        const STATE_MISMATCH: SessionTransitionDecision = SessionTransitionDecision::StateMismatch;
        const ILLEGAL: SessionTransitionDecision = SessionTransitionDecision::Illegal;
        const ACCEPTED: SessionTransitionDecision = SessionTransitionDecision::Accepted;

        let decision = if candidate.replay_state != candidate.prior {
            &STATE_MISMATCH
        } else {
            let legal = if candidate.first {
                (candidate.generation == 1
                    && candidate.prior == "absent"
                    && candidate.next == "active")
                    || (candidate.generation > 1
                        && candidate.prior == "interrupted"
                        && candidate.next == "active")
                    || (candidate.gap_pending
                        && matches!(
                            (candidate.prior, candidate.next),
                            (
                                "active",
                                "interrupted" | "cancelled" | "completed" | "failed"
                            ) | ("interrupted", "cancelled")
                        ))
            } else {
                matches!(
                    (candidate.prior, candidate.next),
                    (
                        "active",
                        "interrupted" | "cancelled" | "completed" | "failed"
                    ) | ("interrupted", "cancelled")
                )
            };
            if legal { &ACCEPTED } else { &ILLEGAL }
        };
        Some(decision)
    }
}

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
    let decision = SessionTransitionPolicy
        .decide(&SessionTransitionInput {
            generation,
            prior,
            next,
            replay_state: &validator.session_state,
            first,
            gap_pending: validator.session_gap_pending,
        })
        .expect("session transition policy always returns a decision");
    match decision {
        SessionTransitionDecision::StateMismatch => {
            validator.error(
                "ASP-REPLAY-SESSION-001",
                ordinal,
                &path,
                "session transition does not continue the replayed state",
            );
            return;
        }
        SessionTransitionDecision::Illegal => {
            validator.error(
                "ASP-REPLAY-SESSION-001",
                ordinal,
                &path,
                "session transition is not legal for the recorded generation",
            );
            return;
        }
        SessionTransitionDecision::Accepted => {}
    }
    validator.session_state = next.to_owned();
    validator.session_transitions += 1;
    validator.session_gap_pending = false;
}
