//! Fail-closed ASP manifest parsing, linting, reporting, and self-validation.

use std::collections::{HashMap, HashSet};
use std::fmt;
use std::fs;
use std::path::Path;

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
pub const RULE_IDEMPOTENCY: &str = "ASP-LINT-IDEMPOTENCY-001";
pub const RULE_SCOPE: &str = "ASP-LINT-SCOPE-001";

const SAFE_INTEGER: i128 = (1_i128 << 53) - 1;
const IMPLEMENTED_RULES: [&str; 4] = [
    RULE_SCHEMA_DECLARATION,
    RULE_RISK_LABEL,
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

fn lint_risk_labels(manifest: &Value, context: &mut Context<'_>) -> Result<(), LintError> {
    for (index, action) in required_array(manifest, "actions")?.iter().enumerate() {
        let object = required_object(action, &format!("/actions/{index}"))?;
        if !has_nonempty_string(object, "risk") {
            context.emit(
                RULE_RISK_LABEL,
                format!("/actions/{index}/risk"),
                "action should declare a non-empty risk label",
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
            ("missing-risk", RULE_RISK_LABEL, "/actions/0/risk"),
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
