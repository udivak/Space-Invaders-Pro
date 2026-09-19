"""Score records: validation, UTF-8 CSV storage, ranking and legacy scores.txt migration.

Scope: a single running game writes the file; there is no multi-process locking.
"""
import csv
import io
import os
import re
import tempfile
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

HEADER = ["run_id", "name", "score", "mode", "level", "ruleset"]
MODES = ("solo", "coop", "legacy")
UNKNOWN_LEVEL = "unknown"
NAME_LIMIT = 24
LEGACY_ENCODING_ENV = "SPACE_INVADERS_LEGACY_ENCODING"
_RULESET_RE = re.compile(r"^[a-z0-9-]{1,32}$")


class ScoreFileError(Exception):
    """The score file cannot be read or parsed reliably; it must not be overwritten."""


class MigrationError(Exception):
    """Legacy scores could not be migrated; the destination was not created."""


@dataclass(frozen=True)
class ScoreRecord:
    run_id: str
    name: str
    score: int
    mode: str
    level: object      # positive int, or UNKNOWN_LEVEL for legacy rows
    ruleset: str

    def to_row(self):
        return [self.run_id, self.name, str(self.score), self.mode, str(self.level), self.ruleset]


def sanitize_name(name):
    cleaned = "".join(ch for ch in name if unicodedata.category(ch) != "Cc").strip()
    return cleaned[:NAME_LIMIT].strip() or "Anonymous"


def validate_record(row):
    if len(row) != len(HEADER):
        raise ValueError(f"expected {len(HEADER)} fields, found {len(row)}")
    run_id, name, score, mode, level, ruleset = row
    if not run_id:
        raise ValueError("empty run_id")
    if not re.fullmatch(r"\d+", score):
        raise ValueError(f"score must be a non-negative integer, found {score[:20]!r}")
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}")
    if level != UNKNOWN_LEVEL:
        if not re.fullmatch(r"\d+", level) or int(level) < 1:
            raise ValueError(f"level must be a positive integer or {UNKNOWN_LEVEL}, found {level!r}")
        level = int(level)
    if not _RULESET_RE.fullmatch(ruleset):
        raise ValueError(f"invalid ruleset {ruleset!r}")
    return ScoreRecord(run_id, name, int(score), mode, level, ruleset)


def parse_csv(text):
    """Return (records, warnings). Raises ScoreFileError for structural problems."""
    try:
        rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except csv.Error as error:
        raise ScoreFileError(f"score file is not valid CSV: {error}") from error
    if not rows:
        raise ScoreFileError("score file is empty (missing header)")
    if rows[0] != HEADER:
        raise ScoreFileError(f"unexpected score file header {rows[0]!r}")
    records, warnings, seen = [], [], set()
    for number, row in enumerate(rows[1:], start=2):
        if not row:
            continue
        try:
            record = validate_record(row)
        except ValueError as error:
            warnings.append(f"row {number}: {error}")
            continue
        if record.run_id in seen:
            warnings.append(f"row {number}: duplicate run_id {record.run_id}")
            continue
        seen.add(record.run_id)
        records.append(record)
    return records, warnings


def read_scores(path):
    """Missing file means empty. Encoding, structure and I/O failures raise ScoreFileError."""
    path = Path(path)
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return [], []
    except OSError as error:
        raise ScoreFileError(f"cannot read {path}: {error}") from error
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ScoreFileError(f"{path} is not valid UTF-8: {error}") from error
    return parse_csv(text)


def rank(records, mode, ruleset, limit=10):
    """Descending score, then level (unknown below known), then original order."""
    selected = [r for r in records if r.mode == mode and r.ruleset == ruleset]
    known = lambda r: (r.level if r.level != UNKNOWN_LEVEL else 0)
    return sorted(selected, key=lambda r: (-r.score, -known(r)))[:limit]


def buckets(records):
    seen = []
    for r in records:
        if (r.mode, r.ruleset) not in seen:
            seen.append((r.mode, r.ruleset))
    return seen


def format_csv(records):
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HEADER)
    for record in records:
        writer.writerow(record.to_row())
    return buffer.getvalue()


def atomic_write_bytes(path, data):
    """Write to a temporary file in the same directory, fsync, then os.replace."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except BaseException:
        try:
            os.unlink(temp)
        except FileNotFoundError:
            pass
        raise


def backup_file(path):
    """Byte-for-byte backup with exclusive creation. Returns the backup path."""
    path = Path(path)
    data = path.read_bytes()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for n in range(1000):
        candidate = path.with_name(f"{path.name}.bak-{stamp}-{n}")
        try:
            with open(candidate, "xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            return candidate
        except FileExistsError:
            continue
    raise OSError(f"could not create a unique backup for {path}")


# -- legacy scores.txt -------------------------------------------------------------
def decode_legacy(data, override=None):
    """Return (text, confirmed, note). Non-UTF-8 text is only confirmed through an explicit override."""
    try:
        return data.decode("utf-8"), True, ""
    except UnicodeDecodeError:
        pass
    if override:
        try:
            return data.decode(override), True, f"decoded with {override}"
        except (LookupError, UnicodeDecodeError) as error:
            note = f"override {override!r} failed: {error}"
    else:
        note = f"encoding unconfirmed; set {LEGACY_ENCODING_ENV} to import"
    # Display only: latin-1 never fails, but names may be shown incorrectly.
    return data.decode("latin-1"), False, note


def parse_legacy(text):
    """Parse '(name, score)' lines. Commas in names survive via the rightmost split."""
    records, warnings = [], []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if not (stripped.startswith("(") and stripped.endswith(")")) or "," not in stripped:
            warnings.append(f"legacy line {number}: not in (name, score) form")
            continue
        name, score = stripped[1:-1].rsplit(",", 1)
        score = score.strip()
        try:
            if not re.fullmatch(r"\d+", score):
                raise ValueError
            value = int(score)
        except ValueError:
            warnings.append(f"legacy line {number}: invalid score {score[:20]!r}")
            continue
        records.append(ScoreRecord(f"legacy-{number}", name, value, "legacy", UNKNOWN_LEVEL, "legacy"))
    return records, warnings


class ScoreStore:
    """Per-user scores.csv with optional one-time import of a legacy scores.txt."""

    def __init__(self, data_dir, legacy_path=None, legacy_encoding=None):
        self.path = Path(data_dir) / "scores.csv"
        self.legacy_path = Path(legacy_path) if legacy_path else None
        self.legacy_encoding = legacy_encoding
        self.migration_warnings = []     # skipped legacy lines from the most recent import

    @property
    def migration_pending(self):
        return self.legacy_path is not None and self.legacy_path.is_file() and not self.path.exists()

    def _legacy_records(self):
        try:
            data = self.legacy_path.read_bytes()
        except OSError as error:
            raise MigrationError(f"cannot read {self.legacy_path}: {error}") from error
        text, confirmed, note = decode_legacy(data, self.legacy_encoding)
        if not confirmed:
            raise MigrationError(f"legacy scores not imported: {note}")
        return parse_legacy(text)

    def migrate(self):
        """Import legacy scores if the destination does not exist yet. Returns skipped-line warnings."""
        if not self.migration_pending:
            return []
        records, warnings = self._legacy_records()
        try:
            atomic_write_bytes(self.path, format_csv(records).encode("utf-8"))
        except OSError as error:
            raise MigrationError(f"cannot write {self.path}: {error}") from error
        self.migration_warnings = warnings
        return warnings

    def migration_notice(self):
        if not self.migration_warnings:
            return ""
        return (f"Imported legacy scores; {len(self.migration_warnings)} unreadable line(s) skipped, "
                f"kept in {self.legacy_path}")

    def load(self):
        """Return (records, notices) for display. Raises ScoreFileError for unreadable files."""
        if self.migration_pending:
            try:
                data = self.legacy_path.read_bytes()
            except OSError as error:
                raise ScoreFileError(f"cannot read {self.legacy_path}: {error}") from error
            text, confirmed, note = decode_legacy(data, self.legacy_encoding)
            records, warnings = parse_legacy(text)
            return records, [f"Legacy scores shown read-only ({note or 'not yet imported'})"] + warnings
        return read_scores(self.path)

    def save(self, record):
        """Save once per run_id. Raises MigrationError, ScoreFileError or OSError; destination is unchanged on failure."""
        migrating = self.migration_pending
        if migrating:
            records, warnings = self._legacy_records()
            invalid = False
        else:
            records, warnings = read_scores(self.path)
            invalid = bool(warnings)
            if any(r.run_id == record.run_id for r in records):
                return False
        if invalid:
            backup_file(self.path)
        atomic_write_bytes(self.path, format_csv(records + [record]).encode("utf-8"))
        if migrating:
            self.migration_warnings = warnings
        return True
