use assert_cmd::Command;
use predicates::prelude::*;

const VALID: &str = "tests/fixtures/positive-openapi.json";
const INVALID: &str = "tests/fixtures/invalid-missing-root.json";

#[test]
fn generate_emits_only_a_candidate_after_all_bounded_checks() {
    let mut command = Command::cargo_bin("asp-api-import").unwrap();
    command
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .args(["generate", VALID])
        .assert()
        .success()
        .stdout(predicate::str::contains("\"surface_hash\""))
        .stdout(predicate::str::contains("deleteEverything").not());
}

#[test]
fn failure_uses_exit_two_and_empty_stdout() {
    let mut command = Command::cargo_bin("asp-api-import").unwrap();
    command
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .args(["generate", INVALID])
        .assert()
        .code(2)
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::contains(
            "root /x-agent-surface annotation is required",
        ));
}

#[test]
fn generate_accepts_standard_input() {
    let document = include_str!("fixtures/positive-asyncapi.json");
    let mut command = Command::cargo_bin("asp-api-import").unwrap();
    command
        .args(["generate", "-"])
        .write_stdin(document)
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "\"surface_hash\": \"sha-256:QD4eNcEWP21OP01F3K-uJpZs2UI_l9vu2yEJxN5IUgs\"",
        ))
        .stderr(predicate::str::is_empty());
}
