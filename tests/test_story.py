import json

import pytest

from sage_viewer.scene.box_profile import FILTER_KEYS, LAYER_KEYS
from sage_viewer.story.io import discover_stories, load_story, save_story
from sage_viewer.story.keys import ENV_KEYS, STORY_STATE_KEYS
from sage_viewer.story.model import Scene, Story


def _sample_story():
    sc1 = Scene(
        id="intro",
        title="The box",
        caption="z = 0",
        snap_num=63,
        camera={"position": [1.0, 2.0, 3.0], "focal_point": [0, 0, 0], "up": [0, 1, 0]},
        state={"halos_visible": True, "filter_gal_smass": [9.0, 14.0]},
        focus={"kind": "sphere", "center": [1.0, 2.0, 3.0], "radius": 5.0},
        target={"position": [1.0, 2.0, 3.0], "radius": 5.0, "galaxy_index": 42},
        motion={"kind": "snapshot_sweep", "from": 60, "to": 63},
    )
    sc2 = Scene(id="end", title="Done", snap_num=50)
    return Story(
        title="Test Story",
        author="Tester",
        scenes=[sc1, sc2],
        requirements={"model": "miniMillennium", "snapshots": [63]},
    )


def test_scene_round_trip():
    sc = _sample_story().scenes[0]
    assert Scene.from_dict(sc.to_dict()).to_dict() == sc.to_dict()


def test_story_round_trip():
    st = _sample_story()
    assert Story.from_dict(st.to_dict()).to_dict() == st.to_dict()


def test_autoplay_round_trip_and_default():
    st = _sample_story()
    assert st.autoplay is False  # default off
    assert Story.from_dict({"title": "X", "autoplay": True, "scenes": []}).autoplay
    st.autoplay = True
    assert Story.from_dict(st.to_dict()).autoplay is True


def test_required_snapshots_unions_everything():
    st = _sample_story()
    # requirements [63] + scene snaps {63, 50} + sweep range {60..63}
    assert st.required_snapshots() == [50, 60, 61, 62, 63]


def test_state_keys_cover_layers_filters_env():
    for k in list(LAYER_KEYS) + list(FILTER_KEYS) + ENV_KEYS:
        assert k in STORY_STATE_KEYS
    # No duplicates.
    assert len(STORY_STATE_KEYS) == len(set(STORY_STATE_KEYS))


def test_save_and_discover(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    st = _sample_story()
    path = save_story(st)
    assert path.exists()
    assert path.parent.name == "sage_stories"

    loaded = load_story(path)
    assert loaded.title == "Test Story"
    assert loaded.source_path == str(path)

    # Discovery includes bundled examples too, so assert membership.
    titles = [s.title for s in discover_stories()]
    assert "Test Story" in titles


def test_overlays_chrome_models_round_trip():
    sc = Scene(
        id="s",
        overlays=[
            {"kind": "equation", "latex": "E=mc^2", "anchor": "top"},
            {"kind": "title", "text": "Hello", "anchor": "top-left"},
        ],
        chrome={"hide_panel": True},
        models={"primary": "miniMillennium", "adjacent": ["microUchuu"]},
    )
    d = sc.to_dict()
    assert "overlays" in d and "chrome" in d and "models" in d
    assert Scene.from_dict(d).to_dict() == d


def test_empty_optional_fields_omitted():
    d = Scene(id="bare").to_dict()
    for k in ("overlays", "chrome", "models", "target", "theme"):
        assert k not in d


def test_normalize_overlay_equation_and_citation():
    from sage_viewer.story.engine import _normalize_overlay

    eq = _normalize_overlay({"kind": "equation", "latex": "x^2", "anchor": "top"})
    assert eq["latex"] == "x^2" and eq["display"] is True
    assert "content" not in eq  # equations carry raw latex, not wrapped content
    assert "translateX(-50%)" in eq["style"]  # top anchor centres horizontally

    inline = _normalize_overlay(
        {"kind": "equation", "latex": "x", "inline": True}
    )
    assert inline["latex"] == "x" and inline["display"] is False

    cite = _normalize_overlay(
        {"kind": "citation", "text": "Croton+2016", "anchor": "bottom-right"}
    )
    assert cite["text"] == "Croton+2016"
    assert "font-style:italic" in cite["style"]
    assert "bottom:" in cite["style"] and "right:" in cite["style"]


def test_normalize_overlay_image():
    from sage_viewer.story.engine import _normalize_overlay

    img = _normalize_overlay(
        {"kind": "image", "src": "/sage_static/SAGElogo.jpg",
         "anchor": "bottom-left", "width": 160}
    )
    assert img["src"] == "/sage_static/SAGElogo.jpg"
    assert "text" not in img and "latex" not in img  # image carries no text
    assert "width:160px" in img["style"]
    assert "bottom:" in img["style"] and "left:" in img["style"]

    # width passes through as a CSS string when given as one.
    css = _normalize_overlay({"kind": "image", "src": "x", "width": "12vw"})
    assert "width:12vw" in css["style"]


def test_resolve_snap_symbolic():
    from sage_viewer.story.engine import resolve_snap

    # count=64 -> last index 63
    assert resolve_snap("last", 64) == 63
    assert resolve_snap("first", 64) == 0
    assert resolve_snap("50%", 64) == round(0.5 * 63)
    assert resolve_snap(40, 64) == 40
    assert resolve_snap(999, 64) == 63          # clamp high
    assert resolve_snap(-5, 64) == 0            # clamp low
    assert resolve_snap("nonsense", 64) == 63   # graceful fallback
    # portability: "last" adapts to a smaller model
    assert resolve_snap("last", 50) == 49


def test_resolve_model_ref_adaptive():
    from sage_viewer.story.engine import StoryPlayer

    class FakeScene:
        primary_name = "millennium"

        def list_models(self):
            return []

    class FakeState:
        models_list = [
            {"name": "millennium"}, {"name": "microuchuu"},
            {"name": "millennium_mbk"},
        ]

    class FakeServer:
        state = FakeState()
        controller = object()

    p = StoryPlayer(FakeServer(), FakeScene())
    avail = p._available_models()
    assert avail == ["millennium", "microuchuu", "millennium_mbk"]
    assert p._resolve_model_ref("current", avail, "millennium", set()) == "millennium"
    assert p._resolve_model_ref("other", avail, "millennium", set()) == "microuchuu"
    # 'auto' skips excluded names
    assert p._resolve_model_ref(
        "auto", avail, "millennium", {"microuchuu"}
    ) == "millennium_mbk"
    # explicit names pass through; None stays None
    assert p._resolve_model_ref("foo", avail, "millennium", set()) == "foo"
    assert p._resolve_model_ref(None, avail, "millennium", set()) is None


def test_portable_example_loads(tmp_path, monkeypatch):
    """The shipped example must parse with symbolic snap/camera values."""
    from sage_viewer.story.model import Scene

    sc = Scene.from_dict({
        "id": "x", "snap_num": "last", "camera": "box",
        "motion": {"kind": "snapshot_sweep", "from": "40%", "to": "last"},
    })
    assert sc.snap_num == "last"
    assert sc.camera == "box"
    # required_snapshots tolerates symbolic refs (skips them, no crash)
    st = Story(title="P", scenes=[sc])
    assert st.required_snapshots() == []


def test_discover_skips_malformed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "sage_stories"
    d.mkdir()
    (d / "bad.json").write_text("{ not valid json", encoding="utf-8")
    save_story(_sample_story())
    # The malformed file is skipped; the good one still loads (bundled
    # examples may also appear, so assert membership not an exact count).
    assert "Test Story" in [s.title for s in discover_stories()]
