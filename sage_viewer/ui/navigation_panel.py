from __future__ import annotations

from trame.widgets import vuetify3 as v3

from sage_viewer.scene.scene import Scene


_FIELD = "padding:8px 0 4px;"
_BTN   = "padding:8px 0 4px;"

_HALO_MODES = [
    {"title": "Mvir", "value": "mvir"},
    {"title": "Rvir", "value": "rvir"},
    {"title": "Vvir", "value": "vvir"},
]

_GALAXY_MODES = [
    {"title": "Stellar Mass", "value": "stellar_mass"},
    {"title": "sSFR",         "value": "ssfr"},
    {"title": "SFR",          "value": "sfr"},
    {"title": "Cold Gas",     "value": "cold_gas"},
    {"title": "Bulge Mass",   "value": "bulge_mass"},
    {"title": "Density",      "value": "density"},
    {"title": "Type",         "value": "type"},
]

_CMAPS = [
    {"title": "Blues",    "value": "Blues"},
    {"title": "Purples",  "value": "Purples"},
    {"title": "Greens",   "value": "Greens"},
    {"title": "Oranges",  "value": "Oranges"},
    {"title": "Reds",     "value": "Reds"},
    {"title": "Viridis",  "value": "viridis"},
    {"title": "Plasma",   "value": "plasma"},
    {"title": "Inferno",  "value": "inferno"},
    {"title": "Magma",    "value": "magma"},
    {"title": "Cividis",  "value": "cividis"},
    {"title": "Coolwarm", "value": "coolwarm"},
    {"title": "RdBu",     "value": "RdBu"},
    {"title": "YlOrRd",   "value": "YlOrRd"},
    {"title": "Spectral", "value": "Spectral"},
]


_HALO_CB = {
    "mvir": ("Mvir",    "10¹⁰",  "10¹⁵ M☉"),
    "rvir": ("Rvir",    "0.03",  "3 Mpc/h"),
    "vvir": ("Vvir",    "30",    "1000 km/s"),
}

_GAL_CB = {
    "stellar_mass": ("M★",      "10⁸",    "10¹²·⁵ M☉"),
    "ssfr":         ("sSFR",    "10⁻¹⁴", "10⁻⁸ yr⁻¹"),
    "sfr":          ("SFR",     "10⁻³",  "10² M☉/yr"),
    "cold_gas":     ("Mgas",    "10⁷",   "10¹¹·⁵ M☉"),
    "bulge_mass":   ("Mbulge",  "10⁷",   "10¹² M☉"),
    "density":      ("Density", "Low",   "High"),
    "type":         ("Type",    "Central","Satellite"),
}

_CBAR_BASE = (
    "height:8px;flex:1;min-width:0;border-radius:2px;"
    "background:"
)

def _cbar_style(gradient: str) -> str:
    return _CBAR_BASE + gradient


def build_navigation_panel(server, scene: Scene) -> None:
    state, ctrl = server.state, server.controller

    # Navigation state
    state.nav_halo_idx         = 0
    state.nav_gal_idx          = 0
    state.nav_gal_last_radius  = 5.0   # 5 Mpc/h
    state.nav_x                = round(scene._cfg.box_size / 2, 2)
    state.nav_y                = round(scene._cfg.box_size / 2, 2)
    state.nav_z                = round(scene._cfg.box_size / 2, 2)
    state.nav_distance         = 5.0   # 5 Mpc/h
    state.nav_box_xmin         = 0.0
    state.nav_box_xmax         = round(scene._cfg.box_size / 2, 2)
    state.nav_box_ymin         = 0.0
    state.nav_box_ymax         = round(scene._cfg.box_size / 2, 2)
    state.nav_box_zmin         = 0.0
    state.nav_box_zmax         = round(scene._cfg.box_size / 2, 2)
    state.focus_active         = False
    state.nav_active_tab       = "layers"

    # ── Filter state (log10 ranges where appropriate) ──────────
    state.filter_halo_mvir   = [10.0, 15.0]   # log10 Msun
    state.filter_gal_smass   = [8.0, 12.5]    # log10 Msun
    state.filter_gal_ssfr    = [-14.0, -8.0]  # log10 yr^-1
    state.filter_gal_bt      = [0.0, 1.0]     # bulge/total
    state.filter_gal_type    = "both"         # both | central | satellite
    state.filter_gal_bhmass  = [0.0, 10.0]    # log10 Msun (0 includes zero-BH gals)
    state.filter_gal_ics     = [0.0, 12.0]    # log10 Msun (0 includes zero-ICS gals)
    state.filter_gal_ffb     = "any"          # any | yes | no   (FFBRegime)
    state.filter_gal_cgm     = "any"          # any | cold | hot (Regime 0/1)
    state.filter_gal_env     = "all"          # all | field | isolated | group | cluster

    # ── Record state ───────────────────────────────────────────
    state.recording_active   = False
    state.recording_frames   = 0
    state.recording_dir      = ""
    state.last_screenshot    = ""
    state.last_movie         = ""
    state.movie_fps          = 10
    state.movie_resolution   = "native"   # native | hd | uhd
    state.movie_format       = "gif"      # gif | mov | png
    state.screenshot_label   = ""
    state.movie_label        = ""
    state.movie_loop         = True   # only used for GIF output

    # Colorbar state — full style strings to avoid Vue concatenation issues
    from sage_viewer.utils.colormap import cmap_css_gradient
    _h_label, _h_min, _h_max = _HALO_CB[scene.halo_layer.color_mode]
    _g_label, _g_min, _g_max = _GAL_CB[scene.galaxy_layer.color_mode]
    state.halo_cbar_style = _cbar_style(cmap_css_gradient(scene.halo_layer.colormap))
    state.halo_cbar_min   = _h_min
    state.halo_cbar_max   = _h_max
    state.gal_cbar_style  = _cbar_style(cmap_css_gradient(scene.galaxy_layer.colormap))
    state.gal_cbar_min    = _g_min
    state.gal_cbar_max    = _g_max

    # Layer state
    state.halos_visible     = True
    state.galaxies_visible  = True
    state.halo_opacity      = scene.halo_layer.opacity
    state.galaxy_opacity    = scene.galaxy_layer.opacity
    state.halo_color_mode   = scene.halo_layer.color_mode
    state.galaxy_color_mode = scene.galaxy_layer.color_mode
    state.halo_colormap     = scene.halo_layer.colormap
    state.galaxy_colormap   = scene.galaxy_layer.colormap


    def _push():
        if hasattr(server.controller, "view_update"):
            server.controller.view_update()

    def _focused() -> bool:
        return bool(state.focus_active)

    # ------------------------------------------------------------------
    # Filter recompute — runs whenever any filter changes OR snapshot changes
    # ------------------------------------------------------------------

    def _apply_filters() -> None:
        import numpy as np
        halos, galaxies = scene._loader.get(scene.current_snap)

        # Halo: Mvir range
        h_lo, h_hi = state.filter_halo_mvir
        h_log = np.log10(np.maximum(halos.masses, 1.0))
        h_mask = (h_log >= float(h_lo)) & (h_log <= float(h_hi))
        # If filter is full range, set None to skip masking work
        if float(h_lo) <= 10.0 + 1e-6 and float(h_hi) >= 15.0 - 1e-6:
            h_mask = None
        scene.halo_layer.set_filter_mask(h_mask)

        # Galaxy: stellar mass, sSFR, B/T, type
        if galaxies.count == 0:
            scene.galaxy_layer.set_filter_mask(None)
        else:
            g_mask = np.ones(galaxies.count, dtype=bool)

            sm_lo, sm_hi = state.filter_gal_smass
            sm_log = np.log10(np.maximum(galaxies.stellar_mass, 1.0))
            g_mask &= (sm_log >= float(sm_lo)) & (sm_log <= float(sm_hi))

            ss_lo, ss_hi = state.filter_gal_ssfr
            ssfr_log = np.log10(np.maximum(galaxies.ssfr, 1e-30))
            g_mask &= (ssfr_log >= float(ss_lo)) & (ssfr_log <= float(ss_hi))

            bt_lo, bt_hi = state.filter_gal_bt
            sm_safe = np.maximum(galaxies.stellar_mass, 1.0)
            bt = galaxies.bulge_mass / sm_safe
            g_mask &= (bt >= float(bt_lo)) & (bt <= float(bt_hi))

            t = str(state.filter_gal_type)
            if t == "central":
                g_mask &= galaxies.gal_type == 0
            elif t == "satellite":
                g_mask &= galaxies.gal_type > 0

            bh_lo, bh_hi = state.filter_gal_bhmass
            bh_log = np.log10(np.maximum(galaxies.bh_mass, 1.0))
            g_mask &= (bh_log >= float(bh_lo)) & (bh_log <= float(bh_hi))

            ics_lo, ics_hi = state.filter_gal_ics
            ics_log = np.log10(np.maximum(galaxies.ics_mass, 1.0))
            g_mask &= (ics_log >= float(ics_lo)) & (ics_log <= float(ics_hi))

            ffb = str(state.filter_gal_ffb)
            if ffb == "yes":
                g_mask &= galaxies.ffb_regime != 0
            elif ffb == "no":
                g_mask &= galaxies.ffb_regime == 0

            cgm = str(state.filter_gal_cgm)
            if cgm == "cold":
                g_mask &= galaxies.cgm_regime == 0
            elif cgm == "hot":
                g_mask &= galaxies.cgm_regime == 1

            # Environment from host (FOF) Mvir
            env = str(state.filter_gal_env)
            if env != "all":
                cm = galaxies.central_mvir
                cm_safe = np.maximum(cm, 1.0)
                log_cm = np.log10(cm_safe)
                if env == "field":
                    g_mask &= log_cm < 11.0
                elif env == "isolated":
                    g_mask &= (log_cm >= 11.0) & (log_cm < 12.5)
                elif env == "group":
                    g_mask &= (log_cm >= 12.5) & (log_cm < 14.0)
                elif env == "cluster":
                    g_mask &= log_cm >= 14.0

            scene.galaxy_layer.set_filter_mask(g_mask)

        _push()

    # Re-apply on every snapshot change (new data, masks must be rebuilt)
    scene.register_snap_change_callback(lambda _n: _apply_filters())

    @state.change(
        "filter_halo_mvir", "filter_gal_smass", "filter_gal_ssfr",
        "filter_gal_bt", "filter_gal_type",
        "filter_gal_bhmass", "filter_gal_ics",
        "filter_gal_ffb", "filter_gal_cgm", "filter_gal_env",
    )
    def on_filter_change(**_):
        _apply_filters()

    @ctrl.set("reset_opacities")
    def on_reset_opacities():
        state.halo_opacity   = 0.10
        state.galaxy_opacity = 1.0
        state.flush()

    @ctrl.set("reset_filters")
    def on_reset_filters():
        state.filter_halo_mvir  = [10.0, 15.0]
        state.filter_gal_smass  = [8.0, 12.5]
        state.filter_gal_ssfr   = [-14.0, -8.0]
        state.filter_gal_bt     = [0.0, 1.0]
        state.filter_gal_type   = "both"
        state.filter_gal_bhmass = [0.0, 10.0]
        state.filter_gal_ics    = [0.0, 12.0]
        state.filter_gal_ffb    = "any"
        state.filter_gal_cgm    = "any"
        state.filter_gal_env    = "all"
        state.flush()

    # ------------------------------------------------------------------
    # Layer change handlers
    # ------------------------------------------------------------------

    @state.change("halos_visible")
    def on_halo_toggle(halos_visible, **_):
        scene.halo_layer.visible = bool(halos_visible)
        _push()

    @state.change("galaxies_visible")
    def on_galaxy_toggle(galaxies_visible, **_):
        scene.galaxy_layer.visible = bool(galaxies_visible)
        _push()

    @state.change("halo_opacity")
    def on_halo_opacity(halo_opacity, **_):
        scene.halo_layer.opacity = float(halo_opacity)
        _push()

    @state.change("galaxy_opacity")
    def on_galaxy_opacity(galaxy_opacity, **_):
        scene.galaxy_layer.opacity = float(galaxy_opacity)
        _push()

    @state.change("halo_color_mode")
    def on_halo_mode(halo_color_mode, **_):
        scene.halo_layer.color_mode = halo_color_mode
        _, lo, hi = _HALO_CB[halo_color_mode]
        state.halo_cbar_min = lo
        state.halo_cbar_max = hi
        _push()

    @state.change("galaxy_color_mode")
    def on_galaxy_mode(galaxy_color_mode, **_):
        scene.galaxy_layer.color_mode = galaxy_color_mode
        _, lo, hi = _GAL_CB[galaxy_color_mode]
        state.gal_cbar_min = lo
        state.gal_cbar_max = hi
        _push()

    @state.change("halo_colormap")
    def on_halo_cmap(halo_colormap, **_):
        scene.halo_layer.colormap = halo_colormap
        from sage_viewer.utils.colormap import cmap_css_gradient
        state.halo_cbar_style = _cbar_style(cmap_css_gradient(halo_colormap))
        _push()

    @state.change("galaxy_colormap")
    def on_galaxy_cmap(galaxy_colormap, **_):
        scene.galaxy_layer.colormap = galaxy_colormap
        from sage_viewer.utils.colormap import cmap_css_gradient
        state.gal_cbar_style = _cbar_style(cmap_css_gradient(galaxy_colormap))
        _push()

    # ------------------------------------------------------------------
    # Navigation controllers
    # ------------------------------------------------------------------

    @ctrl.set("go_to_halo")
    def on_go_to_halo():
        try:
            idx = int(state.nav_halo_idx)
            d   = float(state.nav_distance)
            scene.camera.go_to_halo(idx, d)
            if _focused():
                pos = scene.camera._halo_index.position_of(idx)
                scene.set_focus_sphere(
                    (float(pos[0]), float(pos[1]), float(pos[2])), d
                )
        except Exception:
            pass
        _push()

    def _go_to_galaxy_at_radius(radius: float) -> None:
        try:
            state.nav_gal_last_radius = radius
            center = scene.camera.go_to_galaxy(int(state.nav_gal_idx), radius)
            if center != (0.0, 0.0, 0.0):
                scene.set_focus_sphere(center, radius)
                state.focus_active = True
        except Exception:
            pass
        _push()

    @ctrl.set("go_to_galaxy_1")
    def on_go_to_galaxy_1():
        _go_to_galaxy_at_radius(3.0)    # 3 Mpc/h

    @ctrl.set("go_to_galaxy_3")
    def on_go_to_galaxy_3():
        _go_to_galaxy_at_radius(5.0)    # 5 Mpc/h

    @ctrl.set("go_to_galaxy_5")
    def on_go_to_galaxy_5():
        _go_to_galaxy_at_radius(10.0)   # 10 Mpc/h

    @ctrl.set("go_to_galaxy_enter")
    def on_go_to_galaxy_enter():
        _go_to_galaxy_at_radius(float(state.nav_gal_last_radius))

    @ctrl.set("clear_indicator")
    def on_clear_indicator():
        scene.camera._clear_indicator()
        _push()

    # ------------------------------------------------------------------
    # Record / screenshot controllers
    # ------------------------------------------------------------------

    _record_state: dict = {
        "active": False, "dir": None, "frames": 0, "cb": None,
        "fps": 10, "format": "gif", "scale": 1, "movie_base": "movie",
    }
    _session_state: dict = {"dir": None}

    _RES_SCALE = {"native": 1, "hd": 2, "uhd": 4}

    def _get_session_dir() -> "pathlib.Path":
        """Lazily create one session folder per app launch."""
        import datetime
        if _session_state["dir"] is None:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            sess = _make_outdir("sage_outputs") / f"session_{ts}"
            sess.mkdir(parents=True, exist_ok=True)
            _session_state["dir"] = sess
        return _session_state["dir"]

    def _safe_label(label: str) -> str:
        """Sanitize a user-typed label into a safe filename fragment."""
        import re
        s = re.sub(r"[^\w\-]+", "_", str(label or "").strip())
        return s.strip("_")

    def _resolve_name(user_label: str, prefix: str) -> str:
        """Return '<prefix>_<label>' if labelled, else '<prefix>_<timestamp>'."""
        import datetime
        label = _safe_label(user_label)
        if label:
            return f"{prefix}_{label}"
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{ts}"

    def _capture_image(scale: int = 1):
        """Capture the current render window as a vtkImageData."""
        import vtk
        rw = scene.plotter.ren_win
        rw.Render()
        w2i = vtk.vtkWindowToImageFilter()
        w2i.SetInput(rw)
        w2i.SetScale(int(scale), int(scale))
        w2i.SetInputBufferTypeToRGB()
        w2i.ReadFrontBufferOff()
        w2i.Update()
        return w2i.GetOutput()

    def _save_image(image, path) -> None:
        """Write a vtkImageData to disk; format inferred from extension."""
        import vtk
        ext = str(path).lower().rsplit(".", 1)[-1]
        if ext in ("jpg", "jpeg"):
            writer = vtk.vtkJPEGWriter()
            writer.SetQuality(95)
        elif ext in ("tif", "tiff"):
            writer = vtk.vtkTIFFWriter()
        else:
            writer = vtk.vtkPNGWriter()
        writer.SetFileName(str(path))
        writer.SetInputData(image)
        writer.Write()

    def _make_outdir(sub: str) -> "pathlib.Path":
        import pathlib
        # Anchor outputs inside the SAGE-Viewer repo (gitignored)
        # __file__ = .../SAGE-Viewer/sage_viewer/ui/navigation_panel.py
        repo_root = pathlib.Path(__file__).resolve().parents[2]
        outdir = repo_root / sub
        outdir.mkdir(parents=True, exist_ok=True)
        return outdir

    def _take_screenshot(ext: str) -> None:
        try:
            sess = _get_session_dir()
            name = _resolve_name(state.screenshot_label, "screenshot")
            path = sess / f"{name}.{ext}"
            # If a file with this name already exists (user re-used label),
            # append a short timestamp so we don't overwrite.
            if path.exists():
                import datetime
                ts = datetime.datetime.now().strftime("%H%M%S")
                path = sess / f"{name}_{ts}.{ext}"
            img = _capture_image(scale=1)
            _save_image(img, path)
            state.last_screenshot = str(path)
        except Exception as e:
            state.last_screenshot = f"ERROR: {e!s}"
        state.flush()

    @ctrl.set("take_screenshot")
    def on_take_screenshot():
        _take_screenshot("png")

    @ctrl.set("screenshot_png")
    def on_screenshot_png():
        _take_screenshot("png")

    @ctrl.set("screenshot_jpg")
    def on_screenshot_jpg():
        _take_screenshot("jpg")

    @ctrl.set("screenshot_tiff")
    def on_screenshot_tiff():
        _take_screenshot("tiff")

    # ------------------------------------------------------------------
    # Recording — PNG frames during playback, finalized to GIF/MOV at stop
    # ------------------------------------------------------------------

    _record_task: list = [None]   # asyncio.Task | None

    async def _record_loop():
        import asyncio
        interval = 1.0 / max(1, int(_record_state["fps"]))
        try:
            while _record_state["active"]:
                outpath = (
                    _record_state["dir"]
                    / f"frame_{_record_state['frames']:05d}.png"
                )
                try:
                    img = _capture_image(scale=_record_state["scale"])
                    _save_image(img, outpath)
                    _record_state["frames"] += 1
                    state.recording_frames = _record_state["frames"]
                    state.flush()
                except Exception as e:
                    state.last_movie = f"ERROR capturing frame: {e!s}"
                    state.flush()
                    break
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            pass

    @ctrl.set("start_recording")
    def on_start_recording():
        if _record_state["active"]:
            return
        import asyncio
        sess = _get_session_dir()
        movie_base = _resolve_name(state.movie_label, "movie")
        # Frames go to a temp subdir prefixed with "_" inside the session.
        # On finalize (gif/mov) the temp dir is deleted; for PNG seq we rename it.
        frames_dir = sess / f"_{movie_base}_frames"
        if frames_dir.exists():
            for f in frames_dir.glob("*"):
                try:
                    f.unlink()
                except OSError:
                    pass
        frames_dir.mkdir(parents=True, exist_ok=True)

        scale = _RES_SCALE.get(str(state.movie_resolution), 1)
        fps   = max(1, int(state.movie_fps))
        _record_state.update({
            "active": True, "dir": frames_dir, "frames": 0,
            "fps": fps,
            "format": str(state.movie_format),
            "scale": scale,
            "movie_base": movie_base,
            "session": sess,
        })
        state.recording_active = True
        state.recording_dir    = str(frames_dir)
        state.recording_frames = 0
        state.flush()
        # Schedule the capture loop as a separate task so this handler returns
        # immediately and Trame can process the Stop click while we record.
        _record_task[0] = asyncio.ensure_future(_record_loop())

    def _remove_dir(frames_dir) -> None:
        """Recursively remove a frames temp directory."""
        import pathlib
        import shutil
        try:
            shutil.rmtree(pathlib.Path(frames_dir))
        except OSError:
            pass

    def _finalize_movie(
        frames_dir, session_dir, movie_base: str, fps: int, fmt: str,
        gif_loop: bool = True,
    ) -> str:
        """Convert PNG sequence in frames_dir → <session>/<movie_base>.<fmt>.
        For PNG sequence, renames the temp frames dir to <session>/<movie_base>/.
        On successful gif/mov, the temp frames dir is removed."""
        import subprocess
        import pathlib
        frames_dir = pathlib.Path(frames_dir)
        session_dir = pathlib.Path(session_dir)

        if fmt == "png":
            target = session_dir / movie_base
            if target.exists():
                import datetime
                target = session_dir / f"{movie_base}_{datetime.datetime.now():%H%M%S}"
            frames_dir.rename(target)
            return str(target)

        out_path = session_dir / f"{movie_base}.{fmt}"
        if out_path.exists():
            import datetime
            out_path = session_dir / f"{movie_base}_{datetime.datetime.now():%H%M%S}.{fmt}"

        if fmt == "gif":
            try:
                import imageio.v2 as imageio
                pngs = sorted(frames_dir.glob("frame_*.png"))
                if not pngs:
                    _remove_dir(frames_dir)
                    return "ERROR: no frames captured"
                imgs = [imageio.imread(p) for p in pngs]
                # loop=0 = infinite, loop=1 = play once with no further repeats
                imageio.mimsave(out_path, imgs, fps=fps, loop=0 if gif_loop else 1)
                _remove_dir(frames_dir)
                return str(out_path)
            except Exception as e:
                return f"ERROR (gif): {e!s}"

        if fmt == "mov":
            cmd = [
                "ffmpeg", "-y",
                "-framerate", str(fps),
                "-i", str(frames_dir / "frame_%05d.png"),
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                str(out_path),
            ]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if proc.returncode != 0:
                    return f"ERROR (mov): ffmpeg returned {proc.returncode}: {proc.stderr[-300:]}"
                _remove_dir(frames_dir)
                return str(out_path)
            except FileNotFoundError:
                return "ERROR: ffmpeg not found in PATH"
            except Exception as e:
                return f"ERROR (mov): {e!s}"

        return f"ERROR: unknown format {fmt!r}"

    @ctrl.set("stop_recording")
    def on_stop_recording():
        if not _record_state["active"]:
            return
        _record_state["active"] = False
        state.recording_active = False
        state.flush()
        # Cancel the capture task so no new frames get written before finalize
        if _record_task[0] is not None and not _record_task[0].done():
            _record_task[0].cancel()
        result = _finalize_movie(
            frames_dir=_record_state["dir"],
            session_dir=_record_state["session"],
            movie_base=_record_state["movie_base"],
            fps=_record_state["fps"],
            fmt=_record_state["format"],
            gif_loop=bool(state.movie_loop),
        )
        state.last_movie = result
        state.flush()

    @ctrl.set("go_to_coords")
    def on_go_to_coords():
        x, y, z, d = (
            float(state.nav_x), float(state.nav_y),
            float(state.nav_z), float(state.nav_distance),
        )
        scene.camera.go_to_coords(x, y, z, d)
        if _focused():
            scene.set_focus_sphere((x, y, z), d)
        _push()

    @ctrl.set("zoom_to_box")
    def on_zoom_to_box():
        xmin, xmax = float(state.nav_box_xmin), float(state.nav_box_xmax)
        ymin, ymax = float(state.nav_box_ymin), float(state.nav_box_ymax)
        zmin, zmax = float(state.nav_box_zmin), float(state.nav_box_zmax)
        scene.camera.zoom_to_box(xmin, xmax, ymin, ymax, zmin, zmax)
        if _focused():
            scene.set_focus_box(xmin, xmax, ymin, ymax, zmin, zmax)
        _push()

    @ctrl.set("reset_camera")
    def on_reset():
        scene.camera.reset()
        scene.clear_focus()
        state.focus_active = False
        _push()

    @ctrl.set("toggle_focus")
    def on_toggle_focus():
        currently_on = bool(state.focus_active)
        state.focus_active = not currently_on
        if currently_on:
            scene.clear_focus()
        elif scene._focus_region is not None:
            halos, galaxies = scene._loader.get(scene._current_snap)
            scene._apply_focus_masks(halos.positions, galaxies.positions)
        _push()

    # ------------------------------------------------------------------
    # UI helper
    # ------------------------------------------------------------------

    def _tf(v_model, label):
        v3.VTextField(
            v_model=(v_model,), label=label,
            type="number", hide_details=True,
            variant="outlined", bg_color="#1a1a2e",
            density="compact",
        )

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    with v3.VSheet(
        color="#0d0d1a",
        style=(
            "height:100%;display:flex;flex-direction:column;"
            "color:#e2e8f0;overflow:hidden;"
        ),
    ):
        # ── Reset + Focus ──────────────────────────────────────────
        with v3.VSheet(color="transparent", style="padding:8px;flex-shrink:0;"):
            with v3.VRow(no_gutters=True, style="gap:6px;"):
                with v3.VCol(style="padding:0;"):
                    v3.VBtn(
                        "Reset Camera", block=True, variant="outlined",
                        color="cyan", density="compact",
                        click=ctrl.reset_camera,
                    )
                with v3.VCol(cols="auto", style="padding:0;"):
                    v3.VBtn(
                        icon="mdi-target", variant="outlined",
                        density="compact", click=ctrl.toggle_focus,
                        color=("focus_active ? 'cyan' : '#6b7280'",),
                        title="Focus",
                    )

        v3.VDivider(style="flex-shrink:0;")

        # ── Tab rows: 3-up grid, primary row + secondary row ───────
        with v3.VBtnToggle(
            v_model=("nav_active_tab",),
            mandatory=True,
            density="compact",
            style=(
                "width:100%;flex-shrink:0;background:#111827;"
                "border-radius:0;display:flex;flex-wrap:wrap;"
            ),
        ):
            for label, value in [
                ("Structure", "layers"),
                ("Filters",   "filters"),
                ("Record",    "record"),
                ("Target",    "target"),
                ("Coords",    "coords"),
                ("Box",       "box"),
            ]:
                v3.VBtn(
                    label, value=value,
                    style=(
                        "flex:0 0 33.333%;font-size:0.72rem;letter-spacing:0;"
                        "min-width:0;text-transform:none;font-weight:700;"
                    ),
                    color=(
                        "nav_active_tab === '{}' ? 'cyan' : '#6b7280'".format(value),
                    ),
                    variant="text",
                    density="compact",
                )

        v3.VDivider(style="flex-shrink:0;")

        # ── Tab content (overflow-y:scroll keeps scrollbar space stable
        #    across tab switches so the render view never resizes)
        with v3.VSheet(
            color="transparent",
            style="flex:1;overflow-y:scroll;padding:10px 12px;",
        ):
            # Layers
            with v3.VSheet(
                color="transparent",
                v_show=("nav_active_tab === 'layers'",),
            ):
                v3.VLabel(
                    "DARK MATTER HALOES",
                    style=(
                        "font-size:0.7rem;font-weight:700;letter-spacing:0.08em;"
                        "color:#7c3aed;padding:6px 0 8px;display:block;"
                    ),
                )
                with v3.VSheet(color="transparent", style=_FIELD):
                    v3.VSwitch(
                        v_model=("halos_visible",), label="Visible",
                        color="cyan", hide_details=True, density="compact",
                    )
                with v3.VSheet(color="transparent", style=_FIELD):
                    v3.VSlider(
                        v_model=("halo_opacity",), label="Opacity",
                        min=0.0, max=1.0, step=0.01,
                        thumb_label="always", color="cyan", hide_details=True,
                    )
                with v3.VSheet(color="transparent", style=_FIELD):
                    v3.VSelect(
                        v_model=("halo_color_mode",), items=(_HALO_MODES,),
                        label="Colour by", hide_details=True,
                        variant="outlined", color="cyan", density="compact",
                    )
                with v3.VSheet(color="transparent", style=_FIELD):
                    v3.VSelect(
                        v_model=("halo_colormap",), items=(_CMAPS,),
                        label="Colormap", hide_details=True,
                        variant="outlined", color="cyan", density="compact",
                    )
                with v3.VSheet(color="transparent", style="padding:4px 0 8px;"):
                    with v3.VSheet(
                        color="transparent",
                        style="display:flex;align-items:center;gap:4px;",
                    ):
                        v3.VLabel(
                            "{{ halo_cbar_min }}",
                            style="font-size:0.58rem;color:#6b7280;white-space:nowrap;flex-shrink:0;",
                        )
                        v3.VSheet(style=("halo_cbar_style",), color="transparent")
                        v3.VLabel(
                            "{{ halo_cbar_max }}",
                            style="font-size:0.58rem;color:#6b7280;white-space:nowrap;flex-shrink:0;",
                        )

                v3.VDivider(style="margin:14px 0;")

                v3.VLabel(
                    "GALAXIES",
                    style=(
                        "font-size:0.7rem;font-weight:700;letter-spacing:0.08em;"
                        "color:#7c3aed;padding:6px 0 8px;display:block;"
                    ),
                )
                with v3.VSheet(color="transparent", style=_FIELD):
                    v3.VSwitch(
                        v_model=("galaxies_visible",), label="Visible",
                        color="deep-purple", hide_details=True, density="compact",
                    )
                with v3.VSheet(color="transparent", style=_FIELD):
                    v3.VSlider(
                        v_model=("galaxy_opacity",), label="Opacity",
                        min=0.0, max=1.0, step=0.01,
                        thumb_label="always", color="deep-purple", hide_details=True,
                    )
                with v3.VSheet(color="transparent", style=_FIELD):
                    v3.VSelect(
                        v_model=("galaxy_color_mode",), items=(_GALAXY_MODES,),
                        label="Colour by", hide_details=True,
                        variant="outlined", color="deep-purple", density="compact",
                    )
                with v3.VSheet(color="transparent", style=_FIELD):
                    v3.VSelect(
                        v_model=("galaxy_colormap",), items=(_CMAPS,),
                        label="Colormap", hide_details=True,
                        variant="outlined", color="deep-purple", density="compact",
                    )
                with v3.VSheet(color="transparent", style="padding:4px 0 8px;"):
                    with v3.VSheet(
                        color="transparent",
                        style="display:flex;align-items:center;gap:4px;",
                    ):
                        v3.VLabel(
                            "{{ gal_cbar_min }}",
                            style="font-size:0.58rem;color:#6b7280;white-space:nowrap;flex-shrink:0;",
                        )
                        v3.VSheet(style=("gal_cbar_style",), color="transparent")
                        v3.VLabel(
                            "{{ gal_cbar_max }}",
                            style="font-size:0.58rem;color:#6b7280;white-space:nowrap;flex-shrink:0;",
                        )

                v3.VDivider(style="margin:14px 0 10px;")

                v3.VBtn(
                    "Reset Opacities",
                    block=True, variant="outlined",
                    color="red", density="compact",
                    prepend_icon="mdi-restore",
                    click=ctrl.reset_opacities,
                )

            # Target (halo + galaxy combined)
            with v3.VSheet(
                color="transparent",
                v_show=("nav_active_tab === 'target'",),
            ):
                v3.VLabel(
                    "HALO",
                    style=(
                        "font-size:0.68rem;font-weight:700;letter-spacing:0.06em;"
                        "color:#7c3aed;display:block;padding:4px 0 6px;"
                    ),
                )
                with v3.VSheet(color="transparent", style=_FIELD):
                    _tf("nav_halo_idx", "Halo index")
                with v3.VSheet(color="transparent", style=_FIELD):
                    _tf("nav_distance", "Standoff (Mpc/h)")
                with v3.VSheet(color="transparent", style=_BTN):
                    v3.VBtn(
                        "Go", block=True, color="cyan",
                        density="compact", click=ctrl.go_to_halo,
                    )

                v3.VDivider(style="margin:12px 0;")

                v3.VLabel(
                    "GALAXY",
                    style=(
                        "font-size:0.68rem;font-weight:700;letter-spacing:0.06em;"
                        "color:#7c3aed;display:block;padding:4px 0 6px;"
                    ),
                )
                with v3.VSheet(color="transparent", style=_FIELD):
                    with v3.VForm(submit=ctrl.go_to_galaxy_enter):
                        _tf("nav_gal_idx", "Galaxy index  (Enter to go)")
                with v3.VSheet(color="transparent", style=_BTN):
                    v3.VBtn(
                        "Go", block=True, color="deep-purple",
                        density="compact", click=ctrl.go_to_galaxy_enter,
                    )
                v3.VLabel(
                    "Zoom radius (Mpc/h)",
                    style=(
                        "font-size:0.68rem;color:#9ca3af;"
                        "display:block;padding:10px 0 4px;"
                    ),
                )
                with v3.VBtnGroup(
                    variant="outlined", density="compact",
                    style="width:100%;",
                ):
                    v3.VBtn("3",  style="flex:1;", color="deep-purple",
                            click=ctrl.go_to_galaxy_1)
                    v3.VBtn("5",  style="flex:1;", color="deep-purple",
                            click=ctrl.go_to_galaxy_3)
                    v3.VBtn("10", style="flex:1;", color="deep-purple",
                            click=ctrl.go_to_galaxy_5)

                v3.VDivider(style="margin:14px 0 10px;")

                v3.VBtn(
                    "Clear Indicator",
                    block=True, variant="outlined",
                    color="red", density="compact",
                    prepend_icon="mdi-close-circle-outline",
                    click=ctrl.clear_indicator,
                )

            # Coords
            with v3.VSheet(
                color="transparent",
                v_show=("nav_active_tab === 'coords'",),
            ):
                for label, key in [
                    ("X (Mpc/h)", "nav_x"),
                    ("Y (Mpc/h)", "nav_y"),
                    ("Z (Mpc/h)", "nav_z"),
                    ("Standoff",  "nav_distance"),
                ]:
                    with v3.VSheet(color="transparent", style=_FIELD):
                        _tf(key, label)
                with v3.VSheet(color="transparent", style=_BTN):
                    v3.VBtn(
                        "Go", block=True, color="cyan",
                        density="compact", click=ctrl.go_to_coords,
                    )

            # Box
            with v3.VSheet(
                color="transparent",
                v_show=("nav_active_tab === 'box'",),
            ):
                for label, key in [
                    ("X min", "nav_box_xmin"), ("X max", "nav_box_xmax"),
                    ("Y min", "nav_box_ymin"), ("Y max", "nav_box_ymax"),
                    ("Z min", "nav_box_zmin"), ("Z max", "nav_box_zmax"),
                ]:
                    with v3.VSheet(color="transparent", style=_FIELD):
                        _tf(key, label)
                with v3.VSheet(color="transparent", style=_BTN):
                    v3.VBtn(
                        "Zoom", block=True, color="cyan",
                        density="compact", click=ctrl.zoom_to_box,
                    )

            # ── FILTERS tab ────────────────────────────────────
            with v3.VSheet(
                color="transparent",
                v_show=("nav_active_tab === 'filters'",),
            ):
                v3.VLabel(
                    "DARK MATTER HALOES",
                    style=(
                        "font-size:0.7rem;font-weight:700;letter-spacing:0.08em;"
                        "color:#7c3aed;padding:6px 0 8px;display:block;"
                    ),
                )
                v3.VLabel(
                    "Mvir range  (log₁₀ M☉)",
                    style="font-size:0.68rem;color:#9ca3af;display:block;padding:6px 0 2px;",
                )
                v3.VRangeSlider(
                    v_model=("filter_halo_mvir",),
                    min=10.0, max=15.0, step=0.1,
                    thumb_label=True, color="cyan",
                    density="compact", hide_details=True,
                )

                v3.VDivider(style="margin:14px 0;")

                v3.VLabel(
                    "GALAXIES",
                    style=(
                        "font-size:0.7rem;font-weight:700;letter-spacing:0.08em;"
                        "color:#7c3aed;padding:6px 0 8px;display:block;"
                    ),
                )
                v3.VLabel(
                    "Stellar mass  (log₁₀ M☉)",
                    style="font-size:0.68rem;color:#9ca3af;display:block;padding:6px 0 2px;",
                )
                v3.VRangeSlider(
                    v_model=("filter_gal_smass",),
                    min=8.0, max=12.5, step=0.1,
                    thumb_label=True, color="deep-purple",
                    density="compact", hide_details=True,
                )
                v3.VLabel(
                    "sSFR  (log₁₀ yr⁻¹)",
                    style="font-size:0.68rem;color:#9ca3af;display:block;padding:10px 0 2px;",
                )
                v3.VRangeSlider(
                    v_model=("filter_gal_ssfr",),
                    min=-14.0, max=-8.0, step=0.1,
                    thumb_label=True, color="deep-purple",
                    density="compact", hide_details=True,
                )
                v3.VLabel(
                    "B / T  (bulge / stellar)",
                    style="font-size:0.68rem;color:#9ca3af;display:block;padding:10px 0 2px;",
                )
                v3.VRangeSlider(
                    v_model=("filter_gal_bt",),
                    min=0.0, max=1.0, step=0.02,
                    thumb_label=True, color="deep-purple",
                    density="compact", hide_details=True,
                )
                v3.VLabel(
                    "BH mass  (log₁₀ M☉)",
                    style="font-size:0.68rem;color:#9ca3af;display:block;padding:10px 0 2px;",
                )
                v3.VRangeSlider(
                    v_model=("filter_gal_bhmass",),
                    min=0.0, max=10.0, step=0.1,
                    thumb_label=True, color="deep-purple",
                    density="compact", hide_details=True,
                )
                v3.VLabel(
                    "ICS mass  (log₁₀ M☉)",
                    style="font-size:0.68rem;color:#9ca3af;display:block;padding:10px 0 2px;",
                )
                v3.VRangeSlider(
                    v_model=("filter_gal_ics",),
                    min=0.0, max=12.0, step=0.1,
                    thumb_label=True, color="deep-purple",
                    density="compact", hide_details=True,
                )

                v3.VLabel(
                    "Type",
                    style="font-size:0.68rem;color:#9ca3af;display:block;padding:10px 0 2px;",
                )
                v3.VSelect(
                    v_model=("filter_gal_type",),
                    items=([
                        {"title": "All",         "value": "both"},
                        {"title": "Centrals",    "value": "central"},
                        {"title": "Satellites",  "value": "satellite"},
                    ],),
                    hide_details=True, variant="outlined",
                    color="deep-purple", density="compact",
                )

                v3.VLabel(
                    "FFB regime",
                    style="font-size:0.68rem;color:#9ca3af;display:block;padding:10px 0 2px;",
                )
                v3.VSelect(
                    v_model=("filter_gal_ffb",),
                    items=([
                        {"title": "Any",          "value": "any"},
                        {"title": "FFB only",     "value": "yes"},
                        {"title": "Non-FFB only", "value": "no"},
                    ],),
                    hide_details=True, variant="outlined",
                    color="deep-purple", density="compact",
                )

                v3.VLabel(
                    "CGM / Hot regime",
                    style="font-size:0.68rem;color:#9ca3af;display:block;padding:10px 0 2px;",
                )
                v3.VSelect(
                    v_model=("filter_gal_cgm",),
                    items=([
                        {"title": "Any",                     "value": "any"},
                        {"title": "CGM galaxies",            "value": "cold"},
                        {"title": "Hot atmosphere galaxies", "value": "hot"},
                    ],),
                    hide_details=True, variant="outlined",
                    color="deep-purple", density="compact",
                )

                v3.VLabel(
                    "Environment  (host M_FOF)",
                    style="font-size:0.68rem;color:#9ca3af;display:block;padding:10px 0 2px;",
                )
                v3.VSelect(
                    v_model=("filter_gal_env",),
                    items=([
                        {"title": "All",                          "value": "all"},
                        {"title": "Field      (< 10¹¹ M☉)",       "value": "field"},
                        {"title": "Isolated   (10¹¹–10¹²·⁵ M☉)",  "value": "isolated"},
                        {"title": "Group      (10¹²·⁵–10¹⁴ M☉)",  "value": "group"},
                        {"title": "Cluster    (> 10¹⁴ M☉)",       "value": "cluster"},
                    ],),
                    hide_details=True, variant="outlined",
                    color="deep-purple", density="compact",
                )

                v3.VDivider(style="margin:14px 0 10px;")

                v3.VBtn(
                    "Reset Filters",
                    block=True, variant="outlined",
                    color="red", density="compact",
                    prepend_icon="mdi-restore",
                    click=ctrl.reset_filters,
                )

            # ── RECORD tab ─────────────────────────────────────
            with v3.VSheet(
                color="transparent",
                v_show=("nav_active_tab === 'record'",),
            ):
                v3.VLabel(
                    "SCREENSHOT",
                    style=(
                        "font-size:0.7rem;font-weight:700;letter-spacing:0.08em;"
                        "color:#7c3aed;padding:6px 0 8px;display:block;"
                    ),
                )
                v3.VTextField(
                    v_model=("screenshot_label",),
                    label="Label (optional)",
                    hide_details=True, variant="outlined",
                    bg_color="#1a1a2e", density="compact",
                    style="padding-bottom:8px;",
                )
                v3.VBtn(
                    "Take Screenshot",
                    block=True, color="cyan",
                    density="compact",
                    prepend_icon="mdi-camera",
                    click=ctrl.take_screenshot,
                )
                with v3.VRow(no_gutters=True, style="gap:6px;padding-top:6px;"):
                    with v3.VCol(style="padding:0;"):
                        v3.VBtn(
                            "PNG", block=True, variant="outlined",
                            color="cyan", density="compact",
                            click=ctrl.screenshot_png,
                        )
                    with v3.VCol(style="padding:0;"):
                        v3.VBtn(
                            "JPG", block=True, variant="outlined",
                            color="cyan", density="compact",
                            click=ctrl.screenshot_jpg,
                        )
                    with v3.VCol(style="padding:0;"):
                        v3.VBtn(
                            "TIFF", block=True, variant="outlined",
                            color="cyan", density="compact",
                            click=ctrl.screenshot_tiff,
                        )
                v3.VLabel(
                    "Saved to <SAGE-Viewer>/sage_outputs/session_*/",
                    style="font-size:0.62rem;color:#6b7280;display:block;padding:6px 0 2px;",
                )
                v3.VLabel(
                    "{{ last_screenshot ? 'Last: ' + last_screenshot : '' }}",
                    style="font-size:0.58rem;color:#6b7280;display:block;word-break:break-all;",
                )

                v3.VDivider(style="margin:14px 0;")

                v3.VLabel(
                    "RECORD MOVIE",
                    style=(
                        "font-size:0.7rem;font-weight:700;letter-spacing:0.08em;"
                        "color:#7c3aed;padding:6px 0 8px;display:block;"
                    ),
                )
                v3.VTextField(
                    v_model=("movie_label",),
                    label="Label (optional)",
                    hide_details=True, variant="outlined",
                    bg_color="#1a1a2e", density="compact",
                    style="padding-bottom:8px;",
                )
                v3.VLabel(
                    "FPS (output)  {{ '— ' + movie_fps }}",
                    style="font-size:0.68rem;color:#9ca3af;display:block;padding:4px 0 2px;",
                )
                v3.VSlider(
                    v_model=("movie_fps",),
                    min=1, max=60, step=1,
                    thumb_label=True, color="cyan",
                    density="compact", hide_details=True,
                )

                v3.VLabel(
                    "Resolution",
                    style="font-size:0.68rem;color:#9ca3af;display:block;padding:10px 0 2px;",
                )
                v3.VSelect(
                    v_model=("movie_resolution",),
                    items=([
                        {"title": "Native  (1×)",       "value": "native"},
                        {"title": "High   (2× window)", "value": "hd"},
                        {"title": "Ultra  (4× window)", "value": "uhd"},
                    ],),
                    hide_details=True, variant="outlined",
                    color="cyan", density="compact",
                )

                v3.VLabel(
                    "Output format",
                    style="font-size:0.68rem;color:#9ca3af;display:block;padding:10px 0 2px;",
                )
                v3.VSelect(
                    v_model=("movie_format",),
                    items=([
                        {"title": "GIF",          "value": "gif"},
                        {"title": "MOV  (H.264)", "value": "mov"},
                        {"title": "PNG sequence", "value": "png"},
                    ],),
                    hide_details=True, variant="outlined",
                    color="cyan", density="compact",
                )

                # GIF-only: repeat (loop) checkbox
                v3.VCheckbox(
                    v_model=("movie_loop",),
                    label="Loop GIF forever",
                    v_show=("movie_format === 'gif'",),
                    color="cyan",
                    density="compact",
                    hide_details=True,
                    style="padding-top:4px;",
                )

                with v3.VRow(no_gutters=True, style="gap:6px;padding-top:10px;"):
                    with v3.VCol(style="padding:0;"):
                        v3.VBtn(
                            "Start", block=True, color="red",
                            density="compact",
                            prepend_icon="mdi-record-circle-outline",
                            click=ctrl.start_recording,
                            disabled=("recording_active",),
                        )
                    with v3.VCol(style="padding:0;"):
                        v3.VBtn(
                            "Stop", block=True, color="#6b7280",
                            density="compact",
                            prepend_icon="mdi-stop",
                            click=ctrl.stop_recording,
                            disabled=("!recording_active",),
                        )

                v3.VLabel(
                    "{{ recording_active ? '● Recording — ' + recording_frames + ' frames' : 'Idle' }}",
                    style="font-size:0.68rem;color:#9ca3af;display:block;padding:10px 0 2px;",
                )
                v3.VLabel(
                    "{{ last_movie ? 'Last: ' + last_movie : '' }}",
                    style="font-size:0.58rem;color:#6b7280;display:block;word-break:break-all;padding:4px 0;",
                )
