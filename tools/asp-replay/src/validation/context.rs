use serde_json::Value;

use crate::ReplayError;
use crate::hash::{GRANT_DOMAIN, MANIFEST_DOMAIN, object_hash};
use crate::value::{member, string};

use super::state::Validator;

pub(super) fn check_context(bundle: &Value, validator: &mut Validator) -> Result<(), ReplayError> {
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
