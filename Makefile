.PHONY: test check link unlink

PY = uv run --with pyyaml --with pytest

test:
	$(PY) pytest -q openssf-common/tests

check: test
	sh -n scripts/link-skills.sh
	@for s in */SKILL.md; do head -1 "$$s" | grep -qx -- '---' || { echo "$$s: no frontmatter"; exit 1; }; done

link:
	sh scripts/link-skills.sh

unlink:
	sh scripts/link-skills.sh --unlink
