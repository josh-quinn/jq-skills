.PHONY: check test link unlink install-shell uninstall-shell

test:
	uv run -q --no-project --with pyyaml --with pytest pytest -q tests
	zsh tests/test-git-init-prompt.zsh
	sh tests/test-install-shell.sh

check: test
	sh -n scripts/link-skills.sh scripts/install-shell.sh
	zsh -n jq-repo-setup/scripts/git-init-prompt.zsh
	python3 -c "import ast, sys; ast.parse(open(sys.argv[1]).read())" jq-repo-setup/scripts/check-setup.py
	@for s in */SKILL.md; do head -1 "$$s" | grep -qx -- '---' || { echo "$$s: no frontmatter"; exit 1; }; done

link:
	sh scripts/link-skills.sh

unlink:
	sh scripts/link-skills.sh --unlink

install-shell:
	sh scripts/install-shell.sh

uninstall-shell:
	sh scripts/install-shell.sh --uninstall
