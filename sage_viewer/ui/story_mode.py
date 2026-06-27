"""Story Mode UI — toolbar dropdown button and the playback HUD overlay.

Split into three builders so each can be mounted in the right layout context:

``init_story_mode``
    Initialise reactive state + register controllers (call once in create_app).
``build_story_button``
    The toolbar button + story dropdown (call inside the toolbar context).
``build_story_hud``
    The bottom playback overlay (call inside ``layout.content``).
"""

from __future__ import annotations

from trame.widgets import html, vuetify3 as v3

from sage_viewer.story import discover_stories, load_story
from sage_viewer.story.engine import StoryPlayer

# Theme-neutral HUD styling so the overlay reads on any palette.
_HUD_BG = (
    "background:rgba(8,12,20,0.86);border:1px solid #06b6d4;"
    "color:#e2e8f0;backdrop-filter:blur(2px);"
)


def init_story_mode(server, scene) -> StoryPlayer:
    """Create the player, init reactive state, and wire controllers."""
    state, ctrl = server.state, server.controller
    player = StoryPlayer(server, scene)

    # HUD reactive state.
    state.story_active = False
    state.story_playing = False
    state.story_title = ""
    state.story_scene_title = ""
    state.story_scene_caption = ""
    state.story_scene_index = 0
    state.story_scene_count = 0
    state.story_list = []
    # Overlays are shipped as JSON and rendered by sage_viewer.js OUTSIDE Vue
    # (so KaTeX's DOM writes can't corrupt Vue's virtual DOM).
    state.story_overlays_json = "[]"
    # Scene-selector relay: a scene_menu cell click writes "<index>:<seq>" here
    # (the seq forces a change even when the same cell is clicked twice). This
    # is the only reliable external-JS → server path in Trame 3 (see the PTY
    # relay in navigation_panel.py).
    state.story_goto_relay = ""

    # Right-panel visibility — a Story Mode scene backend option only
    # (scene.chrome.hide_panel). Declared before the client mounts so Vue
    # tracks it reactively. There is no general-use toggle button.
    state.panels_hidden = False

    # Cache of discovered Story objects, index-aligned with state.story_list.
    _discovered: list = []

    @ctrl.set("story_refresh")
    def _story_refresh():
        _discovered.clear()
        _discovered.extend(discover_stories())
        state.story_list = [
            {
                "title": s.title or "Untitled Story",
                "subtitle": f"{len(s.scenes)} scenes"
                + (f"  ·  {s.author}" if s.author else ""),
                "index": i,
            }
            for i, s in enumerate(_discovered)
        ]
        state.flush()

    @ctrl.set("story_open")
    def _story_open(index=0):
        try:
            cached = _discovered[int(index)]
        except (IndexError, ValueError, TypeError):
            return
        # Re-read the JSON from disk on every open so edits take effect by just
        # exiting Story Mode and re-selecting it — no app restart needed.
        story = cached
        if getattr(cached, "source_path", None):
            try:
                story = load_story(cached.source_path)
            except (OSError, ValueError, KeyError):
                story = cached
        player.enter(story)

    @ctrl.set("story_exit")
    def _story_exit():
        player.exit()

    @ctrl.set("story_next")
    def _story_next():
        player.next()

    @ctrl.set("story_prev")
    def _story_prev():
        player.prev()

    @ctrl.set("story_play")
    def _story_play():
        player.play()

    @ctrl.set("story_pause")
    def _story_pause():
        player.pause()

    @ctrl.set("story_menu")
    def _story_menu():
        player.goto_menu()

    @ctrl.set("story_capture_thumbs")
    def _story_capture_thumbs():
        # Authoring one-off: screenshot every scene so a scene_menu shows
        # thumbnails. Runs off the event loop so the UI stays responsive.
        import asyncio

        asyncio.ensure_future(player.capture_thumbnails())

    @server.state.change("story_goto_relay")
    def _on_story_goto(story_goto_relay, **_):
        # Value is "<scene-index>:<seq>"; jump to the chosen scene.
        v = str(story_goto_relay or "")
        if not v:
            return
        try:
            idx = int(v.split(":", 1)[0])
        except ValueError:
            return
        player.goto(idx)

    # Populate the list once at startup.
    _story_refresh()

    return player


def build_story_button(server) -> None:
    """Toolbar button opening the story dropdown menu."""
    ctrl = server.controller
    with v3.VMenu(close_on_content_click=True):
        with v3.Template(v_slot_activator="{ props }"):
            v3.VBtn(
                icon="mdi-book-open-page-variant-outline",
                variant="text",
                density="compact",
                color=("story_active ? 'cyan' : 'white'",),
                title="Story Mode",
                v_bind="props",
                click=ctrl.story_refresh,
                style="margin-left:2px;",
            )
        with v3.VList(density="compact", bg_color="transparent"):
            v3.VListSubheader(
                "STORY MODE", style="color:#06b6d4;font-size:0.65rem;"
            )
            # One item per discovered story.
            with v3.VListItem(
                v_for="(s, i) in story_list",
                key="i",
                title=("s.title",),
                subtitle=("s.subtitle",),
                click=(ctrl.story_open, "[s.index]"),
                color="cyan",
                density="compact",
            ):
                with v3.Template(v_slot_prepend=True):
                    v3.VIcon("mdi-play-box-outline", size="small")
            # Empty-state hint.
            v3.VListItem(
                v_show=("story_list.length === 0",),
                title="No stories found",
                subtitle="Add JSON files to sage_stories/",
                density="compact",
                disabled=True,
            )
            v3.VDivider()
            v3.VListItem(
                title="Capture thumbnails",
                subtitle="Screenshot every scene for the menu grid",
                prepend_icon="mdi-camera-burst",
                click=ctrl.story_capture_thumbs,
                color="cyan",
                density="compact",
                v_show=("story_active",),
            )
            v3.VListItem(
                title="Exit Story Mode",
                prepend_icon="mdi-close",
                click=ctrl.story_exit,
                color="#ef4444",
                density="compact",
                v_show=("story_active",),
            )


def build_story_overlays(server) -> None:
    """Full-bleed text/equation overlay layer over the VTK view.

    Mount inside the VTK sheet (sibling of the render view).  Equations carry
    KaTeX ``\\[...\\]`` / ``\\(...\\)`` delimiters; the client typesets them via
    auto-render (``sage_viewer.js`` watches this container for changes).
    """
    # Empty container — Vue owns the element but NOT its children, which
    # sage_viewer.js builds from story_overlays_json and typesets with KaTeX.
    # Keeping the children out of Vue's vDOM avoids insertBefore corruption.
    html.Div(
        id="sage-overlay-root",
        v_show=("story_active",),
        # Sits inside the VTK sheet (the visible render area), so inset:0 is
        # correct whether or not a story has hidden the panel.
        style=(
            "position:absolute;inset:0;z-index:40;"
            "pointer-events:none;overflow:hidden;"
        ),
    )
    # One-way relay of the overlay JSON for the client renderer to poll.
    html.Input(
        id="sage-overlays-relay",
        value=("story_overlays_json",),
        type="text",
        style=(
            "position:fixed;left:-9999px;"
            "width:1px;height:1px;opacity:0;pointer-events:none;"
        ),
    )
    # Scene-selector relay: sage_viewer.js writes the clicked cell's index here
    # (v_model carries it to the server's story_goto_relay @state.change).
    html.Input(
        id="sage-story-goto-relay",
        v_model=("story_goto_relay",),
        type="text",
        style=(
            "position:fixed;left:-9999px;"
            "width:1px;height:1px;opacity:0;pointer-events:none;"
        ),
    )


def build_story_hud(server) -> None:
    """Compact playback overlay pinned to the lower-right, shown while active."""
    ctrl = server.controller
    with html.Div(
        v_show=("story_active",),
        # Compact card in the lower-right corner (right edge tracks the panel).
        style=(
            "'position:absolute;bottom:18px;z-index:50;"
            "width:min(320px,90vw);"
            "border-radius:6px;padding:8px 12px;"
            + _HUD_BG
            + "right:' + (panels_hidden ? '16px' : '316px')",
        ),
    ):
        # Header: progress + scene title.
        with html.Div(
            style="display:flex;align-items:center;gap:8px;margin-bottom:4px;"
        ):
            v3.VChip(
                "{{ story_scene_index }} / {{ story_scene_count }}",
                size="x-small",
                color="cyan",
                style="font-family:monospace;",
            )
            html.Span(
                "{{ story_scene_title }}",
                style="font-weight:700;font-size:0.92rem;color:#fff;"
                "overflow:hidden;text-overflow:ellipsis;white-space:nowrap;",
            )
        # Caption.
        html.Div(
            "{{ story_scene_caption }}",
            v_show=("story_scene_caption",),
            style=(
                "white-space:pre-wrap;font-size:0.82rem;line-height:1.35;"
                "color:#cbd5e1;margin-bottom:8px;max-height:24vh;overflow:auto;"
            ),
        )
        # Transport row.
        with html.Div(
            style="display:flex;align-items:center;justify-content:center;gap:4px;"
        ):
            v3.VBtn(
                icon="mdi-skip-previous",
                variant="text",
                density="compact",
                color="white",
                title="Previous scene",
                click=ctrl.story_prev,
            )
            v3.VBtn(
                icon="mdi-play",
                variant="text",
                density="compact",
                color="white",
                title="Play",
                v_show=("!story_playing",),
                click=ctrl.story_play,
            )
            v3.VBtn(
                icon="mdi-pause",
                variant="text",
                density="compact",
                color="cyan",
                title="Pause (hand back control)",
                v_show=("story_playing",),
                click=ctrl.story_pause,
            )
            v3.VBtn(
                icon="mdi-skip-next",
                variant="text",
                density="compact",
                color="white",
                title="Next scene",
                click=ctrl.story_next,
            )
            v3.VBtn(
                icon="mdi-view-grid",
                variant="text",
                density="compact",
                color="white",
                title="Scene selection",
                click=ctrl.story_menu,
                style="margin-left:8px;",
            )
            v3.VBtn(
                icon="mdi-close-thick",
                variant="text",
                density="compact",
                color="#ef4444",
                title="Exit Story Mode",
                click=ctrl.story_exit,
                style="margin-left:2px;",
            )
