"""Score records, CSV storage, legacy migration, data paths and preferences. All paths are temporary."""
import hashlib
import os
from pathlib import Path

import pytest

from space_invaders import paths, preferences, scores
from space_invaders.scores import (HEADER, MigrationError, ScoreFileError, ScoreRecord, ScoreStore, decode_legacy,
                                   parse_legacy, rank, sanitize_name)

REPO_SCORES = Path(__file__).resolve().parent.parent / "scores.txt"


def rec(run_id, score, mode="solo", level=1, ruleset="modern-v1", name="n"):
    return ScoreRecord(run_id, name, score, mode, level, ruleset)


def csv_text(*rows):
    return "\n".join([",".join(HEADER)] + [",".join(r) for r in rows]) + "\n"


# -- names and records ------------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [("  Ada ", "Ada"), ("", "Anonymous"), ("   ", "Anonymous"),
                                          ("a\x00b\nc", "abc"), ("é" * 30, "é" * 24)])
def test_sanitize_name(raw, expected):
    assert sanitize_name(raw) == expected


def test_round_trip_commas_and_unicode(tmp_path):
    store = ScoreStore(tmp_path)
    record = rec("r1", 5, name='Zoë, "the" ace')
    assert store.save(record)
    assert scores.read_scores(store.path) == ([record], [])
    assert store.path.read_bytes().startswith(b"run_id,name,score,mode,level,ruleset\n")


def test_missing_file_is_empty(tmp_path):
    assert scores.read_scores(tmp_path / "none.csv") == ([], [])


@pytest.mark.parametrize("row,message", [
    (["a", "n", "-1", "solo", "1", "modern-v1"], "score"),
    (["a", "n", "1.5", "solo", "1", "modern-v1"], "score"),
    (["a", "n", "1", "duo", "1", "modern-v1"], "mode"),
    (["a", "n", "1", "solo", "0", "modern-v1"], "level"),
    (["a", "n", "1", "solo", "1", "Modern V1"], "ruleset"),
    (["", "n", "1", "solo", "1", "modern-v1"], "run_id"),
    (["a", "n", "1", "solo"], "fields"),
])
def test_invalid_rows_are_reported_with_line_numbers(tmp_path, row, message):
    path = tmp_path / "scores.csv"
    path.write_text(csv_text(["ok", "n", "3", "solo", "2", "modern-v1"], row), encoding="utf-8")
    records, warnings = scores.read_scores(path)
    assert [r.run_id for r in records] == ["ok"]
    assert len(warnings) == 1 and warnings[0].startswith("row 3") and message in warnings[0]


@pytest.mark.parametrize("content", [b"bad,header\n", b"", "run_id,name\xff".encode("latin-1")])
def test_structural_errors_raise(tmp_path, content):
    path = tmp_path / "scores.csv"
    path.write_bytes(content)
    with pytest.raises(ScoreFileError):
        scores.read_scores(path)


def test_ranking_filters_and_orders():
    records = [rec("a", 5, level=2), rec("b", 9, level=1), rec("c", 5, level=4), rec("d", 5, level=2),
               rec("e", 50, mode="coop"), rec("f", 50, ruleset="classic-v1"),
               ScoreRecord("g", "x", 5, "solo", "unknown", "modern-v1")]
    ranked = rank(records, "solo", "modern-v1")
    assert [r.run_id for r in ranked] == ["b", "c", "a", "d", "g"]
    assert [r.run_id for r in rank(records, "coop", "modern-v1")] == ["e"]
    many = [rec(str(i), i) for i in range(15)]
    assert [r.score for r in rank(many, "solo", "modern-v1")] == list(range(14, 4, -1))


# -- saving -----------------------------------------------------------------------
def test_save_is_idempotent_per_run_id(tmp_path):
    store = ScoreStore(tmp_path)
    assert store.save(rec("r1", 5))
    assert not store.save(rec("r1", 5))
    assert store.save(rec("r2", 7))
    assert [r.run_id for r in scores.read_scores(store.path)[0]] == ["r1", "r2"]


def test_failed_replace_preserves_destination_and_retry_succeeds(tmp_path, monkeypatch):
    store = ScoreStore(tmp_path)
    store.save(rec("r1", 5))
    before = store.path.read_bytes()
    real_replace = os.replace
    monkeypatch.setattr(scores.os, "replace", lambda *a: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError):
        store.save(rec("r2", 7))
    assert store.path.read_bytes() == before
    assert [p.name for p in tmp_path.iterdir()] == ["scores.csv"]     # temporary file cleaned up
    monkeypatch.setattr(scores.os, "replace", real_replace)
    assert store.save(rec("r2", 7))
    assert [r.run_id for r in scores.read_scores(store.path)[0]] == ["r1", "r2"]


def test_invalid_rows_are_backed_up_before_rewrite(tmp_path):
    store = ScoreStore(tmp_path)
    tmp_path.mkdir(exist_ok=True)
    original = csv_text(["ok", "n", "3", "solo", "2", "modern-v1"], ["bad", "n", "x", "solo", "2", "modern-v1"])
    store.path.write_text(original, encoding="utf-8")
    store.save(rec("new", 1))
    backups = list(tmp_path.glob("scores.csv.bak-*"))
    assert len(backups) == 1 and backups[0].read_text(encoding="utf-8") == original
    assert [r.run_id for r in scores.read_scores(store.path)[0]] == ["ok", "new"]


def test_backup_failure_aborts_save(tmp_path, monkeypatch):
    store = ScoreStore(tmp_path)
    original = csv_text(["bad", "n", "x", "solo", "2", "modern-v1"])
    store.path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(scores, "backup_file", lambda p: (_ for _ in ()).throw(OSError("read-only")))
    with pytest.raises(OSError):
        store.save(rec("new", 1))
    assert store.path.read_text(encoding="utf-8") == original


def test_structurally_broken_file_is_never_overwritten(tmp_path):
    store = ScoreStore(tmp_path)
    store.path.write_bytes(b"garbage\xff\n")
    with pytest.raises(ScoreFileError):
        store.save(rec("new", 1))
    assert store.path.read_bytes() == b"garbage\xff\n"


# -- legacy scores.txt and migration ------------------------------------------------
def test_parse_legacy_keeps_commas_and_skips_bad_lines():
    records, warnings = parse_legacy("(test, 100)\n(a, b, 7)\nnonsense\n(x, -3)\n\n")
    assert [(r.name, r.score, r.mode, r.level, r.ruleset) for r in records] == [
        ("test", 100, "legacy", "unknown", "legacy"), ("a, b", 7, "legacy", "unknown", "legacy")]
    assert [w.split(":")[0] for w in warnings] == ["legacy line 3", "legacy line 4"]


@pytest.mark.parametrize("name,codec", [("Иван", "cp1251"), ("José", "cp1252")])
def test_non_utf8_legacy_needs_explicit_encoding(name, codec):
    data = f"({name}, 5)\n".encode(codec)
    text, confirmed, note = decode_legacy(data)
    assert not confirmed and "unconfirmed" in note
    text, confirmed, _ = decode_legacy(data, codec)
    assert confirmed and parse_legacy(text)[0][0].name == name


def test_wrong_override_stays_unconfirmed():
    data = "(Иван, 5)\n".encode("cp1251")
    assert decode_legacy(data, "ascii")[1] is False
    assert decode_legacy(data, "no-such-codec")[1] is False


def _legacy(tmp_path, data):
    legacy = tmp_path / "repo" / "scores.txt"
    legacy.parent.mkdir()
    legacy.write_bytes(data)
    return legacy


def test_migration_imports_and_retains_original(tmp_path):
    legacy = _legacy(tmp_path, b"(test, 100)\n(a, b, 7)\nbroken\n")
    digest = hashlib.sha256(legacy.read_bytes()).hexdigest()
    store = ScoreStore(tmp_path / "data", legacy)
    assert store.migration_pending
    warnings = store.migrate()
    assert len(warnings) == 1 and not store.migration_pending
    assert [r.name for r in scores.read_scores(store.path)[0]] == ["test", "a, b"]
    assert hashlib.sha256(legacy.read_bytes()).hexdigest() == digest
    assert store.migrate() == []                 # existing destination always wins; no repeat import
    legacy.write_bytes(b"(late, 1)\n")
    ScoreStore(tmp_path / "data", legacy).migrate()
    assert len(scores.read_scores(store.path)[0]) == 2


def test_unconfirmed_migration_blocks_save_until_override(tmp_path):
    raw = "(Иван, 5)\n".encode("cp1251")
    legacy = _legacy(tmp_path, raw)
    store = ScoreStore(tmp_path / "data", legacy)
    with pytest.raises(MigrationError):
        store.migrate()
    records, notices = store.load()                  # display-only view still works
    assert records[0].score == 5 and "unconfirmed" in notices[0]
    with pytest.raises(MigrationError):
        store.save(rec("r1", 3))                     # save after failed migration fails ...
    assert not store.path.exists()                   # ... and does not create the destination
    assert legacy.read_bytes() == raw
    restarted = ScoreStore(tmp_path / "data", legacy, "cp1251")
    restarted.migrate()
    assert [r.name for r in scores.read_scores(restarted.path)[0]] == ["Иван"]


def test_save_performs_pending_migration_in_same_write(tmp_path, monkeypatch):
    legacy = _legacy(tmp_path, b"(old, 9)\n")
    store = ScoreStore(tmp_path / "data", legacy)
    assert store.save(rec("r1", 3))
    assert [r.name for r in scores.read_scores(store.path)[0]] == ["old", "n"]


@pytest.mark.parametrize("tail", ['old,Ada,9,solo,1,"modern-v1\n',
                                  'q,"Ada,9,solo,1,modern-v1\nlost,Bo,5,solo,1,modern-v1\n'])
def test_unterminated_quotes_are_structural_errors(tmp_path, tail):
    store = ScoreStore(tmp_path)
    original = (csv_text(["ok", "n", "3", "solo", "2", "modern-v1"]) + tail).encode("utf-8")
    store.path.write_bytes(original)
    with pytest.raises(ScoreFileError):
        scores.read_scores(store.path)
    with pytest.raises(ScoreFileError):
        store.save(rec("new", 1))
    assert store.path.read_bytes() == original and not list(tmp_path.glob("*.bak-*"))


def test_unreadable_legacy_file_is_a_score_file_error(tmp_path, monkeypatch):
    legacy = _legacy(tmp_path, b"(old, 9)\n")
    store = ScoreStore(tmp_path / "data", legacy)
    real = Path.read_bytes
    monkeypatch.setattr(Path, "read_bytes",
                        lambda self: (_ for _ in ()).throw(PermissionError("denied")) if self == legacy else real(self))
    with pytest.raises(MigrationError):
        store.migrate()
    with pytest.raises(ScoreFileError):
        store.load()
    with pytest.raises(MigrationError):
        store.save(rec("r1", 1))
    assert not store.path.exists()


def test_migration_notice_reports_skipped_lines(tmp_path):
    legacy = _legacy(tmp_path, b"(old, 9)\nbroken\n")
    store = ScoreStore(tmp_path / "data", legacy)
    assert store.migration_notice() == ""
    store.migrate()
    assert "1 unreadable line(s) skipped" in store.migration_notice() and str(legacy) in store.migration_notice()
    via_save = ScoreStore(tmp_path / "data2", legacy)
    via_save.save(rec("r1", 1))
    assert "1 unreadable line(s) skipped" in via_save.migration_notice()


# -- paths --------------------------------------------------------------------------
def test_data_dir_override_and_validation(tmp_path):
    assert paths.data_dir({"SPACE_INVADERS_DATA_DIR": str(tmp_path)}) == tmp_path
    for bad in ("", "relative/dir"):
        with pytest.raises(ValueError):
            paths.data_dir({"SPACE_INVADERS_DATA_DIR": bad})
    afile = tmp_path / "file"
    afile.write_text("x")
    with pytest.raises(ValueError):
        paths.data_dir({"SPACE_INVADERS_DATA_DIR": str(afile)})


def test_platform_data_dirs(tmp_path):
    home = tmp_path / "home"
    assert paths.data_dir({"LOCALAPPDATA": r"C:\L"}, "win32", home) == Path(r"C:\L") / "SpaceInvaders"
    assert paths.data_dir({}, "win32", home) == home / "AppData" / "Local" / "SpaceInvaders"
    assert paths.data_dir({}, "darwin", home) == home / "Library" / "Application Support" / "SpaceInvaders"
    assert paths.data_dir({"XDG_DATA_HOME": "/x"}, "linux", home) == Path("/x") / "space-invaders"
    assert paths.data_dir({}, "linux", home) == home / ".local" / "share" / "space-invaders"
    assert not home.exists()                          # computing a path never creates it


def test_resource_root_contains_media():
    root = paths.resource_root()
    assert (root / "assets" / "player.png").is_file() and (root / "sounds" / "laser-shot.mp3").is_file()


# -- preferences ----------------------------------------------------------------------
def test_preferences_round_trip_and_defaults(tmp_path):
    path = tmp_path / "d" / "settings.json"
    assert preferences.load(path) == (preferences.Preferences(), "")
    assert preferences.Preferences().music_volume == 0.055
    value = preferences.Preferences(0.3, 0.5, True)
    preferences.save(path, value)
    assert preferences.load(path) == (value, "")


@pytest.mark.parametrize("content", ["{not json", "[1, 2]", "\xff"])
def test_malformed_preferences_fall_back(tmp_path, content):
    path = tmp_path / "settings.json"
    path.write_bytes(content.encode("latin-1"))
    prefs, notice = preferences.load(path)
    assert prefs == preferences.Preferences() and notice


def test_preference_values_are_clamped_or_defaulted():
    prefs = preferences.from_dict({"music_volume": 7, "effects_volume": "loud", "reduced_effects": "yes"})
    assert prefs == preferences.Preferences(1.0, 1.0, False)


def test_unwritable_preferences_raise(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    with pytest.raises(OSError):
        preferences.save(blocker / "settings.json", preferences.Preferences())
