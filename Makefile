.PHONY: fmt lint type test check

fmt:
	ruff format .

lint:
	ruff check .

type:
	mypy .

test:
	@echo "pytest not yet configured"

check: fmt lint type test