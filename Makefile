PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
CARGO ?= cargo
export CARGO

PUBLICATION_BASE_REF ?= origin/main
PUBLICATION_CANDIDATE_REF ?= HEAD
HYPERPROMPT_BIN ?= .tools/hyperprompt/hyperprompt

REPLAY_FUZZ_TOOLCHAIN ?= nightly-2026-07-01
REPLAY_FUZZ_TARGETS ?= parse_verify structured_bundle
REPLAY_FUZZ_SEED ?= 1095979603
REPLAY_FUZZ_RUNS ?= 1000
REPLAY_FUZZ_MAX_TOTAL_TIME ?= 30
REPLAY_FUZZ_INPUT_TIMEOUT ?= 5
REPLAY_FUZZ_RSS_LIMIT_MB ?= 1024
REPLAY_FUZZ_OUTER_TIMEOUT ?= 300
REPLAY_FUZZ_TIMEOUT_CMD ?= timeout
REPLAY_FUZZ_PARSE_MAX_LEN ?= 262144
REPLAY_FUZZ_STRUCTURED_MAX_LEN ?= 4096

.PHONY: publication-assembly-toolchain publication-assembly-validate publication-assembly-test publication-assembly-build publication-assembly-check publication-materialization-generate publication-materialization-check publication-ownership-validate publication-ownership-test publication-ownership-check publication-validate publication-history-check publication-test publication-check conformance-validate conformance-test conformance-check mock-validate mock-test mock-check vertical-slice-validate vertical-slice-test vertical-slice-check rust-workspace-fmt rust-workspace-clippy rust-workspace-test rust-workspace-check rust-tooling-check manifest-lint-fmt manifest-lint-clippy manifest-lint-test manifest-lint-self-check manifest-lint-check api-import-self-check api-import-check replay-self-check replay-check replay-fuzz-smoke rfc-toc rfc-toc-check review-build review-data-check review-test review-js-test review-check

publication-assembly-toolchain:
	$(PYTHON) -B publication/assembly/check.py install-toolchain --destination "$(HYPERPROMPT_BIN)"

publication-assembly-validate:
	$(PYTHON) -B publication/assembly/check.py validate

publication-assembly-test:
	$(PYTHON) -B -m unittest discover -s publication/assembly/tests -p 'test_*.py'

publication-assembly-build:
	$(PYTHON) -B publication/assembly/check.py build --compiler "$(HYPERPROMPT_BIN)"

publication-assembly-check: publication-assembly-validate publication-assembly-test publication-assembly-build

publication-materialization-generate:
	$(PYTHON) -B publication/migration/materialize.py generate --compiler "$(HYPERPROMPT_BIN)"

publication-materialization-check:
	$(PYTHON) -B publication/migration/materialize.py check --compiler "$(HYPERPROMPT_BIN)"

publication-ownership-validate:
	$(PYTHON) -B publication/migration/check.py validate

publication-ownership-test:
	$(PYTHON) -B -m unittest discover -s publication/migration/tests -p 'test_*.py'

publication-ownership-check: publication-ownership-validate publication-ownership-test

publication-validate:
	$(PYTHON) -B publication/check.py validate

publication-history-check:
	$(PYTHON) -B publication/check.py validate-history --base-ref "$(PUBLICATION_BASE_REF)" --candidate-ref "$(PUBLICATION_CANDIDATE_REF)"

publication-test:
	$(PYTHON) -B -m unittest discover -s publication/tests -p 'test_*.py'

publication-check: publication-materialization-check publication-assembly-check publication-ownership-check publication-validate publication-history-check publication-test

conformance-validate:
	$(PYTHON) -B conformance/check.py validate

conformance-test:
	$(PYTHON) -B -m unittest discover -s conformance/tests -p 'test_*.py' --durations 20

conformance-check: conformance-validate conformance-test

mock-validate:
	$(PYTHON) -B mocks/check.py validate

mock-test:
	$(PYTHON) -B -m unittest discover -s mocks/tests -p 'test_*.py'

mock-check: mock-validate mock-test

vertical-slice-validate:
	$(PYTHON) -B reference/vertical-slice/check.py validate-evidence

vertical-slice-test:
	$(PYTHON) -B -m unittest discover -s reference/vertical-slice/tests -p 'test_*.py'

vertical-slice-check: vertical-slice-test vertical-slice-validate

rust-workspace-fmt:
	$(CARGO) fmt --all -- --check

rust-workspace-clippy:
	$(CARGO) clippy --workspace --all-targets --locked -- -D warnings

rust-workspace-test:
	$(CARGO) test --workspace --locked

rust-workspace-check: rust-workspace-fmt rust-workspace-clippy rust-workspace-test

rust-tooling-check: rust-workspace-check manifest-lint-self-check api-import-self-check replay-self-check

manifest-lint-fmt: rust-workspace-fmt

manifest-lint-clippy: rust-workspace-clippy

manifest-lint-test: rust-workspace-test

manifest-lint-self-check:
	$(CARGO) run --quiet --locked -p asp-manifest-linter -- self-check --root .

manifest-lint-check: rust-workspace-check manifest-lint-self-check

api-import-self-check:
	$(CARGO) run --quiet --locked -p asp-api-importer -- self-check --root .

api-import-check: rust-workspace-check api-import-self-check

replay-self-check:
	$(CARGO) run --quiet --locked -p asp-replay-tool -- self-check --root .

replay-check: rust-workspace-check replay-self-check

rfc-toc:
	$(PYTHON) -B review/rfc_toc.py

rfc-toc-check:
	$(PYTHON) -B review/rfc_toc.py --check

replay-fuzz-smoke:
	@set -eu; \
	for target in $(REPLAY_FUZZ_TARGETS); do \
		case "$${target}" in \
			parse_verify) max_len=$(REPLAY_FUZZ_PARSE_MAX_LEN) ;; \
			structured_bundle) max_len=$(REPLAY_FUZZ_STRUCTURED_MAX_LEN) ;; \
			*) echo "Unsupported replay fuzz target: $${target}" >&2; exit 2 ;; \
		esac; \
		echo "Fuzzing replay target $${target}"; \
		(cd tools/asp-replay/fuzz && \
			$(REPLAY_FUZZ_TIMEOUT_CMD) --signal=TERM --kill-after=10s $(REPLAY_FUZZ_OUTER_TIMEOUT)s \
				$(CARGO) +$(REPLAY_FUZZ_TOOLCHAIN) fuzz run "$${target}" "corpus/$${target}" -- \
				-dict=dictionaries/replay.dict \
				-max_len=$${max_len} \
				-seed=$(REPLAY_FUZZ_SEED) \
				-runs=$(REPLAY_FUZZ_RUNS) \
				-max_total_time=$(REPLAY_FUZZ_MAX_TOTAL_TIME) \
				-timeout=$(REPLAY_FUZZ_INPUT_TIMEOUT) \
				-rss_limit_mb=$(REPLAY_FUZZ_RSS_LIMIT_MB) \
				-print_final_stats=1); \
	done

review-build: rfc-toc
	$(PYTHON) -B review/build_review.py

review-data-check:
	$(PYTHON) -B review/build_review.py --check-data

review-test:
	$(PYTHON) -B -m unittest discover -s review/tests -p 'test_*.py'

review-js-test:
	node --test review/dashboard-state.test.mjs

review-check: publication-check conformance-check mock-check vertical-slice-check rust-tooling-check rfc-toc-check review-data-check review-test review-js-test
	$(PYTHON) -B review/build_review.py --check
	node review/check_review.mjs
