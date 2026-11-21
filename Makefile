.PHONY: test coverage lint check link unlink sandbox-smoke hooks install-shell uninstall-shell

PY = uv run --no-project --with pyyaml --with pytest

test:
	$(PY) pytest -q privacy-common/tests privacy-sandbox/tests openssf-common/tests jq-repo-setup/tests
	zsh jq-repo-setup/tests/test-git-init-prompt.zsh
	sh jq-repo-setup/tests/test-install-shell.sh

# Line coverage of the helper scripts (the number to quote for the OpenSSF test_most criterion).
coverage:
	uv run -q --no-project --with pyyaml --with pytest --with pytest-cov pytest -q privacy-common/tests privacy-sandbox/tests openssf-common/tests jq-repo-setup/tests --cov=privacy-common/scripts --cov=privacy-sandbox/scripts --cov=privacy-sandbox/assets --cov=openssf-common/scripts --cov=jq-repo-setup/scripts --cov-report=term
	@rm -f .coverage

lint:
	uv run -q --no-project --with ruff==0.17.6 ruff check .

check: test lint
	sh -n scripts/link-skills.sh
	sh -n scripts/sandbox-smoke.sh
	sh -n scripts/install-shell.sh
	zsh -n jq-repo-setup/scripts/git-init-prompt.zsh
	python3 -c "import ast, sys; ast.parse(open(sys.argv[1]).read())" jq-repo-setup/scripts/check-setup.py
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

# jq-repo-setup's git-init prompt: one marked block in ~/.zshrc that sources the wrapper.
install-shell:
	sh scripts/install-shell.sh

uninstall-shell:
	sh scripts/install-shell.sh --uninstall
