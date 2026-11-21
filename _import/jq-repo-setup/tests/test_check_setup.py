"""Tests for jq-repo-setup/scripts/check-setup.py. Temporary repos only; no network."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.dont_write_bytecode = True  # keep __pycache__ out of the skill folder
SCRIPT = Path(__file__).resolve().parents[1] / "jq-repo-setup" / "scripts" / "check-setup.py"
spec = importlib.util.spec_from_file_location("check_setup", SCRIPT)
cs = importlib.util.module_from_spec(spec)
sys.modules["check_setup"] = cs  # dataclasses look the module up
spec.loader.exec_module(cs)

SHA = "11bd71901bbe5b1630ceea73d27597364c9af683"

NOTE = """\
schema: 1
setup:
  skill: jq-repo-setup
  date: 2026-11-17
  visibility: public
  project_type: tool
  team: solo
badges:
  openssf:
    project_id: 123
    level: passing
"""


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def write(repo, rel, text, mode=None):
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    if mode:
        p.chmod(mode)


@pytest.fixture
def repo(tmp_path):
    """A repo that passes every offline check."""
    r = tmp_path / "proj"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    write(r, ".github/repo-setup.yaml", NOTE)
    for f in ["README.md", "LICENSE", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "CHANGELOG.md",
              ".gitignore", "AGENTS.md", "docs/adr/README.md"]:
        write(r, f, "real content\n")
    write(r, "SECURITY.md", "Report privately via GitHub private vulnerability reporting.\n")
    write(r, ".githooks/commit-msg", "#!/bin/sh\n", 0o755)
    write(r, ".githooks/pre-push", "#!/bin/sh\ngitleaks git\n", 0o755)
    git(r, "config", "core.hooksPath", ".githooks")
    write(r, "Makefile", "check:\n\ttrue\n")
    write(r, ".github/workflows/ci.yml",
          f"on: [push, pull_request]\npermissions:\n  contents: read\njobs:\n  t:\n    steps:\n"
          f"      - uses: actions/checkout@{SHA} # v4.2.2\n      - uses: ./local-action\n")
    write(r, ".github/dependabot.yml",
          "version: 2\nupdates:\n  - package-ecosystem: github-actions\n    directory: /\n")
    write(r, "package.json", "{}\n")
    write(r, "package-lock.json", "{}\n")
    return r


def results(repo, **kw):
    kw.setdefault("offline", True)
    kw.setdefault("gitleaks", None)
    return {c.id: c for c in cs.run_checks(repo, **kw)}


def test_complete_repo_passes_offline(repo):
    res = results(repo)
    bad = {k: (c.status, c.detail) for k, c in res.items() if c.status not in ("pass", "skip")}
    assert bad == {}
    assert res["github-settings"].status == "skip"
    assert res["openssf-badge"].status == "skip"


def test_no_note_is_reported(repo):
    (repo / ".github/repo-setup.yaml").unlink()
    note, problems = cs.load_note(repo)
    assert note is None and problems


def test_note_missing_required_fields_fails(repo):
    write(repo, ".github/repo-setup.yaml", "schema: 1\nsetup:\n  skill: jq-repo-setup\n")
    res = results(repo)
    assert res["note"].status == "fail"
    assert "visibility" in res["note"].detail


def test_missing_foundation_files_are_named(repo):
    (repo / "CONTRIBUTING.md").unlink()
    (repo / "AGENTS.md").unlink()
    res = results(repo)
    assert res["foundations"].status == "fail"
    assert "CONTRIBUTING.md" in res["foundations"].detail and "AGENTS.md" in res["foundations"].detail


def test_claude_md_counts_as_agent_rules(repo):
    (repo / "AGENTS.md").unlink()
    write(repo, "CLAUDE.md", "rules\n")
    assert results(repo)["foundations"].status == "pass"


def test_private_repo_needs_no_licence_or_code_of_conduct(repo):
    write(repo, ".github/repo-setup.yaml", NOTE.replace("public", "private"))
    (repo / "LICENSE").unlink()
    (repo / "CODE_OF_CONDUCT.md").unlink()
    assert results(repo)["foundations"].status == "pass"


def test_placeholders_fail(repo):
    write(repo, "SECURITY.md", "Email security@example.com or <SECURITY_CONTACT>.\n")
    res = results(repo)
    assert res["placeholders"].status == "fail"
    assert "SECURITY.md" in res["placeholders"].detail


def test_hooks_missing_fail_and_not_enabled_warns(repo):
    git(repo, "config", "--unset", "core.hooksPath")
    assert results(repo)["hooks"].status == "warn"
    (repo / ".githooks/pre-push").unlink()
    assert results(repo)["hooks"].status == "fail"


def test_pre_commit_framework_counts_as_hooks(repo):
    git(repo, "config", "--unset", "core.hooksPath")
    for f in (repo / ".githooks").iterdir():
        f.unlink()
    write(repo, ".pre-commit-config.yaml", "repos: []\n")
    assert results(repo)["hooks"].status == "pass"


def test_check_target_alternatives(repo):
    (repo / "Makefile").unlink()
    assert results(repo)["check-target"].status == "fail"
    write(repo, "package.json", json.dumps({"scripts": {"check": "npm test"}}))
    assert results(repo)["check-target"].status == "pass"


def test_ci_needs_pull_request_trigger(repo):
    write(repo, ".github/workflows/ci.yml", "on: [push]\npermissions: {}\njobs: {}\n")
    assert results(repo)["ci"].status == "fail"


def test_unpinned_action_fails_but_slsa_generator_is_allowed(repo):
    wf = repo / ".github/workflows/ci.yml"
    wf.write_text(wf.read_text() + "      - uses: actions/setup-node@v4\n")
    res = results(repo)
    assert res["actions-pinned"].status == "fail"
    assert "actions/setup-node@v4" in res["actions-pinned"].detail
    wf.write_text(wf.read_text().replace("actions/setup-node@v4",
        "slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@v2.1.0"))
    assert results(repo)["actions-pinned"].status == "pass"


def test_workflow_without_top_level_permissions_fails(repo):
    write(repo, ".github/workflows/ci.yml",
          f"on: [pull_request]\njobs:\n  t:\n    steps:\n      - uses: actions/checkout@{SHA}\n")
    assert results(repo)["workflow-permissions"].status == "fail"


def test_dependency_updates_must_cover_actions(repo):
    write(repo, ".github/dependabot.yml", "version: 2\nupdates:\n  - package-ecosystem: npm\n")
    assert results(repo)["dependency-updates"].status == "fail"
    (repo / ".github/dependabot.yml").unlink()
    write(repo, "renovate.json", "{}\n")
    assert results(repo)["dependency-updates"].status == "pass"


def test_lockfile_needed_for_each_manifest(repo):
    (repo / "package-lock.json").unlink()
    res = results(repo)
    assert res["lockfile"].status == "fail" and "package.json" in res["lockfile"].detail
    (repo / "package.json").unlink()
    assert results(repo)["lockfile"].status == "skip"


def test_badge_check_uses_the_site(repo):
    def fetch(url):
        assert url.endswith("/projects/123.json")
        return {"badge_level": "passing", "badge_percentage_0": 100}
    write(repo, "README.md", "[![OpenSSF](https://www.bestpractices.dev/projects/123/badge)]"
                             "(https://www.bestpractices.dev/projects/123)\n")
    res = results(repo, offline=False, fetch=fetch, gh=lambda *a: None)
    assert res["openssf-badge"].status == "pass"


def test_badge_level_below_record_fails(repo):
    write(repo, "README.md", "https://www.bestpractices.dev/projects/123/badge\n")
    res = results(repo, offline=False, fetch=lambda u: {"badge_level": "in_progress",
                                                        "badge_percentage_0": 97},
                  gh=lambda *a: None)
    assert res["openssf-badge"].status == "fail"
    assert "97%" in res["openssf-badge"].detail


def test_badge_missing_from_readme_warns(repo):
    res = results(repo, offline=False, fetch=lambda u: {"badge_level": "passing"},
                  gh=lambda *a: None)
    assert res["openssf-badge"].status == "warn"


def test_github_settings(repo):
    git(repo, "remote", "add", "origin", "https://github.com/o/r.git")
    calls = {
        "repos/o/r": {"default_branch": "main", "visibility": "public",
                      "security_and_analysis": {"secret_scanning": {"status": "enabled"}}},
        "repos/o/r/rules/branches/main": [{"type": "pull_request"}],
        "repos/o/r/private-vulnerability-reporting": {"enabled": True},
    }
    res = results(repo, offline=False, fetch=lambda u: {"badge_level": "passing"},
                  gh=lambda path: calls.get(path))
    assert res["github-settings"].status == "pass", res["github-settings"].detail
    calls["repos/o/r/rules/branches/main"] = []
    calls["repos/o/r/private-vulnerability-reporting"] = {"enabled": False}
    d = results(repo, offline=False, fetch=lambda u: {"badge_level": "passing"},
                gh=lambda path: calls.get(path))["github-settings"]
    assert d.status == "fail"
    assert "ruleset" in d.detail and "private vulnerability reporting" in d.detail


def test_cli_exit_codes(repo, monkeypatch):
    monkeypatch.setattr(cs.shutil, "which", lambda name: None)
    assert cs.main([str(repo), "--offline"]) == 0
    (repo / "SECURITY.md").unlink()
    assert cs.main([str(repo), "--offline"]) == 1
    (repo / ".github/repo-setup.yaml").unlink()
    assert cs.main([str(repo), "--offline"]) == 2


def test_cli_json_lists_failures(repo, capsys, monkeypatch):
    monkeypatch.setattr(cs.shutil, "which", lambda name: None)
    (repo / "SECURITY.md").unlink()
    cs.main([str(repo), "--offline", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["failed"] == ["foundations"]
    assert any(c["id"] == "foundations" and "SECURITY.md" in c["detail"] for c in data["checks"])
