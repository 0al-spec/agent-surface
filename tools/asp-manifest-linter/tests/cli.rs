use std::io::Write;
use std::path::Path;
use std::process::{Command, Stdio};

fn binary() -> &'static str {
    env!("CARGO_BIN_EXE_asp-lint")
}

fn fixture(name: &str) -> String {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures")
        .join(name)
        .display()
        .to_string()
}

#[test]
fn valid_manifest_exits_zero() {
    let output = Command::new(binary())
        .args(["check", &fixture("valid.json")])
        .output()
        .unwrap();
    assert!(output.status.success());
    assert!(
        String::from_utf8(output.stdout)
            .unwrap()
            .contains("no findings")
    );
}

#[test]
fn findings_exit_one_and_emit_json_report() {
    let output = Command::new(binary())
        .args(["check", &fixture("invalid-scope.json"), "--format", "json"])
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(1));
    let report: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(report["diagnostics"][0]["rule_id"], "ASP-LINT-SCOPE-001");
}

#[test]
fn malformed_input_exits_two() {
    let mut child = Command::new(binary())
        .args(["check", "-"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(br#"{"a":1,"a":2}"#)
        .unwrap();
    let output = child.wait_with_output().unwrap();
    assert_eq!(output.status.code(), Some(2));
    assert!(
        String::from_utf8(output.stderr)
            .unwrap()
            .contains("duplicate JSON object member")
    );
}

#[test]
fn self_check_exits_zero() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(Path::parent)
        .unwrap();
    let output = Command::new(binary())
        .args(["self-check", "--root", &root.display().to_string()])
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
}
