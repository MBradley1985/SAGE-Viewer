"""Story discovery and load/save.

Stories live as ``*.json`` files in a ``sage_stories/`` folder in the current
working directory (plus the bundled ``examples/`` folder) — the same convention
the Library tab uses for ``sage_library`` / ``sage_outputs``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from visage.story.model import Story


def stories_dir() -> Path:
    """Return (creating if needed) the ``sage_stories/`` folder in CWD.

    This is where the user's own stories live (and where Capture writes).
    """
    d = Path.cwd() / "sage_stories"
    d.mkdir(parents=True, exist_ok=True)
    return d


def bundled_dir() -> Path:
    """Return the package's read-only ``examples`` folder (always present)."""
    return Path(__file__).resolve().parent.parent / "examples"


def discover_stories() -> list[Story]:
    """Load valid stories from the bundled examples and ``CWD/sage_stories``.

    Bundled examples ship with the package (so they appear on any install /
    launch directory); user stories in ``CWD/sage_stories`` override a bundled
    one with the same title. Malformed files are skipped silently.
    """
    out: list[Story] = []
    seen: set[str] = set()
    # CWD (user) first so it wins over a bundled story of the same title.
    for d in (stories_dir(), bundled_dir()):
        if not d.exists():
            continue
        for path in sorted(d.glob("*.json")):
            try:
                story = load_story(path)
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                continue
            key = story.title.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(story)
    out.sort(key=lambda s: s.title.lower())
    return out


def load_story(path: str | Path) -> Story:
    path = Path(path)
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return Story.from_dict(data, source_path=str(path))


def save_story(story: Story, path: str | Path | None = None) -> Path:
    """Write *story* to JSON.  Defaults to its ``source_path`` or a slug."""
    if path is None:
        path = story.source_path or (
            stories_dir() / f"{_slug(story.title)}.json"
        )
    path = Path(path)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(story.to_dict(), fh, indent=2)
    story.source_path = str(path)
    return path


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "story"
