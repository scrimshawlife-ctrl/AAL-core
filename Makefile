.PHONY: yggdrasil yggdrasil-lint evidence-relock test

# Override if needed:
PY ?= python

yggdrasil:
	PYTHONPATH=. $(PY) scripts/gen_yggdrasil_manifest.py --repo-root . --out yggdrasil.manifest.json --source-commit $$(git rev-parse HEAD 2>/dev/null || echo unknown)

yggdrasil-lint:
	PYTHONPATH=. $(PY) scripts/yggdrasil_lint.py --manifest yggdrasil.manifest.json

evidence-relock:
	@echo "Usage: make evidence-relock BUNDLE=path/to.bundle.json"
	@if [ -z "$$BUNDLE" ]; then echo "Missing BUNDLE=..."; exit 2; fi
	PYTHONPATH=. $(PY) scripts/evidence_relock.py --bundle "$$BUNDLE"

test:
	pytest -q
