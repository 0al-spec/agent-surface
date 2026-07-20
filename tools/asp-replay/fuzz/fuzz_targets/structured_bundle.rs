#![no_main]

use arbitrary::Arbitrary;
use libfuzzer_sys::fuzz_target;
use serde_json::{Map, Value};

const MAX_MUTATIONS: usize = 16;
const FIXTURES: [&[u8]; 3] = [
    include_bytes!("../../tests/fixtures/complete-session.json"),
    include_bytes!("../../tests/fixtures/explicit-capture-gap.json"),
    include_bytes!("../../tests/fixtures/event-receipt-flow.json"),
];
const DIGEST_A: &str = "sha-256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
const DIGEST_E: &str = "sha-256:EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE";

#[derive(Arbitrary, Debug)]
struct StructuredInput {
    fixture: u8,
    mutations: Vec<Mutation>,
}

#[derive(Arbitrary, Debug)]
enum Mutation {
    CaptureCompleteness(bool),
    ReverseCaptureTime,
    RecordPair {
        slot: u8,
        pair: RecordPair,
    },
    SessionStates {
        slot: u8,
        prior: SessionState,
        next: SessionState,
    },
    EventAttempt {
        slot: u8,
        value: u32,
    },
    EventSequence {
        slot: u8,
        value: u32,
    },
    EventSource {
        slot: u8,
        alternate: bool,
    },
    AckOutcome {
        slot: u8,
        outcome: AckOutcome,
    },
    AckCursor {
        slot: u8,
        alternate: bool,
    },
    ReceiptResult {
        slot: u8,
        result: ReceiptResult,
    },
    ReceiptParent {
        slot: u8,
        alternate: bool,
    },
    DuplicateRecordId {
        source: u8,
        target: u8,
    },
    InsertSecret {
        slot: u8,
        field: SecretField,
    },
    RemoveBodyMember {
        slot: u8,
        member: BodyMember,
    },
}

#[derive(Arbitrary, Debug)]
enum RecordPair {
    Session,
    EventDelivery,
    EventAck,
    EventGap,
    RuntimeReceipt,
    AppReceipt,
    ApprovalReceipt,
    CaptureGap,
}

impl RecordPair {
    fn values(&self) -> (&'static str, &'static str) {
        match self {
            Self::Session => ("session_transition", "session.transition"),
            Self::EventDelivery => ("event_delivery", "event.delivery"),
            Self::EventAck => ("event_ack", "event.ack"),
            Self::EventGap => ("event_gap", "event.gap"),
            Self::RuntimeReceipt => ("receipt", "receipt.runtime"),
            Self::AppReceipt => ("receipt", "receipt.app"),
            Self::ApprovalReceipt => ("receipt", "receipt.approval"),
            Self::CaptureGap => ("capture_gap", "capture.gap"),
        }
    }
}

#[derive(Arbitrary, Debug)]
enum SessionState {
    Absent,
    Active,
    Interrupted,
    Cancelled,
    Completed,
    Failed,
}

impl SessionState {
    fn as_str(&self) -> &'static str {
        match self {
            Self::Absent => "absent",
            Self::Active => "active",
            Self::Interrupted => "interrupted",
            Self::Cancelled => "cancelled",
            Self::Completed => "completed",
            Self::Failed => "failed",
        }
    }
}

#[derive(Arbitrary, Debug)]
enum AckOutcome {
    Processed,
    Discarded,
    Retry,
    Unknown,
}

impl AckOutcome {
    fn as_str(&self) -> &'static str {
        match self {
            Self::Processed => "processed",
            Self::Discarded => "discarded",
            Self::Retry => "retry",
            Self::Unknown => "unknown",
        }
    }
}

#[derive(Arbitrary, Debug)]
enum ReceiptResult {
    Success,
    Denied,
    Failed,
    Approved,
    Unknown,
}

impl ReceiptResult {
    fn as_str(&self) -> &'static str {
        match self {
            Self::Success => "success",
            Self::Denied => "denied",
            Self::Failed => "failed",
            Self::Approved => "approved",
            Self::Unknown => "unknown",
        }
    }
}

#[derive(Arbitrary, Debug)]
enum SecretField {
    Authorization,
    AccessToken,
    RefreshToken,
    ExecutionToken,
    PrivateKey,
}

impl SecretField {
    fn as_str(&self) -> &'static str {
        match self {
            Self::Authorization => "authorization",
            Self::AccessToken => "access_token",
            Self::RefreshToken => "refresh_token",
            Self::ExecutionToken => "execution_token",
            Self::PrivateKey => "private_key",
        }
    }
}

#[derive(Arbitrary, Debug)]
enum BodyMember {
    SessionGeneration,
    PriorState,
    NextState,
    Reason,
    EventId,
    EventHash,
    DeliveryId,
    Cursor,
    ReceiptHash,
    PolicyDecision,
}

impl BodyMember {
    fn as_str(&self) -> &'static str {
        match self {
            Self::SessionGeneration => "session_generation",
            Self::PriorState => "prior_state",
            Self::NextState => "next_state",
            Self::Reason => "reason",
            Self::EventId => "id",
            Self::EventHash => "aspeventhash",
            Self::DeliveryId => "aspdeliveryid",
            Self::Cursor => "aspcursor",
            Self::ReceiptHash => "receipt_hash",
            Self::PolicyDecision => "policy_decision",
        }
    }
}

fn selected_record_mut(bundle: &mut Value, slot: u8) -> Option<&mut Value> {
    let records = bundle.get_mut("records")?.as_array_mut()?;
    if records.is_empty() {
        return None;
    }
    let index = usize::from(slot) % records.len();
    records.get_mut(index)
}

fn selected_body_mut(bundle: &mut Value, slot: u8) -> Option<&mut Map<String, Value>> {
    selected_record_mut(bundle, slot)?
        .get_mut("body")?
        .as_object_mut()
}

fn apply_mutation(bundle: &mut Value, mutation: Mutation) {
    match mutation {
        Mutation::CaptureCompleteness(partial) => {
            bundle["capture"]["completeness"] =
                Value::String(if partial { "partial" } else { "complete" }.to_owned());
        }
        Mutation::ReverseCaptureTime => {
            bundle["capture"]["started_at"] = Value::String("2026-07-20T12:00:00Z".to_owned());
            bundle["capture"]["ended_at"] = Value::String("2026-07-20T11:59:59Z".to_owned());
        }
        Mutation::RecordPair { slot, pair } => {
            let Some(record) = selected_record_mut(bundle, slot) else {
                return;
            };
            let (kind, name) = pair.values();
            record["kind"] = Value::String(kind.to_owned());
            record["name"] = Value::String(name.to_owned());
        }
        Mutation::SessionStates { slot, prior, next } => {
            let Some(body) = selected_body_mut(bundle, slot) else {
                return;
            };
            body.insert(
                "prior_state".to_owned(),
                Value::String(prior.as_str().to_owned()),
            );
            body.insert(
                "next_state".to_owned(),
                Value::String(next.as_str().to_owned()),
            );
        }
        Mutation::EventAttempt { slot, value } => {
            if let Some(body) = selected_body_mut(bundle, slot) {
                body.insert("aspattempt".to_owned(), Value::from(value));
            }
        }
        Mutation::EventSequence { slot, value } => {
            if let Some(body) = selected_body_mut(bundle, slot) {
                body.insert("aspsequence".to_owned(), Value::from(value));
            }
        }
        Mutation::EventSource { slot, alternate } => {
            if let Some(body) = selected_body_mut(bundle, slot) {
                body.insert(
                    "source".to_owned(),
                    Value::String(
                        if alternate {
                            "https://other.example.com"
                        } else {
                            "https://code.example.com"
                        }
                        .to_owned(),
                    ),
                );
            }
        }
        Mutation::AckOutcome { slot, outcome } => {
            if let Some(payload) = selected_body_mut(bundle, slot)
                .and_then(|body| body.get_mut("payload"))
                .and_then(Value::as_object_mut)
            {
                payload.insert(
                    "outcome".to_owned(),
                    Value::String(outcome.as_str().to_owned()),
                );
            }
        }
        Mutation::AckCursor { slot, alternate } => {
            if let Some(payload) = selected_body_mut(bundle, slot)
                .and_then(|body| body.get_mut("payload"))
                .and_then(Value::as_object_mut)
            {
                payload.insert(
                    "cursor".to_owned(),
                    Value::String(
                        if alternate {
                            "opaque:alternate"
                        } else {
                            "opaque:position-after-42"
                        }
                        .to_owned(),
                    ),
                );
            }
        }
        Mutation::ReceiptResult { slot, result } => {
            if let Some(body) = selected_body_mut(bundle, slot) {
                body.insert(
                    "result".to_owned(),
                    Value::String(result.as_str().to_owned()),
                );
            }
        }
        Mutation::ReceiptParent { slot, alternate } => {
            if let Some(body) = selected_body_mut(bundle, slot) {
                body.insert(
                    "parent_receipt_hash".to_owned(),
                    Value::String(if alternate { DIGEST_E } else { DIGEST_A }.to_owned()),
                );
            }
        }
        Mutation::DuplicateRecordId { source, target } => {
            let Some(records) = bundle.get_mut("records").and_then(Value::as_array_mut) else {
                return;
            };
            if records.is_empty() {
                return;
            }
            let source = usize::from(source) % records.len();
            let target = usize::from(target) % records.len();
            let Some(record_id) = records[source]
                .get("record_id")
                .and_then(Value::as_str)
                .map(str::to_owned)
            else {
                return;
            };
            records[target]["record_id"] = Value::String(record_id);
        }
        Mutation::InsertSecret { slot, field } => {
            if let Some(body) = selected_body_mut(bundle, slot) {
                body.insert(
                    field.as_str().to_owned(),
                    Value::String("synthetic-fuzz-secret".to_owned()),
                );
            }
        }
        Mutation::RemoveBodyMember { slot, member } => {
            if let Some(body) = selected_body_mut(bundle, slot) {
                body.remove(member.as_str());
            }
        }
    }
}

fuzz_target!(|input: StructuredInput| {
    let fixture = FIXTURES[usize::from(input.fixture) % FIXTURES.len()];
    let mut bundle: Value =
        serde_json::from_slice(fixture).expect("checked-in replay fixture must remain valid JSON");

    for mutation in input.mutations.into_iter().take(MAX_MUTATIONS) {
        apply_mutation(&mut bundle, mutation);
    }

    let Ok(report) = asp_replay::fuzz_support::rehash_and_verify(&mut bundle) else {
        return;
    };

    assert!(report.diagnostics.len() <= asp_replay::MAX_DIAGNOSTICS);
    let findings = report
        .checks
        .iter()
        .map(|check| check.findings)
        .sum::<usize>();
    assert_eq!(
        findings,
        report.diagnostics.len() + report.diagnostics_omitted
    );
    assert_eq!(report.claim_effect, "descriptive_only");
});
