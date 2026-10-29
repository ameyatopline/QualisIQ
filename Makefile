PYTHON ?= .venv/bin/python
.PHONY: install web test model dev e2e check
install:
	python3 -m venv .venv
	$(PYTHON) -m pip install -r requirements.lock
	npm --prefix frontend ci --no-audit --no-fund
web:
	npm --prefix frontend run build
test:
	$(PYTHON) -m pytest -q
model:
	$(PYTHON) scripts/train_model.py
dev: web
	$(PYTHON) -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
e2e: web
	npm --prefix frontend run test:e2e
check: web test
	$(PYTHON) -m pip check
	$(PYTHON) -m compileall -q app ml scripts
