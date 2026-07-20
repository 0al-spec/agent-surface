use serde_json::Value;
use specification_core::Specification;

use crate::specifications::RequiredMembers;

use super::state::Validator;

pub(super) fn require_members(
    value: &Value,
    required: &[&str],
    check: &str,
    ordinal: usize,
    path: &str,
    message: &str,
    validator: &mut Validator,
) -> bool {
    if RequiredMembers::new(required).is_satisfied_by(value) {
        return true;
    }
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
