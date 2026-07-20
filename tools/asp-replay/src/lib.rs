//! Deterministic, offline consistency replay for portable ASP evidence bundles.

use std::collections::{BTreeMap, HashMap, HashSet};
use std::fmt;
use std::fs;
use std::path::{Component, Path};

use base64::Engine;
use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use serde::de::{self, Deserializer, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};
use thiserror::Error;

pub const MAX_INPUT_BYTES: usize = 16 * 1024 * 1024;
pub const MAX_RECORDS: usize = 4096;
pub const MAX_DIAGNOSTICS: usize = 256;
pub const MAX_DIAGNOSTIC_PATH_CHARS: usize = 512;
pub const MAX_DIAGNOSTIC_MESSAGE_CHARS: usize = 256;
pub const TOOL_NAME: &str = "asp-replay";
pub const TOOL_VERSION: &str = env!("CARGO_PKG_VERSION");
pub const PROFILE: &str = "https://github.com/0al-spec/agent-surface/profiles/replay-bundle/v1";
pub const REPORT_PROFILE: &str =
    "https://github.com/0al-spec/agent-surface/tools/asp-replay/report/v1";
pub const CHECK_PROFILE: &str =
    "https://github.com/0al-spec/agent-surface/tools/asp-replay/checks/v1";

pub const BUNDLE_SCHEMA: &str = include_str!("../schema/bundle.schema.json");
pub const REPORT_SCHEMA: &str = include_str!("../schema/report.schema.json");
pub const CHECKS_SCHEMA: &str = include_str!("../schema/checks.schema.json");
pub const CASES_SCHEMA: &str = include_str!("../schema/cases.schema.json");
pub const CHECK_REGISTRY: &str = include_str!("../checks/v1/checks.json");
pub const CASE_REGISTRY: &str = include_str!("../cases/v1/cases.json");

const MANIFEST_DOMAIN: &str = "https://github.com/0al-spec/agent-surface/hash/manifest/v1";
const GRANT_DOMAIN: &str = "https://github.com/0al-spec/agent-surface/hash/grant/v1";
const EVENT_DOMAIN: &str = "https://github.com/0al-spec/agent-surface/hash/event/v1";
const POLICY_DOMAIN: &str = "https://github.com/0al-spec/agent-surface/hash/policy-decision/v1";
const EXECUTION_DOMAIN: &str = "https://github.com/0al-spec/agent-surface/hash/action-execution/v1";
const ACTUAL_EFFECTS_DOMAIN: &str =
    "https://github.com/0al-spec/agent-surface/hash/actual-effects/v1";
const RECEIPT_DOMAIN: &str = "https://github.com/0al-spec/agent-surface/hash/receipt/v1";
const RECORD_DOMAIN: &str = "https://github.com/0al-spec/agent-surface/hash/replay-record/v1";
const BUNDLE_DOMAIN: &str = "https://github.com/0al-spec/agent-surface/hash/replay-bundle/v1";
const REPORT_DOMAIN: &str = "https://github.com/0al-spec/agent-surface/hash/replay-report/v1";
const SAFE_INTEGER: i128 = (1_i128 << 53) - 1;
const DIGEST_PATTERN_LENGTH: usize = 51;

const IMPLEMENTED_CHECKS: [&str; 12] = [
    "ASP-REPLAY-SCHEMA-001",
    "ASP-REPLAY-CONTEXT-001",
    "ASP-REPLAY-ORDER-001",
    "ASP-REPLAY-SESSION-001",
    "ASP-REPLAY-EVENT-001",
    "ASP-REPLAY-DELIVERY-001",
    "ASP-REPLAY-ACK-001",
    "ASP-REPLAY-GAP-001",
    "ASP-REPLAY-RECEIPT-HASH-001",
    "ASP-REPLAY-RECEIPT-CHAIN-001",
    "ASP-REPLAY-RECEIPT-LINK-001",
    "ASP-REPLAY-SECRETS-001",
];

#[derive(Debug, Error)]
pub enum ReplayError {
    #[error("strict JSON parse failed: {0}")]
    StrictJson(String),
    #[error("cannot read {path}: {source}")]
    Io {
        path: String,
        #[source]
        source: std::io::Error,
    },
    #[error("self-check failed: {0}")]
    SelfCheck(String),
    #[error("cannot serialize canonical JSON: {0}")]
    Canonical(String),
}

#[derive(Clone, Debug)]
struct StrictValue(Value);

struct StrictVisitor;

fn reject_unicode_noncharacters<E: de::Error>(value: &str) -> Result<(), E> {
    if let Some(code_point) = value.chars().map(u32::from).find(|code_point| {
        (0xfdd0..=0xfdef).contains(code_point)
            || code_point & 0xffff == 0xfffe
            || code_point & 0xffff == 0xffff
    }) {
        return Err(E::custom(format!(
            "Unicode noncharacter U+{code_point:04X} is forbidden"
        )));
    }
    Ok(())
}

impl<'de> Visitor<'de> for StrictVisitor {
    type Value = StrictValue;

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("duplicate-free I-JSON")
    }

    fn visit_bool<E>(self, value: bool) -> Result<Self::Value, E> {
        Ok(StrictValue(Value::Bool(value)))
    }

    fn visit_i64<E>(self, value: i64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        if i128::from(value).abs() > SAFE_INTEGER {
            return Err(E::custom("integer is outside the I-JSON safe range"));
        }
        Ok(StrictValue(Value::Number(value.into())))
    }

    fn visit_u64<E>(self, value: u64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        if i128::from(value) > SAFE_INTEGER {
            return Err(E::custom("integer is outside the I-JSON safe range"));
        }
        Ok(StrictValue(Value::Number(value.into())))
    }

    fn visit_f64<E>(self, value: f64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        if !value.is_finite() {
            return Err(E::custom("non-finite numbers are forbidden"));
        }
        if value == 0.0 && value.is_sign_negative() {
            return Err(E::custom("JSON negative zero is forbidden"));
        }
        if value.fract() == 0.0 && value.abs() > SAFE_INTEGER as f64 {
            return Err(E::custom(
                "integral number is outside the I-JSON safe range",
            ));
        }
        let number = serde_json::Number::from_f64(value)
            .ok_or_else(|| E::custom("number cannot be represented as binary64"))?;
        Ok(StrictValue(Value::Number(number)))
    }

    fn visit_str<E>(self, value: &str) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        reject_unicode_noncharacters::<E>(value)?;
        Ok(StrictValue(Value::String(value.to_owned())))
    }

    fn visit_string<E>(self, value: String) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        reject_unicode_noncharacters::<E>(&value)?;
        Ok(StrictValue(Value::String(value)))
    }

    fn visit_none<E>(self) -> Result<Self::Value, E> {
        Ok(StrictValue(Value::Null))
    }

    fn visit_unit<E>(self) -> Result<Self::Value, E> {
        Ok(StrictValue(Value::Null))
    }

    fn visit_some<D>(self, deserializer: D) -> Result<Self::Value, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_any(StrictVisitor)
    }

    fn visit_seq<A>(self, mut sequence: A) -> Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        let mut values = Vec::new();
        while let Some(value) = sequence.next_element::<StrictValue>()? {
            values.push(value.0);
        }
        Ok(StrictValue(Value::Array(values)))
    }

    fn visit_map<A>(self, mut object: A) -> Result<Self::Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        let mut values = Map::new();
        while let Some(key) = object.next_key::<String>()? {
            reject_unicode_noncharacters::<A::Error>(&key)?;
            if values.contains_key(&key) {
                return Err(de::Error::custom(format!(
                    "duplicate JSON object member {key:?}"
                )));
            }
            let value = object.next_value::<StrictValue>()?;
            values.insert(key, value.0);
        }
        Ok(StrictValue(Value::Object(values)))
    }
}

impl<'de> Deserialize<'de> for StrictValue {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_any(StrictVisitor)
    }
}

fn reject_lexical_negative_zero(document: &str) -> Result<(), ReplayError> {
    let bytes = document.as_bytes();
    let mut index = 0;
    let mut in_string = false;
    let mut escaped = false;
    while index < bytes.len() {
        let byte = bytes[index];
        if in_string {
            if escaped {
                escaped = false;
            } else if byte == b'\\' {
                escaped = true;
            } else if byte == b'"' {
                in_string = false;
            }
            index += 1;
            continue;
        }
        if byte == b'"' {
            in_string = true;
            index += 1;
            continue;
        }
        let boundary = index == 0
            || matches!(
                bytes[index - 1],
                b' ' | b'\t' | b'\r' | b'\n' | b'[' | b'{' | b',' | b':'
            );
        if byte != b'-' || !boundary || bytes.get(index + 1) != Some(&b'0') {
            index += 1;
            continue;
        }
        let start = index;
        index += 2;
        while bytes.get(index).is_some_and(|byte| {
            byte.is_ascii_digit() || matches!(*byte, b'.' | b'e' | b'E' | b'+' | b'-')
        }) {
            index += 1;
        }
        let token = &document[start..index];
        let mantissa = token[1..]
            .split_once(['e', 'E'])
            .map_or(&token[1..], |(mantissa, _)| mantissa);
        if mantissa
            .bytes()
            .filter(|byte| *byte != b'.')
            .all(|byte| byte == b'0')
        {
            return Err(ReplayError::StrictJson(
                "JSON negative zero is forbidden".to_owned(),
            ));
        }
    }
    Ok(())
}

fn parse_strict(document: &[u8]) -> Result<Value, ReplayError> {
    if document.len() > MAX_INPUT_BYTES {
        return Err(ReplayError::StrictJson(format!(
            "input exceeds {MAX_INPUT_BYTES} bytes"
        )));
    }
    let text = std::str::from_utf8(document)
        .map_err(|error| ReplayError::StrictJson(format!("input is not UTF-8: {error}")))?;
    reject_lexical_negative_zero(text)?;
    let mut deserializer = serde_json::Deserializer::from_str(text);
    let value = StrictValue::deserialize(&mut deserializer)
        .map_err(|error| ReplayError::StrictJson(error.to_string()))?
        .0;
    deserializer
        .end()
        .map_err(|error| ReplayError::StrictJson(error.to_string()))?;
    if !value.is_object() {
        return Err(ReplayError::StrictJson(
            "bundle root must be an object".to_owned(),
        ));
    }
    Ok(value)
}

fn raw_sha256(bytes: &[u8]) -> String {
    format!("sha-256:{}", URL_SAFE_NO_PAD.encode(Sha256::digest(bytes)))
}

fn object_hash(domain: &str, value: &Value, exclusions: &[&str]) -> Result<String, ReplayError> {
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

fn valid_digest(value: &str) -> bool {
    if value.len() != DIGEST_PATTERN_LENGTH || !value.starts_with("sha-256:") {
        return false;
    }
    URL_SAFE_NO_PAD
        .decode(&value[8..])
        .is_ok_and(|bytes| bytes.len() == 32 && URL_SAFE_NO_PAD.encode(bytes) == value[8..])
}

fn valid_bundle_id(value: &str) -> bool {
    if value.is_empty() || value.len() > 256 || !value.is_ascii() {
        return false;
    }
    let mut bytes = value.bytes();
    bytes
        .next()
        .is_some_and(|byte| byte.is_ascii_alphanumeric())
        && bytes
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b':' | b'-'))
}

#[derive(Clone, Debug, Deserialize)]
struct CheckRegistry {
    schema_version: u64,
    profile: String,
    version: String,
    checks: Vec<CheckDefinition>,
}

#[derive(Clone, Debug, Deserialize)]
struct CheckDefinition {
    check_id: String,
    title: String,
}

fn registry() -> Result<CheckRegistry, ReplayError> {
    serde_json::from_str(CHECK_REGISTRY)
        .map_err(|error| ReplayError::SelfCheck(format!("check registry: {error}")))
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct Diagnostic {
    pub check_id: String,
    pub severity: String,
    pub path: String,
    pub message: String,
    #[serde(skip_serializing)]
    ordinal: usize,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct CheckResult {
    pub check_id: String,
    pub title: String,
    pub status: String,
    pub findings: usize,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct ReplaySummary {
    pub status: String,
    pub final_session_state: String,
    pub session_generation: u64,
    pub session_transitions: usize,
    pub event_occurrences: usize,
    pub event_deliveries: usize,
    pub event_attempts: usize,
    pub event_acknowledgements: usize,
    pub event_gaps: usize,
    pub capture_gaps: usize,
    pub receipts: usize,
    pub receipt_roots: usize,
    pub receipt_heads: usize,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct ReportTool {
    pub name: String,
    pub version: String,
    pub check_profile: String,
    pub check_version: String,
    pub check_registry_sha256: String,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct ReportInput {
    pub source_sha256: String,
    pub bundle_id: Option<String>,
    pub bundle_hash: Option<String>,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct Assurance {
    pub verified: Vec<String>,
    pub not_verified: Vec<String>,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct Report {
    #[serde(rename = "$schema")]
    pub schema: String,
    pub schema_version: u64,
    pub report_profile: String,
    pub claim_effect: String,
    pub tool: ReportTool,
    pub input: ReportInput,
    pub evaluation_state: String,
    pub integrity_verdict: String,
    pub replay_completeness: String,
    pub verdict: String,
    pub checks: Vec<CheckResult>,
    pub diagnostics: Vec<Diagnostic>,
    pub diagnostics_truncated: bool,
    pub diagnostics_omitted: usize,
    pub replay: ReplaySummary,
    pub assurance: Assurance,
    pub report_hash: String,
}

#[derive(Clone, Debug)]
struct Delivery {
    source: String,
    event_id: String,
    event_hash: String,
    subscription_id: String,
    stream: String,
    sequence: u64,
    cursor: String,
    last_attempt: u64,
    terminal_ack: Option<(String, Option<String>)>,
}

#[derive(Clone, Debug)]
struct StreamProgress {
    sequence: u64,
    delivery_id: String,
    terminal: bool,
    capture_gap_epoch: u64,
    protocol_gap_epoch: u64,
}

#[derive(Clone, Debug, Default)]
struct FindingSummary {
    errors: usize,
    incomplete: usize,
}

#[derive(Clone, Debug)]
struct ApprovalRequirement {
    accepted_roles: HashSet<String>,
    max_age_seconds: u64,
}

#[derive(Clone, Debug)]
struct ReceiptProjection {
    ordinal: usize,
    receipt_type: String,
    grant_hash: String,
    surface_hash: String,
    surface_version: String,
    session_id: String,
    session_generation: u64,
    trace_id: String,
    linked_trace_id: Option<String>,
    action_id: String,
    idempotency_key: String,
    input_hash: String,
    execution: Option<Value>,
    execution_hash: Option<String>,
    timestamp: String,
    result: String,
    effect_outcome: Option<String>,
    actual_effect_ids: HashSet<String>,
    approval_role: Option<String>,
    approval_receipt_hashes: BTreeMap<String, String>,
    target_receipt_hash: Option<String>,
}

#[derive(Clone, Debug)]
enum PendingReferenceKind {
    Acknowledgement,
    ReceiptParent,
    ApprovalSideLink { role: String },
    RecoveryTarget,
}

#[derive(Clone, Debug)]
struct PendingReference {
    check_id: &'static str,
    ordinal: usize,
    path: String,
    target: String,
    kind: PendingReferenceKind,
}

#[derive(Debug)]
struct Validator {
    diagnostics: Vec<Diagnostic>,
    diagnostics_truncated: bool,
    diagnostics_omitted: usize,
    has_errors: bool,
    finding_summaries: HashMap<String, FindingSummary>,
    incomplete: bool,
    capture_partial: bool,
    session_state: String,
    session_generation: u64,
    session_transitions: usize,
    session_gap_pending: bool,
    initial_session_error_reported: bool,
    occurrence_hashes: HashMap<(String, String), String>,
    deliveries: HashMap<String, Delivery>,
    streams: HashMap<(String, String), StreamProgress>,
    capture_gap_epoch: u64,
    protocol_gap_epochs: HashMap<String, u64>,
    event_attempts: usize,
    event_acknowledgements: usize,
    event_gaps: usize,
    capture_gaps: usize,
    validated_capture_gaps: usize,
    receipts_by_id: HashMap<String, String>,
    receipts_by_hash: HashMap<String, ReceiptProjection>,
    receipt_hashes: HashSet<String>,
    receipt_parents: HashSet<String>,
    receipt_roots: HashSet<String>,
    pending_references: Vec<PendingReference>,
}

impl Validator {
    fn new(capture_partial: bool) -> Self {
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

    fn error(&mut self, check: &str, ordinal: usize, path: impl Into<String>, message: &str) {
        self.has_errors = true;
        self.finding_summaries
            .entry(check.to_owned())
            .or_default()
            .errors += 1;
        self.push_diagnostic(check, "error", ordinal, path.into(), message);
    }

    fn incomplete(&mut self, check: &str, ordinal: usize, path: impl Into<String>, message: &str) {
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

fn member<'a>(value: &'a Value, name: &str) -> Option<&'a Value> {
    value.as_object()?.get(name)
}

fn string<'a>(value: &'a Value, name: &str) -> Option<&'a str> {
    member(value, name)?.as_str()
}

fn uint(value: &Value, name: &str) -> Option<u64> {
    member(value, name)?.as_u64()
}

fn has_only(object: &Map<String, Value>, members: &[&str]) -> bool {
    object.keys().all(|key| members.contains(&key.as_str()))
}

fn require_members(
    value: &Value,
    required: &[&str],
    check: &str,
    ordinal: usize,
    path: &str,
    message: &str,
    validator: &mut Validator,
) -> bool {
    let Some(object) = value.as_object() else {
        validator.error(check, ordinal, path, message);
        return false;
    };
    let mut complete = true;
    for name in required {
        if !object.contains_key(*name) {
            validator.error(check, ordinal, format!("{path}/{name}"), message);
            complete = false;
        }
    }
    complete
}

fn timestamp_shape(value: &str) -> bool {
    let bytes = value.as_bytes();
    if !(value.len() == 20 || (22..=30).contains(&value.len()))
        || bytes.last() != Some(&b'Z')
        || bytes.get(4) != Some(&b'-')
        || bytes.get(7) != Some(&b'-')
        || bytes.get(10) != Some(&b'T')
        || bytes.get(13) != Some(&b':')
        || bytes.get(16) != Some(&b':')
        || (value.len() > 20 && bytes.get(19) != Some(&b'.'))
        || bytes.iter().enumerate().any(|(index, byte)| {
            !matches!(index, 4 | 7 | 10 | 13 | 16 | 19)
                && index + 1 != value.len()
                && !byte.is_ascii_digit()
        })
    {
        return false;
    }
    let number = |start: usize, end: usize| {
        value
            .get(start..end)
            .and_then(|part| part.parse::<u32>().ok())
    };
    let (Some(year), Some(month), Some(day), Some(hour), Some(minute), Some(second)) = (
        number(0, 4),
        number(5, 7),
        number(8, 10),
        number(11, 13),
        number(14, 16),
        number(17, 19),
    ) else {
        return false;
    };
    let leap = year.is_multiple_of(4) && (!year.is_multiple_of(100) || year.is_multiple_of(400));
    let days = match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 if leap => 29,
        2 => 28,
        _ => return false,
    };
    day >= 1 && day <= days && hour <= 23 && minute <= 59 && second <= 59
}

fn timestamp_order_key(value: &str) -> Option<(String, String)> {
    if !timestamp_shape(value) {
        return None;
    }
    let value = value.strip_suffix('Z')?;
    let (seconds, fraction) = value.split_once('.').unwrap_or((value, ""));
    debug_assert_eq!(seconds.len(), 19);
    debug_assert!(fraction.len() <= 9);
    let mut normalized_fraction = fraction.to_owned();
    normalized_fraction.extend(std::iter::repeat_n('0', 9 - fraction.len()));
    Some((seconds.to_owned(), normalized_fraction))
}

fn timestamp_not_after(left: &str, right: &str) -> bool {
    timestamp_order_key(left)
        .zip(timestamp_order_key(right))
        .is_some_and(|(left, right)| left <= right)
}

fn timestamp_epoch_nanos(value: &str) -> Option<i128> {
    if !timestamp_shape(value) {
        return None;
    }
    let number = |start: usize, end: usize| value.get(start..end)?.parse::<i128>().ok();
    let year = number(0, 4)?;
    let month = number(5, 7)?;
    let day = number(8, 10)?;
    let hour = number(11, 13)?;
    let minute = number(14, 16)?;
    let second = number(17, 19)?;
    let leap = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
    let month_offsets = [0_i128, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
    let days_before_year = year * 365 + (year + 3) / 4 - (year + 99) / 100 + (year + 399) / 400;
    let days_before_month =
        *month_offsets.get((month - 1) as usize)? + if leap && month > 2 { 1 } else { 0 };
    let days = days_before_year + days_before_month + day - 1;
    let fraction = value
        .strip_suffix('Z')?
        .split_once('.')
        .map(|(_, fraction)| fraction)
        .unwrap_or("");
    let mut nanos = fraction.to_owned();
    nanos.extend(std::iter::repeat_n('0', 9 - nanos.len()));
    let nanos = nanos.parse::<i128>().ok()?;
    Some((((days * 24 + hour) * 60 + minute) * 60 + second) * 1_000_000_000 + nanos)
}

fn timestamp_within_seconds(start: &str, end: &str, max_seconds: u64) -> bool {
    timestamp_epoch_nanos(start)
        .zip(timestamp_epoch_nanos(end))
        .is_some_and(|(start, end)| {
            end > start && end - start <= i128::from(max_seconds).saturating_mul(1_000_000_000)
        })
}

fn timestamp_elapsed_within(start: &str, end: &str, max_seconds: u64) -> bool {
    timestamp_epoch_nanos(start)
        .zip(timestamp_epoch_nanos(end))
        .is_some_and(|(start, end)| {
            end >= start && end - start <= i128::from(max_seconds).saturating_mul(1_000_000_000)
        })
}

fn validate_schema(bundle: &Value, validator: &mut Validator) -> Result<(), ReplayError> {
    let schema: Value = serde_json::from_str(BUNDLE_SCHEMA)
        .map_err(|error| ReplayError::SelfCheck(format!("bundle schema: {error}")))?;
    let compiled = jsonschema::draft202012::options()
        .should_validate_formats(true)
        .build(&schema)
        .map_err(|error| ReplayError::SelfCheck(format!("bundle schema: {error}")))?;
    for error in compiled.iter_errors(bundle) {
        let path = error.instance_path().to_string();
        validator.error(
            "ASP-REPLAY-SCHEMA-001",
            0,
            &path,
            "bundle does not match the closed replay schema",
        );
    }
    Ok(())
}

fn check_context(bundle: &Value, validator: &mut Validator) -> Result<(), ReplayError> {
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
    if string(surface, "protocol") != Some("agent-surface/0.1") {
        validator.error(
            "ASP-REPLAY-CONTEXT-001",
            0,
            "/context/surface/protocol",
            "historical Surface protocol is not agent-surface/0.1",
        );
    }

    for (value, required, base) in [
        (
            surface,
            &[
                "protocol",
                "app_id",
                "issuer",
                "surface_mode",
                "surface_version",
                "surface_hash",
                "surface_url",
                "auth",
                "agent_api",
                "scopes",
                "data_classes",
                "resources",
                "actions",
                "events",
                "audit",
                "revocation",
            ][..],
            "/context/surface",
        ),
        (
            grant,
            &[
                "grant_id",
                "grant_hash",
                "subject",
                "delegate",
                "resource_server",
                "scopes",
                "constraints",
                "data_exposure",
                "credential_profile",
                "credential_binding",
                "audit",
            ][..],
            "/context/grant",
        ),
    ] {
        for required_member in required {
            if member(value, required_member).is_none() {
                validator.error(
                    "ASP-REPLAY-CONTEXT-001",
                    0,
                    format!("{base}/{required_member}"),
                    "historical context omits a required complete binding field",
                );
            }
        }
    }
    for (value, strings, arrays, objects, base) in [
        (
            surface,
            &[
                "protocol",
                "app_id",
                "issuer",
                "surface_mode",
                "surface_version",
                "surface_hash",
                "surface_url",
            ][..],
            &["scopes", "data_classes", "resources", "actions", "events"][..],
            &["auth", "agent_api", "audit", "revocation"][..],
            "/context/surface",
        ),
        (
            grant,
            &["grant_id", "grant_hash", "credential_profile"][..],
            &["scopes", "data_exposure"][..],
            &[
                "subject",
                "delegate",
                "resource_server",
                "constraints",
                "credential_binding",
                "audit",
            ][..],
            "/context/grant",
        ),
    ] {
        for name in strings {
            if string(value, name).is_none() {
                validator.error(
                    "ASP-REPLAY-CONTEXT-001",
                    0,
                    format!("{base}/{name}"),
                    "historical context binding has the wrong JSON type",
                );
            }
        }
        for name in arrays {
            if member(value, name).and_then(Value::as_array).is_none() {
                validator.error(
                    "ASP-REPLAY-CONTEXT-001",
                    0,
                    format!("{base}/{name}"),
                    "historical context collection has the wrong JSON type",
                );
            }
        }
        for name in objects {
            if member(value, name).and_then(Value::as_object).is_none() {
                validator.error(
                    "ASP-REPLAY-CONTEXT-001",
                    0,
                    format!("{base}/{name}"),
                    "historical context object has the wrong JSON type",
                );
            }
        }
    }
    if member(grant, "actions")
        .and_then(Value::as_array)
        .is_some_and(|actions| !actions.is_empty())
        && member(grant, "locations")
            .and_then(Value::as_array)
            .is_none_or(Vec::is_empty)
    {
        validator.error(
            "ASP-REPLAY-CONTEXT-001",
            0,
            "/context/grant/locations",
            "a Grant carrying action authority requires non-empty locations",
        );
    }

    if let Some(expected) = string(surface, "surface_hash") {
        let actual = object_hash(MANIFEST_DOMAIN, surface, &["surface_hash"])?;
        if expected != actual {
            validator.error(
                "ASP-REPLAY-CONTEXT-001",
                0,
                "/context/surface/surface_hash",
                "historical Surface hash does not match its complete object",
            );
        }
    } else {
        validator.error(
            "ASP-REPLAY-CONTEXT-001",
            0,
            "/context/surface/surface_hash",
            "historical Surface must contain its recomputable hash",
        );
    }
    if let Some(expected) = string(grant, "grant_hash") {
        let mut hash_view = grant.clone();
        if let Some(object) = hash_view.as_object_mut() {
            object.remove("grant_hash");
            if object.get("type").and_then(Value::as_str)
                == Some(
                    "https://github.com/0al-spec/agent-surface/authorization-details/agent-grant",
                )
            {
                object.remove("type");
            }
        }
        let actual = object_hash(GRANT_DOMAIN, &hash_view, &[])?;
        if expected != actual {
            validator.error(
                "ASP-REPLAY-CONTEXT-001",
                0,
                "/context/grant/grant_hash",
                "historical Grant hash does not match its complete object",
            );
        }
    } else {
        validator.error(
            "ASP-REPLAY-CONTEXT-001",
            0,
            "/context/grant/grant_hash",
            "historical Grant must contain its recomputable hash",
        );
    }

    let bindings = [
        (
            string(scope, "issuer"),
            string(surface, "issuer"),
            "/scope/issuer",
        ),
        (
            string(scope, "app_id"),
            string(surface, "app_id"),
            "/scope/app_id",
        ),
        (
            string(scope, "surface_version"),
            string(surface, "surface_version"),
            "/scope/surface_version",
        ),
        (
            string(scope, "surface_hash"),
            string(surface, "surface_hash"),
            "/scope/surface_hash",
        ),
        (
            string(scope, "grant_id"),
            string(grant, "grant_id"),
            "/scope/grant_id",
        ),
        (
            string(scope, "grant_hash"),
            string(grant, "grant_hash"),
            "/scope/grant_hash",
        ),
        (
            string(scope, "subject_user"),
            member(grant, "subject").and_then(|value| string(value, "user")),
            "/scope/subject_user",
        ),
        (
            string(scope, "runtime_id"),
            member(grant, "delegate").and_then(|value| string(value, "runtime")),
            "/scope/runtime_id",
        ),
        (
            string(scope, "agent_id"),
            member(grant, "delegate").and_then(|value| string(value, "agent")),
            "/scope/agent_id",
        ),
        (
            string(scope, "passport_hash"),
            member(grant, "delegate").and_then(|value| string(value, "passport_hash")),
            "/scope/passport_hash",
        ),
        (
            string(scope, "issuer"),
            member(grant, "resource_server").and_then(|value| string(value, "issuer")),
            "/context/grant/resource_server/issuer",
        ),
        (
            string(scope, "app_id"),
            member(grant, "resource_server").and_then(|value| string(value, "app_id")),
            "/context/grant/resource_server/app_id",
        ),
        (
            string(scope, "surface_version"),
            member(grant, "resource_server").and_then(|value| string(value, "surface_version")),
            "/context/grant/resource_server/surface_version",
        ),
        (
            string(scope, "surface_hash"),
            member(grant, "resource_server").and_then(|value| string(value, "surface_hash")),
            "/context/grant/resource_server/surface_hash",
        ),
    ];
    for (left, right, path) in bindings {
        if left.is_some() && left != right {
            validator.error(
                "ASP-REPLAY-CONTEXT-001",
                0,
                path,
                "historical context conflicts with the replay scope",
            );
        }
    }
    Ok(())
}

fn transition(body: &Value, ordinal: usize, validator: &mut Validator) {
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

fn event_declaration<'a>(surface: &'a Value, event_type: &str) -> Option<&'a Value> {
    member(surface, "events")?
        .as_array()?
        .iter()
        .find(|event| string(event, "id") == Some(event_type))
}

fn check_event(
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
    if required.iter().any(|name| member(event, name).is_none()) {
        validator.error(
            "ASP-REPLAY-EVENT-001",
            ordinal,
            &path,
            "event delivery is missing a required ASP CloudEvents member",
        );
        return Ok(());
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

    let Some(source) = string(event, "source") else {
        return Ok(());
    };
    let Some(event_id) = string(event, "id") else {
        return Ok(());
    };
    let Some(event_hash) = string(event, "aspeventhash") else {
        return Ok(());
    };
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

    let Some(delivery_id) = string(event, "aspdeliveryid") else {
        return Ok(());
    };
    let Some(subscription_id) = string(event, "aspsubid") else {
        return Ok(());
    };
    let Some(stream) = string(event, "aspstream") else {
        return Ok(());
    };
    let Some(sequence) = uint(event, "aspsequence") else {
        return Ok(());
    };
    let Some(cursor) = string(event, "aspcursor") else {
        return Ok(());
    };
    let Some(attempt) = uint(event, "aspattempt") else {
        return Ok(());
    };
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

fn check_ack(body: &Value, ordinal: usize, validator: &mut Validator) {
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
    let Some(delivery_id) = string(payload, "delivery_id") else {
        return;
    };
    let outcome = string(payload, "outcome").unwrap_or_default();
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

fn check_gap(body: &Value, ordinal: usize, validator: &mut Validator) {
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

fn action_available(surface: &Value, grant: &Value, action_id: &str) -> bool {
    let declared = member(surface, "actions")
        .and_then(Value::as_array)
        .is_some_and(|actions| {
            actions
                .iter()
                .any(|action| string(action, "id") == Some(action_id))
        });
    let granted = member(grant, "actions")
        .and_then(Value::as_array)
        .is_some_and(|actions| {
            actions
                .iter()
                .any(|action| action.as_str() == Some(action_id))
        });
    declared && granted
}

fn action_declaration<'a>(surface: &'a Value, action_id: &str) -> Option<&'a Value> {
    member(surface, "actions")?
        .as_array()?
        .iter()
        .find(|action| string(action, "id") == Some(action_id))
}

fn approval_requirement(grant: &Value, action_id: &str) -> Option<ApprovalRequirement> {
    let approval_receipt =
        member(grant, "audit").and_then(|audit| member(audit, "approval_receipt"))?;
    if string(approval_receipt, "profile")
        != Some("https://github.com/0al-spec/agent-surface/profiles/approval-receipt/v1")
    {
        return None;
    }
    let requirement = member(approval_receipt, "requirements")?
        .as_array()?
        .iter()
        .find(|requirement| string(requirement, "action_id") == Some(action_id))?;
    Some(ApprovalRequirement {
        accepted_roles: member(requirement, "accepted_roles")?
            .as_array()?
            .iter()
            .map(|role| role.as_str().map(str::to_owned))
            .collect::<Option<HashSet<_>>>()?,
        max_age_seconds: uint(requirement, "max_age_seconds")?,
    })
}

fn approval_links(receipt: &Value) -> Option<BTreeMap<String, String>> {
    let links = member(receipt, "approval_receipt_hashes")?.as_object()?;
    Some(
        links
            .iter()
            .filter_map(|(role, hash)| Some((role.clone(), hash.as_str()?.to_owned())))
            .collect(),
    )
}

fn receipt_projection(receipt: &Value, ordinal: usize) -> Option<ReceiptProjection> {
    let execution = member(receipt, "execution").cloned();
    let actual_effect_ids = member(receipt, "actual_effects")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .filter_map(|effect| string(effect, "effect_id"))
        .map(str::to_owned)
        .collect();
    Some(ReceiptProjection {
        ordinal,
        receipt_type: string(receipt, "receipt_type")?.to_owned(),
        grant_hash: string(receipt, "grant_hash")?.to_owned(),
        surface_hash: string(receipt, "surface_hash")?.to_owned(),
        surface_version: string(receipt, "surface_version")?.to_owned(),
        session_id: string(receipt, "session_id")?.to_owned(),
        session_generation: uint(receipt, "session_generation")?,
        trace_id: string(receipt, "trace_id")?.to_owned(),
        linked_trace_id: string(receipt, "linked_trace_id").map(str::to_owned),
        action_id: string(receipt, "action_id")?.to_owned(),
        idempotency_key: string(receipt, "idempotency_key")?.to_owned(),
        input_hash: string(receipt, "input_hash")?.to_owned(),
        execution_hash: string(receipt, "execution_hash").map(str::to_owned),
        timestamp: string(receipt, "timestamp")?.to_owned(),
        target_receipt_hash: execution
            .as_ref()
            .and_then(|value| string(value, "target_receipt_hash"))
            .map(str::to_owned),
        execution,
        result: string(receipt, "result")?.to_owned(),
        effect_outcome: string(receipt, "effect_outcome").map(str::to_owned),
        actual_effect_ids,
        approval_role: member(receipt, "approval")
            .and_then(|approval| string(approval, "role"))
            .map(str::to_owned),
        approval_receipt_hashes: approval_links(receipt).unwrap_or_default(),
    })
}

fn same_invocation_projection(left: &ReceiptProjection, right: &ReceiptProjection) -> bool {
    left.grant_hash == right.grant_hash
        && left.surface_hash == right.surface_hash
        && left.surface_version == right.surface_version
        && left.session_id == right.session_id
        && left.session_generation == right.session_generation
        && left.action_id == right.action_id
        && left.idempotency_key == right.idempotency_key
        && left.input_hash == right.input_hash
        && left.execution == right.execution
        && left.execution_hash == right.execution_hash
}

fn validate_parent_projection(
    child: &ReceiptProjection,
    parent: &ReceiptProjection,
    validator: &mut Validator,
) {
    let path = format!("/records/{}/body/parent_receipt_hash", child.ordinal);
    if child.receipt_type == "approval" || parent.receipt_type == "approval" {
        validator.error(
            "ASP-REPLAY-RECEIPT-CHAIN-001",
            child.ordinal,
            &path,
            "approval receipt cannot participate in the parent chain",
        );
        return;
    }
    if !same_invocation_projection(child, parent) {
        validator.error(
            "ASP-REPLAY-RECEIPT-CHAIN-001",
            child.ordinal,
            &path,
            "receipt parent does not preserve the exact invocation projection",
        );
    }
    if child.trace_id != parent.trace_id
        && child.linked_trace_id.as_deref() != Some(parent.trace_id.as_str())
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-CHAIN-001",
            child.ordinal,
            &path,
            "receipt parent trace is neither preserved nor explicitly linked",
        );
    }
    if parent.receipt_type == "runtime" && child.receipt_type == "app" {
        let parent_runtime = parent.approval_receipt_hashes.get("runtime");
        let child_runtime = child.approval_receipt_hashes.get("runtime");
        if parent_runtime != child_runtime || (parent_runtime.is_none() && child_runtime.is_some())
        {
            validator.error(
                "ASP-REPLAY-RECEIPT-LINK-001",
                child.ordinal,
                format!("/records/{}/body/approval_receipt_hashes", child.ordinal),
                "application receipt did not preserve the runtime approval side link",
            );
        }
    }
}

fn validate_approval_decision(
    receipt: &Value,
    ordinal: usize,
    scope: &Value,
    grant: &Value,
    validator: &mut Validator,
) {
    let path = format!("/records/{ordinal}/body");
    let Some(approval) = member(receipt, "approval") else {
        return;
    };
    let role = string(approval, "role").unwrap_or_default();
    let decided_by = string(approval, "decided_by").unwrap_or_default();
    let result = string(receipt, "result").unwrap_or_default();
    let policy = member(receipt, "policy_decision");
    let outcome = policy
        .and_then(|value| string(value, "outcome"))
        .unwrap_or_default();
    let reason = policy
        .and_then(|value| string(value, "reason_code"))
        .unwrap_or_default();
    let expected = match (role, result, decided_by) {
        ("runtime", "approved", "user") => Some(("allow", "approval_satisfied")),
        ("runtime", "denied", "user") => Some(("deny", "approval_denied")),
        ("runtime", "denied", "policy") => Some(("deny", "local_policy_denied")),
        ("application", "approved", "user" | "policy") => Some(("allow", "approval_satisfied")),
        ("application", "denied", "user") => Some(("deny", "approval_denied")),
        ("application", "denied", "policy") => Some(("deny", "app_policy_denied")),
        _ => None,
    };
    if expected != Some((outcome, reason)) {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            ordinal,
            format!("{path}/approval"),
            "approval receipt role, result, decision source, and policy outcome are inconsistent",
        );
    }
    let enforcer = policy.and_then(|value| member(value, "enforcer"));
    let expected_enforcer = match role {
        "runtime" => Some(("runtime", string(scope, "runtime_id"))),
        "application" => Some(("application", string(scope, "app_id"))),
        _ => None,
    };
    if expected_enforcer.is_none_or(|(kind, id)| {
        enforcer.and_then(|value| string(value, "type")) != Some(kind)
            || enforcer.and_then(|value| string(value, "id")) != id
    }) {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            ordinal,
            format!("{path}/policy_decision/enforcer"),
            "approval receipt enforcer does not match its producer role",
        );
    }
    if policy.and_then(|value| string(value, "evaluated_at")) != string(receipt, "timestamp") {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            ordinal,
            format!("{path}/policy_decision/evaluated_at"),
            "approval policy decision time does not equal receipt timestamp",
        );
    }
    let requirement =
        string(receipt, "action_id").and_then(|action_id| approval_requirement(grant, action_id));
    if requirement
        .as_ref()
        .is_none_or(|requirement| !requirement.accepted_roles.contains(role))
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            ordinal,
            format!("{path}/approval/role"),
            "approval receipt role is not accepted by the historical Grant requirement",
        );
    }
    let valid_until = string(approval, "valid_until");
    if result == "denied" && valid_until.is_some() {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            ordinal,
            format!("{path}/approval/valid_until"),
            "denied approval receipt must omit valid_until",
        );
    }
    if result == "approved"
        && let (Some(timestamp), Some(valid_until), Some(requirement)) = (
            string(receipt, "timestamp"),
            valid_until,
            requirement.as_ref(),
        )
        && !timestamp_within_seconds(timestamp, valid_until, requirement.max_age_seconds)
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            ordinal,
            format!("{path}/approval/valid_until"),
            "approved receipt validity exceeds the historical Grant maximum age",
        );
    }
    if result == "approved"
        && let (Some(valid_until), Some(grant_expiry)) = (
            valid_until,
            member(grant, "constraints").and_then(|value| string(value, "expires_at")),
        )
        && !timestamp_not_after(valid_until, grant_expiry)
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            ordinal,
            format!("{path}/approval/valid_until"),
            "approved receipt validity exceeds the historical Grant expiry",
        );
    }
}

fn validate_approval_map_shape(
    source: &ReceiptProjection,
    surface: &Value,
    grant: &Value,
    validator: &mut Validator,
) {
    let Some(action) = action_declaration(surface, &source.action_id) else {
        return;
    };
    let mode = string(action, "approval").unwrap_or("none");
    let accepted_roles = approval_requirement(grant, &source.action_id)
        .map(|requirement| requirement.accepted_roles);
    let actual: HashSet<&str> = source
        .approval_receipt_hashes
        .keys()
        .map(String::as_str)
        .collect();
    let valid = match (source.receipt_type.as_str(), mode, accepted_roles.as_ref()) {
        ("approval", _, _) => actual.is_empty(),
        (_, "none", _) => actual.is_empty(),
        (_, _, None) => actual.is_empty(),
        ("runtime", "app", Some(_)) => actual.is_empty(),
        ("runtime", "runtime" | "runtime_and_app", Some(roles)) => {
            roles.contains("runtime") && actual == HashSet::from(["runtime"])
        }
        ("runtime", "user_or_app", Some(roles)) => {
            (roles.contains("runtime") && actual == HashSet::from(["runtime"]))
                || (roles.contains("application") && actual.is_empty())
        }
        ("app", "runtime", Some(roles)) => {
            roles.contains("runtime") && actual == HashSet::from(["runtime"])
        }
        ("app", "app", Some(roles)) => {
            roles.contains("application") && actual == HashSet::from(["application"])
        }
        ("app", "runtime_and_app", Some(roles)) => {
            roles.contains("runtime")
                && roles.contains("application")
                && actual == HashSet::from(["application", "runtime"])
        }
        ("app", "user_or_app", Some(roles)) => {
            actual.len() == 1 && actual.iter().all(|role| roles.contains(*role))
        }
        _ => false,
    };
    if !valid {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            source.ordinal,
            format!("/records/{}/body/approval_receipt_hashes", source.ordinal),
            "approval side-link role map does not satisfy the manifest mode and Grant requirement",
        );
    }
}

fn validate_approval_target(
    source: &ReceiptProjection,
    role: &str,
    target: &ReceiptProjection,
    validator: &mut Validator,
) {
    let path = format!(
        "/records/{}/body/approval_receipt_hashes/{role}",
        source.ordinal
    );
    if target.receipt_type != "approval"
        || target.result != "approved"
        || target.approval_role.as_deref() != Some(role)
        || !same_invocation_projection(source, target)
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            source.ordinal,
            path,
            "approval side link does not resolve to an approved role-matched invocation projection",
        );
    }
}

fn relationship_projection(
    entries: Option<&Value>,
    action_id: &str,
    mode: Option<&str>,
) -> Option<(Vec<String>, u64)> {
    entries?.as_array()?.iter().find_map(|entry| {
        if string(entry, "action_id") != Some(action_id)
            || mode.is_some_and(|expected| string(entry, "mode") != Some(expected))
        {
            return None;
        }
        let mut effects: Vec<String> = member(entry, "effect_ids")?
            .as_array()?
            .iter()
            .map(|value| value.as_str().map(str::to_owned))
            .collect::<Option<Vec<_>>>()?;
        effects.sort();
        effects.dedup();
        Some((effects, uint(entry, "recovery_window_seconds")?))
    })
}

fn validate_recovery_target(
    source: &ReceiptProjection,
    target: &ReceiptProjection,
    surface: &Value,
    validator: &mut Validator,
) {
    let path = format!(
        "/records/{}/body/execution/target_receipt_hash",
        source.ordinal
    );
    let mode = source
        .execution
        .as_ref()
        .and_then(|execution| string(execution, "mode"));
    if target.receipt_type != "app" || !matches!(mode, Some("compensate" | "revert")) {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            source.ordinal,
            &path,
            "recovery target must be an earlier application receipt for compensate or revert",
        );
        return;
    }
    if !matches!(
        target.effect_outcome.as_deref(),
        Some("applied" | "partially_applied")
    ) {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            source.ordinal,
            &path,
            "recovery target does not carry a recoverable effect outcome",
        );
    }
    let Some(source_action) = action_declaration(surface, &source.action_id) else {
        return;
    };
    let Some(target_action) = action_declaration(surface, &target.action_id) else {
        return;
    };
    let source_execution = member(source_action, "execution");
    let target_execution = member(target_action, "execution");
    let source_operation = source_execution.and_then(|value| string(value, "operation_id"));
    let target_operation = target_execution.and_then(|value| string(value, "operation_id"));
    let outbound = relationship_projection(
        target_execution.and_then(|value| member(value, "recovery_actions")),
        &source.action_id,
        mode,
    );
    let reciprocal = relationship_projection(
        source_execution.and_then(|value| member(value, "target_actions")),
        &target.action_id,
        None,
    );
    if string(target_execution.unwrap_or(&Value::Null), "mode") != Some("commit")
        || target
            .execution
            .as_ref()
            .and_then(|execution| string(execution, "mode"))
            != Some("commit")
        || string(source_execution.unwrap_or(&Value::Null), "mode") != mode
        || source_operation.is_none()
        || source_operation != target_operation
        || outbound.is_none()
        || outbound != reciprocal
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            source.ordinal,
            &path,
            "recovery target lacks an exact reciprocal manifest relationship",
        );
        return;
    }
    if let Some((effect_ids, _)) = reciprocal
        && effect_ids
            .iter()
            .any(|effect_id| !target.actual_effect_ids.contains(effect_id))
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            source.ordinal,
            path,
            "recovery relationship names an effect absent from the target receipt",
        );
    } else if let Some((_, recovery_window_seconds)) = outbound
        && !timestamp_elapsed_within(
            &target.timestamp,
            &source.timestamp,
            recovery_window_seconds,
        )
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            source.ordinal,
            path,
            "recovery target timestamp falls outside the declared recovery window",
        );
    }
}

fn check_receipt(
    receipt: &Value,
    ordinal: usize,
    scope: &Value,
    surface: &Value,
    grant: &Value,
    validator: &mut Validator,
) -> Result<(), ReplayError> {
    let path = format!("/records/{ordinal}/body");
    let common = [
        "receipt_id",
        "receipt_type",
        "receipt_hash",
        "grant_id",
        "grant_hash",
        "session_id",
        "session_generation",
        "trace_id",
        "span_id",
        "action_id",
        "app_id",
        "surface_version",
        "surface_hash",
        "runtime",
        "actor_agent",
        "subject",
        "idempotency_key",
        "input_hash",
        "policy_decision_hash",
        "policy_decision",
        "timestamp",
        "result",
    ];
    if !require_members(
        receipt,
        &common,
        "ASP-REPLAY-RECEIPT-HASH-001",
        ordinal,
        &path,
        "receipt is missing a required identity, trace, decision, input, or result member",
        validator,
    ) {
        return Ok(());
    }
    let typed_strings = [
        "receipt_id",
        "receipt_type",
        "receipt_hash",
        "grant_id",
        "grant_hash",
        "session_id",
        "trace_id",
        "span_id",
        "action_id",
        "app_id",
        "surface_version",
        "surface_hash",
        "idempotency_key",
        "input_hash",
        "policy_decision_hash",
        "timestamp",
        "result",
    ];
    let typed = typed_strings
        .iter()
        .all(|name| string(receipt, name).is_some())
        && uint(receipt, "session_generation").is_some()
        && ["runtime", "actor_agent", "subject", "policy_decision"]
            .iter()
            .all(|name| member(receipt, name).and_then(Value::as_object).is_some());
    if !typed {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            &path,
            "receipt required members have invalid JSON types",
        );
        return Ok(());
    }
    let Some(receipt_id) = string(receipt, "receipt_id") else {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            &path,
            "receipt identity members have invalid types",
        );
        return Ok(());
    };
    let Some(receipt_type) = string(receipt, "receipt_type") else {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            &path,
            "receipt identity members have invalid types",
        );
        return Ok(());
    };
    let Some(receipt_hash) = string(receipt, "receipt_hash") else {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            &path,
            "receipt identity members have invalid types",
        );
        return Ok(());
    };
    if !valid_digest(receipt_hash) {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            format!("{path}/receipt_hash"),
            "receipt hash is not a canonical SHA-256 digest",
        );
        return Ok(());
    }
    if !["runtime", "app", "approval"].contains(&receipt_type) {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            &path,
            "receipt type is not supported by the replay profile",
        );
    }
    if string(receipt, "timestamp").is_none_or(|time| !timestamp_shape(time)) {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            format!("{path}/timestamp"),
            "receipt timestamp must be a real RFC 3339 UTC instant without leap seconds",
        );
    }
    let action_requires_execution = string(receipt, "action_id")
        .and_then(|action_id| {
            member(surface, "actions")?
                .as_array()?
                .iter()
                .find(|action| string(action, "id") == Some(action_id))
        })
        .and_then(|action| member(action, "execution"))
        .and_then(|execution| string(execution, "mode"))
        .is_some_and(|mode| ["reserve", "commit", "compensate", "revert"].contains(&mode));
    let execution_pair = (
        member(receipt, "execution").is_some(),
        member(receipt, "execution_hash").is_some(),
    );
    if execution_pair.0 != execution_pair.1 || (action_requires_execution && !execution_pair.0) {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            &path,
            "receipt execution and execution_hash must appear together when applicable",
        );
    }
    let effects_pair = (
        member(receipt, "actual_effects").is_some(),
        member(receipt, "actual_effects_hash").is_some(),
    );
    if effects_pair.0 != effects_pair.1 {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            &path,
            "receipt actual_effects and actual_effects_hash must appear together",
        );
    }
    if receipt_type == "approval" {
        let mut required = common.to_vec();
        required.extend(["execution", "execution_hash", "approval"]);
        if !require_members(
            receipt,
            &required,
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            &path,
            "approval receipt is missing a required closed-shape member",
            validator,
        ) {
            return Ok(());
        }
        let allowed = [
            "receipt_id",
            "receipt_type",
            "receipt_hash",
            "grant_id",
            "grant_hash",
            "session_id",
            "session_generation",
            "trace_id",
            "span_id",
            "action_id",
            "app_id",
            "surface_version",
            "surface_hash",
            "runtime",
            "actor_agent",
            "subject",
            "idempotency_key",
            "input_hash",
            "execution",
            "execution_hash",
            "policy_decision_hash",
            "policy_decision",
            "approval",
            "timestamp",
            "result",
            "receipt_signatures",
        ];
        if !receipt
            .as_object()
            .is_some_and(|object| has_only(object, &allowed))
        {
            validator.error(
                "ASP-REPLAY-RECEIPT-HASH-001",
                ordinal,
                &path,
                "approval receipt contains a member outside its closed wire shape",
            );
        }
        let approval_required: &[&str] = if string(receipt, "result") == Some("approved") {
            &["approval_id", "role", "decided_by", "valid_until"]
        } else {
            &["approval_id", "role", "decided_by"]
        };
        let Some(approval) = member(receipt, "approval") else {
            return Ok(());
        };
        if !require_members(
            approval,
            approval_required,
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            &format!("{path}/approval"),
            "approval projection is missing a required closed-shape member",
            validator,
        ) {
            return Ok(());
        }
        let approval_allowed = ["approval_id", "role", "decided_by", "valid_until"];
        if !approval
            .as_object()
            .is_some_and(|object| has_only(object, &approval_allowed))
        {
            validator.error(
                "ASP-REPLAY-RECEIPT-HASH-001",
                ordinal,
                format!("{path}/approval"),
                "approval projection contains a member outside its closed wire shape",
            );
        }
        if let Some(valid_until) = string(approval, "valid_until")
            && (string(receipt, "timestamp").is_none_or(|timestamp| {
                !timestamp_shape(valid_until)
                    || !timestamp_not_after(timestamp, valid_until)
                    || timestamp == valid_until
            }))
        {
            validator.error(
                "ASP-REPLAY-RECEIPT-HASH-001",
                ordinal,
                format!("{path}/approval/valid_until"),
                "approved receipt validity must be a real UTC instant not before its timestamp",
            );
        }
        validate_approval_decision(receipt, ordinal, scope, grant, validator);
    }
    let actual = object_hash(
        RECEIPT_DOMAIN,
        receipt,
        &["receipt_hash", "receipt_signatures"],
    )?;
    if receipt_hash != actual {
        validator.error(
            "ASP-REPLAY-RECEIPT-HASH-001",
            ordinal,
            format!("{path}/receipt_hash"),
            "receipt hash does not match the exact receipt",
        );
    }
    if let Some(policy) = member(receipt, "policy_decision")
        && let Some(expected) = string(receipt, "policy_decision_hash")
    {
        let actual = object_hash(POLICY_DOMAIN, policy, &["policy_decision_hash"])?;
        if expected != actual || string(policy, "policy_decision_hash") != Some(expected) {
            validator.error(
                "ASP-REPLAY-RECEIPT-HASH-001",
                ordinal,
                format!("{path}/policy_decision_hash"),
                "receipt Policy Decision hash binding is invalid",
            );
        }
    }
    if let Some(execution) = member(receipt, "execution")
        && let Some(expected) = string(receipt, "execution_hash")
    {
        let actual = object_hash(EXECUTION_DOMAIN, execution, &["execution_token"])?;
        if expected != actual {
            validator.error(
                "ASP-REPLAY-RECEIPT-HASH-001",
                ordinal,
                format!("{path}/execution_hash"),
                "receipt execution hash binding is invalid",
            );
        }
    }
    if let Some(effects) = member(receipt, "actual_effects")
        && let Some(expected) = string(receipt, "actual_effects_hash")
    {
        let actual = object_hash(ACTUAL_EFFECTS_DOMAIN, effects, &[])?;
        if expected != actual {
            validator.error(
                "ASP-REPLAY-RECEIPT-HASH-001",
                ordinal,
                format!("{path}/actual_effects_hash"),
                "receipt actual-effects hash binding is invalid",
            );
        }
    }
    for (member_name, scope_name) in [
        ("grant_id", "grant_id"),
        ("grant_hash", "grant_hash"),
        ("session_id", "session_id"),
        ("surface_version", "surface_version"),
        ("surface_hash", "surface_hash"),
    ] {
        if let Some(value) = string(receipt, member_name)
            && Some(value) != string(scope, scope_name)
        {
            validator.error(
                "ASP-REPLAY-RECEIPT-CHAIN-001",
                ordinal,
                format!("{path}/{member_name}"),
                "receipt conflicts with the replay scope",
            );
        }
    }
    if uint(receipt, "session_generation") != uint(scope, "session_generation") {
        validator.error(
            "ASP-REPLAY-RECEIPT-CHAIN-001",
            ordinal,
            format!("{path}/session_generation"),
            "receipt generation conflicts with the replay scope",
        );
    }
    let nested_bindings = [
        (string(receipt, "app_id"), string(scope, "app_id"), "app_id"),
        (
            member(receipt, "subject").and_then(|value| string(value, "user")),
            string(scope, "subject_user"),
            "subject/user",
        ),
        (
            member(receipt, "runtime").and_then(|value| string(value, "runtime_id")),
            string(scope, "runtime_id"),
            "runtime/runtime_id",
        ),
        (
            member(receipt, "actor_agent").and_then(|value| string(value, "agent_id")),
            string(scope, "agent_id"),
            "actor_agent/agent_id",
        ),
        (
            member(receipt, "actor_agent").and_then(|value| string(value, "passport_hash")),
            string(scope, "passport_hash"),
            "actor_agent/passport_hash",
        ),
    ];
    for (actual, expected, member_path) in nested_bindings {
        if actual != expected {
            validator.error(
                "ASP-REPLAY-RECEIPT-CHAIN-001",
                ordinal,
                format!("{path}/{member_path}"),
                "receipt participant binding conflicts with the replay scope",
            );
        }
    }
    if let Some(action_id) = string(receipt, "action_id")
        && !action_available(surface, grant, action_id)
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-CHAIN-001",
            ordinal,
            format!("{path}/action_id"),
            "receipt action is absent from the historical Surface or Grant",
        );
    }
    if let Some(previous) = validator.receipts_by_id.get(receipt_id) {
        if previous != receipt_hash {
            validator.error(
                "ASP-REPLAY-RECEIPT-CHAIN-001",
                ordinal,
                format!("{path}/receipt_id"),
                "receipt id was reused for another receipt hash",
            );
        }
    } else {
        validator
            .receipts_by_id
            .insert(receipt_id.to_owned(), receipt_hash.to_owned());
    }
    if let Some(links) = member(receipt, "approval_receipt_hashes")
        && !links.as_object().is_some_and(|object| {
            object.keys().all(|role| {
                matches!(role.as_str(), "runtime" | "application")
                    && object
                        .get(role)
                        .and_then(Value::as_str)
                        .is_some_and(valid_digest)
            })
        })
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            ordinal,
            format!("{path}/approval_receipt_hashes"),
            "approval side-link map must be closed and contain canonical role hashes",
        );
    }
    let execution_mode = member(receipt, "execution").and_then(|value| string(value, "mode"));
    let nested_target =
        member(receipt, "execution").and_then(|value| string(value, "target_receipt_hash"));
    if matches!(execution_mode, Some("compensate" | "revert")) != nested_target.is_some() {
        validator.error(
            "ASP-REPLAY-RECEIPT-LINK-001",
            ordinal,
            format!("{path}/execution/target_receipt_hash"),
            "recovery execution and target receipt hash must appear together",
        );
    }
    let Some(projection) = receipt_projection(receipt, ordinal) else {
        validator.error(
            "ASP-REPLAY-RECEIPT-CHAIN-001",
            ordinal,
            &path,
            "receipt linkage projection contains invalid member types",
        );
        validator.receipt_hashes.insert(receipt_hash.to_owned());
        return Ok(());
    };
    validate_approval_map_shape(&projection, surface, grant, validator);
    if let Some(parent) = string(receipt, "parent_receipt_hash") {
        if !valid_digest(parent) {
            validator.error(
                "ASP-REPLAY-RECEIPT-CHAIN-001",
                ordinal,
                format!("{path}/parent_receipt_hash"),
                "receipt parent reference is not a canonical SHA-256 digest",
            );
        } else {
            validator.receipt_parents.insert(parent.to_owned());
            if let Some(parent_projection) = validator.receipts_by_hash.get(parent).cloned() {
                validate_parent_projection(&projection, &parent_projection, validator);
            } else {
                validator.pending_references.push(PendingReference {
                    check_id: "ASP-REPLAY-RECEIPT-CHAIN-001",
                    ordinal,
                    path: format!("{path}/parent_receipt_hash"),
                    target: parent.to_owned(),
                    kind: PendingReferenceKind::ReceiptParent,
                });
            }
        }
    } else {
        validator.receipt_roots.insert(receipt_hash.to_owned());
    }
    if receipt_type == "approval" && member(receipt, "parent_receipt_hash").is_some() {
        validator.error(
            "ASP-REPLAY-RECEIPT-CHAIN-001",
            ordinal,
            format!("{path}/parent_receipt_hash"),
            "approval receipt must be a root",
        );
    }
    for (role, hash) in &projection.approval_receipt_hashes {
        if let Some(target) = validator.receipts_by_hash.get(hash).cloned() {
            validate_approval_target(&projection, role, &target, validator);
        } else {
            validator.pending_references.push(PendingReference {
                check_id: "ASP-REPLAY-RECEIPT-LINK-001",
                ordinal,
                path: format!("{path}/approval_receipt_hashes/{role}"),
                target: hash.clone(),
                kind: PendingReferenceKind::ApprovalSideLink { role: role.clone() },
            });
        }
    }
    if let Some(target_hash) = &projection.target_receipt_hash {
        if !valid_digest(target_hash) {
            validator.error(
                "ASP-REPLAY-RECEIPT-LINK-001",
                ordinal,
                format!("{path}/execution/target_receipt_hash"),
                "recovery target is not a canonical SHA-256 digest",
            );
        } else if let Some(target) = validator.receipts_by_hash.get(target_hash).cloned() {
            validate_recovery_target(&projection, &target, surface, validator);
        } else {
            validator.pending_references.push(PendingReference {
                check_id: "ASP-REPLAY-RECEIPT-LINK-001",
                ordinal,
                path: format!("{path}/execution/target_receipt_hash"),
                target: target_hash.clone(),
                kind: PendingReferenceKind::RecoveryTarget,
            });
        }
    }
    validator.receipt_hashes.insert(receipt_hash.to_owned());
    if let Some(previous) = validator
        .receipts_by_hash
        .insert(receipt_hash.to_owned(), projection)
        && previous.ordinal != ordinal
    {
        validator.error(
            "ASP-REPLAY-RECEIPT-CHAIN-001",
            ordinal,
            format!("{path}/receipt_hash"),
            "receipt hash was repeated by another replay record",
        );
    }
    Ok(())
}

fn reconcile_pending_references(validator: &mut Validator) {
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

fn scan_secrets(value: &Value, path: &str, ordinal: usize, validator: &mut Validator) {
    const FORBIDDEN: [&str; 16] = [
        "execution_token",
        "grant_credential",
        "access_token",
        "refresh_token",
        "private_key",
        "cookie",
        "authorization",
        "dpop_proof",
        "dpop",
        "client_secret",
        "bearer_token",
        "id_token",
        "api_key",
        "password",
        "set_cookie",
        "proxy_authorization",
    ];
    match value {
        Value::Object(object) => {
            for (key, child) in object {
                let child_path = format!("{path}/{}", key.replace('~', "~0").replace('/', "~1"));
                let normalized = key.to_ascii_lowercase().replace('-', "_");
                if FORBIDDEN.contains(&normalized.as_str()) {
                    validator.error(
                        "ASP-REPLAY-SECRETS-001",
                        ordinal,
                        &child_path,
                        "bundle contains a forbidden raw protocol secret field",
                    );
                } else {
                    scan_secrets(child, &child_path, ordinal, validator);
                }
            }
        }
        Value::Array(array) => {
            for (index, child) in array.iter().enumerate() {
                scan_secrets(child, &format!("{path}/{index}"), ordinal, validator);
            }
        }
        _ => {}
    }
}

fn validate_record_integrity(bundle: &Value, validator: &mut Validator) -> Result<(), ReplayError> {
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

fn validate_records(bundle: &Value, validator: &mut Validator) -> Result<(), ReplayError> {
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

fn report_hash(report: &Report) -> Result<String, ReplayError> {
    let value =
        serde_json::to_value(report).map_err(|error| ReplayError::Canonical(error.to_string()))?;
    object_hash(REPORT_DOMAIN, &value, &["report_hash"])
}

/// Verify one exact replay bundle and produce a deterministic, payload-minimized report.
pub fn verify(_source: &str, document: &[u8]) -> Result<Report, ReplayError> {
    let bundle = parse_strict(document)?;
    let capture_partial = member(&bundle, "capture")
        .and_then(|capture| string(capture, "completeness"))
        == Some("partial");
    let mut validator = Validator::new(capture_partial);
    validate_schema(&bundle, &mut validator)?;

    if string(&bundle, "profile") != Some(PROFILE)
        || string(&bundle, "protocol_version") != Some("agent-surface/0.1")
        || string(&bundle, "claim_effect") != Some("descriptive_only")
        || string(&bundle, "created_at").is_none_or(|time| !timestamp_shape(time))
    {
        validator.error(
            "ASP-REPLAY-SCHEMA-001",
            0,
            "",
            "bundle profile metadata is not canonical",
        );
    }
    if let Some(capture) = member(&bundle, "capture") {
        for member_name in ["started_at", "ended_at"] {
            if string(capture, member_name).is_none_or(|time| !timestamp_shape(time)) {
                validator.error(
                    "ASP-REPLAY-SCHEMA-001",
                    0,
                    format!("/capture/{member_name}"),
                    "capture timestamp is not a real supported RFC 3339 UTC instant",
                );
            }
        }
    }
    if let Some(expected) = string(&bundle, "bundle_hash") {
        if !valid_digest(expected) {
            validator.error(
                "ASP-REPLAY-CONTEXT-001",
                0,
                "/bundle_hash",
                "bundle hash is not a canonical SHA-256 value",
            );
        } else {
            let actual = object_hash(BUNDLE_DOMAIN, &bundle, &["bundle_hash"])?;
            if expected != actual {
                validator.error(
                    "ASP-REPLAY-CONTEXT-001",
                    0,
                    "/bundle_hash",
                    "bundle hash does not match the exact bundle",
                );
            }
        }
    }
    check_context(&bundle, &mut validator)?;
    scan_secrets(&bundle, "", 0, &mut validator);
    validate_record_integrity(&bundle, &mut validator)?;
    let preflight_failed = validator.has_errors;
    if !preflight_failed {
        validate_records(&bundle, &mut validator)?;
    }

    let check_registry = registry()?;
    let order: HashMap<&str, usize> = check_registry
        .checks
        .iter()
        .enumerate()
        .map(|(index, check)| (check.check_id.as_str(), index))
        .collect();
    validator.diagnostics.sort_by(|left, right| {
        (
            left.ordinal,
            order
                .get(left.check_id.as_str())
                .copied()
                .unwrap_or(usize::MAX),
            left.path.as_str(),
            left.message.as_str(),
        )
            .cmp(&(
                right.ordinal,
                order
                    .get(right.check_id.as_str())
                    .copied()
                    .unwrap_or(usize::MAX),
                right.path.as_str(),
                right.message.as_str(),
            ))
    });
    let has_errors = validator.has_errors;
    let evaluation_state = if preflight_failed {
        "preflight_failed"
    } else if has_errors {
        "semantic_invalid"
    } else if validator.incomplete {
        "incomplete"
    } else {
        "valid"
    };
    let integrity_verdict = if has_errors { "invalid" } else { "valid" };
    let replay_completeness = if has_errors {
        "not_evaluated"
    } else if validator.incomplete {
        "incomplete"
    } else {
        "complete"
    };
    let verdict = if has_errors {
        "invalid"
    } else if validator.incomplete {
        "incomplete"
    } else {
        "valid"
    };
    let checks = check_registry
        .checks
        .iter()
        .map(|definition| {
            let summary = validator
                .finding_summaries
                .get(&definition.check_id)
                .cloned()
                .unwrap_or_default();
            let semantic = ![
                "ASP-REPLAY-SCHEMA-001",
                "ASP-REPLAY-CONTEXT-001",
                "ASP-REPLAY-ORDER-001",
                "ASP-REPLAY-SECRETS-001",
            ]
            .contains(&definition.check_id.as_str());
            let status = if preflight_failed && semantic {
                "not_evaluated"
            } else if summary.errors > 0 {
                "fail"
            } else if summary.incomplete > 0 {
                "incomplete"
            } else {
                "pass"
            };
            CheckResult {
                check_id: definition.check_id.clone(),
                title: definition.title.clone(),
                status: status.to_owned(),
                findings: summary.errors + summary.incomplete,
            }
        })
        .collect::<Vec<_>>();
    let check_passes = |check_id: &str| {
        checks
            .iter()
            .find(|check| check.check_id == check_id)
            .is_some_and(|check| check.status == "pass")
    };
    let mut verified = Vec::new();
    if !has_errors {
        if [
            "ASP-REPLAY-SCHEMA-001",
            "ASP-REPLAY-ORDER-001",
            "ASP-REPLAY-RECEIPT-HASH-001",
        ]
        .iter()
        .all(|check| check_passes(check))
        {
            verified.push("canonical_integrity".to_owned());
        }
        if check_passes("ASP-REPLAY-CONTEXT-001") {
            verified.push("historical_context_consistency".to_owned());
        }
        if ["ASP-REPLAY-SESSION-001", "ASP-REPLAY-GAP-001"]
            .iter()
            .all(|check| check_passes(check))
        {
            verified.push("recorded_lifecycle".to_owned());
        }
        if [
            "ASP-REPLAY-EVENT-001",
            "ASP-REPLAY-DELIVERY-001",
            "ASP-REPLAY-ACK-001",
            "ASP-REPLAY-GAP-001",
            "ASP-REPLAY-RECEIPT-CHAIN-001",
            "ASP-REPLAY-RECEIPT-LINK-001",
        ]
        .iter()
        .all(|check| check_passes(check))
        {
            verified.push("recorded_linkage".to_owned());
        }
    }
    let heads = validator
        .receipt_hashes
        .iter()
        .filter(|hash| !validator.receipt_parents.contains(*hash))
        .count();
    let source_hash = raw_sha256(document);
    let bundle_id = string(&bundle, "bundle_id")
        .filter(|value| valid_bundle_id(value))
        .map(str::to_owned);
    let bundle_hash = string(&bundle, "bundle_hash")
        .filter(|value| valid_digest(value))
        .map(str::to_owned);
    let replay = if has_errors {
        ReplaySummary {
            status: "not_evaluated".to_owned(),
            final_session_state: "unknown".to_owned(),
            session_generation: 0,
            session_transitions: 0,
            event_occurrences: 0,
            event_deliveries: 0,
            event_attempts: 0,
            event_acknowledgements: 0,
            event_gaps: 0,
            capture_gaps: 0,
            receipts: 0,
            receipt_roots: 0,
            receipt_heads: 0,
        }
    } else {
        ReplaySummary {
            status: "evaluated".to_owned(),
            final_session_state: validator.session_state,
            session_generation: validator.session_generation,
            session_transitions: validator.session_transitions,
            event_occurrences: validator.occurrence_hashes.len(),
            event_deliveries: validator.deliveries.len(),
            event_attempts: validator.event_attempts,
            event_acknowledgements: validator.event_acknowledgements,
            event_gaps: validator.event_gaps,
            capture_gaps: validator.capture_gaps,
            receipts: validator.receipt_hashes.len(),
            receipt_roots: validator.receipt_roots.len(),
            receipt_heads: heads,
        }
    };
    let mut report = Report {
        schema: "./report.schema.json".to_owned(),
        schema_version: 1,
        report_profile: REPORT_PROFILE.to_owned(),
        claim_effect: "descriptive_only".to_owned(),
        tool: ReportTool {
            name: TOOL_NAME.to_owned(),
            version: TOOL_VERSION.to_owned(),
            check_profile: check_registry.profile,
            check_version: check_registry.version,
            check_registry_sha256: raw_sha256(CHECK_REGISTRY.as_bytes()),
        },
        input: ReportInput {
            source_sha256: source_hash,
            bundle_id,
            bundle_hash,
        },
        evaluation_state: evaluation_state.to_owned(),
        integrity_verdict: integrity_verdict.to_owned(),
        replay_completeness: replay_completeness.to_owned(),
        verdict: verdict.to_owned(),
        checks,
        diagnostics: validator.diagnostics,
        diagnostics_truncated: validator.diagnostics_truncated,
        diagnostics_omitted: validator.diagnostics_omitted,
        replay,
        assurance: Assurance {
            verified,
            not_verified: vec![
                "producer_authentication".to_owned(),
                "signature_validity".to_owned(),
                "current_authority".to_owned(),
                "trusted_time".to_owned(),
                "effect_occurrence".to_owned(),
                "remote_schemas".to_owned(),
                "complete_native_object_semantics".to_owned(),
            ],
        },
        report_hash: String::new(),
    };
    report.report_hash = report_hash(&report)?;
    Ok(report)
}

fn read(path: &Path) -> Result<String, ReplayError> {
    fs::read_to_string(path).map_err(|source| ReplayError::Io {
        path: path.display().to_string(),
        source,
    })
}

fn relative_path<'a>(value: &'a str, label: &str) -> Result<&'a Path, ReplayError> {
    let path = Path::new(value);
    if path.is_absolute()
        || path
            .components()
            .any(|component| !matches!(component, Component::Normal(_)))
    {
        return Err(ReplayError::SelfCheck(format!(
            "{label} must be a confined relative path"
        )));
    }
    Ok(path)
}

fn validate_instance(schema: &Value, instance: &Value, label: &str) -> Result<(), ReplayError> {
    let compiled = jsonschema::validator_for(schema)
        .map_err(|error| ReplayError::SelfCheck(format!("{label} schema: {error}")))?;
    let errors: Vec<String> = compiled
        .iter_errors(instance)
        .map(|error| error.to_string())
        .collect();
    if errors.is_empty() {
        Ok(())
    } else {
        Err(ReplayError::SelfCheck(format!(
            "{label} validation: {}",
            errors.join("; ")
        )))
    }
}

#[derive(Debug, Deserialize)]
struct CaseRegistry {
    schema_version: u64,
    profile: String,
    cases: Vec<Case>,
}

#[derive(Debug, Deserialize)]
#[serde(tag = "expect", rename_all = "snake_case")]
enum Case {
    Report {
        id: String,
        source: String,
        golden: Option<String>,
        evaluation_state: String,
        verdict: String,
        integrity_verdict: String,
        replay_completeness: String,
        diagnostic_check_ids: Vec<String>,
        #[serde(default)]
        mutations: Vec<Mutation>,
        #[serde(default)]
        rehash_after_mutations: bool,
    },
    ParseError {
        id: String,
        source: String,
        error_contains: String,
    },
}

#[derive(Clone, Debug, Deserialize)]
struct Mutation {
    op: String,
    path: String,
    #[serde(default)]
    value: Value,
}

fn unescape_pointer(component: &str) -> String {
    component.replace("~1", "/").replace("~0", "~")
}

fn apply_mutation(root: &mut Value, mutation: &Mutation) -> Result<(), ReplayError> {
    match mutation.op.as_str() {
        "replace" => {
            let target = root.pointer_mut(&mutation.path).ok_or_else(|| {
                ReplayError::SelfCheck(format!(
                    "mutation path {:?} does not resolve",
                    mutation.path
                ))
            })?;
            *target = mutation.value.clone();
        }
        "add" => {
            let (parent_path, member) = mutation.path.rsplit_once('/').ok_or_else(|| {
                ReplayError::SelfCheck("mutation add path has no parent".to_owned())
            })?;
            let parent = if parent_path.is_empty() {
                root
            } else {
                root.pointer_mut(parent_path).ok_or_else(|| {
                    ReplayError::SelfCheck(format!(
                        "mutation parent {:?} does not resolve",
                        parent_path
                    ))
                })?
            };
            parent
                .as_object_mut()
                .ok_or_else(|| {
                    ReplayError::SelfCheck("mutation parent is not an object".to_owned())
                })?
                .insert(unescape_pointer(member), mutation.value.clone());
        }
        "remove" => {
            let (parent_path, member) = mutation.path.rsplit_once('/').ok_or_else(|| {
                ReplayError::SelfCheck("mutation remove path has no parent".to_owned())
            })?;
            let parent = if parent_path.is_empty() {
                root
            } else {
                root.pointer_mut(parent_path).ok_or_else(|| {
                    ReplayError::SelfCheck(format!(
                        "mutation parent {:?} does not resolve",
                        parent_path
                    ))
                })?
            };
            if parent
                .as_object_mut()
                .and_then(|object| object.remove(&unescape_pointer(member)))
                .is_none()
            {
                return Err(ReplayError::SelfCheck(
                    "mutation remove target does not exist".to_owned(),
                ));
            }
        }
        _ => {
            return Err(ReplayError::SelfCheck(format!(
                "unknown mutation operation {:?}",
                mutation.op
            )));
        }
    }
    Ok(())
}

fn set_string(value: &mut Value, name: &str, new_value: String) {
    if let Some(object) = value.as_object_mut() {
        object.insert(name.to_owned(), Value::String(new_value));
    }
}

fn rehash_bundle(bundle: &mut Value) -> Result<(), ReplayError> {
    let surface_hash = {
        let surface = bundle
            .pointer("/context/surface")
            .ok_or_else(|| ReplayError::SelfCheck("rehash requires context.surface".to_owned()))?;
        object_hash(MANIFEST_DOMAIN, surface, &["surface_hash"])?
    };
    set_string(
        bundle
            .pointer_mut("/context/surface")
            .expect("surface was resolved"),
        "surface_hash",
        surface_hash.clone(),
    );
    set_string(
        bundle
            .pointer_mut("/context/grant/resource_server")
            .ok_or_else(|| {
                ReplayError::SelfCheck("rehash requires Grant resource_server".to_owned())
            })?,
        "surface_hash",
        surface_hash.clone(),
    );
    set_string(
        bundle
            .pointer_mut("/scope")
            .ok_or_else(|| ReplayError::SelfCheck("rehash requires scope".to_owned()))?,
        "surface_hash",
        surface_hash.clone(),
    );

    let grant_hash = {
        let grant = bundle
            .pointer("/context/grant")
            .ok_or_else(|| ReplayError::SelfCheck("rehash requires context.grant".to_owned()))?;
        let mut hash_view = grant.clone();
        if let Some(object) = hash_view.as_object_mut() {
            object.remove("grant_hash");
            if object.get("type").and_then(Value::as_str)
                == Some(
                    "https://github.com/0al-spec/agent-surface/authorization-details/agent-grant",
                )
            {
                object.remove("type");
            }
        }
        object_hash(GRANT_DOMAIN, &hash_view, &[])?
    };
    set_string(
        bundle
            .pointer_mut("/context/grant")
            .expect("grant was resolved"),
        "grant_hash",
        grant_hash.clone(),
    );
    set_string(
        bundle.pointer_mut("/scope").expect("scope was resolved"),
        "grant_hash",
        grant_hash.clone(),
    );

    let mut prior_record_hash: Option<String> = None;
    let mut receipt_hash_replacements = HashMap::new();
    let records = member(bundle, "records")
        .and_then(Value::as_array)
        .ok_or_else(|| ReplayError::SelfCheck("rehash requires records".to_owned()))?
        .len();
    for index in 0..records {
        let record_path = format!("/records/{index}");
        let kind = bundle
            .pointer(&record_path)
            .and_then(|record| string(record, "kind"))
            .unwrap_or_default()
            .to_owned();
        let body_path = format!("{record_path}/body");
        if let Some(body) = bundle.pointer_mut(&body_path) {
            match kind.as_str() {
                "event_delivery" => {
                    set_string(body, "aspsurfacehash", surface_hash.clone());
                    let hash = object_hash(
                        EVENT_DOMAIN,
                        body,
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
                    set_string(body, "aspeventhash", hash);
                }
                "receipt" => {
                    set_string(body, "grant_hash", grant_hash.clone());
                    set_string(body, "surface_hash", surface_hash.clone());
                    if let Some(parent) = string(body, "parent_receipt_hash")
                        .and_then(|hash| receipt_hash_replacements.get(hash))
                        .cloned()
                    {
                        set_string(body, "parent_receipt_hash", parent);
                    }
                    for links_name in ["approval_receipt_hashes"] {
                        if let Some(links) = member(body, links_name).and_then(Value::as_object) {
                            let replacements: Vec<(String, String)> = links
                                .iter()
                                .filter_map(|(role, value)| {
                                    let old = value.as_str()?;
                                    Some((
                                        role.clone(),
                                        receipt_hash_replacements.get(old)?.clone(),
                                    ))
                                })
                                .collect();
                            if let Some(links) =
                                body.get_mut(links_name).and_then(Value::as_object_mut)
                            {
                                for (role, hash) in replacements {
                                    links.insert(role, Value::String(hash));
                                }
                            }
                        }
                    }
                    if let Some(target) = body
                        .get("execution")
                        .and_then(|execution| string(execution, "target_receipt_hash"))
                        .and_then(|hash| receipt_hash_replacements.get(hash))
                        .cloned()
                        && let Some(execution) = body.get_mut("execution")
                    {
                        set_string(execution, "target_receipt_hash", target);
                    }
                    if let Some(policy) = body.get_mut("policy_decision") {
                        let hash = object_hash(POLICY_DOMAIN, policy, &["policy_decision_hash"])?;
                        set_string(policy, "policy_decision_hash", hash.clone());
                        set_string(body, "policy_decision_hash", hash);
                    }
                    if let Some(execution) = member(body, "execution") {
                        let hash = object_hash(EXECUTION_DOMAIN, execution, &["execution_token"])?;
                        set_string(body, "execution_hash", hash);
                    }
                    if let Some(effects) = member(body, "actual_effects") {
                        let hash = object_hash(ACTUAL_EFFECTS_DOMAIN, effects, &[])?;
                        set_string(body, "actual_effects_hash", hash);
                    }
                    let old_hash = string(body, "receipt_hash").map(str::to_owned);
                    let hash = object_hash(
                        RECEIPT_DOMAIN,
                        body,
                        &["receipt_hash", "receipt_signatures"],
                    )?;
                    set_string(body, "receipt_hash", hash.clone());
                    if let Some(old_hash) = old_hash {
                        receipt_hash_replacements.insert(old_hash, hash);
                    }
                }
                _ => {}
            }
        }
        let record = bundle
            .pointer_mut(&record_path)
            .expect("record index was resolved");
        if let Some(object) = record.as_object_mut() {
            match &prior_record_hash {
                Some(hash) => {
                    object.insert(
                        "previous_record_hash".to_owned(),
                        Value::String(hash.clone()),
                    );
                }
                None => {
                    object.remove("previous_record_hash");
                }
            }
        }
        let hash = object_hash(RECORD_DOMAIN, record, &["record_hash"])?;
        set_string(record, "record_hash", hash.clone());
        prior_record_hash = Some(hash);
    }
    let hash = object_hash(BUNDLE_DOMAIN, bundle, &["bundle_hash"])?;
    set_string(bundle, "bundle_hash", hash);
    Ok(())
}

#[derive(Debug, Serialize)]
struct GoldenReport<'a> {
    evaluation_state: &'a str,
    integrity_verdict: &'a str,
    replay_completeness: &'a str,
    verdict: &'a str,
    diagnostic_check_ids: Vec<&'a str>,
    report_hash: &'a str,
}

impl Case {
    fn id(&self) -> &str {
        match self {
            Self::Report { id, .. } | Self::ParseError { id, .. } => id,
        }
    }
}

/// Verify all embedded artifacts and execute every registered fixture/golden case.
pub fn self_check(repository_root: &Path) -> Result<(), ReplayError> {
    let crate_root = repository_root.join("tools/asp-replay");
    let artifacts = [
        (crate_root.join("schema/bundle.schema.json"), BUNDLE_SCHEMA),
        (crate_root.join("schema/report.schema.json"), REPORT_SCHEMA),
        (crate_root.join("schema/checks.schema.json"), CHECKS_SCHEMA),
        (crate_root.join("schema/cases.schema.json"), CASES_SCHEMA),
        (crate_root.join("checks/v1/checks.json"), CHECK_REGISTRY),
        (crate_root.join("cases/v1/cases.json"), CASE_REGISTRY),
    ];
    for (path, embedded) in &artifacts {
        if read(path)? != *embedded {
            return Err(ReplayError::SelfCheck(format!(
                "compiled artifact differs from {}",
                path.display()
            )));
        }
    }
    let bundle_schema: Value = serde_json::from_str(BUNDLE_SCHEMA)
        .map_err(|error| ReplayError::SelfCheck(error.to_string()))?;
    let report_schema: Value = serde_json::from_str(REPORT_SCHEMA)
        .map_err(|error| ReplayError::SelfCheck(error.to_string()))?;
    let checks_schema: Value = serde_json::from_str(CHECKS_SCHEMA)
        .map_err(|error| ReplayError::SelfCheck(error.to_string()))?;
    let cases_schema: Value = serde_json::from_str(CASES_SCHEMA)
        .map_err(|error| ReplayError::SelfCheck(error.to_string()))?;
    for (label, schema) in [
        ("bundle", &bundle_schema),
        ("report", &report_schema),
        ("checks", &checks_schema),
        ("cases", &cases_schema),
    ] {
        jsonschema::validator_for(schema)
            .map_err(|error| ReplayError::SelfCheck(format!("{label} schema: {error}")))?;
    }
    let checks_value = parse_strict(CHECK_REGISTRY.as_bytes())?;
    let cases_value = parse_strict(CASE_REGISTRY.as_bytes())?;
    validate_instance(&checks_schema, &checks_value, "check registry")?;
    validate_instance(&cases_schema, &cases_value, "case registry")?;
    let checks = registry()?;
    if checks.schema_version != 1 || checks.profile != CHECK_PROFILE {
        return Err(ReplayError::SelfCheck(
            "check registry metadata is not canonical".to_owned(),
        ));
    }
    let actual: Vec<&str> = checks
        .checks
        .iter()
        .map(|check| check.check_id.as_str())
        .collect();
    if actual != IMPLEMENTED_CHECKS || checks.checks.iter().any(|check| check.title.is_empty()) {
        return Err(ReplayError::SelfCheck(
            "check registry must exactly match implemented checks".to_owned(),
        ));
    }
    let cases: CaseRegistry = serde_json::from_value(cases_value)
        .map_err(|error| ReplayError::SelfCheck(error.to_string()))?;
    if cases.schema_version != 1 || cases.profile != PROFILE {
        return Err(ReplayError::SelfCheck(
            "case registry metadata is not canonical".to_owned(),
        ));
    }
    let mut ids = HashSet::new();
    let mut executable_check_coverage = HashSet::new();
    for case in cases.cases {
        if !ids.insert(case.id().to_owned()) {
            return Err(ReplayError::SelfCheck(format!(
                "duplicate case id {:?}",
                case.id()
            )));
        }
        match case {
            Case::Report {
                id,
                source,
                golden,
                evaluation_state,
                verdict,
                integrity_verdict,
                replay_completeness,
                diagnostic_check_ids,
                mutations,
                rehash_after_mutations,
            } => {
                executable_check_coverage.extend(diagnostic_check_ids.iter().cloned());
                let source_path = crate_root.join(relative_path(&source, "case source")?);
                let source_bytes = fs::read(&source_path).map_err(|source| ReplayError::Io {
                    path: source_path.display().to_string(),
                    source,
                })?;
                let bytes = if mutations.is_empty() {
                    source_bytes
                } else {
                    let mut value = parse_strict(&source_bytes)?;
                    for mutation in &mutations {
                        apply_mutation(&mut value, mutation)?;
                    }
                    if rehash_after_mutations {
                        rehash_bundle(&mut value)?;
                    }
                    serde_json::to_vec(&value)
                        .map_err(|error| ReplayError::SelfCheck(error.to_string()))?
                };
                let report = verify(&source, &bytes)
                    .map_err(|error| ReplayError::SelfCheck(format!("{id}: {error}")))?;
                let report_check_ids: Vec<&str> = report
                    .checks
                    .iter()
                    .map(|check| check.check_id.as_str())
                    .collect();
                if report_check_ids != IMPLEMENTED_CHECKS {
                    return Err(ReplayError::SelfCheck(format!(
                        "{id}: report check order differs from the implemented check profile"
                    )));
                }
                if report.verdict != verdict {
                    return Err(ReplayError::SelfCheck(format!(
                        "{id}: expected verdict {verdict:?}, got {:?}",
                        report.verdict
                    )));
                }
                if report.evaluation_state != evaluation_state {
                    return Err(ReplayError::SelfCheck(format!(
                        "{id}: expected evaluation state {evaluation_state:?}, got {:?}",
                        report.evaluation_state
                    )));
                }
                if report.integrity_verdict != integrity_verdict
                    || report.replay_completeness != replay_completeness
                {
                    return Err(ReplayError::SelfCheck(format!(
                        "{id}: orthogonal report outcomes differ from the case registry"
                    )));
                }
                let actual_check_ids: HashSet<&str> = report
                    .diagnostics
                    .iter()
                    .map(|diagnostic| diagnostic.check_id.as_str())
                    .collect();
                let expected_check_ids: HashSet<&str> =
                    diagnostic_check_ids.iter().map(String::as_str).collect();
                if actual_check_ids != expected_check_ids {
                    return Err(ReplayError::SelfCheck(format!(
                        "{id}: diagnostic check IDs differ: expected {expected_check_ids:?}, got {actual_check_ids:?}"
                    )));
                }
                let value = serde_json::to_value(&report)
                    .map_err(|error| ReplayError::SelfCheck(error.to_string()))?;
                validate_instance(&report_schema, &value, &format!("{id} report"))?;
                if let Some(golden) = golden {
                    let projection = GoldenReport {
                        evaluation_state: &report.evaluation_state,
                        integrity_verdict: &report.integrity_verdict,
                        replay_completeness: &report.replay_completeness,
                        verdict: &report.verdict,
                        diagnostic_check_ids: report
                            .diagnostics
                            .iter()
                            .map(|diagnostic| diagnostic.check_id.as_str())
                            .collect(),
                        report_hash: &report.report_hash,
                    };
                    let actual = format!(
                        "{}\n",
                        serde_json::to_string_pretty(&projection)
                            .map_err(|error| ReplayError::SelfCheck(error.to_string()))?
                    );
                    let golden_path = crate_root.join(relative_path(&golden, "golden report")?);
                    if actual != read(&golden_path)? {
                        return Err(ReplayError::SelfCheck(format!(
                            "{id}: report binding differs from {}",
                            golden_path.display()
                        )));
                    }
                }
            }
            Case::ParseError {
                id,
                source,
                error_contains,
            } => {
                let source_path = crate_root.join(relative_path(&source, "case source")?);
                let bytes = fs::read(&source_path).map_err(|source| ReplayError::Io {
                    path: source_path.display().to_string(),
                    source,
                })?;
                match verify(&source, &bytes) {
                    Err(error) if error.to_string().contains(&error_contains) => {}
                    Err(error) => {
                        return Err(ReplayError::SelfCheck(format!(
                            "{id}: error {error:?} does not contain {error_contains:?}"
                        )));
                    }
                    Ok(_) => {
                        return Err(ReplayError::SelfCheck(format!(
                            "{id}: parse-error case unexpectedly produced a report"
                        )));
                    }
                }
            }
        }
    }
    let uncovered: Vec<&str> = IMPLEMENTED_CHECKS
        .iter()
        .copied()
        .filter(|check| !executable_check_coverage.contains(*check))
        .collect();
    if !uncovered.is_empty() {
        return Err(ReplayError::SelfCheck(format!(
            "implemented checks lack executable diagnostic coverage: {uncovered:?}"
        )));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn jcs_uses_utf16_member_order_and_finite_binary64() {
        let value = parse_strict(br#"{"data":{"\uE000":2,"\uD800\uDC00":1,"value":0.1}}"#).unwrap();
        let canonical = serde_json_canonicalizer::to_string(&value).unwrap();
        assert_eq!(canonical, r#"{"data":{"value":0.1,"𐀀":1,"":2}}"#);
    }

    #[test]
    fn strict_parser_rejects_ijson_hazards() {
        for document in [
            br#"{"value":-0}"#.as_slice(),
            br#"{"value":-0.0}"#,
            br#"{"value":9007199254740992}"#,
            br#"{"value":1,"value":2}"#,
            br#"{"value":1e400}"#,
            br#"{"value":"\uFDD0"}"#,
        ] {
            assert!(parse_strict(document).is_err());
        }
    }

    #[test]
    fn hash_exclusion_is_stable() {
        let first = serde_json::json!({"ordinal":0,"record_hash":"old","body":{"x":1}});
        let second = serde_json::json!({"ordinal":0,"record_hash":"new","body":{"x":1}});
        assert_eq!(
            object_hash(RECORD_DOMAIN, &first, &["record_hash"]).unwrap(),
            object_hash(RECORD_DOMAIN, &second, &["record_hash"]).unwrap()
        );
    }

    #[test]
    fn diagnostics_never_include_values_from_secret_fields() {
        let mut validator = Validator::new(false);
        scan_secrets(
            &serde_json::json!({"execution_token":"do-not-print"}),
            "/body",
            0,
            &mut validator,
        );
        let serialized = serde_json::to_string(&validator.diagnostics).unwrap();
        assert!(!serialized.contains("do-not-print"));
    }

    fn event_fixture(delivery_id: &str, event_id: &str, attempt: u64, sequence: u64) -> Value {
        let mut event = serde_json::json!({
            "specversion": "1.0",
            "id": event_id,
            "source": "https://code.example.com",
            "type": "task.created",
            "time": "2026-07-20T10:00:00Z",
            "dataschema": "https://code.example.com/schemas/task-created.json",
            "datacontenttype": "application/json",
            "data": {"score": 0.1},
            "aspscope": "task.read",
            "aspcontrol": false,
            "aspsurfacehash": "sha-256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "aspeventhash": "",
            "aspsubid": "sub_1",
            "aspdeliveryid": delivery_id,
            "aspattempt": attempt,
            "aspstream": "stream_1",
            "aspsequence": sequence,
            "aspcursor": format!("cursor_{sequence}"),
            "aspsessionid": "sess_1",
            "aspsessiongen": 1
        });
        let hash = object_hash(
            EVENT_DOMAIN,
            &event,
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
        )
        .unwrap();
        event["aspeventhash"] = Value::String(hash);
        event
    }

    fn event_fixture_for(
        delivery_id: &str,
        event_id: &str,
        attempt: u64,
        sequence: u64,
        subscription_id: &str,
        stream: &str,
    ) -> Value {
        let mut event = event_fixture(delivery_id, event_id, attempt, sequence);
        event["aspsubid"] = Value::String(subscription_id.to_owned());
        event["aspstream"] = Value::String(stream.to_owned());
        event
    }

    fn event_scope() -> (Value, Value, Value) {
        (
            serde_json::json!({
                "issuer": "https://code.example.com",
                "surface_hash": "sha-256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                "session_id": "sess_1",
                "session_generation": 1
            }),
            serde_json::json!({
                "events": [{
                    "id": "task.created",
                    "scope": "task.read",
                    "schema": "https://code.example.com/schemas/task-created.json"
                }]
            }),
            serde_json::json!({"scopes":["task.read"]}),
        )
    }

    fn terminal_ack(delivery_id: &str, cursor: &str, ordinal: usize, validator: &mut Validator) {
        check_ack(
            &serde_json::json!({
                "type":"event.ack",
                "payload":{
                    "subscription_id":"sub_1",
                    "delivery_id":delivery_id,
                    "cursor":cursor,
                    "outcome":"processed",
                    "reason":"durably_recorded"
                }
            }),
            ordinal,
            validator,
        );
    }

    #[test]
    fn stream_sequence_requires_terminal_acknowledgement() {
        let scope = serde_json::json!({
            "issuer": "https://code.example.com",
            "surface_hash": "sha-256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "session_id": "sess_1",
            "session_generation": 1
        });
        let surface = serde_json::json!({
            "events": [{
                "id": "task.created",
                "scope": "task.read",
                "schema": "https://code.example.com/schemas/task-created.json"
            }]
        });
        let grant = serde_json::json!({"scopes":["task.read"]});
        let mut validator = Validator::new(false);
        validator.session_generation = 1;
        validator.session_state = "active".to_owned();
        check_event(
            &event_fixture("delivery_1", "event_1", 1, 1),
            0,
            &scope,
            &surface,
            &grant,
            &mut validator,
        )
        .unwrap();
        check_event(
            &event_fixture("delivery_2", "event_2", 1, 2),
            1,
            &scope,
            &surface,
            &grant,
            &mut validator,
        )
        .unwrap();
        assert!(validator.diagnostics.iter().any(|diagnostic| {
            diagnostic.check_id == "ASP-REPLAY-DELIVERY-001" && diagnostic.severity == "error"
        }));
    }

    #[test]
    fn capture_gap_can_cover_a_missing_terminal_acknowledgement() {
        let (scope, surface, grant) = event_scope();
        let mut validator = Validator::new(true);
        validator.session_generation = 1;
        validator.session_state = "active".to_owned();
        check_event(
            &event_fixture("delivery_1", "event_1", 1, 1),
            0,
            &scope,
            &surface,
            &grant,
            &mut validator,
        )
        .unwrap();
        validator.capture_gap_epoch += 1;
        check_event(
            &event_fixture("delivery_2", "event_2", 1, 2),
            2,
            &scope,
            &surface,
            &grant,
            &mut validator,
        )
        .unwrap();
        assert!(!validator.has_errors);
        assert!(validator.diagnostics.iter().any(|diagnostic| {
            diagnostic.check_id == "ASP-REPLAY-DELIVERY-001"
                && diagnostic.severity == "incomplete"
                && diagnostic.message.contains("terminal acknowledgement")
        }));
        assert_eq!(
            validator
                .streams
                .get(&("sub_1".to_owned(), "stream_1".to_owned()))
                .map(|progress| progress.sequence),
            Some(2)
        );
    }

    #[test]
    fn protocol_gap_does_not_cover_a_known_missing_terminal_acknowledgement() {
        let (scope, surface, grant) = event_scope();
        let mut validator = Validator::new(false);
        validator.session_generation = 1;
        validator.session_state = "active".to_owned();
        check_event(
            &event_fixture("delivery_1", "event_1", 1, 1),
            0,
            &scope,
            &surface,
            &grant,
            &mut validator,
        )
        .unwrap();
        check_gap(
            &serde_json::json!({
                "type":"event.gap",
                "payload":{
                    "subscription_id":"sub_1",
                    "last_accepted_cursor":"cursor_1",
                    "earliest_available_cursor":"cursor_2",
                    "reason":"retention_expired"
                }
            }),
            1,
            &mut validator,
        );
        check_event(
            &event_fixture("delivery_2", "event_2", 1, 2),
            2,
            &scope,
            &surface,
            &grant,
            &mut validator,
        )
        .unwrap();
        assert!(validator.diagnostics.iter().any(|diagnostic| {
            diagnostic.check_id == "ASP-REPLAY-DELIVERY-001"
                && diagnostic.severity == "error"
                && diagnostic.message.contains("terminal acknowledgement")
        }));
    }

    #[test]
    fn terminal_ack_allows_the_next_stream_sequence() {
        let scope = serde_json::json!({
            "issuer": "https://code.example.com",
            "surface_hash": "sha-256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "session_id": "sess_1",
            "session_generation": 1
        });
        let surface = serde_json::json!({
            "events": [{
                "id": "task.created",
                "scope": "task.read",
                "schema": "https://code.example.com/schemas/task-created.json"
            }]
        });
        let grant = serde_json::json!({"scopes":["task.read"]});
        let mut validator = Validator::new(false);
        validator.session_generation = 1;
        validator.session_state = "active".to_owned();
        check_event(
            &event_fixture("delivery_1", "event_1", 1, 1),
            0,
            &scope,
            &surface,
            &grant,
            &mut validator,
        )
        .unwrap();
        check_ack(
            &serde_json::json!({
                "type":"event.ack",
                "payload":{
                    "subscription_id":"sub_1",
                    "delivery_id":"delivery_1",
                    "cursor":"cursor_1",
                    "outcome":"processed",
                    "reason":"durably_recorded"
                }
            }),
            1,
            &mut validator,
        );
        check_event(
            &event_fixture("delivery_2", "event_2", 1, 2),
            2,
            &scope,
            &surface,
            &grant,
            &mut validator,
        )
        .unwrap();
        assert!(validator.diagnostics.is_empty());
    }

    #[test]
    fn protocol_gap_epoch_covers_each_stream_once() {
        let (scope, surface, grant) = event_scope();
        let mut validator = Validator::new(false);
        validator.session_generation = 1;
        validator.session_state = "active".to_owned();
        for (ordinal, stream) in ["stream_1", "stream_2"].iter().enumerate() {
            let delivery_id = format!("delivery_{}", ordinal + 1);
            check_event(
                &event_fixture_for(
                    &delivery_id,
                    &format!("event_{}", ordinal + 1),
                    1,
                    1,
                    "sub_1",
                    stream,
                ),
                ordinal * 2,
                &scope,
                &surface,
                &grant,
                &mut validator,
            )
            .unwrap();
            terminal_ack(&delivery_id, "cursor_1", ordinal * 2 + 1, &mut validator);
        }
        check_gap(
            &serde_json::json!({
                "type":"event.gap",
                "payload":{
                    "subscription_id":"sub_1",
                    "last_accepted_cursor":"cursor_1",
                    "earliest_available_cursor":"cursor_3",
                    "reason":"retention_expired"
                }
            }),
            4,
            &mut validator,
        );
        for (offset, stream) in ["stream_1", "stream_2"].iter().enumerate() {
            check_event(
                &event_fixture_for(
                    &format!("delivery_{}", offset + 3),
                    &format!("event_{}", offset + 3),
                    1,
                    3,
                    "sub_1",
                    stream,
                ),
                5 + offset,
                &scope,
                &surface,
                &grant,
                &mut validator,
            )
            .unwrap();
        }
        assert_eq!(
            validator
                .diagnostics
                .iter()
                .filter(|diagnostic| {
                    diagnostic.check_id == "ASP-REPLAY-DELIVERY-001"
                        && diagnostic.severity == "incomplete"
                })
                .count(),
            2
        );
        assert!(!validator.has_errors);
    }

    #[test]
    fn exact_post_gap_position_observes_epoch_for_that_stream() {
        let (scope, surface, grant) = event_scope();
        let mut validator = Validator::new(false);
        validator.session_generation = 1;
        validator.session_state = "active".to_owned();
        check_event(
            &event_fixture("delivery_1", "event_1", 1, 1),
            0,
            &scope,
            &surface,
            &grant,
            &mut validator,
        )
        .unwrap();
        terminal_ack("delivery_1", "cursor_1", 1, &mut validator);
        check_gap(
            &serde_json::json!({
                "type":"event.gap",
                "payload":{
                    "subscription_id":"sub_1",
                    "last_accepted_cursor":"cursor_1",
                    "earliest_available_cursor":"cursor_2",
                    "reason":"retention_expired"
                }
            }),
            2,
            &mut validator,
        );
        check_event(
            &event_fixture("delivery_2", "event_2", 1, 2),
            3,
            &scope,
            &surface,
            &grant,
            &mut validator,
        )
        .unwrap();
        terminal_ack("delivery_2", "cursor_2", 4, &mut validator);
        check_event(
            &event_fixture("delivery_4", "event_4", 1, 4),
            5,
            &scope,
            &surface,
            &grant,
            &mut validator,
        )
        .unwrap();
        assert!(validator.diagnostics.iter().any(|diagnostic| {
            diagnostic.check_id == "ASP-REPLAY-DELIVERY-001" && diagnostic.severity == "error"
        }));
    }

    #[test]
    fn protocol_gap_does_not_cover_another_subscription_or_attempt_gap() {
        let (scope, surface, grant) = event_scope();
        let mut validator = Validator::new(false);
        validator.session_generation = 1;
        validator.session_state = "active".to_owned();
        check_gap(
            &serde_json::json!({
                "type":"event.gap",
                "payload":{
                    "subscription_id":"sub_1",
                    "last_accepted_cursor":"cursor_1",
                    "earliest_available_cursor":"cursor_2",
                    "reason":"retention_expired"
                }
            }),
            0,
            &mut validator,
        );
        check_event(
            &event_fixture_for("delivery_2", "event_2", 1, 2, "sub_2", "stream_1"),
            1,
            &scope,
            &surface,
            &grant,
            &mut validator,
        )
        .unwrap();
        check_event(
            &event_fixture("delivery_retry", "event_retry", 2, 1),
            2,
            &scope,
            &surface,
            &grant,
            &mut validator,
        )
        .unwrap();
        assert!(
            validator
                .finding_summaries
                .get("ASP-REPLAY-DELIVERY-001")
                .is_some_and(|summary| summary.errors == 2)
        );
    }

    #[test]
    fn pending_ack_known_only_later_is_invalid() {
        let (scope, surface, grant) = event_scope();
        let mut validator = Validator::new(false);
        validator.session_generation = 1;
        validator.session_state = "active".to_owned();
        terminal_ack("delivery_1", "cursor_1", 0, &mut validator);
        check_event(
            &event_fixture("delivery_1", "event_1", 1, 1),
            1,
            &scope,
            &surface,
            &grant,
            &mut validator,
        )
        .unwrap();
        reconcile_pending_references(&mut validator);
        assert!(validator.diagnostics.iter().any(|diagnostic| {
            diagnostic.check_id == "ASP-REPLAY-ACK-001"
                && diagnostic.severity == "error"
                && diagnostic.message.contains("later delivery")
        }));
    }

    fn receipt_projection_fixture(
        ordinal: usize,
        receipt_type: &str,
        action_id: &str,
    ) -> ReceiptProjection {
        ReceiptProjection {
            ordinal,
            receipt_type: receipt_type.to_owned(),
            grant_hash: "sha-256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA".to_owned(),
            surface_hash: "sha-256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB".to_owned(),
            surface_version: "2026-07-20".to_owned(),
            session_id: "sess_1".to_owned(),
            session_generation: 1,
            trace_id: "4bf92f3577b34da6a3ce929d0e0e4736".to_owned(),
            linked_trace_id: None,
            action_id: action_id.to_owned(),
            idempotency_key: "idem_1".to_owned(),
            input_hash: "sha-256:CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC".to_owned(),
            execution: Some(serde_json::json!({
                "mode":"commit",
                "execution_id":"exec_1"
            })),
            execution_hash: Some("sha-256:DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD".to_owned()),
            timestamp: "2026-07-20T10:00:00Z".to_owned(),
            result: "success".to_owned(),
            effect_outcome: None,
            actual_effect_ids: HashSet::new(),
            approval_role: None,
            approval_receipt_hashes: BTreeMap::new(),
            target_receipt_hash: None,
        }
    }

    #[test]
    fn receipt_parent_projection_rejects_invocation_and_trace_substitution() {
        let parent = receipt_projection_fixture(0, "runtime", "comment.create");
        let mut child = receipt_projection_fixture(1, "app", "comment.update");
        child.trace_id = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa".to_owned();
        let mut validator = Validator::new(false);
        validate_parent_projection(&child, &parent, &mut validator);
        assert!(
            validator
                .finding_summaries
                .get("ASP-REPLAY-RECEIPT-CHAIN-001")
                .is_some_and(|summary| summary.errors == 2)
        );
    }

    #[test]
    fn pending_receipt_references_known_only_later_are_invalid() {
        let parent_hash = "sha-256:EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE";
        let approval_hash = "sha-256:FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF";
        let mut validator = Validator::new(true);
        validator.validated_capture_gaps = 1;
        validator.pending_references.extend([
            PendingReference {
                check_id: "ASP-REPLAY-RECEIPT-CHAIN-001",
                ordinal: 1,
                path: "/records/1/body/parent_receipt_hash".to_owned(),
                target: parent_hash.to_owned(),
                kind: PendingReferenceKind::ReceiptParent,
            },
            PendingReference {
                check_id: "ASP-REPLAY-RECEIPT-LINK-001",
                ordinal: 2,
                path: "/records/2/body/approval_receipt_hashes/runtime".to_owned(),
                target: approval_hash.to_owned(),
                kind: PendingReferenceKind::ApprovalSideLink {
                    role: "runtime".to_owned(),
                },
            },
        ]);
        validator.receipts_by_hash.insert(
            parent_hash.to_owned(),
            receipt_projection_fixture(3, "runtime", "comment.create"),
        );
        validator.receipts_by_hash.insert(
            approval_hash.to_owned(),
            receipt_projection_fixture(4, "approval", "comment.create"),
        );
        reconcile_pending_references(&mut validator);
        assert_eq!(
            validator
                .diagnostics
                .iter()
                .filter(|diagnostic| {
                    diagnostic.severity == "error" && diagnostic.message.contains("later receipt")
                })
                .count(),
            2
        );
        assert!(
            !validator
                .diagnostics
                .iter()
                .any(|diagnostic| { diagnostic.severity == "incomplete" })
        );
    }

    #[test]
    fn approval_side_link_requires_approved_role_matched_invocation() {
        let source = receipt_projection_fixture(1, "app", "comment.create");
        let mut target = receipt_projection_fixture(0, "approval", "comment.create");
        target.result = "approved".to_owned();
        target.approval_role = Some("runtime".to_owned());
        let mut valid = Validator::new(false);
        validate_approval_target(&source, "runtime", &target, &mut valid);
        assert!(valid.diagnostics.is_empty());

        target.approval_role = Some("application".to_owned());
        target.input_hash = "sha-256:EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE".to_owned();
        let mut invalid = Validator::new(false);
        validate_approval_target(&source, "runtime", &target, &mut invalid);
        assert!(invalid.has_errors);
    }

    #[test]
    fn recovery_target_requires_exact_reciprocal_relationship() {
        let mut source = receipt_projection_fixture(2, "app", "payment.refund");
        source.execution = Some(serde_json::json!({
            "mode":"compensate",
            "execution_id":"exec_refund",
            "target_receipt_hash":"sha-256:FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
        }));
        source.target_receipt_hash =
            Some("sha-256:FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF".to_owned());
        source.timestamp = "2026-07-20T11:00:00Z".to_owned();
        let mut target = receipt_projection_fixture(0, "app", "payment.capture");
        target.effect_outcome = Some("applied".to_owned());
        target.actual_effect_ids.insert("charge".to_owned());
        let surface = serde_json::json!({
            "actions":[
                {
                    "id":"payment.capture",
                    "execution":{
                        "mode":"commit",
                        "operation_id":"payment.capture",
                        "recovery_actions":[{
                            "mode":"compensate",
                            "action_id":"payment.refund",
                            "effect_ids":["charge"],
                            "recovery_window_seconds":3600
                        }]
                    }
                },
                {
                    "id":"payment.refund",
                    "execution":{
                        "mode":"compensate",
                        "operation_id":"payment.capture",
                        "target_actions":[{
                            "action_id":"payment.capture",
                            "effect_ids":["charge"],
                            "recovery_window_seconds":3600
                        }]
                    }
                }
            ]
        });
        let mut valid = Validator::new(false);
        validate_recovery_target(&source, &target, &surface, &mut valid);
        assert!(valid.diagnostics.is_empty());

        let mut broken = surface.clone();
        broken["actions"][1]["execution"]["target_actions"][0]["recovery_window_seconds"] =
            Value::from(1800);
        let mut invalid = Validator::new(false);
        validate_recovery_target(&source, &target, &broken, &mut invalid);
        assert!(invalid.has_errors);

        let mut expired = source.clone();
        expired.timestamp = "2026-07-20T11:00:01Z".to_owned();
        let mut expired_validator = Validator::new(false);
        validate_recovery_target(&expired, &target, &surface, &mut expired_validator);
        assert!(
            expired_validator
                .diagnostics
                .iter()
                .any(|diagnostic| { diagnostic.message.contains("recovery window") })
        );

        let mut reversed = source;
        reversed.timestamp = "2026-07-20T09:59:59Z".to_owned();
        let mut reversed_validator = Validator::new(false);
        validate_recovery_target(&reversed, &target, &surface, &mut reversed_validator);
        assert!(
            reversed_validator
                .diagnostics
                .iter()
                .any(|diagnostic| { diagnostic.message.contains("recovery window") })
        );
    }

    fn approval_decision_fixture(
        role: &str,
        result: &str,
        decided_by: &str,
        outcome: &str,
        reason_code: &str,
        valid_until: Option<&str>,
    ) -> Value {
        let enforcer = if role == "runtime" {
            serde_json::json!({"type":"runtime","id":"runtime_456"})
        } else {
            serde_json::json!({"type":"application","id":"code.example.com"})
        };
        let mut approval = serde_json::json!({
            "approval_id":"approval_1",
            "role":role,
            "decided_by":decided_by
        });
        if let Some(valid_until) = valid_until {
            approval["valid_until"] = Value::String(valid_until.to_owned());
        }
        serde_json::json!({
            "action_id":"comment.create",
            "timestamp":"2026-07-20T10:00:00Z",
            "result":result,
            "approval":approval,
            "policy_decision":{
                "enforcer":enforcer,
                "outcome":outcome,
                "reason_code":reason_code,
                "evaluated_at":"2026-07-20T10:00:00Z"
            }
        })
    }

    fn approval_scope_and_grant(max_age_seconds: u64, expires_at: &str) -> (Value, Value) {
        (
            serde_json::json!({
                "runtime_id":"runtime_456",
                "app_id":"code.example.com"
            }),
            serde_json::json!({
                "constraints":{"expires_at":expires_at},
                "audit":{
                    "approval_receipt":{
                        "profile":"https://github.com/0al-spec/agent-surface/profiles/approval-receipt/v1",
                        "requirements":[{
                            "action_id":"comment.create",
                            "accepted_roles":["application","runtime"],
                            "max_age_seconds":max_age_seconds
                        }]
                    }
                }
            }),
        )
    }

    #[test]
    fn approval_decision_accepts_exact_six_row_semantics() {
        let (scope, grant) = approval_scope_and_grant(300, "2026-07-20T10:10:00Z");
        let rows = [
            ("runtime", "approved", "user", "allow", "approval_satisfied"),
            ("runtime", "denied", "user", "deny", "approval_denied"),
            ("runtime", "denied", "policy", "deny", "local_policy_denied"),
            (
                "application",
                "approved",
                "user",
                "allow",
                "approval_satisfied",
            ),
            ("application", "denied", "user", "deny", "approval_denied"),
            (
                "application",
                "denied",
                "policy",
                "deny",
                "app_policy_denied",
            ),
        ];
        for (ordinal, (role, result, decided_by, outcome, reason)) in rows.into_iter().enumerate() {
            let mut validator = Validator::new(false);
            validate_approval_decision(
                &approval_decision_fixture(
                    role,
                    result,
                    decided_by,
                    outcome,
                    reason,
                    (result == "approved").then_some("2026-07-20T10:04:59Z"),
                ),
                ordinal,
                &scope,
                &grant,
                &mut validator,
            );
            assert!(
                validator.diagnostics.is_empty(),
                "valid row {ordinal} produced {:?}",
                validator.diagnostics
            );
        }
    }

    #[test]
    fn approval_decision_rejects_denied_expiry_and_excessive_age() {
        let (scope, grant) = approval_scope_and_grant(300, "2026-07-20T10:03:00Z");
        let mut denied = Validator::new(false);
        validate_approval_decision(
            &approval_decision_fixture(
                "runtime",
                "denied",
                "user",
                "deny",
                "approval_denied",
                Some("2026-07-20T10:01:00Z"),
            ),
            0,
            &scope,
            &grant,
            &mut denied,
        );
        assert!(denied.has_errors);

        let mut approved = Validator::new(false);
        validate_approval_decision(
            &approval_decision_fixture(
                "application",
                "approved",
                "policy",
                "allow",
                "approval_satisfied",
                Some("2026-07-20T10:06:00Z"),
            ),
            0,
            &scope,
            &grant,
            &mut approved,
        );
        assert!(
            approved
                .finding_summaries
                .get("ASP-REPLAY-RECEIPT-LINK-001")
                .is_some_and(|summary| summary.errors >= 2)
        );

        let mut invalid_combination = Validator::new(false);
        validate_approval_decision(
            &approval_decision_fixture(
                "runtime",
                "approved",
                "policy",
                "allow",
                "approval_satisfied",
                Some("2026-07-20T10:01:00Z"),
            ),
            0,
            &scope,
            &grant,
            &mut invalid_combination,
        );
        assert!(invalid_combination.has_errors);
    }

    #[test]
    fn diagnostics_are_bounded_without_hiding_failure_state() {
        let mut validator = Validator::new(false);
        let long_path = format!("/{}", "x".repeat(MAX_DIAGNOSTIC_PATH_CHARS + 100));
        let long_message = "m".repeat(MAX_DIAGNOSTIC_MESSAGE_CHARS + 100);
        for ordinal in 0..(MAX_DIAGNOSTICS + 44) {
            validator.error("ASP-REPLAY-SCHEMA-001", ordinal, &long_path, &long_message);
        }
        assert!(validator.has_errors);
        assert_eq!(validator.diagnostics.len(), MAX_DIAGNOSTICS);
        assert_eq!(validator.diagnostics_omitted, 44);
        assert!(validator.diagnostics_truncated);
        assert_eq!(
            validator
                .finding_summaries
                .get("ASP-REPLAY-SCHEMA-001")
                .map(|summary| summary.errors),
            Some(MAX_DIAGNOSTICS + 44)
        );
        assert!(validator.diagnostics.iter().all(|diagnostic| {
            diagnostic.path.chars().count() <= MAX_DIAGNOSTIC_PATH_CHARS
                && diagnostic.path.starts_with('/')
                && !diagnostic.path.ends_with('~')
                && diagnostic.message.chars().count() <= MAX_DIAGNOSTIC_MESSAGE_CHARS
        }));
        assert_eq!(validator.diagnostics[0].path, "/<truncated>");
    }

    #[test]
    fn preflight_report_nulls_noncanonical_input_identity() {
        let mut bundle =
            parse_strict(include_bytes!("../tests/fixtures/complete-session.json")).unwrap();
        bundle["bundle_id"] = Value::String("x".repeat(257));
        bundle["bundle_hash"] = Value::String("not-a-digest".to_owned());
        let bytes = serde_json::to_vec(&bundle).unwrap();
        let report = verify("invalid-identity", &bytes).unwrap();
        assert_eq!(report.evaluation_state, "preflight_failed");
        assert_eq!(report.input.bundle_id, None);
        assert_eq!(report.input.bundle_hash, None);
        let schema: Value = serde_json::from_str(REPORT_SCHEMA).unwrap();
        validate_instance(
            &schema,
            &serde_json::to_value(report).unwrap(),
            "preflight report",
        )
        .unwrap();
    }

    #[test]
    fn retained_diagnostics_and_omission_count_account_for_every_finding() {
        let report = verify(
            "invalid-empty",
            include_bytes!("../tests/fixtures/invalid-empty.json"),
        )
        .unwrap();
        let findings: usize = report.checks.iter().map(|check| check.findings).sum();
        assert_eq!(
            findings,
            report.diagnostics.len() + report.diagnostics_omitted
        );
        assert!(
            report
                .diagnostics
                .iter()
                .any(|diagnostic| diagnostic.path.is_empty())
        );
    }

    #[test]
    fn report_schema_rejects_a_truncated_or_fabricated_check_profile() {
        let report_schema: Value = serde_json::from_str(REPORT_SCHEMA).unwrap();
        let report = verify(
            "complete-session",
            include_bytes!("../tests/fixtures/complete-session.json"),
        )
        .unwrap();
        let mut value = serde_json::to_value(report).unwrap();
        value["checks"].as_array_mut().unwrap().truncate(1);
        assert!(validate_instance(&report_schema, &value, "truncated report").is_err());
    }

    #[test]
    fn report_schema_rejects_unknown_diagnostic_checks_and_invalid_json_pointers() {
        let report_schema: Value = serde_json::from_str(REPORT_SCHEMA).unwrap();
        let report = verify(
            "invalid-empty",
            include_bytes!("../tests/fixtures/invalid-empty.json"),
        )
        .unwrap();
        let value = serde_json::to_value(report).unwrap();

        let mut unknown_check = value.clone();
        unknown_check["diagnostics"][0]["check_id"] =
            Value::String("ASP-REPLAY-UNKNOWN-001".to_owned());
        assert!(
            validate_instance(&report_schema, &unknown_check, "unknown diagnostic check").is_err()
        );

        for invalid_path in ["not/a/pointer", "/~2bad"] {
            let mut bad_pointer = value.clone();
            bad_pointer["diagnostics"][0]["path"] = Value::String(invalid_path.to_owned());
            assert!(
                validate_instance(&report_schema, &bad_pointer, "invalid diagnostic path").is_err(),
                "invalid RFC 6901 diagnostic path {invalid_path:?} must be rejected"
            );
        }
    }

    #[test]
    fn case_schema_rejects_an_impossible_report_truth_tuple() {
        let cases_schema: Value = serde_json::from_str(CASES_SCHEMA).unwrap();
        let mut cases = parse_strict(CASE_REGISTRY.as_bytes()).unwrap();
        let first = &mut cases["cases"][0];
        first["integrity_verdict"] = Value::String("invalid".to_owned());
        first["replay_completeness"] = Value::String("not_evaluated".to_owned());
        first["verdict"] = Value::String("incomplete".to_owned());
        assert!(validate_instance(&cases_schema, &cases, "impossible case tuple").is_err());
    }
}
