use assert_cmd::Command;
use predicates::prelude::*;

const VALID: &str = "tests/fixtures/complete-session.json";
const INVALID: &str = "tests/fixtures/invalid-empty.json";
const PARSE_ERROR: &str = "tests/fixtures/invalid-duplicate.json";

#[test]
fn verify_emits_a_deterministic_valid_report() {
    let mut command = Command::cargo_bin("asp-replay").unwrap();
    command
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .args(["verify", VALID])
        .assert()
        .success()
        .stdout(predicate::str::contains("\"integrity_verdict\": \"valid\""))
        .stdout(predicate::str::contains(
            "\"replay_completeness\": \"complete\"",
        ))
        .stderr(predicate::str::is_empty());
}

#[test]
fn evaluated_invalid_bundle_uses_exit_one_and_emits_report() {
    let mut command = Command::cargo_bin("asp-replay").unwrap();
    command
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .args(["verify", INVALID])
        .assert()
        .code(1)
        .stdout(predicate::str::contains("\"verdict\": \"invalid\""))
        .stderr(predicate::str::is_empty());
}

#[test]
fn parse_failure_uses_exit_two_and_empty_stdout() {
    let mut command = Command::cargo_bin("asp-replay").unwrap();
    command
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .args(["verify", PARSE_ERROR])
        .assert()
        .code(2)
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::contains("duplicate JSON object member"));
}

#[test]
fn standard_input_is_supported() {
    let document = include_str!("fixtures/complete-session.json");
    let mut command = Command::cargo_bin("asp-replay").unwrap();
    command
        .args(["verify", "-"])
        .write_stdin(document)
        .assert()
        .success()
        .stdout(predicate::str::contains("\"verdict\": \"valid\""));
}
