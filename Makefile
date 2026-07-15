PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: conformance-validate conformance-test conformance-check mock-validate mock-test mock-check review-build review-data-check review-test review-js-test review-check

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

review-build:
	$(PYTHON) -B review/build_review.py

review-data-check:
	$(PYTHON) -B review/build_review.py --check-data

review-test:
	$(PYTHON) -B -m unittest discover -s review/tests -p 'test_*.py'

review-js-test:
	node --test review/dashboard-state.test.mjs

review-check: conformance-check mock-check review-data-check review-test review-js-test
	$(PYTHON) -B review/build_review.py --check
	node review/check_review.mjs
