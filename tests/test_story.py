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

    # x/y pass through as pixel offsets so logos pin together regardless of
    # window width (rather than drifting as percentages).
    px = _normalize_overlay(
        {"kind": "image", "src": "x", "anchor": "bottom-left",
         "x": "150px", "y": 0}
    )
    assert "left:150px" in px["style"] and "bottom:0.0%" in px["style"]


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


def test_story_model_names_collects_all_referenced_models():
    """Preload must cover every model the story uses: the launched primary,
    requirements.models, and each scene's primary/adjacent refs (deduped,
    symbolic refs resolved)."""
    from sage_viewer.story.engine import StoryPlayer

    class FakeScene:
        primary_name = "millennium_vanilla"

        def list_models(self):
            return []

    class FakeState:
        models_list = [
            {"name": "millennium_vanilla"}, {"name": "microuchuu"},
            {"name": "millennium"},
        ]

    class FakeServer:
        state = FakeState()
        controller = object()

    story = Story.from_dict({
        "title": "T",
        "requirements": {"models": ["millennium"]},
        "scenes": [
            {"id": "a", "models": {"primary": "current",
                                   "adjacent": ["microuchuu"]}},
            {"id": "b", "models": {"primary": "millennium_vanilla",
                                   "adjacent": []}},
        ],
    })
    p = StoryPlayer(FakeServer(), FakeScene())
    names = p._story_model_names(story)
    assert names[0] == "millennium_vanilla"          # launched primary first
    assert set(names) == {"millennium_vanilla", "microuchuu", "millennium"}
    assert len(names) == 3                            # no duplicates


def test_propagate_layer_visibility_mirrors_all_boxes():
    """Visibility toggled on the active box is mirrored to every loaded box
    (so a paused multi-box scene resumes with both boxes matching)."""
    from sage_viewer.story.engine import StoryPlayer

    class FakeLayer:
        def __init__(self):
            self.visible = True

    class FakeModel:
        def __init__(self, name):
            self.name = name
            self.halo_layer = FakeLayer()
            self.galaxy_layer = FakeLayer()

    prim = FakeModel("millennium_vanilla")
    adj = FakeModel("millennium")
    # A third model is PRELOADED (in _models) but NOT displayed — it must be
    # left alone, never made visible on top of the primary.
    hidden = FakeModel("preloaded_hidden")
    hidden.halo_layer.visible = False
    hidden.galaxy_layer.visible = False

    class FakeScene:
        primary_name = "millennium_vanilla"
        _adjacent_order = ["millennium"]
        _models = {"millennium_vanilla": prim, "millennium": adj,
                   "preloaded_hidden": hidden}

        def list_models(self):
            return list(self._models.values())

    class FakeState:
        halos_visible = True
        galaxies_visible = True  # user just switched galaxies on while paused

    class FakeServer:
        state = FakeState()
        controller = object()

    p = StoryPlayer(FakeServer(), FakeScene())
    p._propagate_layer_visibility(None)
    # Both DISPLAYED boxes show galaxies; the preloaded-hidden model is untouched.
    assert prim.galaxy_layer.visible and adj.galaxy_layer.visible
    assert prim.halo_layer.visible and adj.halo_layer.visible
    assert hidden.galaxy_layer.visible is False  # not stacked on the primary
    assert hidden.halo_layer.visible is False

    # Hiding galaxies mirrors across displayed boxes too.
    FakeState.galaxies_visible = False
    p._propagate_layer_visibility(None)
    assert not prim.galaxy_layer.visible and not adj.galaxy_layer.visible

    # Single-box scenes are left untouched (no mirroring needed).
    solo = FakeModel("solo")
    solo.galaxy_layer.visible = True

    class SoloScene:
        primary_name = "solo"
        _adjacent_order: list = []
        _models = {"solo": solo}

        def list_models(self):
            return [solo]

    p2 = StoryPlayer(FakeServer(), SoloScene())
    p2._propagate_layer_visibility(None)  # FakeState.galaxies_visible is False
    assert solo.galaxy_layer.visible is True  # unchanged


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


def test_scene_menu_expands_to_clickable_grid():
    """A {"kind":"scene_menu"} overlay expands into a grid of the story's
    scenes — excluding the menu scene itself and (by default) card-* dividers —
    each cell carrying its scene index for goto and an empty thumb until one is
    captured."""
    from sage_viewer.story.engine import StoryPlayer

    class FakeState:
        story_overlays_json = "[]"

    class FakeServer:
        state = FakeState()
        controller = object()

    story = Story.from_dict({
        "title": "T",
        "scenes": [
            {"id": "intro", "title": "Intro"},
            {"id": "card-x", "title": "Divider"},
            {"id": "galaxies", "title": "Galaxies"},
            {"id": "menu", "title": "",
             "overlays": [{"kind": "scene_menu", "title": "Jump", "cols": 3}]},
        ],
    })
    server = FakeServer()
    p = StoryPlayer(server, object())
    p._story = story

    p._apply_overlays(story.scenes[3])
    items = json.loads(server.state.story_overlays_json)
    assert len(items) == 1
    menu = items[0]
    assert menu["menu"] is True
    assert menu["cols"] == 3
    assert menu["title"] == "Jump"
    # card-* and the menu scene itself are excluded; indices are preserved.
    assert [c["index"] for c in menu["cells"]] == [0, 2]
    assert [c["label"] for c in menu["cells"]] == ["Intro", "Galaxies"]
    assert [c["n"] for c in menu["cells"]] == [1, 3]
    # No thumbnails captured yet → empty src (the client shows a number cell).
    assert all(c["thumb"] == "" for c in menu["cells"])


def test_scene_menu_include_cards():
    """include_cards:true keeps the card-* divider scenes in the grid."""
    from sage_viewer.story.engine import StoryPlayer

    class FakeState:
        story_overlays_json = "[]"

    class FakeServer:
        state = FakeState()
        controller = object()

    story = Story.from_dict({
        "title": "T",
        "scenes": [
            {"id": "card-x", "title": "Divider"},
            {"id": "menu", "overlays": [
                {"kind": "scene_menu", "include_cards": True}]},
        ],
    })
    server = FakeServer()
    p = StoryPlayer(server, object())
    p._story = story
    p._apply_overlays(story.scenes[1])
    menu = json.loads(server.state.story_overlays_json)[0]
    assert [c["index"] for c in menu["cells"]] == [0]


def test_goto_menu_jumps_to_the_scene_selector_scene():
    """goto_menu() finds the scene carrying a scene_menu overlay and jumps to
    it (here scene index 2)."""
    from sage_viewer.story.engine import StoryPlayer

    class FakeState:
        pass

    class FakeServer:
        state = FakeState()
        controller = object()

    story = Story.from_dict({
        "title": "T",
        "scenes": [
            {"id": "intro", "title": "Intro"},
            {"id": "mid", "title": "Mid"},
            {"id": "menu", "overlays": [{"kind": "scene_menu"}]},
        ],
    })
    p = StoryPlayer(FakeServer(), object())
    p._story = story
    jumped = []
    p.goto = lambda i: jumped.append(i)  # avoid needing an event loop
    p.goto_menu()
    assert jumped == [2]
    assert p._scene_has_menu(story.scenes[2]) is True
    assert p._scene_has_menu(story.scenes[0]) is False


def test_resolve_snap_redshift_spec():
    """A 'z=...' snap spec resolves to the closest snapshot via the model's
    redshift table, so it carries over to whatever box is loaded; without a
    table it falls back to the last snapshot."""
    from sage_viewer.story.engine import resolve_snap

    class FakeTable:
        # redshifts for 5 snapshots, z=0 last (typical ordering)
        _z = [3.0, 2.0, 1.4, 0.7, 0.0]
        count = 5

        def z_to_snap(self, z):
            import numpy as np
            return int(np.argmin(np.abs(np.array(self._z) - z)))

    t = FakeTable()
    assert resolve_snap("z=1.5", 5, t) == 2     # 1.4 is closest to 1.5
    assert resolve_snap("z1.5", 5, t) == 2      # 'z' prefix form
    assert resolve_snap("z=0", 5, t) == 4       # z=0 → last
    assert resolve_snap("z=2.1", 5, t) == 1
    # no table → safe fallback to last
    assert resolve_snap("z=1.5", 5) == 4
    # non-redshift specs still work alongside the table
    assert resolve_snap("first", 5, t) == 0
    assert resolve_snap("last", 5, t) == 4
    assert resolve_snap(3, 5, t) == 3
