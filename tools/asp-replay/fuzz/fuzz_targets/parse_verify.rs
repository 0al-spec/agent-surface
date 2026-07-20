#![no_main]

use libfuzzer_sys::fuzz_target;

fuzz_target!(|document: &[u8]| {
    let Ok(report) = asp_replay::fuzz_support::parse_verify(document) else {
        return;
    };

    assert!(report.diagnostics.len() <= asp_replay::MAX_DIAGNOSTICS);
    let findings = report
        .checks
        .iter()
        .map(|check| check.findings)
        .sum::<usize>();
    assert_eq!(
        findings,
        report.diagnostics.len() + report.diagnostics_omitted
    );
    assert_eq!(report.claim_effect, "descriptive_only");
});
