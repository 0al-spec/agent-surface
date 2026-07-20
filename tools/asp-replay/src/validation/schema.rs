use std::sync::OnceLock;

use serde_json::Value;

use crate::{BUNDLE_SCHEMA, ReplayError};

use super::state::Validator;

static BUNDLE_SCHEMA_VALIDATOR: OnceLock<Result<jsonschema::Validator, String>> = OnceLock::new();

fn bundle_schema_validator() -> Result<&'static jsonschema::Validator, ReplayError> {
    BUNDLE_SCHEMA_VALIDATOR
        .get_or_init(|| {
            let schema: Value = serde_json::from_str(BUNDLE_SCHEMA)
                .map_err(|error| format!("bundle schema: {error}"))?;
            jsonschema::draft202012::options()
                .should_validate_formats(true)
                .build(&schema)
                .map_err(|error| format!("bundle schema: {error}"))
        })
        .as_ref()
        .map_err(|error| ReplayError::SelfCheck(error.clone()))
}

pub(super) fn validate_schema(
    bundle: &Value,
    validator: &mut Validator,
) -> Result<(), ReplayError> {
    for error in bundle_schema_validator()?.iter_errors(bundle) {
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
