use std::collections::{BTreeMap, HashMap, HashSet};

use serde_json::Value;

use crate::{Diagnostic, MAX_DIAGNOSTIC_MESSAGE_CHARS, MAX_DIAGNOSTIC_PATH_CHARS, MAX_DIAGNOSTICS};

#[derive(Clone, Debug)]
pub(super) struct Delivery {
    pub(super) source: String,
    pub(super) event_id: String,
    pub(super) event_hash: String,
    pub(super) subscription_id: String,
    pub(super) stream: String,
    pub(super) sequence: u64,
    pub(super) cursor: String,
    pub(super) last_attempt: u64,
    pub(super) terminal_ack: Option<(String, Option<String>)>,
}

#[derive(Clone, Debug)]
pub(super) struct StreamProgress {
    pub(super) sequence: u64,
    pub(super) delivery_id: String,
    pub(super) terminal: bool,
    pub(super) capture_gap_epoch: u64,
    pub(super) protocol_gap_epoch: u64,
}

#[derive(Clone, Debug, Default)]
pub(super) struct FindingSummary {
    pub(super) errors: usize,
    pub(super) incomplete: usize,
}

#[derive(Clone, Debug)]
pub(super) struct ApprovalRequirement {
    pub(super) accepted_roles: HashSet<String>,
    pub(super) max_age_seconds: u64,
}

#[derive(Clone, Debug)]
pub(super) struct ReceiptProjection {
    pub(super) ordinal: usize,
    pub(super) receipt_type: String,
    pub(super) grant_hash: String,
    pub(super) surface_hash: String,
    pub(super) surface_version: String,
    pub(super) session_id: String,
    pub(super) session_generation: u64,
    pub(super) trace_id: String,
    pub(super) linked_trace_id: Option<String>,
    pub(super) action_id: String,
    pub(super) idempotency_key: String,
    pub(super) input_hash: String,
    pub(super) execution: Option<Value>,
    pub(super) execution_hash: Option<String>,
    pub(super) timestamp: String,
    pub(super) result: String,
    pub(super) effect_outcome: Option<String>,
    pub(super) actual_effect_ids: HashSet<String>,
    pub(super) approval_role: Option<String>,
    pub(super) approval_receipt_hashes: BTreeMap<String, String>,
    pub(super) target_receipt_hash: Option<String>,
}

#[derive(Clone, Debug)]
pub(super) enum PendingReferenceKind {
    Acknowledgement,
    ReceiptParent,
    ApprovalSideLink { role: String },
    RecoveryTarget,
}

#[derive(Clone, Debug)]
pub(super) struct PendingReference {
    pub(super) check_id: &'static str,
    pub(super) ordinal: usize,
    pub(super) path: String,
    pub(super) target: String,
    pub(super) kind: PendingReferenceKind,
}

#[derive(Debug)]
pub(super) struct Validator {
    pub(super) diagnostics: Vec<Diagnostic>,
    pub(super) diagnostics_truncated: bool,
    pub(super) diagnostics_omitted: usize,
    pub(super) has_errors: bool,
    pub(super) finding_summaries: HashMap<String, FindingSummary>,
    pub(super) incomplete: bool,
    pub(super) capture_partial: bool,
    pub(super) session_state: String,
    pub(super) session_generation: u64,
    pub(super) session_transitions: usize,
    pub(super) session_gap_pending: bool,
    pub(super) initial_session_error_reported: bool,
    pub(super) occurrence_hashes: HashMap<(String, String), String>,
    pub(super) deliveries: HashMap<String, Delivery>,
    pub(super) streams: HashMap<(String, String), StreamProgress>,
    pub(super) capture_gap_epoch: u64,
    pub(super) protocol_gap_epochs: HashMap<String, u64>,
    pub(super) event_attempts: usize,
    pub(super) event_acknowledgements: usize,
    pub(super) event_gaps: usize,
    pub(super) capture_gaps: usize,
    pub(super) validated_capture_gaps: usize,
    pub(super) receipts_by_id: HashMap<String, String>,
    pub(super) receipts_by_hash: HashMap<String, ReceiptProjection>,
    pub(super) receipt_hashes: HashSet<String>,
    pub(super) receipt_parents: HashSet<String>,
    pub(super) receipt_roots: HashSet<String>,
    pub(super) pending_references: Vec<PendingReference>,
}

impl Validator {
    pub(super) fn new(capture_partial: bool) -> Self {
        Self {
            diagnostics: Vec::new(),
            diagnostics_truncated: false,
            diagnostics_omitted: 0,
            has_errors: false,
            finding_summaries: HashMap::new(),
            incomplete: capture_partial,
            capture_partial,
            session_state: "absent".to_owned(),
            session_generation: 0,
            session_transitions: 0,
            session_gap_pending: false,
            initial_session_error_reported: false,
            occurrence_hashes: HashMap::new(),
            deliveries: HashMap::new(),
            streams: HashMap::new(),
            capture_gap_epoch: 0,
            protocol_gap_epochs: HashMap::new(),
            event_attempts: 0,
            event_acknowledgements: 0,
            event_gaps: 0,
            capture_gaps: 0,
            validated_capture_gaps: 0,
            receipts_by_id: HashMap::new(),
            receipts_by_hash: HashMap::new(),
            receipt_hashes: HashSet::new(),
            receipt_parents: HashSet::new(),
            receipt_roots: HashSet::new(),
            pending_references: Vec::new(),
        }
    }

    pub(super) fn error(
        &mut self,
        check: &str,
        ordinal: usize,
        path: impl Into<String>,
        message: &str,
    ) {
        self.has_errors = true;
        self.finding_summaries
            .entry(check.to_owned())
            .or_default()
            .errors += 1;
        self.push_diagnostic(check, "error", ordinal, path.into(), message);
    }

    pub(super) fn incomplete(
        &mut self,
        check: &str,
        ordinal: usize,
        path: impl Into<String>,
        message: &str,
    ) {
        self.incomplete = true;
        self.finding_summaries
            .entry(check.to_owned())
            .or_default()
            .incomplete += 1;
        self.push_diagnostic(check, "incomplete", ordinal, path.into(), message);
    }

    fn push_diagnostic(
        &mut self,
        check: &str,
        severity: &str,
        ordinal: usize,
        path: String,
        message: &str,
    ) {
        let (path, path_truncated) = bounded_path(&path);
        let (message, message_truncated) = bounded_text(message, MAX_DIAGNOSTIC_MESSAGE_CHARS);
        self.diagnostics_truncated |= path_truncated || message_truncated;
        if self.diagnostics.len() >= MAX_DIAGNOSTICS {
            self.diagnostics_truncated = true;
            self.diagnostics_omitted += 1;
            if severity == "error"
                && !self
                    .diagnostics
                    .iter()
                    .any(|diagnostic| diagnostic.severity == "error")
            {
                self.diagnostics.pop();
            } else {
                return;
            }
        }
        self.diagnostics.push(Diagnostic {
            check_id: check.to_owned(),
            severity: severity.to_owned(),
            path,
            message,
            ordinal,
        });
    }
}

fn bounded_text(value: &str, max_chars: usize) -> (String, bool) {
    if value.chars().count() <= max_chars {
        return (value.to_owned(), false);
    }
    let mut bounded: String = value.chars().take(max_chars.saturating_sub(1)).collect();
    bounded.push('…');
    (bounded, true)
}

fn bounded_path(value: &str) -> (String, bool) {
    if (value.is_empty() || value.starts_with('/'))
        && value.chars().count() <= MAX_DIAGNOSTIC_PATH_CHARS
    {
        return (value.to_owned(), false);
    }
    ("/<truncated>".to_owned(), true)
}
