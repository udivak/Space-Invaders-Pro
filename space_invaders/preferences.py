"""Small persistent user preferences stored as settings.json in the data directory."""
import json
import math
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from space_invaders.assets import DEFAULT_MUSIC_VOLUME
from space_invaders.scores import atomic_write_bytes


@dataclass(frozen=True)
class Preferences:
    music_volume: float = DEFAULT_MUSIC_VOLUME
    effects_volume: float = 1.0
    reduced_effects: bool = False


def _volume(raw):
    """Clamped float in 0..1, or None when raw is not a usable finite number."""
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    try:
        value = float(raw)
    except OverflowError:
        value = math.inf if raw > 0 else -math.inf
    if math.isnan(value):
        return None
    return min(1.0, max(0.0, value))


def parse(data):
    """Return (preferences, invalid) from untrusted data; invalid fields fall back to defaults."""
    defaults, values, invalid = Preferences(), {}, False
    for key in ("music_volume", "effects_volume"):
        if key in data:
            value = _volume(data[key])
            invalid |= value is None
            values[key] = getattr(defaults, key) if value is None else value
    if "reduced_effects" in data:
        raw = data["reduced_effects"]
        invalid |= not isinstance(raw, bool)
        values["reduced_effects"] = raw if isinstance(raw, bool) else defaults.reduced_effects
    return replace(defaults, **values), invalid


def from_dict(data):
    return parse(data)[0]


def load(path):
    """Return (preferences, notice). Missing file is silent; malformed content gives defaults plus a notice."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return Preferences(), ""
    except (OSError, ValueError) as error:     # includes JSON and integer-size errors
        return Preferences(), f"Settings reset to defaults ({error.__class__.__name__})"
    if not isinstance(data, dict):
        return Preferences(), "Settings reset to defaults (unexpected format)"
    preferences, invalid = parse(data)
    return preferences, "Some settings were invalid and reset to defaults" if invalid else ""


def save(path, preferences):
    atomic_write_bytes(path, json.dumps(asdict(preferences), indent=2).encode("utf-8"))
