PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
CARGO ?= cargo
export CARGO

.PHONY: conformance-validate conformance-test conformance-check mock-validate mock-test mock-check rust-workspace-fmt rust-workspace-clippy rust-workspace-test rust-workspace-check manifest-lint-fmt manifest-lint-clippy manifest-lint-test manifest-lint-self-check manifest-lint-check api-import-self-check api-import-check replay-self-check replay-check review-build review-data-check review-test review-js-test review-check

conformance-validate:
	$(PYTHON) -B conformance/check.py validate

conformance-test:
	$(PYTHON) -B -m unittest discover -s conformance/tests -p 'test_*.py'

conformance-check: conformance-validate conformance-test

mock-validate:
	$(PYTHON) -B mocks/check.py validate

mock-test:
	$(PYTHON) -B -m unittest discover -s mocks/tests -p 'test_*.py'

mock-check: mock-validate mock-test

rust-workspace-fmt:
	$(CARGO) fmt --all -- --check

rust-workspace-clippy:
	$(CARGO) clippy --workspace --all-targets --locked -- -D warnings

rust-workspace-test:
	$(CARGO) test --workspace --locked

rust-workspace-check: rust-workspace-fmt rust-workspace-clippy rust-workspace-test

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

review-build:
	$(PYTHON) -B review/build_review.py

review-data-check:
	$(PYTHON) -B review/build_review.py --check-data

review-test:
	$(PYTHON) -B -m unittest discover -s review/tests -p 'test_*.py'

review-js-test:
	node --test review/dashboard-state.test.mjs

review-check: conformance-check mock-check manifest-lint-check api-import-check replay-check review-data-check review-test review-js-test
	$(PYTHON) -B review/build_review.py --check
	node review/check_review.mjs
