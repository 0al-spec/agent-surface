use serde_json::Value;

use super::state::Validator;

pub(super) fn scan_secrets(value: &Value, path: &str, ordinal: usize, validator: &mut Validator) {
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
