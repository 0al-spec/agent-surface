use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Component, Path};

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::hash::{
    ACTUAL_EFFECTS_DOMAIN, BUNDLE_DOMAIN, EVENT_DOMAIN, EXECUTION_DOMAIN, GRANT_DOMAIN,
    MANIFEST_DOMAIN, POLICY_DOMAIN, RECEIPT_DOMAIN, RECORD_DOMAIN, object_hash,
};
use crate::registry::{IMPLEMENTED_CHECKS, registry};
use crate::strict_json::parse_strict;
use crate::value::{member, string};
use crate::{
    BUNDLE_SCHEMA, CASE_REGISTRY, CASES_SCHEMA, CHECK_PROFILE, CHECK_REGISTRY, CHECKS_SCHEMA,
    PROFILE, REPORT_SCHEMA, ReplayError, verify,
};

fn read(path: &Path) -> Result<String, ReplayError> {
    fs::read_to_string(path).map_err(|source| ReplayError::Io {
        path: path.display().to_string(),
        source,
    })
}

fn relative_path<'a>(value: &'a str, label: &str) -> Result<&'a Path, ReplayError> {
    let path = Path::new(value);
    if path.is_absolute()
        || path
            .components()
            .any(|component| !matches!(component, Component::Normal(_)))
    {
        return Err(ReplayError::SelfCheck(format!(
            "{label} must be a confined relative path"
        )));
    }
    Ok(path)
}

pub(crate) fn validate_instance(
    schema: &Value,
    instance: &Value,
    label: &str,
) -> Result<(), ReplayError> {
    let compiled = jsonschema::validator_for(schema)
        .map_err(|error| ReplayError::SelfCheck(format!("{label} schema: {error}")))?;
    let errors: Vec<String> = compiled
        .iter_errors(instance)
        .map(|error| error.to_string())
        .collect();
    if errors.is_empty() {
        Ok(())
    } else {
        Err(ReplayError::SelfCheck(format!(
            "{label} validation: {}",
            errors.join("; ")
        )))
    }
}

#[derive(Debug, Deserialize)]
struct CaseRegistry {
    schema_version: u64,
    profile: String,
    cases: Vec<Case>,
}

#[derive(Debug, Deserialize)]
#[serde(tag = "expect", rename_all = "snake_case")]
enum Case {
    Report {
        id: String,
        source: String,
        golden: Option<String>,
        evaluation_state: String,
        verdict: String,
        integrity_verdict: String,
        replay_completeness: String,
        diagnostic_check_ids: Vec<String>,
        #[serde(default)]
        mutations: Vec<Mutation>,
        #[serde(default)]
        rehash_after_mutations: bool,
    },
    ParseError {
        id: String,
        source: String,
        error_contains: String,
    },
}

#[derive(Clone, Debug, Deserialize)]
struct Mutation {
    op: String,
    path: String,
    #[serde(default)]
    value: Value,
}

fn unescape_pointer(component: &str) -> String {
    component.replace("~1", "/").replace("~0", "~")
}

fn apply_mutation(root: &mut Value, mutation: &Mutation) -> Result<(), ReplayError> {
    match mutation.op.as_str() {
        "replace" => {
            let target = root.pointer_mut(&mutation.path).ok_or_else(|| {
                ReplayError::SelfCheck(format!(
                    "mutation path {:?} does not resolve",
                    mutation.path
                ))
            })?;
            *target = mutation.value.clone();
        }
        "add" => {
            let (parent_path, member) = mutation.path.rsplit_once('/').ok_or_else(|| {
                ReplayError::SelfCheck("mutation add path has no parent".to_owned())
            })?;
            let parent = if parent_path.is_empty() {
                root
            } else {
                root.pointer_mut(parent_path).ok_or_else(|| {
                    ReplayError::SelfCheck(format!(
                        "mutation parent {:?} does not resolve",
                        parent_path
                    ))
                })?
            };
            parent
                .as_object_mut()
                .ok_or_else(|| {
                    ReplayError::SelfCheck("mutation parent is not an object".to_owned())
                })?
                .insert(unescape_pointer(member), mutation.value.clone());
        }
        "remove" => {
            let (parent_path, member) = mutation.path.rsplit_once('/').ok_or_else(|| {
                ReplayError::SelfCheck("mutation remove path has no parent".to_owned())
            })?;
            let parent = if parent_path.is_empty() {
                root
            } else {
                root.pointer_mut(parent_path).ok_or_else(|| {
                    ReplayError::SelfCheck(format!(
                        "mutation parent {:?} does not resolve",
                        parent_path
                    ))
                })?
            };
            if parent
                .as_object_mut()
                .and_then(|object| object.remove(&unescape_pointer(member)))
                .is_none()
            {
                return Err(ReplayError::SelfCheck(
                    "mutation remove target does not exist".to_owned(),
                ));
            }
        }
        _ => {
            return Err(ReplayError::SelfCheck(format!(
                "unknown mutation operation {:?}",
                mutation.op
            )));
        }
    }
    Ok(())
}

fn set_string(value: &mut Value, name: &str, new_value: String) {
    if let Some(object) = value.as_object_mut() {
        object.insert(name.to_owned(), Value::String(new_value));
    }
}

pub(crate) fn rehash_bundle(bundle: &mut Value) -> Result<(), ReplayError> {
    let surface_hash = {
        let surface = bundle
            .pointer("/context/surface")
            .ok_or_else(|| ReplayError::SelfCheck("rehash requires context.surface".to_owned()))?;
        object_hash(MANIFEST_DOMAIN, surface, &["surface_hash"])?
    };
    set_string(
        bundle
            .pointer_mut("/context/surface")
            .expect("surface was resolved"),
        "surface_hash",
        surface_hash.clone(),
    );
    set_string(
        bundle
            .pointer_mut("/context/grant/resource_server")
            .ok_or_else(|| {
                ReplayError::SelfCheck("rehash requires Grant resource_server".to_owned())
            })?,
        "surface_hash",
        surface_hash.clone(),
    );
    set_string(
        bundle
            .pointer_mut("/scope")
            .ok_or_else(|| ReplayError::SelfCheck("rehash requires scope".to_owned()))?,
        "surface_hash",
        surface_hash.clone(),
    );

    let grant_hash = {
        let grant = bundle
            .pointer("/context/grant")
            .ok_or_else(|| ReplayError::SelfCheck("rehash requires context.grant".to_owned()))?;
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
        object_hash(GRANT_DOMAIN, &hash_view, &[])?
    };
    set_string(
        bundle
            .pointer_mut("/context/grant")
            .expect("grant was resolved"),
        "grant_hash",
        grant_hash.clone(),
    );
    set_string(
        bundle.pointer_mut("/scope").expect("scope was resolved"),
        "grant_hash",
        grant_hash.clone(),
    );

    let mut prior_record_hash: Option<String> = None;
    let mut receipt_hash_replacements = HashMap::new();
    let records = member(bundle, "records")
        .and_then(Value::as_array)
        .ok_or_else(|| ReplayError::SelfCheck("rehash requires records".to_owned()))?
        .len();
    for index in 0..records {
        let record_path = format!("/records/{index}");
        let kind = bundle
            .pointer(&record_path)
            .and_then(|record| string(record, "kind"))
            .unwrap_or_default()
            .to_owned();
        let body_path = format!("{record_path}/body");
        if let Some(body) = bundle.pointer_mut(&body_path) {
            match kind.as_str() {
                "event_delivery" => {
                    set_string(body, "aspsurfacehash", surface_hash.clone());
                    let hash = object_hash(
                        EVENT_DOMAIN,
                        body,
                        &[
                            "aspeventhash",
                            "aspsubid",
                            "aspdeliveryid",
                            "aspattempt",
                            "aspstream",
                            "aspsequence",
                            "aspcursor",
                            "traceparent",
                            "tracestate",
                        ],
                    )?;
                    set_string(body, "aspeventhash", hash);
                }
                "receipt" => {
                    set_string(body, "grant_hash", grant_hash.clone());
                    set_string(body, "surface_hash", surface_hash.clone());
                    if let Some(parent) = string(body, "parent_receipt_hash")
                        .and_then(|hash| receipt_hash_replacements.get(hash))
                        .cloned()
                    {
                        set_string(body, "parent_receipt_hash", parent);
                    }
                    for links_name in ["approval_receipt_hashes"] {
                        if let Some(links) = member(body, links_name).and_then(Value::as_object) {
                            let replacements: Vec<(String, String)> = links
                                .iter()
                                .filter_map(|(role, value)| {
                                    let old = value.as_str()?;
                                    Some((
                                        role.clone(),
                                        receipt_hash_replacements.get(old)?.clone(),
                                    ))
                                })
                                .collect();
                            if let Some(links) =
                                body.get_mut(links_name).and_then(Value::as_object_mut)
                            {
                                for (role, hash) in replacements {
                                    links.insert(role, Value::String(hash));
                                }
                            }
                        }
                    }
                    if let Some(target) = body
                        .get("execution")
                        .and_then(|execution| string(execution, "target_receipt_hash"))
                        .and_then(|hash| receipt_hash_replacements.get(hash))
                        .cloned()
                        && let Some(execution) = body.get_mut("execution")
                    {
                        set_string(execution, "target_receipt_hash", target);
                    }
                    if let Some(policy) = body.get_mut("policy_decision") {
                        let hash = object_hash(POLICY_DOMAIN, policy, &["policy_decision_hash"])?;
                        set_string(policy, "policy_decision_hash", hash.clone());
                        set_string(body, "policy_decision_hash", hash);
                    }
                    if let Some(execution) = member(body, "execution") {
                        let hash = object_hash(EXECUTION_DOMAIN, execution, &["execution_token"])?;
                        set_string(body, "execution_hash", hash);
                    }
                    if let Some(effects) = member(body, "actual_effects") {
                        let hash = object_hash(ACTUAL_EFFECTS_DOMAIN, effects, &[])?;
                        set_string(body, "actual_effects_hash", hash);
                    }
                    let old_hash = string(body, "receipt_hash").map(str::to_owned);
                    let hash = object_hash(
                        RECEIPT_DOMAIN,
                        body,
                        &["receipt_hash", "receipt_signatures"],
                    )?;
                    set_string(body, "receipt_hash", hash.clone());
                    if let Some(old_hash) = old_hash {
                        receipt_hash_replacements.insert(old_hash, hash);
                    }
                }
                _ => {}
            }
        }
        let record = bundle
            .pointer_mut(&record_path)
            .expect("record index was resolved");
        if let Some(object) = record.as_object_mut() {
            match &prior_record_hash {
                Some(hash) => {
                    object.insert(
                        "previous_record_hash".to_owned(),
                        Value::String(hash.clone()),
                    );
                }
                None => {
                    object.remove("previous_record_hash");
                }
            }
        }
        let hash = object_hash(RECORD_DOMAIN, record, &["record_hash"])?;
        set_string(record, "record_hash", hash.clone());
        prior_record_hash = Some(hash);
    }
    let hash = object_hash(BUNDLE_DOMAIN, bundle, &["bundle_hash"])?;
    set_string(bundle, "bundle_hash", hash);
    Ok(())
}

#[derive(Debug, Serialize)]
struct GoldenReport<'a> {
    evaluation_state: &'a str,
    integrity_verdict: &'a str,
    replay_completeness: &'a str,
    verdict: &'a str,
    diagnostic_check_ids: Vec<&'a str>,
    report_hash: &'a str,
}

impl Case {
    fn id(&self) -> &str {
        match self {
            Self::Report { id, .. } | Self::ParseError { id, .. } => id,
        }
    }
}

/// Verify all embedded artifacts and execute every registered fixture/golden case.
pub(crate) fn run(repository_root: &Path) -> Result<(), ReplayError> {
    let crate_root = repository_root.join("tools/asp-replay");
    let artifacts = [
        (crate_root.join("schema/bundle.schema.json"), BUNDLE_SCHEMA),
        (crate_root.join("schema/report.schema.json"), REPORT_SCHEMA),
        (crate_root.join("schema/checks.schema.json"), CHECKS_SCHEMA),
        (crate_root.join("schema/cases.schema.json"), CASES_SCHEMA),
        (crate_root.join("checks/v1/checks.json"), CHECK_REGISTRY),
        (crate_root.join("cases/v1/cases.json"), CASE_REGISTRY),
    ];
    for (path, embedded) in &artifacts {
        if read(path)? != *embedded {
            return Err(ReplayError::SelfCheck(format!(
                "compiled artifact differs from {}",
                path.display()
            )));
        }
    }
    let bundle_schema: Value = serde_json::from_str(BUNDLE_SCHEMA)
        .map_err(|error| ReplayError::SelfCheck(error.to_string()))?;
    let report_schema: Value = serde_json::from_str(REPORT_SCHEMA)
        .map_err(|error| ReplayError::SelfCheck(error.to_string()))?;
    let checks_schema: Value = serde_json::from_str(CHECKS_SCHEMA)
        .map_err(|error| ReplayError::SelfCheck(error.to_string()))?;
    let cases_schema: Value = serde_json::from_str(CASES_SCHEMA)
        .map_err(|error| ReplayError::SelfCheck(error.to_string()))?;
    for (label, schema) in [
        ("bundle", &bundle_schema),
        ("report", &report_schema),
        ("checks", &checks_schema),
        ("cases", &cases_schema),
    ] {
        jsonschema::validator_for(schema)
            .map_err(|error| ReplayError::SelfCheck(format!("{label} schema: {error}")))?;
    }
    let checks_value = parse_strict(CHECK_REGISTRY.as_bytes())?;
    let cases_value = parse_strict(CASE_REGISTRY.as_bytes())?;
    validate_instance(&checks_schema, &checks_value, "check registry")?;
    validate_instance(&cases_schema, &cases_value, "case registry")?;
    let checks = registry()?;
    if checks.schema_version != 1 || checks.profile != CHECK_PROFILE {
        return Err(ReplayError::SelfCheck(
            "check registry metadata is not canonical".to_owned(),
        ));
    }
    let actual: Vec<&str> = checks
        .checks
        .iter()
        .map(|check| check.check_id.as_str())
        .collect();
    if actual != IMPLEMENTED_CHECKS || checks.checks.iter().any(|check| check.title.is_empty()) {
        return Err(ReplayError::SelfCheck(
            "check registry must exactly match implemented checks".to_owned(),
        ));
    }
    let cases: CaseRegistry = serde_json::from_value(cases_value)
        .map_err(|error| ReplayError::SelfCheck(error.to_string()))?;
    if cases.schema_version != 1 || cases.profile != PROFILE {
        return Err(ReplayError::SelfCheck(
            "case registry metadata is not canonical".to_owned(),
        ));
    }
    let mut ids = HashSet::new();
    let mut executable_check_coverage = HashSet::new();
    for case in cases.cases {
        if !ids.insert(case.id().to_owned()) {
            return Err(ReplayError::SelfCheck(format!(
                "duplicate case id {:?}",
                case.id()
            )));
        }
        match case {
            Case::Report {
                id,
                source,
                golden,
                evaluation_state,
                verdict,
                integrity_verdict,
                replay_completeness,
                diagnostic_check_ids,
                mutations,
                rehash_after_mutations,
            } => {
                executable_check_coverage.extend(diagnostic_check_ids.iter().cloned());
                let source_path = crate_root.join(relative_path(&source, "case source")?);
                let source_bytes = fs::read(&source_path).map_err(|source| ReplayError::Io {
                    path: source_path.display().to_string(),
                    source,
                })?;
                let bytes = if mutations.is_empty() {
                    source_bytes
                } else {
                    let mut value = parse_strict(&source_bytes)?;
                    for mutation in &mutations {
                        apply_mutation(&mut value, mutation)?;
                    }
                    if rehash_after_mutations {
                        rehash_bundle(&mut value)?;
                    }
                    serde_json::to_vec(&value)
                        .map_err(|error| ReplayError::SelfCheck(error.to_string()))?
                };
                let report = verify(&source, &bytes)
                    .map_err(|error| ReplayError::SelfCheck(format!("{id}: {error}")))?;
                let report_check_ids: Vec<&str> = report
                    .checks
                    .iter()
                    .map(|check| check.check_id.as_str())
                    .collect();
                if report_check_ids != IMPLEMENTED_CHECKS {
                    return Err(ReplayError::SelfCheck(format!(
                        "{id}: report check order differs from the implemented check profile"
                    )));
                }
                if report.verdict != verdict {
                    return Err(ReplayError::SelfCheck(format!(
                        "{id}: expected verdict {verdict:?}, got {:?}",
                        report.verdict
                    )));
                }
                if report.evaluation_state != evaluation_state {
                    return Err(ReplayError::SelfCheck(format!(
                        "{id}: expected evaluation state {evaluation_state:?}, got {:?}",
                        report.evaluation_state
                    )));
                }
                if report.integrity_verdict != integrity_verdict
                    || report.replay_completeness != replay_completeness
                {
                    return Err(ReplayError::SelfCheck(format!(
                        "{id}: orthogonal report outcomes differ from the case registry"
                    )));
                }
                let actual_check_ids: HashSet<&str> = report
                    .diagnostics
                    .iter()
                    .map(|diagnostic| diagnostic.check_id.as_str())
                    .collect();
                let expected_check_ids: HashSet<&str> =
                    diagnostic_check_ids.iter().map(String::as_str).collect();
                if actual_check_ids != expected_check_ids {
                    return Err(ReplayError::SelfCheck(format!(
                        "{id}: diagnostic check IDs differ: expected {expected_check_ids:?}, got {actual_check_ids:?}"
                    )));
                }
                let value = serde_json::to_value(&report)
                    .map_err(|error| ReplayError::SelfCheck(error.to_string()))?;
                validate_instance(&report_schema, &value, &format!("{id} report"))?;
                if let Some(golden) = golden {
                    let projection = GoldenReport {
                        evaluation_state: &report.evaluation_state,
                        integrity_verdict: &report.integrity_verdict,
                        replay_completeness: &report.replay_completeness,
                        verdict: &report.verdict,
                        diagnostic_check_ids: report
                            .diagnostics
                            .iter()
                            .map(|diagnostic| diagnostic.check_id.as_str())
                            .collect(),
                        report_hash: &report.report_hash,
                    };
                    let actual = format!(
                        "{}\n",
                        serde_json::to_string_pretty(&projection)
                            .map_err(|error| ReplayError::SelfCheck(error.to_string()))?
                    );
                    let golden_path = crate_root.join(relative_path(&golden, "golden report")?);
                    if actual != read(&golden_path)? {
                        return Err(ReplayError::SelfCheck(format!(
                            "{id}: report binding differs from {}",
                            golden_path.display()
                        )));
                    }
                }
            }
            Case::ParseError {
                id,
                source,
                error_contains,
            } => {
                let source_path = crate_root.join(relative_path(&source, "case source")?);
                let bytes = fs::read(&source_path).map_err(|source| ReplayError::Io {
                    path: source_path.display().to_string(),
                    source,
                })?;
                match verify(&source, &bytes) {
                    Err(error) if error.to_string().contains(&error_contains) => {}
                    Err(error) => {
                        return Err(ReplayError::SelfCheck(format!(
                            "{id}: error {error:?} does not contain {error_contains:?}"
                        )));
                    }
                    Ok(_) => {
                        return Err(ReplayError::SelfCheck(format!(
                            "{id}: parse-error case unexpectedly produced a report"
                        )));
                    }
                }
            }
        }
    }
    let uncovered: Vec<&str> = IMPLEMENTED_CHECKS
        .iter()
        .copied()
        .filter(|check| !executable_check_coverage.contains(*check))
        .collect();
    if !uncovered.is_empty() {
        return Err(ReplayError::SelfCheck(format!(
            "implemented checks lack executable diagnostic coverage: {uncovered:?}"
        )));
    }
    Ok(())
}
