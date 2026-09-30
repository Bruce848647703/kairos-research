PY ?= python3

.PHONY: help bootstrap test lint format clean check
help:
	@echo "targets: bootstrap test lint format clean check"

bootstrap:
	$(PY) -m venv .venv
	. .venv/bin/activate && $(PY) -m pip install -U pip && pip install -e ".[dev]"

test:
	$(PY) -m pytest -q

# 离线校验：笔记齐全、来源标注、key_findings.csv 可读、README 索引文件存在
check: test
	$(PY) -c "import csv;print(sum(1 for _ in csv.reader(open('data/key_findings.csv'))),'rows in key_findings')"

lint:
	@if command -v ruff >/dev/null 2>&1; then ruff check .; else echo "pip install ruff 后再 lint"; fi

format:
	@if command -v ruff >/dev/null 2>&1; then ruff format .; else echo "pip install ruff 后再 format"; fi

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name '*.egg-info' -prune -exec rm -rf {} +
	rm -rf .pytest_cache build dist
