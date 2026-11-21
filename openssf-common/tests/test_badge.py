import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import badge  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def criteria_dir(tmp_path):
    d = tmp_path / "criteria"
    d.mkdir()
    for f in FIXTURES.iterdir():
        (d / f.name).write_text(f.read_text())
    return d


def keys(items):
    return [c["key"] for c in items]


def good_answers():
    return {
        "level": "passing",
        "answers": {
            "description_good": {"status": "Met", "justification": "README opens with it.", "evidence": "README.md:1"},
            "contribution": {
                "status": "Met",
                "justification": "CONTRIBUTING.md. https://github.com/o/r/blob/main/CONTRIBUTING.md",
                "evidence": "CONTRIBUTING.md exists",
            },
            "documentation_basics": {"status": "Met", "justification": "docs/README.md", "evidence": "docs/README.md"},
            "know_secure_design": {
                "status": "Met",
                "justification": "The maintainer applies least privilege.",
                "evidence": "the user confirmed",
                "asked_user": True,
            },
            "crypto_pfs": {"status": "N/A", "justification": "No cryptography."},
            "static_analysis": {"status": "Met", "justification": "CodeQL in CI.", "evidence": ".github/workflows/codeql.yml"},
            "test_most": {"status": "Unmet", "justification": "Coverage is 40%."},
        },
    }


# --- criteria -------------------------------------------------------------


def test_lists_a_metal_level_in_order_without_obsolete_or_future(criteria_dir):
    items = badge.load_criteria(criteria_dir, "passing")
    assert keys(items) == [
        "description_good",
        "contribution",
        "documentation_basics",
        "know_secure_design",
        "crypto_pfs",
        "static_analysis",
        "test_most",
    ]


def test_criterion_carries_flags_group_and_plain_text(criteria_dir):
    c = {c["key"]: c for c in badge.load_criteria(criteria_dir, "passing")}["contribution"]
    assert c["category"] == "MUST"
    assert c["met_url_required"] is True
    assert c["na_allowed"] is False
    assert c["group"] == "Basics / Basic project website content"
    assert c["description"] == "The information on how to contribute MUST explain the contribution process."
    assert c["details"] == "Projects should use pull requests."


def test_lists_a_baseline_level_with_original_ids(criteria_dir):
    items = badge.load_criteria(criteria_dir, "baseline-1")
    assert keys(items) == ["osps_ac_01_01", "osps_le_03_01"]
    assert items[0]["original_id"] == "OSPS-AC-01.01"
    assert items[1]["met_url_required"] is True


def test_unknown_level_is_rejected(criteria_dir):
    with pytest.raises(SystemExit):
        badge.load_criteria(criteria_dir, "platinum")


# --- config ---------------------------------------------------------------


def test_config_is_created_with_defaults_under_the_override_root(tmp_path, monkeypatch):
    monkeypatch.setenv("JQ_TOOLS_CONFIG", str(tmp_path / "cfg"))
    cfg = badge.load_config()
    path = tmp_path / "cfg" / "openssf-badge-skills" / "config.yaml"
    assert path.exists()
    assert cfg["data_dir"] == str(Path("~/development/openssf-badges").expanduser())


def test_config_written_by_the_user_is_read_and_never_rewritten(tmp_path, monkeypatch):
    monkeypatch.setenv("JQ_TOOLS_CONFIG", str(tmp_path))
    path = tmp_path / "openssf-badge-skills" / "config.yaml"
    path.parent.mkdir(parents=True)
    text = "# mine\ndata_dir: ~/elsewhere\n"
    path.write_text(text)
    assert badge.load_config()["data_dir"] == str(Path("~/elsewhere").expanduser())
    assert path.read_text() == text


def test_init_creates_the_work_dir_and_snapshots_criteria(tmp_path, monkeypatch):
    monkeypatch.setenv("JQ_TOOLS_CONFIG", str(tmp_path / "cfg"))
    (tmp_path / "cfg" / "openssf-badge-skills").mkdir(parents=True)
    (tmp_path / "cfg" / "openssf-badge-skills" / "config.yaml").write_text(f"data_dir: {tmp_path / 'data'}\n")
    out = badge.init_workdir("my proj", "passing", repo_url=None, criteria_from=FIXTURES, lookup=False)
    work = tmp_path / "data" / "my-proj" / "passing"
    assert out["workdir"] == str(work)
    assert (work / "criteria" / "criteria.yml").exists()
    assert "description_good" in (work / "gaps.md").read_text()
    # a second init keeps the gap table the agent has been filling in
    (work / "gaps.md").write_text("edited")
    badge.init_workdir("my proj", "passing", repo_url=None, criteria_from=FIXTURES, lookup=False)
    assert (work / "gaps.md").read_text() == "edited"


# --- gap table ------------------------------------------------------------


def test_gap_table_lists_every_criterion_with_the_sites_current_status(criteria_dir):
    items = badge.load_criteria(criteria_dir, "passing")
    project = {"contribution_status": "Met", "static_analysis_status": "Unmet"}
    md = badge.render_gaps(items, "passing", project=project, source={"ref": "abc123"})
    for c in items:
        assert f"| {c['key']} " in md
    assert "| contribution | MUST | U | Met |" in md
    assert "| static_analysis | MUST | NJ | Unmet |" in md
    assert "| description_good | MUST |  | ? |" in md
    assert "abc123" in md


def test_gap_table_reads_baseline_status_by_original_id(criteria_dir):
    items = badge.load_criteria(criteria_dir, "baseline-1")
    md = badge.render_gaps(items, "baseline-1", project={"OSPS-AC-01.01_status": "Met"}, source={})
    assert "| osps_ac_01_01 | MUST | N | Met |" in md


# --- answers check --------------------------------------------------------


def check(criteria_dir, answers, level="passing"):
    return badge.check_answers(badge.load_criteria(criteria_dir, level), answers)


def test_complete_honest_answers_pass(criteria_dir):
    result = check(criteria_dir, good_answers())
    assert result["errors"] == []
    assert result["blocking"] == []


def test_every_criterion_must_be_answered(criteria_dir):
    a = good_answers()
    del a["answers"]["static_analysis"]
    assert any("static_analysis" in e and "missing" in e for e in check(criteria_dir, a)["errors"])


def test_unknown_keys_are_errors(criteria_dir):
    a = good_answers()
    a["answers"]["made_up"] = {"status": "Met", "justification": "x", "evidence": "y"}
    assert any("made_up" in e for e in check(criteria_dir, a)["errors"])


def test_status_must_be_one_the_form_accepts(criteria_dir):
    a = good_answers()
    a["answers"]["test_most"]["status"] = "Partly"
    assert any("test_most" in e for e in check(criteria_dir, a)["errors"])


def test_na_is_rejected_where_the_form_has_no_na_option(criteria_dir):
    a = good_answers()
    a["answers"]["description_good"] = {"status": "N/A", "justification": "x"}
    assert any("description_good" in e and "N/A" in e for e in check(criteria_dir, a)["errors"])


def test_na_needs_a_justification_where_required(criteria_dir):
    a = good_answers()
    a["answers"]["crypto_pfs"]["justification"] = ""
    assert any("crypto_pfs" in e for e in check(criteria_dir, a)["errors"])


def test_met_needs_a_url_where_the_site_requires_one(criteria_dir):
    a = good_answers()
    a["answers"]["contribution"]["justification"] = "CONTRIBUTING.md explains it."
    assert any("contribution" in e and "URL" in e for e in check(criteria_dir, a)["errors"])


def test_met_needs_a_justification_where_required(criteria_dir):
    a = good_answers()
    a["answers"]["static_analysis"]["justification"] = " "
    assert any("static_analysis" in e for e in check(criteria_dir, a)["errors"])


def test_no_met_without_evidence(criteria_dir):
    a = good_answers()
    del a["answers"]["description_good"]["evidence"]
    assert any("description_good" in e and "evidence" in e for e in check(criteria_dir, a)["errors"])


def test_statements_about_the_person_must_come_from_the_user(criteria_dir):
    a = good_answers()
    del a["answers"]["know_secure_design"]["asked_user"]
    assert any("know_secure_design" in e and "user" in e for e in check(criteria_dir, a)["errors"])


def test_should_unmet_needs_a_justification(criteria_dir):
    a = good_answers()
    a["answers"]["crypto_pfs"] = {"status": "Unmet", "justification": ""}
    assert any("crypto_pfs" in e for e in check(criteria_dir, a)["errors"])


def test_must_that_is_not_met_blocks_the_badge(criteria_dir):
    a = good_answers()
    a["answers"]["static_analysis"] = {"status": "Unmet", "justification": "None yet."}
    result = check(criteria_dir, a)
    assert result["errors"] == []
    assert result["blocking"] == ["static_analysis"]


def test_unknown_status_on_a_must_blocks_and_warns(criteria_dir):
    a = good_answers()
    a["answers"]["description_good"] = {"status": "?"}
    result = check(criteria_dir, a)
    assert "description_good" in result["blocking"]
    assert any("description_good" in w for w in result["warnings"])


def test_summary_counts_by_category_and_status(criteria_dir):
    s = check(criteria_dir, good_answers())["summary"]
    assert s["MUST"] == {"Met": 5}
    assert s["SHOULD"] == {"N/A": 1}
    assert s["SUGGESTED"] == {"Unmet": 1}


# --- proposal URLs --------------------------------------------------------


def params(url):
    return {k: v[0] for k, v in parse_qs(urlsplit(url).query, keep_blank_values=True).items()}


def test_proposal_url_for_a_known_project(criteria_dir):
    urls = badge.proposal_urls(good_answers(), level="passing", project_id=42)
    assert len(urls) == 1
    u = urlsplit(urls[0])
    assert (u.scheme, u.netloc, u.path) == ("https", "www.bestpractices.dev", "/en/projects/42/passing/edit")
    p = params(urls[0])
    assert p["contribution_status"] == "Met"
    assert p["contribution_justification"].endswith("/CONTRIBUTING.md")
    assert "overrides" not in p


def test_unknown_answers_are_not_proposed_because_they_would_reset_the_field(criteria_dir):
    a = good_answers()
    a["answers"]["test_most"] = {"status": "?"}
    assert "test_most_status" not in params(badge.proposal_urls(a, level="passing", project_id=42)[0])


def test_changed_existing_answers_are_forced_and_unchanged_ones_are_left_alone(criteria_dir):
    project = {
        "description_good_status": "Met",
        "description_good_justification": "README opens with it.",
        "test_most_status": "Met",
        "test_most_justification": "old",
        "contribution_status": "?",
    }
    p = params(badge.proposal_urls(good_answers(), level="passing", project_id=42, project=project)[0])
    forced = set(p["overrides"].split(","))
    assert forced == {"test_most_status"}
    assert "description_good_status" not in p  # already the same on the site


def test_a_justification_only_change_is_forced(criteria_dir):
    project = {"contribution_status": "Met", "contribution_justification": "no url"}
    p = params(badge.proposal_urls(good_answers(), level="passing", project_id=42, project=project)[0])
    assert "contribution_status" in p["overrides"].split(",")


def test_long_proposals_are_split_into_several_urls(criteria_dir):
    a = good_answers()
    for v in a["answers"].values():
        if v.get("justification"):
            v["justification"] = v["justification"] + " " + "word " * 60
    urls = badge.proposal_urls(a, level="passing", project_id=42, max_length=900)
    assert len(urls) > 1
    assert all(len(u) <= 900 for u in urls)
    proposed = set()
    for u in urls:
        proposed |= {k for k in params(u) if k.endswith("_status")}
    assert proposed == {f"{k}_status" for k in a["answers"]}


def test_proposal_url_by_repo_url_when_there_is_no_project_id(criteria_dir):
    url = badge.proposal_urls(good_answers(), level="passing", repo_url="https://github.com/o/r")[0]
    u = urlsplit(url)
    assert u.path == "/en/projects"
    p = params(url)
    assert p["as"] == "edit"
    assert p["url"] == "https://github.com/o/r"
    assert p["section"] == "passing"


# --- CLI ------------------------------------------------------------------


def test_cli_check_exits_non_zero_on_errors(criteria_dir, tmp_path, capsys):
    a = good_answers()
    del a["answers"]["description_good"]["evidence"]
    f = tmp_path / "answers.yaml"
    f.write_text(json.dumps(a))  # JSON is valid YAML
    code = badge.main(["check", "--criteria", str(criteria_dir), str(f)])
    assert code == 1
    assert "description_good" in capsys.readouterr().out


def test_cli_closed_pipe_is_not_an_error(monkeypatch):
    # `badge.py list | head` closes stdout early; that isn't a failure.
    def boom(argv=None):
        raise BrokenPipeError

    monkeypatch.setattr(badge, "main", boom)
    monkeypatch.setattr(badge.os, "dup2", lambda *a: None)
    assert badge.cli([]) == 0
