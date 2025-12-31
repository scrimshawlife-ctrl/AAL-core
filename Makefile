.PHONY: yggdrasil yggdrasil-lint bridge-patch-lint bridge-unlockability-lint evidence-relock test

# Override if needed:
PY ?= python

yggdrasil:
	PYTHONPATH=. $(PY) scripts/gen_yggdrasil_manifest.py --repo-root . --out yggdrasil.manifest.json --source-commit $$(git rev-parse HEAD 2>/dev/null || echo unknown)

yggdrasil-lint:
	PYTHONPATH=. $(PY) scripts/yggdrasil_lint.py --manifest yggdrasil.manifest.json

bridge-patch-lint:
	PYTHONPATH=. $(PY) scripts/bridge_patch_lint.py --manifest yggdrasil.manifest.json

bridge-unlockability-lint:
	PYTHONPATH=. $(PY) scripts/bridge_unlockability_lint.py --manifest yggdrasil.manifest.json

evidence-relock:
	@echo "Usage: make evidence-relock BUNDLE=path/to.bundle.json"
	@if [ -z "$$BUNDLE" ]; then echo "Missing BUNDLE=..."; exit 2; fi
	PYTHONPATH=. $(PY) scripts/evidence_relock.py --bundle "$$BUNDLE"

test:
	pytest -q

tuning-plane-test:
	pytest -q \
		tests/test_tuning_plane_validator.py \
		tests/test_tuning_plane_hot_apply.py \
		tests/test_stabilization_store.py \
		tests/test_rent_paid.py \
		tests/test_promoted_tune_requires_evidence.py

docs:
	@echo "Docs present: docs/TUNING_PLANE.md"
