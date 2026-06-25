"""Story / Scene data model.

Plain dataclasses that round-trip to the JSON schema documented in
``docs/project/story_mode_design.md``.  Every scene captures the *complete*
state (full snapshot per scene), so scenes are reorderable with no hidden
inter-scene dependencies.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

SCHEMA_VERSION = 1

# Default transition / dwell used when a scene omits them.
DEFAULT_TRANSITION_SECS = 4.0
DEFAULT_EASING = "smoothstep"
DEFAULT_DWELL_SECS = 6.0


@dataclass
class Scene:
    """One captured viewpoint + narration."""

    id: str
    title: str = ""
    caption: str = ""
    # int (absolute) or symbolic "first"/"last"/"40%" — resolved per model.
    snap_num: int | str = 0
    theme: str | None = None  # None → inherit story theme

    # Camera pose: explicit dict {position, focal_point, up} OR the string
    # "box"/"reset" to frame the whole box (box-size aware → portable).
    camera: dict[str, list[float]] | str = field(default_factory=dict)

    # Full captured flat state (STORY_STATE_KEYS → value).
    state: dict[str, Any] = field(default_factory=dict)

    # Focus geometry: {"kind": "none"|"sphere"|"box", ...}
    focus: dict[str, Any] = field(default_factory=lambda: {"kind": "none"})

    # Optional object target.
    target: dict[str, Any] | None = None

    # In-view text overlays (titles / headings / citations / equations).
    overlays: list[dict[str, Any]] = field(default_factory=list)

    # UI chrome control, e.g. {"hide_panel": True}.
    chrome: dict[str, Any] = field(default_factory=dict)

    # Optional model / multi-box layout, e.g.
    # {"primary": "miniMillennium", "adjacent": ["microUchuu"]}.
    models: dict[str, Any] | None = None

    # Playback behaviour.
    transition: dict[str, Any] = field(
        default_factory=lambda: {
            "duration_secs": DEFAULT_TRANSITION_SECS,
            "easing": DEFAULT_EASING,
        }
    )
    dwell_secs: float = DEFAULT_DWELL_SECS
    motion: dict[str, Any] = field(default_factory=lambda: {"kind": "still"})

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "caption": self.caption,
            "snap_num": self.snap_num,
            "camera": deepcopy(self.camera),
            "state": deepcopy(self.state),
            "focus": deepcopy(self.focus),
            "transition": deepcopy(self.transition),
            "dwell_secs": self.dwell_secs,
            "motion": deepcopy(self.motion),
        }
        if self.theme is not None:
            d["theme"] = self.theme
        if self.target is not None:
            d["target"] = deepcopy(self.target)
        if self.overlays:
            d["overlays"] = deepcopy(self.overlays)
        if self.chrome:
            d["chrome"] = deepcopy(self.chrome)
        if self.models is not None:
            d["models"] = deepcopy(self.models)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Scene":
        return cls(
            id=str(d["id"]),
            title=d.get("title", ""),
            caption=d.get("caption", ""),
            snap_num=d.get("snap_num", 0),  # int or symbolic str
            theme=d.get("theme"),
            camera=deepcopy(d.get("camera", {})),
            state=deepcopy(d.get("state", {})),
            focus=deepcopy(d.get("focus", {"kind": "none"})),
            target=deepcopy(d["target"]) if d.get("target") else None,
            overlays=deepcopy(d.get("overlays", [])),
            chrome=deepcopy(d.get("chrome", {})),
            models=deepcopy(d["models"]) if d.get("models") else None,
            transition=deepcopy(
                d.get(
                    "transition",
                    {
                        "duration_secs": DEFAULT_TRANSITION_SECS,
                        "easing": DEFAULT_EASING,
                    },
                )
            ),
            dwell_secs=float(d.get("dwell_secs", DEFAULT_DWELL_SECS)),
            motion=deepcopy(d.get("motion", {"kind": "still"})),
        )


@dataclass
class Story:
    """An ordered set of scenes plus sandbox requirements."""

    title: str
    scenes: list[Scene]
    author: str = ""
    description: str = ""
    theme: str = "dos_blue"
    requirements: dict[str, Any] = field(default_factory=dict)
    # Start playback automatically on enter (e.g. a title scene that flies
    # through the box until the presenter clicks Next).
    autoplay: bool = False
    schema_version: int = SCHEMA_VERSION
    # Set by the loader; not serialised.
    source_path: str | None = field(default=None, compare=False)

    # ---- Sandbox helpers ------------------------------------------------

    @property
    def model_name(self) -> str | None:
        return self.requirements.get("model")

    def required_snapshots(self) -> list[int]:
        """Absolute snapshot numbers the sandbox must preload.

        Union of ``requirements.snapshots`` (list or {"from","to"} range),
        every scene's ``snap_num``, and any ``snapshot_sweep`` motion range.
        Symbolic refs (``"first"``/``"last"``/``"40%"``) are skipped here — they
        are resolved at runtime against the active model by the engine.
        """
        def _as_int(v):
            try:
                return int(v)
            except (TypeError, ValueError):
                return None

        snaps: set[int] = set()
        req = self.requirements.get("snapshots")
        if isinstance(req, dict):
            lo, hi = _as_int(req.get("from", 0)), _as_int(req.get("to"))
            if lo is not None and hi is not None:
                snaps.update(range(min(lo, hi), max(lo, hi) + 1))
        elif isinstance(req, (list, tuple)):
            snaps.update(s for s in (_as_int(x) for x in req) if s is not None)
        for sc in self.scenes:
            s = _as_int(sc.snap_num)
            if s is not None:
                snaps.add(s)
            m = sc.motion or {}
            if m.get("kind") == "snapshot_sweep":
                lo, hi = _as_int(m.get("from")), _as_int(m.get("to"))
                if lo is not None and hi is not None:
                    snaps.update(range(min(lo, hi), max(lo, hi) + 1))
        return sorted(snaps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "title": self.title,
            "author": self.author,
            "description": self.description,
            "theme": self.theme,
            "requirements": deepcopy(self.requirements),
            "autoplay": self.autoplay,
            "scenes": [s.to_dict() for s in self.scenes],
        }

    @classmethod
    def from_dict(
        cls, d: dict[str, Any], *, source_path: str | None = None
    ) -> "Story":
        return cls(
            title=d.get("title", "Untitled Story"),
            author=d.get("author", ""),
            description=d.get("description", ""),
            theme=d.get("theme", "dos_blue"),
            requirements=deepcopy(d.get("requirements", {})),
            autoplay=bool(d.get("autoplay", False)),
            schema_version=int(d.get("schema_version", SCHEMA_VERSION)),
            scenes=[Scene.from_dict(s) for s in d.get("scenes", [])],
            source_path=source_path,
        )
