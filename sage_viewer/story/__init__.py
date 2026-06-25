"""Story Mode — guided, data-driven scene playback.

A *story* is an ordered set of *scenes* (captured viewpoints + narration)
loaded from JSON files in a ``sage_stories/`` folder.  Story Mode is a
non-destructive overlay on the normal viewer: pausing hands full control back
to the user, and exiting restores their prior state.
"""

from __future__ import annotations

from sage_viewer.story.model import Scene, Story
from sage_viewer.story.engine import StoryPlayer
from sage_viewer.story.io import (
    discover_stories,
    load_story,
    save_story,
    stories_dir,
)

__all__ = [
    "Scene",
    "Story",
    "StoryPlayer",
    "discover_stories",
    "load_story",
    "save_story",
    "stories_dir",
]
