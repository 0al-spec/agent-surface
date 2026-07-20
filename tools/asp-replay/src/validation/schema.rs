use serde_json::Value;

use crate::{BUNDLE_SCHEMA, ReplayError};

use super::state::Validator;

pub(super) fn validate_schema(
    bundle: &Value,
    validator: &mut Validator,
) -> Result<(), ReplayError> {
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
