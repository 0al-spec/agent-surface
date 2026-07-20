use std::sync::OnceLock;

use serde::Deserialize;

use crate::{CHECK_REGISTRY, ReplayError};

pub(crate) const IMPLEMENTED_CHECKS: [&str; 12] = [
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

#[derive(Clone, Debug, Deserialize)]
pub(crate) struct CheckRegistry {
    pub(crate) schema_version: u64,
    pub(crate) profile: String,
    pub(crate) version: String,
    pub(crate) checks: Vec<CheckDefinition>,
}

#[derive(Clone, Debug, Deserialize)]
pub(crate) struct CheckDefinition {
    pub(crate) check_id: String,
    pub(crate) title: String,
}

static CHECK_REGISTRY_CACHE: OnceLock<Result<CheckRegistry, String>> = OnceLock::new();

pub(crate) fn registry() -> Result<&'static CheckRegistry, ReplayError> {
    CHECK_REGISTRY_CACHE
        .get_or_init(|| {
            serde_json::from_str(CHECK_REGISTRY).map_err(|error| format!("check registry: {error}"))
        })
        .as_ref()
        .map_err(|error| ReplayError::SelfCheck(error.clone()))
}
