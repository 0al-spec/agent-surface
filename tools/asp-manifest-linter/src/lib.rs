//! Fail-closed ASP manifest parsing, linting, reporting, and self-validation.

use std::collections::{HashMap, HashSet};
use std::fmt;
use std::fs;
use std::path::Path;

use fluent_uri::Uri;
use serde::de::{self, Deserializer, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use thiserror::Error;

pub const TOOL_NAME: &str = "asp-manifest-linter";
pub const TOOL_VERSION: &str = env!("CARGO_PKG_VERSION");
pub const RULE_SCHEMA: &str = include_str!("../schema/rules.schema.json");
pub const DIAGNOSTICS_SCHEMA: &str = include_str!("../schema/diagnostics.schema.json");
pub const RULE_REGISTRY: &str = include_str!("../rules/v1/rules.json");

pub const RULE_SCHEMA_DECLARATION: &str = "ASP-LINT-SCHEMA-001";
pub const RULE_RISK_LABEL: &str = "ASP-LINT-RISK-001";
pub const RULE_RISK_EXPLANATION: &str = "ASP-LINT-RISK-EXPLANATION-001";
pub const RULE_IDEMPOTENCY: &str = "ASP-LINT-IDEMPOTENCY-001";
pub const RULE_SCOPE: &str = "ASP-LINT-SCOPE-001";

const SAFE_INTEGER: i128 = (1_i128 << 53) - 1;
const CORE_RISK_LABELS: [&str; 8] = [
    "read",
    "propose",
    "write",
    "public_side_effect",
    "external_side_effect",
    "financial_side_effect",
    "destructive",
    "privileged",
];
const LANGUAGE_TAG_PATTERN: &str =
    "^[a-z]{2,8}(?:-[a-z]{4})?(?:-(?:[a-z]{2}|[0-9]{3}))?(?:-(?:[a-z0-9]{5,8}|[0-9][a-z0-9]{3}))*$";
const IMPLEMENTED_RULES: [&str; 5] = [
    RULE_SCHEMA_DECLARATION,
    RULE_RISK_LABEL,
    RULE_RISK_EXPLANATION,
    RULE_IDEMPOTENCY,
    RULE_SCOPE,
];

#[derive(Debug, Error)]
pub enum LintError {
    #[error("strict JSON parse failed: {0}")]
    StrictJson(String),
    #[error("manifest structure is invalid: {0}")]
    Structure(String),
    #[error("rule registry is invalid: {0}")]
    Registry(String),
    #[error("self-check failed: {0}")]
    SelfCheck(String),
    #[error("cannot read {path}: {source}")]
    Io {
        path: String,
        #[source]
        source: std::io::Error,
    },
}

#[derive(Clone, Debug)]
struct StrictValue(Value);

struct StrictVisitor;

impl<'de> Visitor<'de> for StrictVisitor {
    type Value = StrictValue;

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("strict I-JSON without duplicate members or floats")
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

    fn visit_f64<E>(self, _value: f64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Err(E::custom("floating-point values are forbidden"))
    }

    fn visit_str<E>(self, value: &str) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(StrictValue(Value::String(value.to_owned())))
    }

    fn visit_string<E>(self, value: String) -> Result<Self::Value, E> {
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

pub fn parse_strict_json(document: &str) -> Result<Value, LintError> {
    let mut deserializer = serde_json::Deserializer::from_str(document);
    let value = StrictValue::deserialize(&mut deserializer)
        .map_err(|error| LintError::StrictJson(error.to_string()))?
        .0;
    deserializer
        .end()
        .map_err(|error| LintError::StrictJson(error.to_string()))?;
    if !value.is_object() {
        return Err(LintError::Structure(
            "manifest root must be a JSON object".to_owned(),
        ));
    }
    Ok(value)
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum Severity {
    Error,
    Warning,
}

#[derive(Clone, Debug, Deserialize)]
pub struct RuleDefinition {
    pub rule_id: String,
    pub title: String,
    pub severity: Severity,
    pub rfc_anchor: String,
    pub help: String,
}

#[derive(Clone, Debug, Deserialize)]
struct RuleRegistry {
    schema_version: u64,
    ruleset_id: String,
    ruleset_version: String,
    rules: Vec<RuleDefinition>,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct Diagnostic {
    pub rule_id: String,
    pub severity: Severity,
    pub path: String,
    pub message: String,
    pub help: String,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct ToolDescriptor {
    pub name: String,
    pub version: String,
    pub ruleset_id: String,
    pub ruleset_version: String,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct InputDescriptor {
    pub source: String,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct Summary {
    pub errors: usize,
    pub warnings: usize,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct LintReport {
    #[serde(rename = "$schema")]
    pub schema: String,
    pub schema_version: u64,
    pub tool: ToolDescriptor,
    pub input: InputDescriptor,
    pub summary: Summary,
    pub diagnostics: Vec<Diagnostic>,
}

fn registry() -> Result<RuleRegistry, LintError> {
    let value = parse_strict_json(RULE_REGISTRY)?;
    serde_json::from_value(value).map_err(|error| LintError::Registry(error.to_string()))
}

struct Context<'a> {
    rules: HashMap<&'a str, &'a RuleDefinition>,
    diagnostics: Vec<Diagnostic>,
}

impl<'a> Context<'a> {
    fn new(registry: &'a RuleRegistry) -> Self {
        Self {
            rules: registry
                .rules
                .iter()
                .map(|rule| (rule.rule_id.as_str(), rule))
                .collect(),
            diagnostics: Vec::new(),
        }
    }

    fn emit(&mut self, rule_id: &str, path: String, message: impl Into<String>) {
        let rule = self
            .rules
            .get(rule_id)
            .expect("implemented rule must exist in validated registry");
        self.diagnostics.push(Diagnostic {
            rule_id: rule_id.to_owned(),
            severity: rule.severity.clone(),
            path,
            message: message.into(),
            help: rule.help.clone(),
        });
    }
}

fn required_array<'a>(manifest: &'a Value, name: &str) -> Result<&'a Vec<Value>, LintError> {
    manifest
        .get(name)
        .and_then(Value::as_array)
        .ok_or_else(|| LintError::Structure(format!("/{name} must be an array")))
}

fn required_object<'a>(value: &'a Value, path: &str) -> Result<&'a Map<String, Value>, LintError> {
    value
        .as_object()
        .ok_or_else(|| LintError::Structure(format!("{path} must be an object")))
}

fn has_nonempty_string(object: &Map<String, Value>, member: &str) -> bool {
    object
        .get(member)
        .and_then(Value::as_str)
        .is_some_and(|value| !value.is_empty())
}

fn lint_schema_declarations(manifest: &Value, context: &mut Context<'_>) -> Result<(), LintError> {
    for (index, resource) in required_array(manifest, "resources")?.iter().enumerate() {
        let object = required_object(resource, &format!("/resources/{index}"))?;
        if !has_nonempty_string(object, "schema") {
            context.emit(
                RULE_SCHEMA_DECLARATION,
                format!("/resources/{index}/schema"),
                "resource must declare a non-empty schema URI",
            );
        }
    }
    for (index, action) in required_array(manifest, "actions")?.iter().enumerate() {
        let object = required_object(action, &format!("/actions/{index}"))?;
        for member in ["input_schema", "output_schema"] {
            if !has_nonempty_string(object, member) {
                context.emit(
                    RULE_SCHEMA_DECLARATION,
                    format!("/actions/{index}/{member}"),
                    format!("action must declare a non-empty {member}"),
                );
            }
        }
    }
    for (index, event) in required_array(manifest, "events")?.iter().enumerate() {
        let object = required_object(event, &format!("/events/{index}"))?;
        if !has_nonempty_string(object, "schema") {
            context.emit(
                RULE_SCHEMA_DECLARATION,
                format!("/events/{index}/schema"),
                "event must declare a non-empty schema URI",
            );
        }
    }
    Ok(())
}

fn is_absolute_risk_uri(value: &str) -> bool {
    value.is_ascii()
        && value
            .split_once(':')
            .is_some_and(|(_, remainder)| !remainder.is_empty())
        && Uri::parse(value).is_ok()
}

fn is_valid_risk_label(value: &str) -> bool {
    CORE_RISK_LABELS.contains(&value) || is_absolute_risk_uri(value)
}

fn lint_risk_labels(manifest: &Value, context: &mut Context<'_>) -> Result<(), LintError> {
    for (index, action) in required_array(manifest, "actions")?.iter().enumerate() {
        let object = required_object(action, &format!("/actions/{index}"))?;
        if !object
            .get("risk")
            .and_then(Value::as_str)
            .is_some_and(is_valid_risk_label)
        {
            context.emit(
                RULE_RISK_LABEL,
                format!("/actions/{index}/risk"),
                "risk must be one of the eight core labels or a non-empty ASCII RFC 3986 URI",
            );
        }
    }
    Ok(())
}

fn json_pointer_token(value: &str) -> String {
    value.replace('~', "~0").replace('/', "~1")
}

fn lint_closed_object(
    object: &Map<String, Value>,
    allowed: &[&str],
    path: &str,
    context: &mut Context<'_>,
) {
    for member in object.keys() {
        if !allowed.contains(&member.as_str()) {
            context.emit(
                RULE_RISK_EXPLANATION,
                format!("{path}/{}", json_pointer_token(member)),
                format!("risk explanation object member {member:?} is not allowed"),
            );
        }
    }
}

fn is_canonical_language_tag(value: &str) -> bool {
    if value.len() > 63 {
        return false;
    }
    let subtags: Vec<&str> = value.split('-').collect();
    let Some(primary) = subtags.first() else {
        return false;
    };
    if !(2..=8).contains(&primary.len()) || !primary.bytes().all(|byte| byte.is_ascii_lowercase()) {
        return false;
    }
    let mut index = 1;
    if subtags.get(index).is_some_and(|subtag| {
        subtag.len() == 4 && subtag.bytes().all(|byte| byte.is_ascii_lowercase())
    }) {
        index += 1;
    }
    if subtags.get(index).is_some_and(|subtag| {
        (subtag.len() == 2 && subtag.bytes().all(|byte| byte.is_ascii_lowercase()))
            || (subtag.len() == 3 && subtag.bytes().all(|byte| byte.is_ascii_digit()))
    }) {
        index += 1;
    }
    let mut variants = HashSet::new();
    subtags[index..].iter().all(|subtag| {
        (((5..=8).contains(&subtag.len())
            && subtag
                .bytes()
                .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit()))
            || (subtag.len() == 4
                && subtag.as_bytes()[0].is_ascii_digit()
                && subtag
                    .bytes()
                    .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit())))
            && variants.insert(*subtag)
    })
}

fn is_forbidden_explanation_control(character: char) -> bool {
    matches!(
        character as u32,
        0x00..=0x1f
            | 0x7f..=0x9f
            | 0x061c
            | 0x200e
            | 0x200f
            | 0x202a..=0x202e
            | 0x2066..=0x2069
    )
}

fn lint_explanation_text(
    value: Option<&Value>,
    path: String,
    label: &str,
    context: &mut Context<'_>,
) {
    let Some(text) = value.and_then(Value::as_str) else {
        context.emit(
            RULE_RISK_EXPLANATION,
            path,
            format!("{label} must be a string"),
        );
        return;
    };
    let length = text.chars().count();
    if !(1..=512).contains(&length) {
        context.emit(
            RULE_RISK_EXPLANATION,
            path.clone(),
            format!("{label} must contain 1 to 512 Unicode code points"),
        );
    }
    if text.chars().any(is_forbidden_explanation_control) {
        context.emit(
            RULE_RISK_EXPLANATION,
            path,
            format!("{label} must not contain C0, C1, or Unicode Bidi_Control characters"),
        );
    }
}

fn parent_effect_ids<'a>(
    action: &'a Map<String, Value>,
    action_index: usize,
    context: &mut Context<'_>,
) -> Option<Vec<&'a str>> {
    let Some(effects) = action.get("effects") else {
        return Some(Vec::new());
    };
    let Some(effects) = effects.as_array() else {
        context.emit(
            RULE_RISK_EXPLANATION,
            format!("/actions/{action_index}/effects"),
            "effects must be an array when risk_explanation is present",
        );
        return None;
    };
    let mut effect_ids = Vec::with_capacity(effects.len());
    let mut seen = HashSet::new();
    let mut valid = true;
    for (effect_index, effect) in effects.iter().enumerate() {
        let path = format!("/actions/{action_index}/effects/{effect_index}");
        let Some(object) = effect.as_object() else {
            context.emit(
                RULE_RISK_EXPLANATION,
                path,
                "effect must be an object when risk_explanation is present",
            );
            valid = false;
            continue;
        };
        let Some(effect_id) = object.get("effect_id").and_then(Value::as_str) else {
            context.emit(
                RULE_RISK_EXPLANATION,
                format!("{path}/effect_id"),
                "effect_id must be a non-empty string when risk_explanation is present",
            );
            valid = false;
            continue;
        };
        if effect_id.is_empty() {
            context.emit(
                RULE_RISK_EXPLANATION,
                format!("{path}/effect_id"),
                "effect_id must be a non-empty string when risk_explanation is present",
            );
            valid = false;
            continue;
        }
        if !seen.insert(effect_id) {
            context.emit(
                RULE_RISK_EXPLANATION,
                format!("{path}/effect_id"),
                format!("effect_id {effect_id:?} is declared more than once"),
            );
            valid = false;
        }
        effect_ids.push(effect_id);
    }
    valid.then_some(effect_ids)
}

fn lint_effect_summaries(
    value: Option<&Value>,
    path: &str,
    expected_effect_ids: Option<&[&str]>,
    context: &mut Context<'_>,
) {
    let Some(effect_summaries) = value.and_then(Value::as_array) else {
        context.emit(
            RULE_RISK_EXPLANATION,
            path.to_owned(),
            "effect_summaries must be an array",
        );
        return;
    };
    let mut actual_effect_ids = Vec::with_capacity(effect_summaries.len());
    let mut structurally_valid = true;
    for (effect_index, effect_summary) in effect_summaries.iter().enumerate() {
        let effect_path = format!("{path}/{effect_index}");
        let Some(object) = effect_summary.as_object() else {
            context.emit(
                RULE_RISK_EXPLANATION,
                effect_path,
                "effect summary must be an object",
            );
            structurally_valid = false;
            continue;
        };
        lint_closed_object(object, &["effect_id", "summary"], &effect_path, context);
        match object.get("effect_id").and_then(Value::as_str) {
            Some(effect_id) if !effect_id.is_empty() => actual_effect_ids.push(effect_id),
            _ => {
                context.emit(
                    RULE_RISK_EXPLANATION,
                    format!("{effect_path}/effect_id"),
                    "effect summary effect_id must be a non-empty string",
                );
                structurally_valid = false;
            }
        }
        lint_explanation_text(
            object.get("summary"),
            format!("{effect_path}/summary"),
            "effect summary",
            context,
        );
    }
    if structurally_valid
        && expected_effect_ids.is_some_and(|expected| actual_effect_ids.as_slice() != expected)
    {
        context.emit(
            RULE_RISK_EXPLANATION,
            path.to_owned(),
            "effect_summaries must cover each parent action effect_id exactly once and in declaration order",
        );
    }
}

fn lint_risk_explanations(manifest: &Value, context: &mut Context<'_>) -> Result<(), LintError> {
    for (action_index, action) in required_array(manifest, "actions")?.iter().enumerate() {
        let action = required_object(action, &format!("/actions/{action_index}"))?;
        let Some(explanation) = action.get("risk_explanation") else {
            continue;
        };
        let explanation_path = format!("/actions/{action_index}/risk_explanation");
        let Some(explanation) = explanation.as_object() else {
            context.emit(
                RULE_RISK_EXPLANATION,
                explanation_path,
                "risk_explanation must be an object",
            );
            continue;
        };
        lint_closed_object(
            explanation,
            &["default_language", "localizations"],
            &explanation_path,
            context,
        );

        let default_language = match explanation.get("default_language").and_then(Value::as_str) {
            Some(language) if is_canonical_language_tag(language) => Some(language),
            _ => {
                context.emit(
                    RULE_RISK_EXPLANATION,
                    format!("{explanation_path}/default_language"),
                    format!(
                        "default_language must match {LANGUAGE_TAG_PATTERN}, contain unique variant subtags, and be at most 63 characters"
                    ),
                );
                None
            }
        };
        let Some(localizations) = explanation.get("localizations").and_then(Value::as_array) else {
            context.emit(
                RULE_RISK_EXPLANATION,
                format!("{explanation_path}/localizations"),
                "localizations must be an array",
            );
            continue;
        };
        if !(1..=16).contains(&localizations.len()) {
            context.emit(
                RULE_RISK_EXPLANATION,
                format!("{explanation_path}/localizations"),
                "localizations must contain 1 to 16 entries",
            );
        }

        let expected_effect_ids = parent_effect_ids(action, action_index, context);
        let mut languages = Vec::with_capacity(localizations.len());
        let mut seen_languages = HashSet::new();
        let mut previous_language: Option<&str> = None;
        for (localization_index, localization) in localizations.iter().enumerate() {
            let localization_path =
                format!("{explanation_path}/localizations/{localization_index}");
            let Some(localization) = localization.as_object() else {
                context.emit(
                    RULE_RISK_EXPLANATION,
                    localization_path,
                    "localization must be an object",
                );
                continue;
            };
            lint_closed_object(
                localization,
                &["language", "summary", "effect_summaries"],
                &localization_path,
                context,
            );
            match localization.get("language").and_then(Value::as_str) {
                Some(language) if is_canonical_language_tag(language) => {
                    if !seen_languages.insert(language) {
                        context.emit(
                            RULE_RISK_EXPLANATION,
                            format!("{localization_path}/language"),
                            format!("language {language:?} is declared more than once"),
                        );
                    }
                    if previous_language.is_some_and(|previous| previous > language) {
                        context.emit(
                            RULE_RISK_EXPLANATION,
                            format!("{localization_path}/language"),
                            "localizations must be sorted lexicographically by language",
                        );
                    }
                    previous_language = Some(language);
                    languages.push(language);
                }
                _ => context.emit(
                    RULE_RISK_EXPLANATION,
                    format!("{localization_path}/language"),
                    format!(
                        "language must match {LANGUAGE_TAG_PATTERN}, contain unique variant subtags, and be at most 63 characters"
                    ),
                ),
            }
            lint_explanation_text(
                localization.get("summary"),
                format!("{localization_path}/summary"),
                "localization summary",
                context,
            );
            lint_effect_summaries(
                localization.get("effect_summaries"),
                &format!("{localization_path}/effect_summaries"),
                expected_effect_ids.as_deref(),
                context,
            );
        }
        if default_language.is_some_and(|default| !languages.contains(&default)) {
            context.emit(
                RULE_RISK_EXPLANATION,
                format!("{explanation_path}/default_language"),
                "default_language must exactly match one localization language",
            );
        }
    }
    Ok(())
}

fn lint_idempotency(manifest: &Value, context: &mut Context<'_>) -> Result<(), LintError> {
    const STATE_CHANGING_MODES: [&str; 4] = ["reserve", "commit", "compensate", "revert"];
    for (index, action) in required_array(manifest, "actions")?.iter().enumerate() {
        let object = required_object(action, &format!("/actions/{index}"))?;
        let execution = object.get("execution").and_then(Value::as_object);
        let mode = execution
            .and_then(|value| value.get("mode"))
            .and_then(Value::as_str);
        let persisted_proposal = mode == Some("propose")
            && execution
                .and_then(|value| value.get("persisted"))
                .and_then(Value::as_bool)
                == Some(true);
        let requires_idempotency = object.get("side_effect").and_then(Value::as_bool) == Some(true)
            || mode.is_some_and(|value| STATE_CHANGING_MODES.contains(&value))
            || persisted_proposal;
        if !requires_idempotency {
            continue;
        }
        if object.get("idempotency").and_then(Value::as_str) != Some("required") {
            context.emit(
                RULE_IDEMPOTENCY,
                format!("/actions/{index}/idempotency"),
                "state-changing or persisted proposal action requires idempotency",
            );
        }
        let normalization_profile = object
            .get("idempotency_normalization")
            .and_then(Value::as_object)
            .and_then(|value| value.get("profile"))
            .and_then(Value::as_str);
        if normalization_profile != Some("asp-json-normalization-v1") {
            context.emit(
                RULE_IDEMPOTENCY,
                format!("/actions/{index}/idempotency_normalization/profile"),
                "idempotency normalization profile must be asp-json-normalization-v1",
            );
        }
        if object.get("input_hash_profile").and_then(Value::as_str) != Some("asp-jcs-sha-256") {
            context.emit(
                RULE_IDEMPOTENCY,
                format!("/actions/{index}/input_hash_profile"),
                "idempotency-required action must use asp-jcs-sha-256 input hashing",
            );
        }
        if !has_nonempty_string(object, "input_schema_hash") {
            context.emit(
                RULE_IDEMPOTENCY,
                format!("/actions/{index}/input_schema_hash"),
                "idempotency-required action must publish input_schema_hash",
            );
        }
    }
    Ok(())
}

fn check_scope_reference(
    context: &mut Context<'_>,
    declared: &HashSet<&str>,
    object: &Map<String, Value>,
    member: &str,
    path: String,
) {
    match object.get(member).and_then(Value::as_str) {
        Some(scope) if !scope.is_empty() && declared.contains(scope) => {}
        Some(scope) if !scope.is_empty() => context.emit(
            RULE_SCOPE,
            path,
            format!("scope {scope:?} is not declared in /scopes"),
        ),
        _ => context.emit(RULE_SCOPE, path, "scope reference must be non-empty"),
    }
}

fn lint_scopes(manifest: &Value, context: &mut Context<'_>) -> Result<(), LintError> {
    let scopes = required_array(manifest, "scopes")?;
    let mut declared = HashSet::new();
    for (index, scope) in scopes.iter().enumerate() {
        let object = required_object(scope, &format!("/scopes/{index}"))?;
        match object.get("id").and_then(Value::as_str) {
            Some(id) if !id.is_empty() && declared.insert(id) => {}
            Some(id) if !id.is_empty() => context.emit(
                RULE_SCOPE,
                format!("/scopes/{index}/id"),
                format!("scope id {id:?} is declared more than once"),
            ),
            _ => context.emit(
                RULE_SCOPE,
                format!("/scopes/{index}/id"),
                "scope id must be non-empty",
            ),
        }
    }
    for (index, resource) in required_array(manifest, "resources")?.iter().enumerate() {
        let object = required_object(resource, &format!("/resources/{index}"))?;
        check_scope_reference(
            context,
            &declared,
            object,
            "read_scope",
            format!("/resources/{index}/read_scope"),
        );
    }
    for (index, action) in required_array(manifest, "actions")?.iter().enumerate() {
        let object = required_object(action, &format!("/actions/{index}"))?;
        check_scope_reference(
            context,
            &declared,
            object,
            "scope",
            format!("/actions/{index}/scope"),
        );
    }
    for (index, event) in required_array(manifest, "events")?.iter().enumerate() {
        let object = required_object(event, &format!("/events/{index}"))?;
        let is_control = object.get("control").and_then(Value::as_bool) == Some(true);
        if is_control {
            if object.contains_key("scope") {
                context.emit(
                    RULE_SCOPE,
                    format!("/events/{index}/scope"),
                    "control event must omit scope",
                );
            }
        } else {
            check_scope_reference(
                context,
                &declared,
                object,
                "scope",
                format!("/events/{index}/scope"),
            );
        }
    }
    Ok(())
}

pub fn lint_manifest(source: &str, document: &str) -> Result<LintReport, LintError> {
    let manifest = parse_strict_json(document)?;
    let registry = registry()?;
    let mut context = Context::new(&registry);
    lint_schema_declarations(&manifest, &mut context)?;
    lint_risk_labels(&manifest, &mut context)?;
    lint_risk_explanations(&manifest, &mut context)?;
    lint_idempotency(&manifest, &mut context)?;
    lint_scopes(&manifest, &mut context)?;
    let errors = context
        .diagnostics
        .iter()
        .filter(|item| item.severity == Severity::Error)
        .count();
    let warnings = context.diagnostics.len() - errors;
    Ok(LintReport {
        schema:
            "https://github.com/0al-spec/agent-surface/tools/asp-manifest-linter/diagnostics/v1"
                .to_owned(),
        schema_version: 1,
        tool: ToolDescriptor {
            name: TOOL_NAME.to_owned(),
            version: TOOL_VERSION.to_owned(),
            ruleset_id: registry.ruleset_id.clone(),
            ruleset_version: registry.ruleset_version.clone(),
        },
        input: InputDescriptor {
            source: source.to_owned(),
        },
        summary: Summary { errors, warnings },
        diagnostics: context.diagnostics,
    })
}

pub fn render_text(report: &LintReport) -> String {
    if report.diagnostics.is_empty() {
        return format!("{}: no findings\n", report.input.source);
    }
    let mut output = String::new();
    for diagnostic in &report.diagnostics {
        let severity = match diagnostic.severity {
            Severity::Error => "error",
            Severity::Warning => "warning",
        };
        output.push_str(&format!(
            "{}{}: {} [{}] {}\n  help: {}\n",
            report.input.source,
            diagnostic.path,
            severity,
            diagnostic.rule_id,
            diagnostic.message,
            diagnostic.help
        ));
    }
    output.push_str(&format!(
        "{} finding(s): {} error(s), {} warning(s)\n",
        report.diagnostics.len(),
        report.summary.errors,
        report.summary.warnings
    ));
    output
}

fn validate_instance(schema: &Value, instance: &Value, label: &str) -> Result<(), LintError> {
    let validator = jsonschema::validator_for(schema)
        .map_err(|error| LintError::SelfCheck(format!("{label} schema: {error}")))?;
    let errors: Vec<String> = validator
        .iter_errors(instance)
        .map(|error| error.to_string())
        .collect();
    if errors.is_empty() {
        Ok(())
    } else {
        Err(LintError::SelfCheck(format!(
            "{label} validation: {}",
            errors.join("; ")
        )))
    }
}

pub fn self_check(repository_root: &Path) -> Result<(), LintError> {
    let crate_root = repository_root.join("tools/asp-manifest-linter");
    let artifacts = [
        (crate_root.join("schema/rules.schema.json"), RULE_SCHEMA),
        (
            crate_root.join("schema/diagnostics.schema.json"),
            DIAGNOSTICS_SCHEMA,
        ),
        (crate_root.join("rules/v1/rules.json"), RULE_REGISTRY),
    ];
    for (path, embedded) in &artifacts {
        let source = fs::read_to_string(path).map_err(|source| LintError::Io {
            path: path.display().to_string(),
            source,
        })?;
        if source != *embedded {
            return Err(LintError::SelfCheck(format!(
                "compiled artifact differs from {}",
                path.display()
            )));
        }
    }
    let rule_schema = parse_strict_json(RULE_SCHEMA)?;
    let diagnostics_schema = parse_strict_json(DIAGNOSTICS_SCHEMA)?;
    let registry_value = parse_strict_json(RULE_REGISTRY)?;
    validate_instance(&rule_schema, &registry_value, "rule registry")?;
    let registry = registry()?;
    if registry.schema_version != 1 {
        return Err(LintError::SelfCheck(
            "rule registry schema_version must be 1".to_owned(),
        ));
    }
    let actual: HashSet<&str> = registry
        .rules
        .iter()
        .map(|rule| rule.rule_id.as_str())
        .collect();
    let expected: HashSet<&str> = IMPLEMENTED_RULES.into_iter().collect();
    if actual != expected || actual.len() != registry.rules.len() {
        return Err(LintError::SelfCheck(
            "rule registry must exactly match implemented rule IDs".to_owned(),
        ));
    }
    if registry
        .rules
        .iter()
        .any(|rule| rule.title.is_empty() || rule.rfc_anchor.is_empty() || rule.help.is_empty())
    {
        return Err(LintError::SelfCheck(
            "rule metadata must be complete".to_owned(),
        ));
    }
    let sample = lint_manifest(
        "self-check.json",
        include_str!("../tests/fixtures/valid.json"),
    )?;
    let sample_value =
        serde_json::to_value(sample).map_err(|error| LintError::SelfCheck(error.to_string()))?;
    validate_instance(&diagnostics_schema, &sample_value, "diagnostics report")?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture(name: &str) -> &'static str {
        match name {
            "valid" => include_str!("../tests/fixtures/valid.json"),
            "missing-schema" => include_str!("../tests/fixtures/invalid-missing-schema.json"),
            "missing-risk" => include_str!("../tests/fixtures/invalid-missing-risk.json"),
            "risk-label" => include_str!("../tests/fixtures/invalid-risk-label.json"),
            "risk-explanation" => {
                include_str!("../tests/fixtures/invalid-risk-explanation.json")
            }
            "idempotency" => include_str!("../tests/fixtures/invalid-idempotency.json"),
            "scope" => include_str!("../tests/fixtures/invalid-scope.json"),
            _ => panic!("unknown fixture"),
        }
    }

    #[test]
    fn valid_manifest_has_no_findings() {
        let report = lint_manifest("valid.json", fixture("valid")).unwrap();
        assert!(report.diagnostics.is_empty());
        assert_eq!(
            report.summary,
            Summary {
                errors: 0,
                warnings: 0
            }
        );
    }

    #[test]
    fn each_rule_reports_a_stable_pointer() {
        let cases = [
            (
                "missing-schema",
                RULE_SCHEMA_DECLARATION,
                "/actions/0/input_schema",
            ),
            ("risk-label", RULE_RISK_LABEL, "/actions/0/risk"),
            (
                "risk-explanation",
                RULE_RISK_EXPLANATION,
                "/actions/0/risk_explanation/localizations/0/effect_summaries",
            ),
            ("idempotency", RULE_IDEMPOTENCY, "/actions/0/idempotency"),
            ("scope", RULE_SCOPE, "/actions/0/scope"),
        ];
        for (fixture_name, rule_id, path) in cases {
            let report = lint_manifest(fixture_name, fixture(fixture_name)).unwrap();
            assert!(
                report
                    .diagnostics
                    .iter()
                    .any(|item| item.rule_id == rule_id && item.path == path)
            );
        }
    }

    fn manifest_with_risk_label(risk: Value) -> String {
        let mut manifest: Value = serde_json::from_str(fixture("valid")).unwrap();
        manifest["actions"][0]["risk"] = risk;
        serde_json::to_string(&manifest).unwrap()
    }

    #[test]
    fn risk_label_is_core_or_absolute_extension_uri() {
        for risk in CORE_RISK_LABELS {
            let document = manifest_with_risk_label(Value::String(risk.into()));
            let report = lint_manifest("risk-label.json", &document).unwrap();
            assert!(
                report
                    .diagnostics
                    .iter()
                    .all(|item| item.rule_id != RULE_RISK_LABEL),
                "rejected core risk {risk:?}: {:?}",
                report.diagnostics
            );
        }
        for risk in [
            "https://user@example.com:443/risks/dangerous?source=spec#v1",
            "urn:example:risk:dangerous",
            "risk+v1:dangerous",
            "risk:danger%20level",
        ] {
            let document = manifest_with_risk_label(Value::String(risk.into()));
            let report = lint_manifest("risk-label.json", &document).unwrap();
            assert!(
                report
                    .diagnostics
                    .iter()
                    .all(|item| item.rule_id != RULE_RISK_LABEL),
                "rejected extension risk URI {risk:?}: {:?}",
                report.diagnostics
            );
        }

        for risk in [
            "dangerous",
            "1risk:dangerous",
            "risk_name:dangerous",
            "risk:",
            "risk:danger ous",
            "risk:danger\u{00a0}ous",
            "risk:danger\nous",
            "risk:опасно",
            "risk:zero\u{200b}width",
            "risk:danger<ous",
            "risk:bad%ZZ",
            "risk:[",
            "https://[broken",
            "risk:value#one#two",
        ] {
            let document = manifest_with_risk_label(Value::String(risk.into()));
            let report = lint_manifest("risk-label.json", &document).unwrap();
            assert!(
                report.diagnostics.iter().any(|item| {
                    item.rule_id == RULE_RISK_LABEL && item.path == "/actions/0/risk"
                }),
                "accepted invalid risk label {risk:?}: {:?}",
                report.diagnostics
            );
        }
    }

    fn manifest_with_risk_explanation(explanation: Value, effects: Value) -> String {
        let mut manifest: Value = serde_json::from_str(fixture("valid")).unwrap();
        manifest["actions"][0]["effects"] = effects;
        manifest["actions"][0]["risk_explanation"] = explanation;
        serde_json::to_string(&manifest).unwrap()
    }

    fn valid_effect_explanation() -> Value {
        serde_json::json!({
            "default_language": "fr",
            "localizations": [
                {
                    "language": "en",
                    "summary": "Reads and records the selected task.",
                    "effect_summaries": [
                        {"effect_id": "task-read", "summary": "Reads task fields."},
                        {"effect_id": "audit-record", "summary": "Records an audit entry."}
                    ]
                },
                {
                    "language": "fr",
                    "summary": "Lit et journalise la tâche sélectionnée.",
                    "effect_summaries": [
                        {"effect_id": "task-read", "summary": "Lit les champs de la tâche."},
                        {"effect_id": "audit-record", "summary": "Enregistre une entrée d'audit."}
                    ]
                }
            ]
        })
    }

    fn effect_declarations() -> Value {
        serde_json::json!([
            {"effect_id": "task-read"},
            {"effect_id": "audit-record"}
        ])
    }

    fn assert_risk_finding(explanation: Value, effects: Value, expected_path: &str) {
        let document = manifest_with_risk_explanation(explanation, effects);
        let report = lint_manifest("risk-explanation.json", &document).unwrap();
        assert!(
            report
                .diagnostics
                .iter()
                .any(|item| item.rule_id == RULE_RISK_EXPLANATION && item.path == expected_path),
            "missing {expected_path:?} in {:?}",
            report.diagnostics
        );
    }

    #[test]
    fn valid_risk_explanation_covers_effects_in_order() {
        let document =
            manifest_with_risk_explanation(valid_effect_explanation(), effect_declarations());
        let report = lint_manifest("risk-explanation.json", &document).unwrap();
        assert!(
            report
                .diagnostics
                .iter()
                .all(|item| item.rule_id != RULE_RISK_EXPLANATION),
            "{:?}",
            report.diagnostics
        );
    }

    #[test]
    fn risk_explanation_objects_are_closed_and_bounded() {
        let mut explanation = valid_effect_explanation();
        explanation["unknown"] = Value::Bool(true);
        assert_risk_finding(
            explanation,
            effect_declarations(),
            "/actions/0/risk_explanation/unknown",
        );

        let mut explanation = valid_effect_explanation();
        explanation["localizations"][0]["unknown/member"] = Value::Bool(true);
        assert_risk_finding(
            explanation,
            effect_declarations(),
            "/actions/0/risk_explanation/localizations/0/unknown~1member",
        );

        let mut explanation = valid_effect_explanation();
        explanation["localizations"][0]["effect_summaries"][0]["unknown"] = Value::Bool(true);
        assert_risk_finding(
            explanation,
            effect_declarations(),
            "/actions/0/risk_explanation/localizations/0/effect_summaries/0/unknown",
        );

        let mut explanation = valid_effect_explanation();
        explanation["localizations"] = Value::Array(Vec::new());
        assert_risk_finding(
            explanation,
            effect_declarations(),
            "/actions/0/risk_explanation/localizations",
        );

        let mut localizations = Vec::new();
        for suffix in b'a'..=b'q' {
            localizations.push(serde_json::json!({
                "language": format!("a{}", char::from(suffix)),
                "summary": "Bounded summary.",
                "effect_summaries": []
            }));
        }
        assert_risk_finding(
            serde_json::json!({
                "default_language": "aa",
                "localizations": localizations
            }),
            Value::Array(Vec::new()),
            "/actions/0/risk_explanation/localizations",
        );
    }

    #[test]
    fn risk_explanation_languages_are_canonical_unique_and_ordered() {
        for language in [
            "en",
            "en-us",
            "es-419",
            "zh-hans",
            "zh-hans-cn",
            "de-1901",
            "sl-latn-si-rozaj-biske",
            "en-1abc",
        ] {
            assert!(
                is_canonical_language_tag(language),
                "rejected valid language tag {language:?}"
            );
        }
        for language in [
            "en-a",
            "en-12",
            "zh-cmn",
            "en-u-ca-gregory",
            "x-private",
            "i-klingon",
            "en-US",
            "en-ab1d",
            "en-abc",
            "de-1901-1901",
        ] {
            assert!(
                !is_canonical_language_tag(language),
                "accepted invalid language tag {language:?}"
            );
        }

        let mut explanation = valid_effect_explanation();
        explanation["localizations"][0]["language"] = Value::String("EN".to_owned());
        assert_risk_finding(
            explanation,
            effect_declarations(),
            "/actions/0/risk_explanation/localizations/0/language",
        );

        let mut explanation = valid_effect_explanation();
        explanation["localizations"][1]["language"] = Value::String("en".to_owned());
        assert_risk_finding(
            explanation,
            effect_declarations(),
            "/actions/0/risk_explanation/localizations/1/language",
        );

        let mut explanation = valid_effect_explanation();
        explanation["localizations"]
            .as_array_mut()
            .unwrap()
            .reverse();
        assert_risk_finding(
            explanation,
            effect_declarations(),
            "/actions/0/risk_explanation/localizations/1/language",
        );

        let mut explanation = valid_effect_explanation();
        explanation["default_language"] = Value::String("de".to_owned());
        assert_risk_finding(
            explanation,
            effect_declarations(),
            "/actions/0/risk_explanation/default_language",
        );

        let mut explanation = valid_effect_explanation();
        explanation["default_language"] = Value::String(format!("aa-{}", "a".repeat(61)));
        assert_risk_finding(
            explanation,
            effect_declarations(),
            "/actions/0/risk_explanation/default_language",
        );
    }

    #[test]
    fn risk_explanation_text_is_bounded_and_control_free() {
        let mut explanation = valid_effect_explanation();
        explanation["localizations"][0]["summary"] = Value::String(String::new());
        assert_risk_finding(
            explanation,
            effect_declarations(),
            "/actions/0/risk_explanation/localizations/0/summary",
        );

        let mut explanation = valid_effect_explanation();
        explanation["localizations"][0]["summary"] = Value::String("x".repeat(513));
        assert_risk_finding(
            explanation,
            effect_declarations(),
            "/actions/0/risk_explanation/localizations/0/summary",
        );

        let mut explanation = valid_effect_explanation();
        explanation["localizations"][0]["summary"] = Value::String("unsafe\nsummary".to_owned());
        assert_risk_finding(
            explanation,
            effect_declarations(),
            "/actions/0/risk_explanation/localizations/0/summary",
        );

        let mut explanation = valid_effect_explanation();
        explanation["localizations"][0]["effect_summaries"][0]["summary"] =
            Value::String("unsafe\u{0085}summary".to_owned());
        assert_risk_finding(
            explanation,
            effect_declarations(),
            "/actions/0/risk_explanation/localizations/0/effect_summaries/0/summary",
        );

        for bidi_control in [
            '\u{061c}', '\u{200e}', '\u{200f}', '\u{202a}', '\u{202b}', '\u{202c}', '\u{202d}',
            '\u{202e}', '\u{2066}', '\u{2067}', '\u{2068}', '\u{2069}',
        ] {
            let mut explanation = valid_effect_explanation();
            explanation["localizations"][0]["summary"] =
                Value::String(format!("unsafe{bidi_control}summary"));
            assert_risk_finding(
                explanation,
                effect_declarations(),
                "/actions/0/risk_explanation/localizations/0/summary",
            );
        }

        let mut explanation = valid_effect_explanation();
        explanation["localizations"][0]["effect_summaries"][0]["summary"] =
            Value::String("unsafe\u{202e}summary".to_owned());
        assert_risk_finding(
            explanation,
            effect_declarations(),
            "/actions/0/risk_explanation/localizations/0/effect_summaries/0/summary",
        );
    }

    #[test]
    fn risk_explanation_effect_coverage_is_exact_and_ordered() {
        let mut explanation = valid_effect_explanation();
        explanation["localizations"][0]["effect_summaries"]
            .as_array_mut()
            .unwrap()
            .reverse();
        assert_risk_finding(
            explanation,
            effect_declarations(),
            "/actions/0/risk_explanation/localizations/0/effect_summaries",
        );

        let mut explanation = valid_effect_explanation();
        explanation["localizations"][0]["effect_summaries"]
            .as_array_mut()
            .unwrap()
            .pop();
        assert_risk_finding(
            explanation,
            effect_declarations(),
            "/actions/0/risk_explanation/localizations/0/effect_summaries",
        );

        let mut explanation = valid_effect_explanation();
        explanation["localizations"][0]["effect_summaries"][1]["effect_id"] =
            Value::String("task-read".to_owned());
        assert_risk_finding(
            explanation,
            effect_declarations(),
            "/actions/0/risk_explanation/localizations/0/effect_summaries",
        );
    }

    #[test]
    fn strict_json_rejects_ambiguous_values() {
        for document in [
            r#"{"scopes":[],"scopes":[],"resources":[],"actions":[],"events":[]}"#,
            r#"{"value":1.5}"#,
            r#"{"value":9007199254740992}"#,
            r#"{"value":"\ud800"}"#,
        ] {
            assert!(parse_strict_json(document).is_err(), "accepted {document}");
        }
    }

    #[test]
    fn report_matches_machine_schema() {
        let schema = parse_strict_json(DIAGNOSTICS_SCHEMA).unwrap();
        let report = lint_manifest("invalid.json", fixture("scope")).unwrap();
        let value = serde_json::to_value(report).unwrap();
        validate_instance(&schema, &value, "test report").unwrap();
    }

    #[test]
    fn bundle_self_check_passes() {
        let root = Path::new(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .and_then(Path::parent)
            .unwrap();
        self_check(root).unwrap();
    }
}
