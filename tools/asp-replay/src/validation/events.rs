use serde_json::Value;
use specification_core::Specification;

use crate::ReplayError;
use crate::hash::{EVENT_DOMAIN, object_hash};
use crate::specifications::{MemberType, RequiredMembers};
use crate::value::{member, string, timestamp_shape, uint};

use super::state::{Delivery, PendingReference, PendingReferenceKind, StreamProgress, Validator};
use super::support::require_members;
use crate::value::has_only;

pub(super) fn event_declaration<'a>(surface: &'a Value, event_type: &str) -> Option<&'a Value> {
    member(surface, "events")?
        .as_array()?
        .iter()
        .find(|event| string(event, "id") == Some(event_type))
}

pub(super) fn check_event(
    event: &Value,
    ordinal: usize,
    scope: &Value,
    surface: &Value,
    grant: &Value,
    validator: &mut Validator,
) -> Result<(), ReplayError> {
    let path = format!("/records/{ordinal}/body");
    let required = [
        "specversion",
        "id",
        "source",
        "type",
        "time",
        "dataschema",
        "datacontenttype",
        "data",
        "aspcontrol",
        "aspsurfacehash",
        "aspeventhash",
        "aspsubid",
        "aspdeliveryid",
        "aspattempt",
        "aspstream",
        "aspsequence",
        "aspcursor",
    ];
    if !RequiredMembers::new(&required).is_satisfied_by(event) {
        validator.error(
            "ASP-REPLAY-EVENT-001",
            ordinal,
            &path,
            "event delivery is missing a required ASP CloudEvents member",
        );
        return Ok(());
    }
    let mut occurrence_shape_valid = true;
    for name in ["source", "id", "aspeventhash"] {
        if !MemberType::string(name).is_satisfied_by(event) {
            validator.error(
                "ASP-REPLAY-EVENT-001",
                ordinal,
                format!("{path}/{name}"),
                "event occurrence identity member must be a string",
            );
            occurrence_shape_valid = false;
        }
    }
    let mut delivery_shape_valid = true;
    for name in ["aspdeliveryid", "aspsubid", "aspstream", "aspcursor"] {
        if !MemberType::string(name).is_satisfied_by(event) {
            validator.error(
                "ASP-REPLAY-DELIVERY-001",
                ordinal,
                format!("{path}/{name}"),
                "event delivery identity member must be a string",
            );
            delivery_shape_valid = false;
        }
    }
    for name in ["aspattempt", "aspsequence"] {
        if !MemberType::unsigned_integer(name).is_satisfied_by(event) {
            validator.error(
                "ASP-REPLAY-DELIVERY-001",
                ordinal,
                format!("{path}/{name}"),
                "event attempt and stream sequence must be unsigned integers",
            );
            delivery_shape_valid = false;
        }
    }
    if string(event, "specversion") != Some("1.0")
        || string(event, "datacontenttype") != Some("application/json")
        || member(event, "data_base64").is_some()
    {
        validator.error(
            "ASP-REPLAY-EVENT-001",
            ordinal,
            &path,
            "event delivery is outside the ASP CloudEvents JSON profile",
        );
    }
    if string(event, "source") != string(scope, "issuer")
        || string(event, "aspsurfacehash") != string(scope, "surface_hash")
    {
        validator.error(
            "ASP-REPLAY-EVENT-001",
            ordinal,
            &path,
            "event delivery conflicts with the replay scope",
        );
    }
    if let (Some(session), Some(generation)) =
        (string(event, "aspsessionid"), uint(event, "aspsessiongen"))
    {
        if Some(session) != string(scope, "session_id")
            || generation != validator.session_generation
        {
            validator.error(
                "ASP-REPLAY-EVENT-001",
                ordinal,
                &path,
                "session-correlated event conflicts with replayed session state",
            );
        }
    } else if member(event, "aspsessionid").is_some() || member(event, "aspsessiongen").is_some() {
        validator.error(
            "ASP-REPLAY-EVENT-001",
            ordinal,
            &path,
            "event session id and generation must appear together",
        );
    }
    let event_type = string(event, "type").unwrap_or_default();
    if let Some(declaration) = event_declaration(surface, event_type) {
        if string(event, "dataschema") != string(declaration, "schema") {
            validator.error(
                "ASP-REPLAY-EVENT-001",
                ordinal,
                &path,
                "event schema does not match the historical Surface declaration",
            );
        }
        let control = member(event, "aspcontrol").and_then(Value::as_bool);
        let declared_control = member(declaration, "control")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        if control != Some(declared_control) {
            validator.error(
                "ASP-REPLAY-EVENT-001",
                ordinal,
                &path,
                "event control mode does not match the historical Surface declaration",
            );
        }
        if declared_control {
            if member(event, "aspscope").is_some()
                || string(event, "aspaudience") != string(scope, "runtime_id")
            {
                validator.error(
                    "ASP-REPLAY-EVENT-001",
                    ordinal,
                    &path,
                    "control event has an invalid scope or audience projection",
                );
            }
        } else {
            let declared_scope = string(declaration, "scope");
            let granted = member(grant, "scopes")
                .and_then(Value::as_array)
                .is_some_and(|scopes| scopes.iter().any(|value| value.as_str() == declared_scope));
            if string(event, "aspscope") != declared_scope
                || member(event, "aspaudience").is_some()
                || !granted
            {
                validator.error(
                    "ASP-REPLAY-EVENT-001",
                    ordinal,
                    &path,
                    "event scope is not bound by the historical Surface and Grant",
                );
            }
        }
    } else {
        validator.error(
            "ASP-REPLAY-EVENT-001",
            ordinal,
            &path,
            "event type is absent from the historical Surface",
        );
    }

    if let Some(expected) = string(event, "aspeventhash") {
        let actual = object_hash(
            EVENT_DOMAIN,
            event,
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
        if expected != actual {
            validator.error(
                "ASP-REPLAY-EVENT-001",
                ordinal,
                format!("{path}/aspeventhash"),
                "event occurrence hash does not match the exact CloudEvent",
            );
        }
    }

    if !occurrence_shape_valid {
        return Ok(());
    }
    let source = string(event, "source").expect("validated event source");
    let event_id = string(event, "id").expect("validated event id");
    let event_hash = string(event, "aspeventhash").expect("validated event occurrence hash");
    let occurrence = (source.to_owned(), event_id.to_owned());
    if let Some(previous) = validator.occurrence_hashes.get(&occurrence) {
        if previous != event_hash {
            validator.error(
                "ASP-REPLAY-DELIVERY-001",
                ordinal,
                &path,
                "event occurrence identity was reused with a different hash",
            );
        }
    } else {
        validator
            .occurrence_hashes
            .insert(occurrence, event_hash.to_owned());
    }

    if !delivery_shape_valid {
        return Ok(());
    }
    let delivery_id = string(event, "aspdeliveryid").expect("validated delivery id");
    let subscription_id = string(event, "aspsubid").expect("validated subscription id");
    let stream = string(event, "aspstream").expect("validated event stream");
    let sequence = uint(event, "aspsequence").expect("validated event sequence");
    let cursor = string(event, "aspcursor").expect("validated event cursor");
    let attempt = uint(event, "aspattempt").expect("validated delivery attempt");
    if attempt == 0 || sequence == 0 || attempt > i32::MAX as u64 || sequence > i32::MAX as u64 {
        validator.error(
            "ASP-REPLAY-DELIVERY-001",
            ordinal,
            &path,
            "event attempt and stream sequence must be positive signed 32-bit values",
        );
    }
    if string(event, "time").is_none_or(|time| !timestamp_shape(time)) {
        validator.error(
            "ASP-REPLAY-EVENT-001",
            ordinal,
            &path,
            "event time must be an RFC 3339 UTC timestamp",
        );
    }
    if let Some(previous) = validator.deliveries.get_mut(delivery_id) {
        let stable = previous.source == source
            && previous.event_id == event_id
            && previous.event_hash == event_hash
            && previous.subscription_id == subscription_id
            && previous.stream == stream
            && previous.sequence == sequence
            && previous.cursor == cursor;
        if previous.terminal_ack.is_some() {
            validator.error(
                "ASP-REPLAY-DELIVERY-001",
                ordinal,
                &path,
                "event delivery was transmitted after a terminal acknowledgement",
            );
        } else if !stable || attempt != previous.last_attempt + 1 {
            validator.error(
                "ASP-REPLAY-DELIVERY-001",
                ordinal,
                &path,
                "event delivery retry changed stable identity or attempt ordering",
            );
        } else {
            previous.last_attempt = attempt;
        }
    } else {
        if attempt != 1 {
            if validator.capture_gaps > 0 {
                validator.incomplete(
                    "ASP-REPLAY-DELIVERY-001",
                    ordinal,
                    &path,
                    "first captured event attempt has an unavailable predecessor",
                );
            } else {
                validator.error(
                    "ASP-REPLAY-DELIVERY-001",
                    ordinal,
                    &path,
                    "complete capture must begin a delivery at attempt one",
                );
            }
        }
        let stream_key = (subscription_id.to_owned(), stream.to_owned());
        let protocol_gap_epoch = validator
            .protocol_gap_epochs
            .get(subscription_id)
            .copied()
            .unwrap_or(0);
        let mut accept_stream_position = true;
        if let Some(progress) = validator.streams.get(&stream_key) {
            if sequence <= progress.sequence {
                validator.error(
                    "ASP-REPLAY-DELIVERY-001",
                    ordinal,
                    &path,
                    "known stream progress conflicts with delivery ordering",
                );
                accept_stream_position = false;
            } else if !progress.terminal {
                let covered_by_capture = validator.capture_gap_epoch > progress.capture_gap_epoch;
                if covered_by_capture {
                    validator.incomplete(
                        "ASP-REPLAY-DELIVERY-001",
                        ordinal,
                        &path,
                        "terminal acknowledgement for known stream progress is outside an explicit capture gap",
                    );
                } else {
                    validator.error(
                        "ASP-REPLAY-DELIVERY-001",
                        ordinal,
                        &path,
                        "known stream progress lacks a terminal acknowledgement",
                    );
                    accept_stream_position = false;
                }
            } else if sequence > progress.sequence + 1 {
                let covered_by_capture = validator.capture_gap_epoch > progress.capture_gap_epoch;
                let covered_by_protocol = protocol_gap_epoch > progress.protocol_gap_epoch;
                if covered_by_capture || covered_by_protocol {
                    validator.incomplete(
                        "ASP-REPLAY-DELIVERY-001",
                        ordinal,
                        &path,
                        "stream predecessor ordering crosses an explicit evidence gap",
                    );
                } else {
                    validator.error(
                        "ASP-REPLAY-DELIVERY-001",
                        ordinal,
                        &path,
                        "next stream sequence lacks a terminally acknowledged predecessor",
                    );
                    accept_stream_position = false;
                }
            }
        } else if sequence != 1 {
            if validator.capture_gap_epoch > 0 || protocol_gap_epoch > 0 {
                validator.incomplete(
                    "ASP-REPLAY-DELIVERY-001",
                    ordinal,
                    &path,
                    "first captured stream sequence has an unavailable predecessor",
                );
            } else {
                validator.error(
                    "ASP-REPLAY-DELIVERY-001",
                    ordinal,
                    &path,
                    "complete capture must begin a stream at sequence one",
                );
                accept_stream_position = false;
            }
        }
        if accept_stream_position {
            validator.streams.insert(
                stream_key,
                StreamProgress {
                    sequence,
                    delivery_id: delivery_id.to_owned(),
                    terminal: false,
                    capture_gap_epoch: validator.capture_gap_epoch,
                    protocol_gap_epoch,
                },
            );
        }
        validator.deliveries.insert(
            delivery_id.to_owned(),
            Delivery {
                source: source.to_owned(),
                event_id: event_id.to_owned(),
                event_hash: event_hash.to_owned(),
                subscription_id: subscription_id.to_owned(),
                stream: stream.to_owned(),
                sequence,
                cursor: cursor.to_owned(),
                last_attempt: attempt,
                terminal_ack: None,
            },
        );
    }
    validator.event_attempts += 1;
    Ok(())
}

pub(super) fn check_ack(body: &Value, ordinal: usize, validator: &mut Validator) {
    let path = format!("/records/{ordinal}/body");
    if !require_members(
        body,
        &["type", "payload"],
        "ASP-REPLAY-ACK-001",
        ordinal,
        &path,
        "event acknowledgement is missing a required member",
        validator,
    ) {
        return;
    }
    if !body
        .as_object()
        .is_some_and(|object| has_only(object, &["type", "payload"]))
        || string(body, "type") != Some("event.ack")
    {
        validator.error(
            "ASP-REPLAY-ACK-001",
            ordinal,
            &path,
            "event acknowledgement has the wrong message type",
        );
        return;
    }
    let Some(payload) = member(body, "payload") else {
        return;
    };
    if !require_members(
        payload,
        &["subscription_id", "delivery_id", "cursor", "outcome"],
        "ASP-REPLAY-ACK-001",
        ordinal,
        &format!("{path}/payload"),
        "event acknowledgement payload is missing a required member",
        validator,
    ) {
        return;
    }
    if !payload.as_object().is_some_and(|object| {
        has_only(
            object,
            &[
                "subscription_id",
                "delivery_id",
                "cursor",
                "outcome",
                "reason",
            ],
        )
    }) {
        validator.error(
            "ASP-REPLAY-ACK-001",
            ordinal,
            &path,
            "event acknowledgement payload contains an unknown member",
        );
    }
    let payload_path = format!("{path}/payload");
    let mut payload_shape_valid = true;
    for name in ["subscription_id", "delivery_id", "cursor", "outcome"] {
        if !MemberType::string(name).is_satisfied_by(payload) {
            validator.error(
                "ASP-REPLAY-ACK-001",
                ordinal,
                format!("{payload_path}/{name}"),
                "event acknowledgement identity and outcome members must be strings",
            );
            payload_shape_valid = false;
        }
    }
    if member(payload, "reason").is_some() && !MemberType::string("reason").is_satisfied_by(payload)
    {
        validator.error(
            "ASP-REPLAY-ACK-001",
            ordinal,
            format!("{payload_path}/reason"),
            "event acknowledgement reason must be a string when present",
        );
        payload_shape_valid = false;
    }
    if !payload_shape_valid {
        return;
    }
    let delivery_id = string(payload, "delivery_id").expect("validated acknowledgement delivery");
    let outcome = string(payload, "outcome").expect("validated acknowledgement outcome");
    if !["processed", "discarded", "retry"].contains(&outcome)
        || (outcome == "discarded" && string(payload, "reason").is_none())
    {
        validator.error(
            "ASP-REPLAY-ACK-001",
            ordinal,
            &path,
            "event acknowledgement outcome or reason is invalid",
        );
    }
    validator.event_acknowledgements += 1;
    let Some(delivery_snapshot) = validator.deliveries.get(delivery_id).cloned() else {
        validator.pending_references.push(PendingReference {
            check_id: "ASP-REPLAY-ACK-001",
            ordinal,
            path,
            target: delivery_id.to_owned(),
            kind: PendingReferenceKind::Acknowledgement,
        });
        return;
    };
    if string(payload, "subscription_id") != Some(delivery_snapshot.subscription_id.as_str())
        || string(payload, "cursor") != Some(delivery_snapshot.cursor.as_str())
    {
        validator.error(
            "ASP-REPLAY-ACK-001",
            ordinal,
            &path,
            "acknowledgement subscription or cursor conflicts with its delivery",
        );
    }
    if outcome == "retry" && delivery_snapshot.terminal_ack.is_some() {
        validator.error(
            "ASP-REPLAY-ACK-001",
            ordinal,
            &path,
            "retry acknowledgement cannot follow a terminal acknowledgement",
        );
    } else if outcome != "retry" {
        let current = (
            outcome.to_owned(),
            string(payload, "reason").map(str::to_owned),
        );
        if let Some(previous) = &delivery_snapshot.terminal_ack {
            if previous != &current {
                validator.error(
                    "ASP-REPLAY-ACK-001",
                    ordinal,
                    &path,
                    "terminal acknowledgement was replayed with a conflicting outcome",
                );
            }
        } else {
            if let Some(delivery) = validator.deliveries.get_mut(delivery_id) {
                delivery.terminal_ack = Some(current);
            }
            let stream_key = (
                delivery_snapshot.subscription_id.clone(),
                delivery_snapshot.stream.clone(),
            );
            if let Some(progress) = validator.streams.get_mut(&stream_key)
                && progress.delivery_id == delivery_id
            {
                progress.terminal = true;
            }
        }
    }
}

pub(super) fn check_gap(body: &Value, ordinal: usize, validator: &mut Validator) {
    validator.event_gaps += 1;
    validator.incomplete(
        "ASP-REPLAY-GAP-001",
        ordinal,
        format!("/records/{ordinal}/body"),
        "protocol event gap makes replay history incomplete",
    );
    if !body
        .as_object()
        .is_some_and(|object| has_only(object, &["type", "payload"]))
        || string(body, "type") != Some("event.gap")
        || !member(body, "payload").is_some_and(|payload| {
            payload.as_object().is_some_and(|object| {
                has_only(
                    object,
                    &[
                        "subscription_id",
                        "last_accepted_cursor",
                        "earliest_available_cursor",
                        "reason",
                    ],
                )
            }) && matches!(
                string(payload, "reason"),
                Some("retention_expired" | "authorization_changed")
            ) && string(payload, "subscription_id").is_some()
                && string(payload, "last_accepted_cursor").is_some()
        })
    {
        validator.error(
            "ASP-REPLAY-GAP-001",
            ordinal,
            format!("/records/{ordinal}/body"),
            "event gap message is not a closed supported gap projection",
        );
    } else if let Some(subscription_id) =
        member(body, "payload").and_then(|payload| string(payload, "subscription_id"))
    {
        *validator
            .protocol_gap_epochs
            .entry(subscription_id.to_owned())
            .or_default() += 1;
    }
}
