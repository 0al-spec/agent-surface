PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
CARGO ?= cargo

.PHONY: conformance-validate conformance-test conformance-check mock-validate mock-test mock-check manifest-lint-fmt manifest-lint-clippy manifest-lint-test manifest-lint-self-check manifest-lint-check review-build review-data-check review-test review-js-test review-check

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

manifest-lint-fmt:
	$(CARGO) fmt --all -- --check

manifest-lint-clippy:
	$(CARGO) clippy --workspace --all-targets --locked -- -D warnings

manifest-lint-test:
	$(CARGO) test --workspace --locked

manifest-lint-self-check:
	$(CARGO) run --quiet --locked -p asp-manifest-linter -- self-check --root .

manifest-lint-check: manifest-lint-fmt manifest-lint-clippy manifest-lint-test manifest-lint-self-check

review-build:
	$(PYTHON) -B review/build_review.py

review-data-check:
	$(PYTHON) -B review/build_review.py --check-data

review-test:
	$(PYTHON) -B -m unittest discover -s review/tests -p 'test_*.py'

review-js-test:
	node --test review/dashboard-state.test.mjs

review-check: conformance-check mock-check manifest-lint-check review-data-check review-test review-js-test
	$(PYTHON) -B review/build_review.py --check
	node review/check_review.mjs
