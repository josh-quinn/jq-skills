.PHONY: test check link unlink sandbox-smoke hooks

PY = uv run --no-project --with pyyaml --with pytest

test:
	$(PY) pytest -q privacy-common/tests privacy-sandbox/tests

check: test
	sh -n scripts/link-skills.sh
	sh -n scripts/sandbox-smoke.sh
	@for s in */SKILL.md; do head -1 "$$s" | grep -qx -- '---' || { echo "$$s: no frontmatter"; exit 1; }; done
	@! LC_ALL=C grep -n '[^ -~]' privacy-common/scripts/signatures.yaml || { echo "signatures.yaml: non-ASCII"; exit 1; }

# Runs a planted leaky package in a real sandbox (needs Docker); nothing leaves the machine.
sandbox-smoke:
	sh scripts/sandbox-smoke.sh

link:
	sh scripts/link-skills.sh

unlink:
	sh scripts/link-skills.sh --unlink

# Once per clone: Conventional Commits on commit, gitleaks on push.
hooks:
	git config core.hooksPath .githooks
