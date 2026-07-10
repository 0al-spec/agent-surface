PYTHON ?= python3

.PHONY: review-build review-check

review-build:
	$(PYTHON) review/build_review.py

review-check:
	$(PYTHON) review/build_review.py --check
	node review/check_review.mjs
