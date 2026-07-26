use asp_reference_vertical_app::{canonical_digest, parse_unique_json};
use base64::Engine as _;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::collections::BTreeMap;
use std::fs;
use std::io::{BufRead, BufReader, Read, Write};
use std::net::{TcpListener, TcpStream};
#[cfg(unix)]
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use std::time::Duration;

const COMMENT_ACTION: &str = "comment.create";
const READ_ACTION: &str = "task.read";
const APP_PROTOCOL: &str = "asp-reference-app/1";
const MAX_JSON_LINE_BYTES: usize = 1_048_576;
const IO_TIMEOUT: Duration = Duration::from_secs(5);

#[derive(Debug, Clone)]
struct Grant {
    runtime_id: String,
    agent_id: String,
    credential: String,
    actions: Vec<String>,
    active: bool,
}

#[derive(Debug, Clone)]
struct IdempotencyRecord {
    input_hash: String,
    execution_hash: String,
    response: Value,
}

#[derive(Debug)]
struct AppState {
    control_credential: String,
    next_grant: u64,
    next_receipt: u64,
    grants: BTreeMap<String, Grant>,
    idempotency: BTreeMap<(String, String, String), IdempotencyRecord>,
    executions: BTreeMap<(String, String, String), String>,
    comments: Vec<Value>,
    receipts: Vec<Value>,
    denied_count: u64,
}

impl AppState {
    fn new(control_credential: String) -> Self {
        Self {
            control_credential,
            next_grant: 0,
            next_receipt: 0,
            grants: BTreeMap::new(),
            idempotency: BTreeMap::new(),
            executions: BTreeMap::new(),
            comments: Vec::new(),
            receipts: Vec::new(),
            denied_count: 0,
        }
    }
}

#[derive(Debug, Serialize)]
struct PublicState<'a> {
    schema_version: u8,
    boundary_id: &'static str,
    grant_count: usize,
    active_grant_count: usize,
    effect_count: usize,
    receipt_count: usize,
    denied_count: u64,
    comments: &'a [Value],
    receipts: &'a [Value],
}

#[derive(Debug, Deserialize)]
struct ServerRequest {
    #[serde(default)]
    operation: Option<String>,
    #[serde(default)]
    protocol: Option<String>,
    #[serde(default)]
    request_id: Option<String>,
    #[serde(default)]
    execution_id: Option<String>,
    #[serde(default)]
    runtime_id: Option<String>,
    #[serde(default)]
    agent_id: Option<String>,
    #[serde(default)]
    grant_id: Option<String>,
    #[serde(default)]
    credential: Option<String>,
    #[serde(default)]
    actions: Option<Vec<String>>,
    #[serde(default)]
    action_id: Option<String>,
    #[serde(default)]
    idempotency_key: Option<String>,
    #[serde(default)]
    input: Option<Value>,
    #[serde(default)]
    control_credential: Option<String>,
}

fn response_ok(result: Value) -> Value {
    json!({"schema_version": 1, "ok": true, "result": result})
}

fn response_error(code: &str) -> Value {
    json!({"schema_version": 1, "ok": false, "error": code})
}

fn manifest() -> Value {
    json!({
        "manifest_version": "agent-surface/0.1",
        "surface_id": "https://github.com/0al-spec/agent-surface/reference/task-comments/v1",
        "surface_version": "1.0.0",
        "boundary_id": "reference/application",
        "resources": [
            {
                "resource_id": "task",
                "read_action": READ_ACTION
            }
        ],
        "actions": [
            {
                "action_id": READ_ACTION,
                "mode": "read",
                "risk": ["read"]
            },
            {
                "action_id": COMMENT_ACTION,
                "mode": "commit",
                "risk": ["write", "external_side_effect"],
                "idempotency": "required",
                "input_schema": {
                    "type": "object",
                    "additionalProperties": false,
                    "required": ["task_id", "text"],
                    "properties": {
                        "task_id": {"type": "string", "minLength": 1, "maxLength": 128},
                        "text": {"type": "string", "minLength": 1, "maxLength": 256}
                    }
                },
                "input_normalization": {
                    "profile": "asp-json-normalization-v1",
                    "defaults": {},
                    "unordered_arrays": []
                },
                "receipt": "application"
            }
        ]
    })
}

fn public_state(state: &AppState) -> PublicState<'_> {
    PublicState {
        schema_version: 1,
        boundary_id: "reference/application",
        grant_count: state.grants.len(),
        active_grant_count: state.grants.values().filter(|grant| grant.active).count(),
        effect_count: state.comments.len(),
        receipt_count: state.receipts.len(),
        denied_count: state.denied_count,
        comments: &state.comments,
        receipts: &state.receipts,
    }
}

fn save_state(path: &Path, state: &AppState) -> Result<(), String> {
    let encoded = serde_json::to_vec_pretty(&public_state(state))
        .map_err(|error| format!("cannot encode state: {error}"))?;
    let temporary = path.with_extension("tmp");
    fs::write(&temporary, encoded).map_err(|error| format!("cannot write state: {error}"))?;
    fs::rename(&temporary, path).map_err(|error| format!("cannot publish state: {error}"))
}

fn required(value: Option<String>, name: &str) -> Result<String, Value> {
    value.ok_or_else(|| response_error(&format!("missing_{name}")))
}

fn generate_grant_credential() -> Result<String, Value> {
    let mut secret = [0_u8; 32];
    getrandom::fill(&mut secret).map_err(|_| response_error("credential_generation_failed"))?;
    Ok(format!(
        "reference-private-v1.{}",
        base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(secret)
    ))
}

fn require_control(state: &mut AppState, request: &ServerRequest) -> Result<(), Value> {
    if request.control_credential.as_deref() == Some(state.control_credential.as_str()) {
        Ok(())
    } else {
        state.denied_count += 1;
        Err(response_error("control_unauthorized"))
    }
}

fn handle(state: &mut AppState, request: ServerRequest) -> (Value, bool) {
    let operation = request
        .operation
        .clone()
        .or_else(|| request.action_id.as_ref().map(|_| "invoke".to_owned()))
        .unwrap_or_default();
    match operation.as_str() {
        "manifest" => (response_ok(manifest()), false),
        "issue_grant" => {
            if let Err(error) = require_control(state, &request) {
                return (error, false);
            }
            let runtime_id = match required(request.runtime_id, "runtime_id") {
                Ok(value) => value,
                Err(error) => return (error, false),
            };
            let agent_id = match required(request.agent_id, "agent_id") {
                Ok(value) => value,
                Err(error) => return (error, false),
            };
            let actions = request.actions.unwrap_or_default();
            if actions.is_empty()
                || actions
                    .iter()
                    .any(|action| !matches!(action.as_str(), READ_ACTION | COMMENT_ACTION))
            {
                state.denied_count += 1;
                return (response_error("grant_scope_invalid"), false);
            }
            let credential = match generate_grant_credential() {
                Ok(value) => value,
                Err(error) => return (error, false),
            };
            state.next_grant += 1;
            let grant_id = format!("grant-{}", state.next_grant);
            state.grants.insert(
                grant_id.clone(),
                Grant {
                    runtime_id: runtime_id.clone(),
                    agent_id: agent_id.clone(),
                    credential: credential.clone(),
                    actions: actions.clone(),
                    active: true,
                },
            );
            (
                response_ok(json!({
                    "grant_id": grant_id,
                    "credential": credential,
                    "runtime_id": runtime_id,
                    "agent_id": agent_id,
                    "actions": actions,
                    "status": "active"
                })),
                false,
            )
        }
        "revoke" => {
            if let Err(error) = require_control(state, &request) {
                return (error, false);
            }
            let grant_id = match required(request.grant_id, "grant_id") {
                Ok(value) => value,
                Err(error) => return (error, false),
            };
            match state.grants.get_mut(&grant_id) {
                Some(grant) if grant.active => {
                    grant.active = false;
                    (
                        response_ok(json!({
                            "grant_id": grant_id,
                            "status": "revoked",
                            "revocation_fence": "established"
                        })),
                        false,
                    )
                }
                Some(_) => (
                    response_ok(json!({
                        "grant_id": grant_id,
                        "status": "revoked",
                        "replay": true
                    })),
                    false,
                ),
                None => (response_error("grant_unknown"), false),
            }
        }
        "invoke" => {
            if request.protocol.as_deref() != Some(APP_PROTOCOL) {
                state.denied_count += 1;
                return (response_error("protocol_invalid"), false);
            }
            let _request_id = match required(request.request_id, "request_id") {
                Ok(value) if !value.is_empty() => value,
                _ => return (response_error("request_invalid"), false),
            };
            let execution_id = match required(request.execution_id, "execution_id") {
                Ok(value) if !value.is_empty() => value,
                _ => return (response_error("execution_invalid"), false),
            };
            let runtime_id = match required(request.runtime_id, "runtime_id") {
                Ok(value) => value,
                Err(error) => return (error, false),
            };
            let grant_id = match required(request.grant_id, "grant_id") {
                Ok(value) => value,
                Err(error) => return (error, false),
            };
            let agent_id = match required(request.agent_id, "agent_id") {
                Ok(value) => value,
                Err(error) => return (error, false),
            };
            let credential = match required(request.credential, "credential") {
                Ok(value) => value,
                Err(error) => return (error, false),
            };
            let action_id = match required(request.action_id, "action_id") {
                Ok(value) => value,
                Err(error) => return (error, false),
            };
            let input = request.input.unwrap_or_else(|| json!({}));
            let Some(grant) = state.grants.get(&grant_id) else {
                state.denied_count += 1;
                return (response_error("grant_unknown"), false);
            };
            if !grant.active {
                state.denied_count += 1;
                return (response_error("grant_revoked"), false);
            }
            if grant.runtime_id != runtime_id
                || grant.agent_id != agent_id
                || grant.credential != credential
            {
                state.denied_count += 1;
                return (response_error("grant_delegate_invalid"), false);
            }
            if !grant.actions.contains(&action_id) {
                state.denied_count += 1;
                return (response_error("action_not_granted"), false);
            }
            if action_id != COMMENT_ACTION {
                return (
                    response_ok(json!({
                        "action_id": action_id,
                        "tasks": [{"task_id": "task-1", "title": "Review ASP slice"}]
                    })),
                    false,
                );
            }
            let idempotency_key = match required(request.idempotency_key, "idempotency_key") {
                Ok(value) => value,
                Err(error) => return (error, false),
            };
            let Some(input_object) = input.as_object() else {
                state.denied_count += 1;
                return (response_error("input_schema_invalid"), false);
            };
            let expected_input_members = ["task_id", "text"];
            if input_object.len() != expected_input_members.len()
                || expected_input_members
                    .iter()
                    .any(|name| !input_object.contains_key(*name))
            {
                state.denied_count += 1;
                return (response_error("input_schema_invalid"), false);
            }
            let Some(task_id) = input_object.get("task_id").and_then(Value::as_str) else {
                state.denied_count += 1;
                return (response_error("input_schema_invalid"), false);
            };
            let Some(text) = input_object.get("text").and_then(Value::as_str) else {
                state.denied_count += 1;
                return (response_error("input_schema_invalid"), false);
            };
            if task_id.is_empty()
                || task_id.chars().count() > 128
                || text.is_empty()
                || text.chars().count() > 256
            {
                state.denied_count += 1;
                return (response_error("input_schema_invalid"), false);
            }
            let input_hash = match canonical_digest("ASP-REFERENCE-COMMENT-INPUT-V1", &input) {
                Ok(value) => value,
                Err(_) => return (response_error("input_invalid"), false),
            };
            let execution = json!({
                "execution_id": execution_id,
                "grant_id": grant_id,
                "runtime_id": runtime_id,
                "agent_id": agent_id,
                "action_id": action_id,
                "idempotency_key": idempotency_key,
                "input_hash": input_hash
            });
            let execution_hash =
                canonical_digest("ASP-REFERENCE-EXECUTION-V1", &execution).unwrap_or_default();
            let idempotency_scope = (grant_id.clone(), action_id.clone(), idempotency_key.clone());
            if let Some(record) = state.idempotency.get(&idempotency_scope) {
                if record.input_hash == input_hash && record.execution_hash == execution_hash {
                    return (response_ok(record.response.clone()), false);
                }
                state.denied_count += 1;
                return (response_error("idempotency_conflict"), false);
            }
            let execution_scope = (grant_id.clone(), action_id.clone(), execution_id.clone());
            if state.executions.contains_key(&execution_scope) {
                state.denied_count += 1;
                return (response_error("idempotency_conflict"), false);
            }
            let comment_id = format!("comment-{}", state.comments.len() + 1);
            let comment = json!({
                "comment_id": comment_id,
                "task_id": task_id,
                "text": text
            });
            state.comments.push(comment.clone());
            state.next_receipt += 1;
            let receipt = json!({
                "receipt_id": format!("app-receipt-{}", state.next_receipt),
                "producer_role": "application",
                "boundary_id": "reference/application",
                "execution_hash": execution_hash,
                "effect": {
                    "kind": "comment_created",
                    "comment_id": comment_id
                }
            });
            state.receipts.push(receipt.clone());
            let result = json!({
                "action_id": COMMENT_ACTION,
                "comment": comment,
                "receipt": receipt
            });
            state.idempotency.insert(
                idempotency_scope,
                IdempotencyRecord {
                    input_hash,
                    execution_hash,
                    response: result.clone(),
                },
            );
            state.executions.insert(execution_scope, idempotency_key);
            (response_ok(result), false)
        }
        "state" => {
            if let Err(error) = require_control(state, &request) {
                return (error, false);
            }
            (
                response_ok(serde_json::to_value(public_state(state)).unwrap_or_default()),
                false,
            )
        }
        "shutdown" => {
            if let Err(error) = require_control(state, &request) {
                return (error, false);
            }
            (response_ok(json!({"stopped": true})), true)
        }
        _ => {
            state.denied_count += 1;
            (response_error("operation_unknown"), false)
        }
    }
}

fn serve_connection(
    mut stream: TcpStream,
    state: &mut AppState,
) -> Result<bool, Box<dyn std::error::Error>> {
    stream.set_read_timeout(Some(IO_TIMEOUT))?;
    stream.set_write_timeout(Some(IO_TIMEOUT))?;
    let mut line = String::new();
    BufReader::new(stream.try_clone()?)
        .take((MAX_JSON_LINE_BYTES + 1) as u64)
        .read_line(&mut line)?;
    if line.is_empty() || line.len() > MAX_JSON_LINE_BYTES || !line.ends_with('\n') {
        return Err("request must be one bounded JSON line".into());
    }
    let request: ServerRequest = parse_unique_json(&line)?;
    let (response, stop) = handle(state, request);
    serde_json::to_writer(&mut stream, &response)?;
    stream.write_all(b"\n")?;
    stream.flush()?;
    Ok(stop)
}

fn parse_args() -> Result<(String, PathBuf, PathBuf, PathBuf), String> {
    let mut listen = "127.0.0.1:0".to_owned();
    let mut ready_file = None;
    let mut state_file = None;
    let mut control_secret_file = None;
    let mut args = std::env::args().skip(1);
    while let Some(argument) = args.next() {
        match argument.as_str() {
            "--listen" => {
                listen = args
                    .next()
                    .ok_or_else(|| "--listen requires a value".to_owned())?;
            }
            "--ready-file" => {
                ready_file = Some(PathBuf::from(
                    args.next()
                        .ok_or_else(|| "--ready-file requires a value".to_owned())?,
                ));
            }
            "--state-file" => {
                state_file = Some(PathBuf::from(
                    args.next()
                        .ok_or_else(|| "--state-file requires a value".to_owned())?,
                ));
            }
            "--control-secret-file" => {
                control_secret_file =
                    Some(PathBuf::from(args.next().ok_or_else(|| {
                        "--control-secret-file requires a value".to_owned()
                    })?));
            }
            _ => return Err(format!("unknown argument: {argument}")),
        }
    }
    Ok((
        listen,
        ready_file.ok_or_else(|| "--ready-file is required".to_owned())?,
        state_file.ok_or_else(|| "--state-file is required".to_owned())?,
        control_secret_file.ok_or_else(|| "--control-secret-file is required".to_owned())?,
    ))
}

fn load_control_credential(path: &Path) -> Result<String, String> {
    let metadata = fs::symlink_metadata(path)
        .map_err(|error| format!("cannot inspect control secret: {error}"))?;
    if !metadata.file_type().is_file() || metadata.file_type().is_symlink() {
        return Err("control secret must be a regular non-symlink file".to_owned());
    }
    #[cfg(unix)]
    if metadata.permissions().mode() & 0o777 != 0o600 {
        return Err("control secret must have mode 0600".to_owned());
    }
    let secret = fs::read_to_string(path)
        .map_err(|error| format!("cannot read control secret: {error}"))?
        .trim()
        .to_owned();
    if secret.len() < 32 || secret.len() > 512 {
        return Err("control secret must contain 32 to 512 characters".to_owned());
    }
    Ok(secret)
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let (listen, ready_file, state_file, control_secret_file) =
        parse_args().map_err(|error| format!("invalid arguments: {error}"))?;
    let control_credential = load_control_credential(&control_secret_file)
        .map_err(|error| format!("invalid control credential: {error}"))?;
    let listener = TcpListener::bind(&listen)?;
    let address = listener.local_addr()?.to_string();
    fs::write(&ready_file, format!("{address}\n"))?;
    let mut state = AppState::new(control_credential);
    save_state(&state_file, &state).map_err(|error| format!("initial state: {error}"))?;
    for incoming in listener.incoming() {
        let result = serve_connection(incoming?, &mut state);
        save_state(&state_file, &state).map_err(|error| format!("state update: {error}"))?;
        match result {
            Ok(true) => break,
            Ok(false) => {}
            Err(error) => eprintln!("request rejected: {error}"),
        }
    }
    Ok(())
}

fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        std::process::exit(2);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const CONTROL: &str = "test-control-credential-at-least-32-bytes";

    fn request(value: Value) -> ServerRequest {
        serde_json::from_value(value).unwrap()
    }

    #[test]
    fn duplicate_input_members_are_rejected_before_dispatch() {
        let error = parse_unique_json::<ServerRequest>(
            r#"{"operation":"invoke","input":{"task_id":"task-1","text":"first","text":"second"}}"#,
        )
        .unwrap_err();
        assert!(
            error
                .to_string()
                .contains("duplicate JSON object member \"text\"")
        );
    }

    #[test]
    fn exact_replay_does_not_repeat_effect() {
        let mut state = AppState::new(CONTROL.to_owned());
        let (grant, _) = handle(
            &mut state,
            request(json!({
                "operation": "issue_grant",
                "control_credential": CONTROL,
                "runtime_id": "runtime-a",
                "agent_id": "agent-a",
                "actions": [COMMENT_ACTION]
            })),
        );
        let result = grant["result"].clone();
        let invoke = json!({
            "operation": "invoke",
            "protocol": APP_PROTOCOL,
            "request_id": "request-a",
            "execution_id": "execution-a",
            "runtime_id": "runtime-a",
            "agent_id": "agent-a",
            "grant_id": result["grant_id"],
            "credential": result["credential"],
            "action_id": COMMENT_ACTION,
            "idempotency_key": "key-a",
            "input": {"task_id": "task-1", "text": "hello"}
        });
        let original = handle(&mut state, request(invoke.clone())).0;
        assert!(original["ok"] == true);
        let mut replay_request = invoke.clone();
        replay_request["request_id"] = json!("request-b");
        let replay = handle(&mut state, request(replay_request)).0;
        assert_eq!(replay, original);

        let mut conflicting_execution = invoke.clone();
        conflicting_execution["request_id"] = json!("request-c");
        conflicting_execution["execution_id"] = json!("execution-b");
        let conflict = handle(&mut state, request(conflicting_execution)).0;
        assert_eq!(conflict["error"], "idempotency_conflict");

        let mut conflicting_idempotency_key = invoke;
        conflicting_idempotency_key["request_id"] = json!("request-d");
        conflicting_idempotency_key["idempotency_key"] = json!("key-b");
        let reverse_conflict = handle(&mut state, request(conflicting_idempotency_key)).0;
        assert_eq!(reverse_conflict["error"], "idempotency_conflict");
        assert_eq!(state.comments.len(), 1);
        assert_eq!(state.receipts.len(), 1);
    }

    #[test]
    fn idempotency_key_is_scoped_to_grant_and_action() {
        let mut state = AppState::new(CONTROL.to_owned());
        let mut grant_results = Vec::new();
        for (runtime_id, agent_id) in [("runtime-a", "agent-a"), ("runtime-b", "agent-b")] {
            let (grant, _) = handle(
                &mut state,
                request(json!({
                    "operation": "issue_grant",
                    "control_credential": CONTROL,
                    "runtime_id": runtime_id,
                    "agent_id": agent_id,
                    "actions": [COMMENT_ACTION]
                })),
            );
            grant_results.push((runtime_id, agent_id, grant["result"].clone()));
        }

        let first_credential = grant_results[0].2["credential"].as_str().unwrap();
        let second_credential = grant_results[1].2["credential"].as_str().unwrap();
        assert_ne!(first_credential, second_credential);
        assert!(!first_credential.contains("grant-1"));
        assert!(!first_credential.contains("runtime-a"));

        for (index, (runtime_id, agent_id, grant)) in grant_results.into_iter().enumerate() {
            let (response, _) = handle(
                &mut state,
                request(json!({
                    "operation": "invoke",
                    "protocol": APP_PROTOCOL,
                    "request_id": format!("request-{index}"),
                    "execution_id": format!("execution-{index}"),
                    "runtime_id": runtime_id,
                    "agent_id": agent_id,
                    "grant_id": grant["grant_id"],
                    "credential": grant["credential"],
                    "action_id": COMMENT_ACTION,
                    "idempotency_key": "shared-key",
                    "input": {"task_id": "task-1", "text": "hello"}
                })),
            );
            assert_eq!(response["ok"], true);
        }

        assert_eq!(state.comments.len(), 2);
        assert_eq!(state.receipts.len(), 2);
    }

    #[test]
    fn control_and_delegate_boundaries_fail_closed() {
        let mut state = AppState::new(CONTROL.to_owned());
        let (unauthorized, _) = handle(
            &mut state,
            request(json!({
                "operation": "issue_grant",
                "runtime_id": "runtime-a",
                "agent_id": "agent-a",
                "actions": [COMMENT_ACTION]
            })),
        );
        assert_eq!(unauthorized["error"], "control_unauthorized");
        assert!(state.grants.is_empty());

        let (grant, _) = handle(
            &mut state,
            request(json!({
                "operation": "issue_grant",
                "control_credential": CONTROL,
                "runtime_id": "runtime-a",
                "agent_id": "agent-a",
                "actions": [COMMENT_ACTION]
            })),
        );
        let result = &grant["result"];
        let (substitution, _) = handle(
            &mut state,
            request(json!({
                "operation": "invoke",
                "protocol": APP_PROTOCOL,
                "request_id": "request-substitution",
                "execution_id": "execution-substitution",
                "runtime_id": "runtime-a",
                "agent_id": "agent-b",
                "grant_id": result["grant_id"],
                "credential": result["credential"],
                "action_id": COMMENT_ACTION,
                "idempotency_key": "key-substitution",
                "input": {"task_id": "task-1", "text": "hello"}
            })),
        );
        assert_eq!(substitution["error"], "grant_delegate_invalid");
        assert!(state.comments.is_empty());
        assert!(state.receipts.is_empty());

        let (overparameterized, _) = handle(
            &mut state,
            request(json!({
                "operation": "invoke",
                "protocol": APP_PROTOCOL,
                "request_id": "request-overparameterized",
                "execution_id": "execution-overparameterized",
                "runtime_id": "runtime-a",
                "agent_id": "agent-a",
                "grant_id": result["grant_id"],
                "credential": result["credential"],
                "action_id": COMMENT_ACTION,
                "idempotency_key": "key-overparameterized",
                "input": {
                    "task_id": "task-1",
                    "text": "hello",
                    "admin": true
                }
            })),
        );
        assert_eq!(overparameterized["error"], "input_schema_invalid");
        assert!(state.comments.is_empty());
        assert!(state.receipts.is_empty());

        let (unicode_boundary, _) = handle(
            &mut state,
            request(json!({
                "operation": "invoke",
                "protocol": APP_PROTOCOL,
                "request_id": "request-unicode-boundary",
                "execution_id": "execution-unicode-boundary",
                "runtime_id": "runtime-a",
                "agent_id": "agent-a",
                "grant_id": result["grant_id"],
                "credential": result["credential"],
                "action_id": COMMENT_ACTION,
                "idempotency_key": "key-unicode-boundary",
                "input": {
                    "task_id": "task-1",
                    "text": "é".repeat(256)
                }
            })),
        );
        assert_eq!(unicode_boundary["ok"], true);
        assert_eq!(state.comments.len(), 1);
        assert_eq!(state.receipts.len(), 1);
    }
}
