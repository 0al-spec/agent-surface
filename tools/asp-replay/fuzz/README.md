# ASP Replay fuzz workspace

This is an isolated `cargo-fuzz` workspace for the passive Replay Tool. It is
deliberately excluded from the repository Cargo workspace so fuzz-only
dependencies and the nested `Cargo.lock` do not change the production lockfile.

The production crate keeps its Rust 1.97 boundary. Running libFuzzer requires a
nightly toolchain and the pinned cargo-fuzz frontend:

```sh
rustup toolchain install nightly
cargo install cargo-fuzz --version 0.13.2 --locked
```

Run the bounded targets from this directory:

```sh
cargo +nightly fuzz run parse_verify corpus/parse_verify -- \
  -dict=dictionaries/replay.dict -max_len=262144

cargo +nightly fuzz run structured_bundle corpus/structured_bundle -- \
  -dict=dictionaries/replay.dict -max_len=4096
```

For a deterministic smoke run, add `-runs=1000`. Crash and timeout inputs are
written below `artifacts/`; minimized and discovered corpus entries are written
below `corpus/` and ignored unless deliberately promoted to a named `seed-*`
regression input.

## Target boundaries

- `parse_verify` passes arbitrary bytes through the strict parser and bounded
  verifier. Parse errors and deterministic invalid reports are expected.
- `structured_bundle` starts from one of the checked-in synthetic valid replay
  fixtures, applies at most sixteen typed mutations, recomputes the replay hash
  chain through the fuzz-only bridge, and then verifies the result. This keeps
  semantic lifecycle, event, acknowledgement, gap, and receipt paths reachable
  instead of spending the campaign only on preflight hashes. The same rehashed
  bundle also exercises fail-closed full-profile composition. A synthetic
  seven-provider plan makes `eligible_valid`, `eligible_incomplete`, native
  rejection, and unavailable-coverage paths reachable while the target checks
  the report schema, composition digest, and provider evidence binding.

Both targets call `asp_replay::fuzz_support`, which is available only under
`cfg(fuzzing)`. The bridge is linked statically by cargo-fuzz; there is no
runtime plugin discovery. The targets assert only bounded report invariants and
do not expand the verifier's conformance claims.

Fuzz corpora and artifacts retain their exact input bytes. Use only synthetic
or approved test bundles; never seed the workspace with production events,
receipts, credentials, user data, or other confidential evidence.
