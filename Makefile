.PHONY: yggdrasil yggdrasil-lint test

# Override if needed:
PY ?= python

yggdrasil:
	PYTHONPATH=. $(PY) scripts/gen_yggdrasil_manifest.py --repo-root . --out yggdrasil.manifest.json --source-commit $$(git rev-parse HEAD 2>/dev/null || echo unknown)

yggdrasil-lint:
	PYTHONPATH=. $(PY) scripts/yggdrasil_lint.py --manifest yggdrasil.manifest.json

test:
	pytest -q
