//! Deterministic, offline consistency replay for portable ASP evidence bundles.

use std::path::Path;

use serde::Serialize;
use thiserror::Error;

mod hash;
mod registry;
mod rehash;
mod selfcheck;
mod specifications;
mod strict_json;
mod validation;
mod value;

#[cfg(fuzzing)]
#[doc(hidden)]
pub mod fuzz_support;

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

/// Verify one exact replay bundle and produce a deterministic, payload-minimized report.
pub fn verify(source: &str, document: &[u8]) -> Result<Report, ReplayError> {
    validation::verify_document(source, document)
}

/// Verify all embedded artifacts and execute every registered fixture/golden case.
pub fn self_check(repository_root: &Path) -> Result<(), ReplayError> {
    selfcheck::run(repository_root)
}
