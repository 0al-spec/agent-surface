PYTHON ?= python3

.PHONY: review-build review-data-check review-test review-check

review-build:
	$(PYTHON) -B review/build_review.py

review-data-check:
	$(PYTHON) -B review/build_review.py --check-data

review-test:
	$(PYTHON) -B -m unittest discover -s review/tests -p 'test_*.py'

review-check: review-data-check review-test
	$(PYTHON) -B review/build_review.py --check
	node review/check_review.mjs
