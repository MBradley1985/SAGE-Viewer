from __future__ import annotations

from trame.widgets import vuetify3 as v3

from sage_viewer.scene.scene import Scene


def build_toolbar(server, scene: Scene) -> None:
    """Build the top toolbar: play/pause/stop, snapshot slider, speed, label."""
    state, ctrl = server.state, server.controller
    snap_count = scene._snap_table.count

    state.snap_num = scene.current_snap
    state.snap_label = scene.snap_label
    state.play_speed = 1
    state.is_playing = False

    # Keep snap_label in sync when the snapshot changes
    scene.register_snap_change_callback(
        lambda n: state.update(
            {"snap_num": n, "snap_label": scene.snap_label}
        )
    )

    @state.change("snap_num")
    def on_snap_slider(snap_num, **_):
        if not state.is_playing:
            scene.set_snapshot(int(snap_num))

    @ctrl.set("play")
    def on_play():
        state.is_playing = True
        fps = {1: 3, 2: 6, 5: 15}.get(state.play_speed, 3)
        scene.play(fps=fps)

    @ctrl.set("pause")
    def on_pause():
        state.is_playing = False
        scene.pause()

    @ctrl.set("stop")
    def on_stop():
        state.is_playing = False
        scene.stop()

    with v3.VAppBar(density="compact", color="#1a1a2e"):
        v3.VToolbarTitle("SAGE-Viewer", style="font-size:1rem;")
        v3.VSpacer()

        # Play / Pause / Stop
        with v3.VBtnGroup(variant="outlined", density="compact"):
            v3.VBtn(
                icon="mdi-play",
                click=ctrl.play,
                disabled=("is_playing",),
            )
            v3.VBtn(
                icon="mdi-pause",
                click=ctrl.pause,
                disabled=("!is_playing",),
            )
            v3.VBtn(icon="mdi-stop", click=ctrl.stop)

        v3.VSpacer()

        # Snapshot slider
        with v3.VCol(cols="5", style="padding: 0 12px;"):
            v3.VSlider(
                v_model=("snap_num",),
                min=0,
                max=snap_count - 1,
                step=1,
                thumb_label=False,
                hide_details=True,
                color="cyan",
            )

        # Snapshot label chip
        v3.VChip(
            ("snap_label",),
            size="small",
            color="deep-purple",
            style="font-family: monospace;",
        )

        v3.VSpacer()

        # Speed selector
        v3.VSelect(
            v_model=("play_speed",),
            items=([{"title": "1×", "value": 1},
                    {"title": "2×", "value": 2},
                    {"title": "5×", "value": 5}],),
            density="compact",
            hide_details=True,
            style="max-width:80px;",
        )
