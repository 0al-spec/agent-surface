use std::collections::HashSet;

use serde_json::Value;

use crate::MAX_RECORDS;
use crate::ReplayError;
use crate::hash::{RECORD_DOMAIN, object_hash};
use crate::value::{has_only, member, string, timestamp_not_after, timestamp_shape, uint};

use super::events::{check_ack, check_event, check_gap};
use super::receipts::check_receipt;
use super::session::transition;
use super::state::{PendingReferenceKind, Validator};

pub(super) fn reconcile_pending_references(validator: &mut Validator) {
    let pending = std::mem::take(&mut validator.pending_references);
    let partial_evidence = validator.capture_partial && validator.validated_capture_gaps > 0;
    for reference in pending {
        let known_later = match &reference.kind {
            PendingReferenceKind::Acknowledgement => {
                validator.deliveries.contains_key(&reference.target)
            }
            PendingReferenceKind::ReceiptParent
            | PendingReferenceKind::ApprovalSideLink { .. }
            | PendingReferenceKind::RecoveryTarget => {
                validator.receipts_by_hash.contains_key(&reference.target)
            }
        };
        if known_later {
            let message = match &reference.kind {
                PendingReferenceKind::Acknowledgement => {
                    "acknowledgement resolves only to a later delivery"
                }
                PendingReferenceKind::ReceiptParent => {
                    "receipt parent resolves only to a later receipt"
                }
                PendingReferenceKind::ApprovalSideLink { role } => {
                    if role == "runtime" {
                        "runtime approval side link resolves only to a later receipt"
                    } else {
                        "application approval side link resolves only to a later receipt"
                    }
                }
                PendingReferenceKind::RecoveryTarget => {
                    "recovery target resolves only to a later receipt"
                }
            };
            validator.error(
                reference.check_id,
                reference.ordinal,
                reference.path,
                message,
            );
        } else if partial_evidence {
            validator.incomplete(
                reference.check_id,
                reference.ordinal,
                reference.path,
                "referenced predecessor is outside the validated partial capture",
            );
        } else {
            validator.error(
                reference.check_id,
                reference.ordinal,
                reference.path,
                "referenced predecessor is absent from a complete capture",
            );
        }
    }
}

pub(super) fn validate_record_integrity(
    bundle: &Value,
    validator: &mut Validator,
) -> Result<(), ReplayError> {
    let Some(records) = member(bundle, "records").and_then(Value::as_array) else {
        return Ok(());
    };
    if records.len() > MAX_RECORDS {
        validator.error(
            "ASP-REPLAY-ORDER-001",
            0,
            "/records",
            "bundle exceeds the maximum record count",
        );
        return Ok(());
    }
    let mut ids = HashSet::new();
    let mut previous_hash: Option<String> = None;
    for (index, record) in records.iter().enumerate() {
        let ordinal = uint(record, "ordinal").unwrap_or(u64::MAX);
        if ordinal != index as u64 {
            validator.error(
                "ASP-REPLAY-ORDER-001",
                index,
                format!("/records/{index}/ordinal"),
                "record ordinals must be contiguous and start at zero",
            );
        }
        if let Some(record_id) = string(record, "record_id")
            && !ids.insert(record_id)
        {
            validator.error(
                "ASP-REPLAY-ORDER-001",
                index,
                format!("/records/{index}/record_id"),
                "record id is not unique in the bundle",
            );
        }
        match (&previous_hash, string(record, "previous_record_hash")) {
            (None, None) => {}
            (Some(expected), Some(actual)) if expected == actual => {}
            _ => validator.error(
                "ASP-REPLAY-ORDER-001",
                index,
                format!("/records/{index}/previous_record_hash"),
                "record does not link to the exact preceding record hash",
            ),
        }
        if let Some(expected) = string(record, "record_hash") {
            let actual = object_hash(RECORD_DOMAIN, record, &["record_hash"])?;
            if expected != actual {
                validator.error(
                    "ASP-REPLAY-ORDER-001",
                    index,
                    format!("/records/{index}/record_hash"),
                    "record hash does not match the exact record",
                );
            }
            previous_hash = Some(expected.to_owned());
        }
        if string(record, "representation") != Some("exact")
            || member(record, "elisions")
                .and_then(Value::as_array)
                .is_none_or(|elisions| !elisions.is_empty())
            || string(record, "recorded_at").is_none_or(|time| !timestamp_shape(time))
        {
            validator.error(
                "ASP-REPLAY-ORDER-001",
                index,
                format!("/records/{index}"),
                "record representation, elisions, or timestamp is invalid",
            );
        }
        let Some(kind) = string(record, "kind") else {
            continue;
        };
        let Some(body) = member(record, "body") else {
            continue;
        };
        let expected_name = match kind {
            "session_transition" => Some("session.transition"),
            "event_delivery" => Some("event.delivery"),
            "event_ack" => Some("event.ack"),
            "event_gap" => Some("event.gap"),
            "capture_gap" => Some("capture.gap"),
            "receipt" => string(body, "receipt_type").and_then(|receipt_type| match receipt_type {
                "runtime" => Some("receipt.runtime"),
                "app" => Some("receipt.app"),
                "approval" => Some("receipt.approval"),
                _ => None,
            }),
            _ => None,
        };
        if expected_name != string(record, "name") {
            validator.error(
                "ASP-REPLAY-SCHEMA-001",
                index,
                format!("/records/{index}/name"),
                "record name does not match its kind and exact body",
            );
        }
    }
    Ok(())
}

pub(super) fn validate_records(
    bundle: &Value,
    validator: &mut Validator,
) -> Result<(), ReplayError> {
    let Some(records) = member(bundle, "records").and_then(Value::as_array) else {
        return Ok(());
    };
    if records.len() > MAX_RECORDS {
        validator.error(
            "ASP-REPLAY-ORDER-001",
            0,
            "/records",
            "bundle exceeds the maximum record count",
        );
        return Ok(());
    }
    let Some(scope) = member(bundle, "scope") else {
        return Ok(());
    };
    let Some(context) = member(bundle, "context") else {
        return Ok(());
    };
    let Some(surface) = member(context, "surface") else {
        return Ok(());
    };
    let Some(grant) = member(context, "grant") else {
        return Ok(());
    };
    let mut ids = HashSet::new();
    let mut previous_hash: Option<String> = None;
    validator.session_generation = uint(scope, "session_generation").unwrap_or(0);
    validator.session_state = if validator.session_generation > 1 {
        "interrupted".to_owned()
    } else {
        "absent".to_owned()
    };

    for (index, record) in records.iter().enumerate() {
        let ordinal = uint(record, "ordinal").unwrap_or(u64::MAX);
        if ordinal != index as u64 {
            validator.error(
                "ASP-REPLAY-ORDER-001",
                index,
                format!("/records/{index}/ordinal"),
                "record ordinals must be contiguous and start at zero",
            );
        }
        if let Some(record_id) = string(record, "record_id")
            && !ids.insert(record_id)
        {
            validator.error(
                "ASP-REPLAY-ORDER-001",
                index,
                format!("/records/{index}/record_id"),
                "record id is not unique in the bundle",
            );
        }
        match (&previous_hash, string(record, "previous_record_hash")) {
            (None, None) => {}
            (Some(expected), Some(actual)) if expected == actual => {}
            _ => validator.error(
                "ASP-REPLAY-ORDER-001",
                index,
                format!("/records/{index}/previous_record_hash"),
                "record does not link to the exact preceding record hash",
            ),
        }
        if let Some(expected) = string(record, "record_hash") {
            let actual = object_hash(RECORD_DOMAIN, record, &["record_hash"])?;
            if expected != actual {
                validator.error(
                    "ASP-REPLAY-ORDER-001",
                    index,
                    format!("/records/{index}/record_hash"),
                    "record hash does not match the exact record",
                );
            }
            previous_hash = Some(expected.to_owned());
        }
        if string(record, "representation") != Some("exact")
            || member(record, "elisions")
                .and_then(Value::as_array)
                .is_none_or(|elisions| !elisions.is_empty())
            || string(record, "recorded_at").is_none_or(|time| !timestamp_shape(time))
        {
            validator.error(
                "ASP-REPLAY-ORDER-001",
                index,
                format!("/records/{index}"),
                "record representation, elisions, or timestamp is invalid",
            );
        }
        let Some(kind) = string(record, "kind") else {
            continue;
        };
        let Some(body) = member(record, "body") else {
            continue;
        };
        if validator.session_transitions == 0
            && !validator.session_gap_pending
            && kind != "session_transition"
            && kind != "capture_gap"
            && !validator.initial_session_error_reported
        {
            validator.error(
                "ASP-REPLAY-SESSION-001",
                index,
                format!("/records/{index}"),
                "session evidence requires an initial transition unless a preceding capture gap makes it indeterminate",
            );
            validator.initial_session_error_reported = true;
        }
        let expected_name = match kind {
            "session_transition" => Some("session.transition"),
            "event_delivery" => Some("event.delivery"),
            "event_ack" => Some("event.ack"),
            "event_gap" => Some("event.gap"),
            "capture_gap" => Some("capture.gap"),
            "receipt" => string(body, "receipt_type").and_then(|receipt_type| match receipt_type {
                "runtime" => Some("receipt.runtime"),
                "app" => Some("receipt.app"),
                "approval" => Some("receipt.approval"),
                _ => None,
            }),
            _ => None,
        };
        if expected_name != string(record, "name") {
            validator.error(
                "ASP-REPLAY-SCHEMA-001",
                index,
                format!("/records/{index}/name"),
                "record name does not match its kind and exact body",
            );
        }
        match kind {
            "session_transition" => transition(body, index, validator),
            "event_delivery" => {
                check_event(body, index, scope, surface, grant, validator)?;
            }
            "event_ack" => check_ack(body, index, validator),
            "event_gap" => check_gap(body, index, validator),
            "receipt" => {
                check_receipt(body, index, scope, surface, grant, validator)?;
            }
            "capture_gap" => {
                validator.capture_gaps += 1;
                let shape_valid = body.as_object().is_some_and(|object| {
                    has_only(object, &["reason", "started_at", "ended_at"])
                        && matches!(
                            string(body, "reason"),
                            Some("not_captured" | "redacted" | "source_unavailable")
                        )
                        && string(body, "started_at").is_some_and(timestamp_shape)
                        && string(body, "ended_at").is_some_and(timestamp_shape)
                });
                if !shape_valid {
                    validator.error(
                        "ASP-REPLAY-GAP-001",
                        index,
                        format!("/records/{index}/body"),
                        "capture gap is not a closed supported gap marker",
                    );
                } else if !timestamp_not_after(
                    string(body, "started_at").expect("validated gap start"),
                    string(body, "ended_at").expect("validated gap end"),
                ) {
                    validator.error(
                        "ASP-REPLAY-GAP-001",
                        index,
                        format!("/records/{index}/body"),
                        "capture gap start must not be later than its end",
                    );
                } else {
                    validator.validated_capture_gaps += 1;
                    validator.capture_gap_epoch += 1;
                    validator.session_gap_pending = true;
                    validator.incomplete(
                        "ASP-REPLAY-GAP-001",
                        index,
                        format!("/records/{index}/body"),
                        "explicit capture gap makes replay history incomplete",
                    );
                }
            }
            _ => validator.error(
                "ASP-REPLAY-SCHEMA-001",
                index,
                format!("/records/{index}/kind"),
                "record kind is not supported by replay v1",
            ),
        }
    }
    reconcile_pending_references(validator);
    if validator.capture_partial != (validator.validated_capture_gaps > 0) {
        validator.error(
            "ASP-REPLAY-GAP-001",
            0,
            "/capture/completeness",
            "capture completeness must agree with explicit capture gap records",
        );
    }
    if validator.session_transitions == 0
        && !validator.session_gap_pending
        && !validator.initial_session_error_reported
    {
        validator.error(
            "ASP-REPLAY-SESSION-001",
            0,
            "/records",
            "session evidence requires an initial transition unless a preceding capture gap makes it indeterminate",
        );
    }
    if let Some(capture) = member(bundle, "capture")
        && let (Some(started_at), Some(ended_at)) =
            (string(capture, "started_at"), string(capture, "ended_at"))
        && !timestamp_not_after(started_at, ended_at)
    {
        validator.error(
            "ASP-REPLAY-GAP-001",
            0,
            "/capture",
            "capture start must not be later than its end",
        );
    }
    Ok(())
}
