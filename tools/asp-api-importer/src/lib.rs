//! Fail-closed publishing-time import of explicit OpenAPI and AsyncAPI annotations.

use std::cmp::Ordering;
use std::collections::HashSet;
use std::fmt;
use std::fs;
use std::path::{Component, Path};

use asp_manifest_linter::{lint_manifest_value, parse_strict_json};
use base64::Engine;
use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use serde::Deserialize;
use serde::de::{self, Deserializer, MapAccess, SeqAccess, Visitor};
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};
use thiserror::Error;

pub const PROFILE: &str = "https://github.com/0al-spec/agent-surface/profiles/api-import/v1";
pub const MANIFEST_HASH_DOMAIN: &str = "https://github.com/0al-spec/agent-surface/hash/manifest/v1";
pub const ANNOTATION_SCHEMA: &str = include_str!("../schema/annotation.schema.json");
pub const CASES_SCHEMA: &str = include_str!("../schema/cases.schema.json");
pub const CASES_REGISTRY: &str = include_str!("../cases/v1/cases.json");

const EXTENSION: &str = "x-agent-surface";
const OUTPUT_MEMBERS: [&str; 4] = ["surface_hash", "resources", "actions", "events"];
const REQUIRED_BASE_MEMBERS: [&str; 12] = [
    "protocol",
    "app_id",
    "issuer",
    "surface_mode",
    "surface_version",
    "surface_url",
    "auth",
    "agent_api",
    "scopes",
    "data_classes",
    "audit",
    "revocation",
];
const HTTP_METHODS: [&str; 8] = [
    "get", "put", "post", "delete", "options", "head", "patch", "trace",
];
const SAFE_INTEGER: i128 = (1_i128 << 53) - 1;

#[derive(Debug, Error)]
pub enum ImportError {
    #[error("{0}")]
    Invalid(String),
    #[error("strict JSON parse failed: {0}")]
    StrictJson(String),
    #[error("final manifest lint failed: {0}")]
    Lint(String),
    #[error("cannot read {path}: {source}")]
    Io {
        path: String,
        #[source]
        source: std::io::Error,
    },
    #[error("self-check failed: {0}")]
    SelfCheck(String),
}

#[derive(Clone, Debug)]
struct StrictSourceValue(Value);

struct StrictSourceVisitor;

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

impl<'de> Visitor<'de> for StrictSourceVisitor {
    type Value = StrictSourceValue;

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("duplicate-free I-JSON")
    }

    fn visit_bool<E>(self, value: bool) -> Result<Self::Value, E> {
        Ok(StrictSourceValue(Value::Bool(value)))
    }

    fn visit_i64<E>(self, value: i64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        if i128::from(value).abs() > SAFE_INTEGER {
            return Err(E::custom("integer is outside the I-JSON safe range"));
        }
        Ok(StrictSourceValue(Value::Number(value.into())))
    }

    fn visit_u64<E>(self, value: u64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        if i128::from(value) > SAFE_INTEGER {
            return Err(E::custom("integer is outside the I-JSON safe range"));
        }
        Ok(StrictSourceValue(Value::Number(value.into())))
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
            return Err(E::custom("integer is outside the I-JSON safe range"));
        }
        let number = serde_json::Number::from_f64(value)
            .ok_or_else(|| E::custom("number cannot be represented as binary64"))?;
        Ok(StrictSourceValue(Value::Number(number)))
    }

    fn visit_str<E>(self, value: &str) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        reject_unicode_noncharacters::<E>(value)?;
        Ok(StrictSourceValue(Value::String(value.to_owned())))
    }

    fn visit_string<E>(self, value: String) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        reject_unicode_noncharacters::<E>(&value)?;
        Ok(StrictSourceValue(Value::String(value)))
    }

    fn visit_none<E>(self) -> Result<Self::Value, E> {
        Ok(StrictSourceValue(Value::Null))
    }

    fn visit_unit<E>(self) -> Result<Self::Value, E> {
        Ok(StrictSourceValue(Value::Null))
    }

    fn visit_some<D>(self, deserializer: D) -> Result<Self::Value, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_any(StrictSourceVisitor)
    }

    fn visit_seq<A>(self, mut sequence: A) -> Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        let mut values = Vec::new();
        while let Some(value) = sequence.next_element::<StrictSourceValue>()? {
            values.push(value.0);
        }
        Ok(StrictSourceValue(Value::Array(values)))
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
            let value = object.next_value::<StrictSourceValue>()?;
            values.insert(key, value.0);
        }
        Ok(StrictSourceValue(Value::Object(values)))
    }
}

impl<'de> Deserialize<'de> for StrictSourceValue {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_any(StrictSourceVisitor)
    }
}

fn reject_lexical_negative_zero(document: &str) -> Result<(), ImportError> {
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
        let at_number_boundary = index == 0
            || matches!(
                bytes[index - 1],
                b' ' | b'\t' | b'\r' | b'\n' | b'[' | b'{' | b',' | b':'
            );
        if byte != b'-' || !at_number_boundary || bytes.get(index + 1) != Some(&b'0') {
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
            return Err(ImportError::StrictJson(
                "JSON negative zero is forbidden".to_owned(),
            ));
        }
    }
    Ok(())
}

fn parse_source_json(document: &str) -> Result<Value, ImportError> {
    reject_lexical_negative_zero(document)?;
    let mut deserializer = serde_json::Deserializer::from_str(document);
    let value = StrictSourceValue::deserialize(&mut deserializer)
        .map_err(|error| ImportError::StrictJson(error.to_string()))?
        .0;
    deserializer
        .end()
        .map_err(|error| ImportError::StrictJson(error.to_string()))?;
    if !value.is_object() {
        return Err(ImportError::Invalid(
            "source root must be a JSON object".to_owned(),
        ));
    }
    Ok(value)
}

#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
enum MemberKind {
    Resource,
    Action,
    Event,
}

impl MemberKind {
    fn parse(value: &str, path: &str) -> Result<Self, ImportError> {
        match value {
            "resource" => Ok(Self::Resource),
            "action" => Ok(Self::Action),
            "event" => Ok(Self::Event),
            _ => Err(ImportError::Invalid(format!(
                "{path}/kind: unknown member kind {value:?}"
            ))),
        }
    }

    fn singular(self) -> &'static str {
        match self {
            Self::Resource => "resource",
            Self::Action => "action",
            Self::Event => "event",
        }
    }
}

#[derive(Debug, Default)]
struct Inventory {
    resources: Vec<Value>,
    actions: Vec<Value>,
    events: Vec<Value>,
    identities: HashSet<(MemberKind, String)>,
}

impl Inventory {
    fn push(
        &mut self,
        kind: MemberKind,
        declaration: Value,
        path: &str,
    ) -> Result<(), ImportError> {
        let id = declaration
            .as_object()
            .and_then(|object| object.get("id"))
            .and_then(Value::as_str)
            .filter(|id| !id.is_empty())
            .ok_or_else(|| {
                ImportError::Invalid(format!("{path}/declaration.id must be a non-empty string"))
            })?
            .to_owned();
        if !self.identities.insert((kind, id.clone())) {
            return Err(ImportError::Invalid(format!(
                "{path}: duplicate {} id {id:?}",
                kind.singular()
            )));
        }
        match kind {
            MemberKind::Resource => self.resources.push(declaration),
            MemberKind::Action => self.actions.push(declaration),
            MemberKind::Event => self.events.push(declaration),
        }
        Ok(())
    }

    fn is_empty(&self) -> bool {
        self.identities.is_empty()
    }

    fn sort(&mut self) {
        fn by_unsigned_utf8_id(left: &Value, right: &Value) -> Ordering {
            let left = left
                .get("id")
                .and_then(Value::as_str)
                .expect("validated member id");
            let right = right
                .get("id")
                .and_then(Value::as_str)
                .expect("validated member id");
            left.as_bytes().cmp(right.as_bytes())
        }
        self.resources.sort_by(by_unsigned_utf8_id);
        self.actions.sort_by(by_unsigned_utf8_id);
        self.events.sort_by(by_unsigned_utf8_id);
    }
}

#[derive(Clone, Copy, Debug)]
enum SourceKind {
    OpenApi,
    AsyncApi,
}

fn object<'a>(value: &'a Value, path: &str) -> Result<&'a Map<String, Value>, ImportError> {
    value
        .as_object()
        .ok_or_else(|| ImportError::Invalid(format!("{path} must be an object")))
}

fn version_is_supported(value: &str, families: &[&str]) -> bool {
    let components: Vec<&str> = value.split('.').collect();
    components.len() == 3
        && components.iter().all(|component| {
            !component.is_empty() && component.bytes().all(|byte| byte.is_ascii_digit())
        })
        && families
            .iter()
            .any(|family| value.starts_with(&format!("{family}.")))
}

fn source_kind(root: &Map<String, Value>) -> Result<SourceKind, ImportError> {
    match (root.get("openapi"), root.get("asyncapi")) {
        (Some(openapi), None) => {
            let version = openapi.as_str().ok_or_else(|| {
                ImportError::Invalid("/openapi must be a version string".to_owned())
            })?;
            if !version_is_supported(version, &["3.1", "3.2"]) {
                return Err(ImportError::Invalid(format!(
                    "unsupported OpenAPI version {version:?}; v1 accepts 3.1.x or 3.2.x"
                )));
            }
            Ok(SourceKind::OpenApi)
        }
        (None, Some(asyncapi)) => {
            let version = asyncapi.as_str().ok_or_else(|| {
                ImportError::Invalid("/asyncapi must be a version string".to_owned())
            })?;
            if !version_is_supported(version, &["3.0", "3.1"]) {
                return Err(ImportError::Invalid(format!(
                    "unsupported AsyncAPI version {version:?}; v1 accepts 3.0.x or 3.1.x"
                )));
            }
            Ok(SourceKind::AsyncApi)
        }
        _ => Err(ImportError::Invalid(
            "source must contain exactly one of openapi or asyncapi".to_owned(),
        )),
    }
}

fn reject_unknown_members(
    value: &Map<String, Value>,
    permitted: &[&str],
    label: &str,
) -> Result<(), ImportError> {
    if let Some(name) = value
        .keys()
        .find(|name| !permitted.contains(&name.as_str()))
    {
        return Err(ImportError::Invalid(format!(
            "unknown {label} member {name:?}"
        )));
    }
    Ok(())
}

fn parse_members(
    value: &Value,
    path: &str,
    allowed_kind: Option<MemberKind>,
    inventory: &mut Inventory,
) -> Result<(), ImportError> {
    let members = value
        .as_array()
        .ok_or_else(|| ImportError::Invalid(format!("{path} must be an array")))?;
    if members.is_empty() {
        return Err(ImportError::Invalid(format!("{path} must be non-empty")));
    }
    for (index, item) in members.iter().enumerate() {
        let item_path = format!("{path}/{index}");
        let envelope = object(item, &item_path)?;
        reject_unknown_members(envelope, &["kind", "declaration"], "member annotation")?;
        for required in ["kind", "declaration"] {
            if !envelope.contains_key(required) {
                return Err(ImportError::Invalid(format!(
                    "{item_path} must contain {required}"
                )));
            }
        }
        let kind_name = envelope
            .get("kind")
            .and_then(Value::as_str)
            .ok_or_else(|| ImportError::Invalid(format!("{item_path}/kind must be a string")))?;
        let kind = MemberKind::parse(kind_name, &item_path)?;
        if allowed_kind.is_some_and(|allowed| allowed != kind) {
            return Err(ImportError::Invalid(format!(
                "{item_path}: {} members are not allowed at this annotation location",
                kind.singular()
            )));
        }
        let declaration = envelope
            .get("declaration")
            .filter(|value| value.is_object())
            .ok_or_else(|| {
                ImportError::Invalid(format!("{item_path}/declaration must be an object"))
            })?
            .clone();
        inventory.push(kind, declaration, &item_path)?;
    }
    Ok(())
}

fn parse_root_annotation(
    annotation: &Value,
    inventory: &mut Inventory,
) -> Result<Map<String, Value>, ImportError> {
    let annotation = object(annotation, "/x-agent-surface")?;
    reject_unknown_members(
        annotation,
        &["profile", "manifest_base", "members"],
        "root annotation",
    )?;
    if annotation.get("profile").and_then(Value::as_str) != Some(PROFILE) {
        return Err(ImportError::Invalid(format!(
            "/x-agent-surface/profile must equal {PROFILE:?}"
        )));
    }
    let base = annotation
        .get("manifest_base")
        .ok_or_else(|| {
            ImportError::Invalid("/x-agent-surface/manifest_base is required".to_owned())
        })
        .and_then(|value| object(value, "/x-agent-surface/manifest_base"))?;
    for required in REQUIRED_BASE_MEMBERS {
        if !base.contains_key(required) {
            return Err(ImportError::Invalid(format!(
                "manifest_base is missing required member {required}"
            )));
        }
    }
    for reserved in OUTPUT_MEMBERS {
        if base.contains_key(reserved) {
            return Err(ImportError::Invalid(format!(
                "manifest_base must omit output-owned member {reserved}"
            )));
        }
    }
    if let Some(members) = annotation.get("members") {
        parse_members(members, "/x-agent-surface/members", None, inventory)?;
    }
    Ok(base.clone())
}

fn parse_local_annotation(
    annotation: &Value,
    path: &str,
    allowed_kind: MemberKind,
    inventory: &mut Inventory,
) -> Result<(), ImportError> {
    let annotation = object(annotation, path)?;
    reject_unknown_members(annotation, &["members"], "local annotation")?;
    let members = annotation
        .get("members")
        .ok_or_else(|| ImportError::Invalid(format!("{path}/members is required")))?;
    parse_members(
        members,
        &format!("{path}/members"),
        Some(allowed_kind),
        inventory,
    )
}

fn collect_annotation_paths(value: &Value, path: &mut Vec<String>, output: &mut Vec<Vec<String>>) {
    match value {
        Value::Object(object) => {
            for (key, child) in object {
                path.push(key.clone());
                if key == EXTENSION {
                    output.push(path.clone());
                }
                collect_annotation_paths(child, path, output);
                path.pop();
            }
        }
        Value::Array(array) => {
            for (index, child) in array.iter().enumerate() {
                path.push(index.to_string());
                collect_annotation_paths(child, path, output);
                path.pop();
            }
        }
        _ => {}
    }
}

fn pointer(path: &[String]) -> String {
    let escaped: Vec<String> = path
        .iter()
        .map(|component| component.replace('~', "~0").replace('/', "~1"))
        .collect();
    format!("/{}", escaped.join("/"))
}

fn parse_openapi_operations(
    root: &Map<String, Value>,
    allowed_paths: &mut HashSet<Vec<String>>,
    inventory: &mut Inventory,
) -> Result<(), ImportError> {
    let Some(paths) = root.get("paths") else {
        return Ok(());
    };
    let paths = object(paths, "/paths")?;
    for (route, path_item) in paths {
        if !route.starts_with('/') {
            continue;
        }
        let path_item_path = format!(
            "/paths/{}",
            pointer(std::slice::from_ref(route)).trim_start_matches('/')
        );
        let Some(path_item) = path_item.as_object() else {
            continue;
        };
        for method in HTTP_METHODS {
            let Some(operation) = path_item.get(method) else {
                continue;
            };
            let operation_path = format!("{path_item_path}/{method}");
            let Some(operation) = operation.as_object() else {
                continue;
            };
            let Some(annotation) = operation.get(EXTENSION) else {
                continue;
            };
            if path_item.contains_key("$ref") || operation.contains_key("$ref") {
                return Err(ImportError::Invalid(format!(
                    "{operation_path}: annotated $ref object is unsupported"
                )));
            }
            let annotation_path = format!("{operation_path}/{EXTENSION}");
            parse_local_annotation(annotation, &annotation_path, MemberKind::Action, inventory)?;
            allowed_paths.insert(vec![
                "paths".to_owned(),
                route.clone(),
                method.to_owned(),
                EXTENSION.to_owned(),
            ]);
        }
    }
    Ok(())
}

fn parse_asyncapi_operations(
    root: &Map<String, Value>,
    allowed_paths: &mut HashSet<Vec<String>>,
    inventory: &mut Inventory,
) -> Result<(), ImportError> {
    let Some(operations) = root.get("operations") else {
        return Ok(());
    };
    let operations = object(operations, "/operations")?;
    for (operation_id, operation) in operations {
        let operation_path = format!(
            "/operations/{}",
            pointer(std::slice::from_ref(operation_id)).trim_start_matches('/')
        );
        let Some(operation) = operation.as_object() else {
            continue;
        };
        let Some(annotation) = operation.get(EXTENSION) else {
            continue;
        };
        if operation.contains_key("$ref") {
            return Err(ImportError::Invalid(format!(
                "{operation_path}: annotated $ref object is unsupported"
            )));
        }
        if operation.get("action").and_then(Value::as_str) != Some("send") {
            return Err(ImportError::Invalid(format!(
                "{operation_path}: annotated AsyncAPI operation action must be send"
            )));
        }
        let annotation_path = format!("{operation_path}/{EXTENSION}");
        parse_local_annotation(annotation, &annotation_path, MemberKind::Event, inventory)?;
        allowed_paths.insert(vec![
            "operations".to_owned(),
            operation_id.clone(),
            EXTENSION.to_owned(),
        ]);
    }
    Ok(())
}

fn manifest_hash(manifest_without_hash: &Value) -> Result<String, ImportError> {
    let wrapper = Value::Object(Map::from_iter([
        (
            "domain".to_owned(),
            Value::String(MANIFEST_HASH_DOMAIN.to_owned()),
        ),
        ("object".to_owned(), manifest_without_hash.clone()),
    ]));
    let canonical = serde_json_canonicalizer::to_vec(&wrapper).map_err(|error| {
        ImportError::Invalid(format!("RFC 8785 canonicalization failed: {error}"))
    })?;
    let digest = Sha256::digest(&canonical);
    Ok(format!("sha-256:{}", URL_SAFE_NO_PAD.encode(digest)))
}

#[derive(Debug, Deserialize, Eq, PartialEq)]
struct LinterRulesetBinding {
    id: String,
    version: String,
}

fn expected_linter_ruleset() -> Result<LinterRulesetBinding, ImportError> {
    let registry = parse_strict_json(CASES_REGISTRY)
        .map_err(|error| ImportError::Invalid(format!("compiled case registry: {error}")))?;
    let binding = registry
        .get("linter_ruleset")
        .cloned()
        .ok_or_else(|| ImportError::Invalid("case registry has no linter_ruleset".to_owned()))?;
    serde_json::from_value(binding)
        .map_err(|error| ImportError::Invalid(format!("invalid linter_ruleset binding: {error}")))
}

fn verify_linter_ruleset(
    actual_id: &str,
    actual_version: &str,
    expected: &LinterRulesetBinding,
) -> Result<(), ImportError> {
    if actual_id != expected.id || actual_version != expected.version {
        return Err(ImportError::Lint(format!(
            "ruleset drift: expected {} version {}, got {} version {}",
            expected.id, expected.version, actual_id, actual_version
        )));
    }
    Ok(())
}

fn reject_lint_findings(source: &str, manifest: &Value) -> Result<(), ImportError> {
    let report = lint_manifest_value(source, manifest)
        .map_err(|error| ImportError::Lint(error.to_string()))?;
    let expected = expected_linter_ruleset()?;
    verify_linter_ruleset(
        &report.tool.ruleset_id,
        &report.tool.ruleset_version,
        &expected,
    )?;
    if report.diagnostics.is_empty() {
        return Ok(());
    }
    let findings = report
        .diagnostics
        .iter()
        .map(|diagnostic| {
            format!(
                "{} {}: {}",
                diagnostic.rule_id, diagnostic.path, diagnostic.message
            )
        })
        .collect::<Vec<_>>()
        .join("; ");
    Err(ImportError::Lint(findings))
}

/// Generate a deterministic lint-clean ASP manifest candidate from one strict JSON source.
pub fn generate_manifest(source: &str, document: &str) -> Result<Value, ImportError> {
    let value = parse_source_json(document)?;
    let root = object(&value, "/")?;
    let kind = source_kind(root)?;
    let root_annotation = root.get(EXTENSION).ok_or_else(|| {
        ImportError::Invalid("root /x-agent-surface annotation is required".to_owned())
    })?;
    if root.contains_key("$ref") {
        return Err(ImportError::Invalid(
            "/: annotated $ref object is unsupported".to_owned(),
        ));
    }

    let mut inventory = Inventory::default();
    let mut manifest = parse_root_annotation(root_annotation, &mut inventory)?;
    let mut allowed_paths = HashSet::from([vec![EXTENSION.to_owned()]]);
    match kind {
        SourceKind::OpenApi => parse_openapi_operations(root, &mut allowed_paths, &mut inventory)?,
        SourceKind::AsyncApi => {
            parse_asyncapi_operations(root, &mut allowed_paths, &mut inventory)?
        }
    }

    let mut actual_paths = Vec::new();
    collect_annotation_paths(&value, &mut Vec::new(), &mut actual_paths);
    if let Some(path) = actual_paths
        .iter()
        .find(|path| !allowed_paths.contains(*path))
    {
        return Err(ImportError::Invalid(format!(
            "unsupported x-agent-surface placement at {}",
            pointer(path)
        )));
    }
    if inventory.is_empty() {
        return Err(ImportError::Invalid(
            "at least one annotated ASP member is required".to_owned(),
        ));
    }

    inventory.sort();
    manifest.insert("resources".to_owned(), Value::Array(inventory.resources));
    manifest.insert("actions".to_owned(), Value::Array(inventory.actions));
    manifest.insert("events".to_owned(), Value::Array(inventory.events));
    let mut output = Value::Object(manifest);
    let hash = manifest_hash(&output)?;
    output
        .as_object_mut()
        .expect("manifest remains an object")
        .insert("surface_hash".to_owned(), Value::String(hash));

    reject_lint_findings(source, &output)?;
    Ok(output)
}

/// Render a generated manifest candidate as pretty JSON with one final newline.
pub fn render_manifest(manifest: &Value) -> Result<String, ImportError> {
    serde_json::to_string_pretty(manifest)
        .map(|value| format!("{value}\n"))
        .map_err(|error| ImportError::Invalid(format!("cannot serialize manifest: {error}")))
}

fn read(path: &Path) -> Result<String, ImportError> {
    fs::read_to_string(path).map_err(|source| ImportError::Io {
        path: path.display().to_string(),
        source,
    })
}

fn validate_instance(schema: &Value, instance: &Value, label: &str) -> Result<(), ImportError> {
    let validator = jsonschema::validator_for(schema)
        .map_err(|error| ImportError::SelfCheck(format!("{label} schema: {error}")))?;
    let errors: Vec<String> = validator
        .iter_errors(instance)
        .map(|error| error.to_string())
        .collect();
    if errors.is_empty() {
        Ok(())
    } else {
        Err(ImportError::SelfCheck(format!(
            "{label} validation: {}",
            errors.join("; ")
        )))
    }
}

fn local_annotation_schema(annotation_schema: &Value) -> Result<Value, ImportError> {
    let mut schema = annotation_schema.clone();
    let object = schema.as_object_mut().ok_or_else(|| {
        ImportError::SelfCheck("annotation schema root must be an object".to_owned())
    })?;
    for keyword in ["type", "required", "properties", "additionalProperties"] {
        object.remove(keyword);
    }
    object.insert(
        "$ref".to_owned(),
        Value::String("#/$defs/local_annotation".to_owned()),
    );
    Ok(schema)
}

fn value_at_path<'a>(root: &'a Value, path: &[String]) -> Option<&'a Value> {
    path.iter().try_fold(root, |value, component| match value {
        Value::Object(object) => object.get(component),
        Value::Array(array) => component
            .parse::<usize>()
            .ok()
            .and_then(|index| array.get(index)),
        _ => None,
    })
}

fn relative_path<'a>(value: &'a str, label: &str) -> Result<&'a Path, ImportError> {
    let path = Path::new(value);
    if path.is_absolute()
        || path
            .components()
            .any(|component| !matches!(component, Component::Normal(_)))
    {
        return Err(ImportError::SelfCheck(format!(
            "{label} must be a confined relative path"
        )));
    }
    Ok(path)
}

#[derive(Debug, Deserialize)]
struct CaseRegistry {
    schema_version: u64,
    profile: String,
    linter_ruleset: LinterRulesetBinding,
    cases: Vec<Case>,
}

#[derive(Debug, Deserialize)]
#[serde(tag = "expect", rename_all = "lowercase")]
enum Case {
    Success {
        id: String,
        source: String,
        golden: String,
    },
    Failure {
        id: String,
        source: String,
        error_contains: String,
    },
}

impl Case {
    fn id(&self) -> &str {
        match self {
            Self::Success { id, .. } | Self::Failure { id, .. } => id,
        }
    }
}

/// Verify compiled artifacts and execute the machine-readable case registry.
pub fn self_check(repository_root: &Path) -> Result<(), ImportError> {
    let crate_root = repository_root.join("tools/asp-api-importer");
    let artifacts = [
        (
            crate_root.join("schema/annotation.schema.json"),
            ANNOTATION_SCHEMA,
        ),
        (crate_root.join("schema/cases.schema.json"), CASES_SCHEMA),
        (crate_root.join("cases/v1/cases.json"), CASES_REGISTRY),
    ];
    for (path, embedded) in &artifacts {
        if read(path)? != *embedded {
            return Err(ImportError::SelfCheck(format!(
                "compiled artifact differs from {}",
                path.display()
            )));
        }
    }

    let annotation_schema = parse_strict_json(ANNOTATION_SCHEMA)
        .map_err(|error| ImportError::SelfCheck(error.to_string()))?;
    jsonschema::validator_for(&annotation_schema)
        .map_err(|error| ImportError::SelfCheck(format!("annotation schema: {error}")))?;
    let local_schema = local_annotation_schema(&annotation_schema)?;
    jsonschema::validator_for(&local_schema)
        .map_err(|error| ImportError::SelfCheck(format!("local annotation schema: {error}")))?;
    let cases_schema = parse_strict_json(CASES_SCHEMA)
        .map_err(|error| ImportError::SelfCheck(error.to_string()))?;
    let cases_value = parse_strict_json(CASES_REGISTRY)
        .map_err(|error| ImportError::SelfCheck(error.to_string()))?;
    validate_instance(&cases_schema, &cases_value, "case registry")?;
    let registry: CaseRegistry = serde_json::from_value(cases_value)
        .map_err(|error| ImportError::SelfCheck(error.to_string()))?;
    if registry.schema_version != 1 || registry.profile != PROFILE {
        return Err(ImportError::SelfCheck(
            "case registry profile metadata is not canonical".to_owned(),
        ));
    }
    if registry.linter_ruleset != expected_linter_ruleset()? {
        return Err(ImportError::SelfCheck(
            "case registry linter_ruleset binding is not canonical".to_owned(),
        ));
    }
    let mut ids = HashSet::new();
    for case in &registry.cases {
        if !ids.insert(case.id()) {
            return Err(ImportError::SelfCheck(format!(
                "duplicate case id {:?}",
                case.id()
            )));
        }
        match case {
            Case::Success { id, source, golden } => {
                let source_path = crate_root.join(relative_path(source, "case source")?);
                let document = read(&source_path)?;
                let root = parse_source_json(&document)
                    .map_err(|error| ImportError::SelfCheck(format!("{id}: {error}")))?;
                let extension = root.get(EXTENSION).ok_or_else(|| {
                    ImportError::SelfCheck(format!("{id}: positive case has no root annotation"))
                })?;
                validate_instance(&annotation_schema, extension, &format!("{id} annotation"))?;
                let mut annotation_paths = Vec::new();
                collect_annotation_paths(&root, &mut Vec::new(), &mut annotation_paths);
                for path in annotation_paths
                    .iter()
                    .filter(|path| path.as_slice() != [EXTENSION])
                {
                    let annotation = value_at_path(&root, path).ok_or_else(|| {
                        ImportError::SelfCheck(format!(
                            "{id}: cannot resolve annotation at {}",
                            pointer(path)
                        ))
                    })?;
                    validate_instance(
                        &local_schema,
                        annotation,
                        &format!("{id} local annotation at {}", pointer(path)),
                    )?;
                }
                let generated = generate_manifest(&source_path.display().to_string(), &document)
                    .map_err(|error| ImportError::SelfCheck(format!("{id}: {error}")))?;
                let actual = render_manifest(&generated)?;
                let golden_path = crate_root.join(relative_path(golden, "golden output")?);
                let expected = read(&golden_path)?;
                if actual != expected {
                    return Err(ImportError::SelfCheck(format!(
                        "{id}: generated output differs from {}",
                        golden_path.display()
                    )));
                }
            }
            Case::Failure {
                id,
                source,
                error_contains,
            } => {
                let source_path = crate_root.join(relative_path(source, "case source")?);
                let document = read(&source_path)?;
                match generate_manifest(&source_path.display().to_string(), &document) {
                    Ok(_) => {
                        return Err(ImportError::SelfCheck(format!(
                            "{id}: negative case unexpectedly succeeded"
                        )));
                    }
                    Err(error) if error.to_string().contains(error_contains) => {}
                    Err(error) => {
                        return Err(ImportError::SelfCheck(format!(
                            "{id}: error {error:?} does not contain {error_contains:?}"
                        )));
                    }
                }
            }
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    const OPENAPI: &str = include_str!("../tests/fixtures/positive-openapi.json");
    const ASYNCAPI: &str = include_str!("../tests/fixtures/positive-asyncapi.json");

    #[test]
    fn generation_is_deterministic_and_omits_unannotated_operations() {
        assert!(OPENAPI.contains("\"minimum\": 0.1"));
        assert!(OPENAPI.contains("\"x-meta\": \"legal non-path metadata\""));
        let first = generate_manifest("openapi.json", OPENAPI).unwrap();
        let second = generate_manifest("openapi.json", OPENAPI).unwrap();
        assert_eq!(first, second);
        let actions = first["actions"].as_array().unwrap();
        assert_eq!(actions.len(), 1);
        assert_eq!(actions[0]["id"], "task.get");
        assert!(
            render_manifest(&first)
                .unwrap()
                .find("deleteEverything")
                .is_none()
        );
        assert_eq!(
            first["surface_hash"],
            "sha-256:dXcnhJ0RSi670ruLORrVKZjVZ8n3r8zjQpqOKaYekAw"
        );
        assert_eq!(first["x-example-risk-threshold"], 0.1);
    }

    #[test]
    fn jcs_uses_utf16_member_order() {
        let value = serde_json::json!({"\u{e000}": 2, "\u{10000}": 1});
        let canonical = serde_json_canonicalizer::to_string(&value).unwrap();
        assert_eq!(canonical, "{\"𐀀\":1,\"\":2}");
    }

    #[test]
    fn asyncapi_x_prefixed_operation_id_is_eligible() {
        assert!(ASYNCAPI.contains("\"x-publish\""));
        let manifest = generate_manifest("asyncapi.json", ASYNCAPI).unwrap();
        assert_eq!(manifest["events"][0]["id"], "message.sent");
    }

    #[test]
    fn source_parser_accepts_finite_metadata_float_but_rejects_ijson_hazards() {
        assert!(parse_source_json(r#"{"minimum":0.1}"#).is_ok());
        assert!(parse_source_json(r#"{"value":1e-0}"#).is_ok());
        assert!(parse_source_json(r#"{"value":10E-0}"#).is_ok());
        for document in [
            r#"{"value":-0}"#,
            r#"{"value":-0.0}"#,
            r#"{"value":-0e10}"#,
            r#"{"value":9007199254740992}"#,
            r#"{"value":9.007199254740992e15}"#,
            r#"{"value":1,"value":2}"#,
            r#"{"value":1e400}"#,
            r#"{"value":"\uFDD0"}"#,
            r#"{"\uFFFF":"value"}"#,
            r#"{"value":"\uDBFF\uDFFE"}"#,
        ] {
            assert!(parse_source_json(document).is_err(), "{document} must fail");
        }
    }

    #[test]
    fn linter_ruleset_binding_fails_closed_on_drift() {
        let expected = expected_linter_ruleset().unwrap();
        assert!(verify_linter_ruleset(&expected.id, &expected.version, &expected).is_ok());
        let error = verify_linter_ruleset(&expected.id, "1.2.0", &expected).unwrap_err();
        assert!(error.to_string().contains("ruleset drift"));
    }
}
