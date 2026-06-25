# Story Mode — MCR Build Hand-off

A complete brief for resuming the **Mid-Candidature Review (MCR) story** work in a
fresh chat. Read this top-to-bottom before making changes.

---

## 0. Paste this to start the new chat

> I'm building my PhD MCR presentation with **Story Mode**, on the **`story-mode`**
> git branch only. The story file is **`sage_stories/mcr.json`**. Read
> `docs/project/story_mode_mcr_handoff.md` (this file) and
> `docs/project/story_mode_design.md` (full schema) first. **Stay strictly inside
> the scope in §3 of the hand-off** — only the MCR JSON and Story Mode framework,
> nothing else, no version bumps, no tags, no merging to main.

---

## 1. What this is

**Story Mode** is a guided, data-driven presentation layer for SAGE-Viewer: an
ordered set of *scenes* (each a captured viewpoint + on-screen text/equations)
stepped through with Previous / Play / Pause / Next. It is used to build the
author's MCR talk.

It is **intentionally NOT in the public release.** It lives only on the
`story-mode` branch. `main` / PyPI ship the framework-free viewer.

## 2. Current repo state (as of hand-off)

- **Branch:** all MCR work happens on **`story-mode`** (pushed to `origin/story-mode`).
- **`main` / PyPI:** frozen at **1.2.1** (the live release). Do **not** touch.
  - ⚠️ `1.2.0` on PyPI was a botched build (tagged from the wrong commit) and was
    **yanked**. Never reuse `1.2.0`.
- **Install (IMPORTANT — read this):** the build loop only works with an
  **editable** install. If `pip show sage-viewer` does **not** list an "Editable
  project location", you have a *regular* install and the `sage-viewer` console
  script runs a **stale copy in site-packages** — repo `.py`/JS edits will NOT
  show up until you reinstall (this bit the build hard, presenting as "my changes
  aren't appearing / autoplay not working / overlay crash"). Fix it **once**:
  `pip install -e . --config-settings editable_mode=compat`. Then the console
  script loads the repo source via a `.pth`. **Do not run a plain `pip install .`
  afterwards** — it reverts you to the stale-copy install. Verify (run from
  OUTSIDE the repo): `python3 -c "import sage_viewer;print(sage_viewer.__file__)"`
  → must print the **repo** path, not `site-packages`.
- **Reload rules (important for the build loop):**
  - **Story content (`sage_stories/mcr.json`)** → edit, then **exit Story Mode and
    re-open it**. Changes load with **NO app restart** (`story_open` re-reads the
    file from disk every time; the dropdown re-scans the folder on open).
  - **Framework Python (`.py`)** → **restart `sage-viewer`** (modules load once).
  - **JS/CSS** (`sage_viewer/static/*`) → restart; they're **cache-busted** so no
    browser hard-refresh needed.
  - You never need to reinstall — just restart (for code) or re-open (for JSON).
- **Tests:** run with **`python3 -m pytest -q`** (the `-m` form uses the source;
  a bare `pytest` may resolve a stale copy).

## 3. SCOPE — what may and may not be touched ⚠️

The MCR build must not disturb anything outside Story Mode. Treat this as a hard
boundary.

### ✅ In scope (allowed)
- **`sage_stories/mcr.json`** — the MCR story content. This is the main work.
- **Story Mode framework**, *only if a Story Mode bug must be fixed*:
  - `sage_viewer/story/` (`engine.py`, `model.py`, `io.py`, `keys.py`, `__init__.py`)
  - `sage_viewer/ui/story_mode.py`
  - `sage_viewer/scene/camera_motion.py`
  - the Story Mode blocks in `sage_viewer/static/sage_viewer.js` (overlay renderer / KaTeX)
  - the Story Mode hooks in `sage_viewer/app.py` (button, HUD, overlays mount)
  - `sage_viewer/static/katex/**` (vendored, don't edit by hand)
  - `tests/test_story.py`
  - `docs/project/story_mode_design.md`, this hand-off
- `sage_viewer/examples/example_tour.json` — bundled demo (only if demonstrating).

### ❌ Out of scope (do NOT touch)
- Any **non-Story-Mode** code: `io/`, `parallel/`, `scene/*` (except `camera_motion.py`),
  `wizard/`, `ui/navigation_panel.py`, `ui/toolbar.py`, `ui/info_panel.py`,
  `utils/*`, etc. — unless a Story Mode scene exposes a *genuine* bug there, in
  which case **flag it and ask before editing**.
- `sage_viewer/_version.py`, `CHANGELOG.md`, `pyproject.toml` — **no version
  bumps, no release edits.**
- The **`main`** branch — no merges to it, no PRs from story-mode.
- **No git tags** of any kind on `story-mode`. A `v*` tag auto-publishes to PyPI
  via `.github/workflows/publish.yml` — never tag this branch.
- General-viewer behaviour/UX changes unrelated to the talk.

### Working rules
- Stay on `story-mode`. Don't merge `main` in (per the author: `main` is frozen,
  no further sync needed).
- Don't bump versions, don't tag, don't release.
- Commit MCR changes to `sage_stories/` freely; push to `origin/story-mode`.
- If a fix needs an out-of-scope file, **stop and ask** first.

## 4. How Story Mode works (essentials)

Full reference: **`docs/project/story_mode_design.md`**. Summary:

- A **story** is one JSON file. `discover_stories()` scans **`CWD/sage_stories/*.json`**
  plus the bundled `sage_viewer/examples/`. So **launch `sage-viewer` from the repo
  root** so `sage_stories/mcr.json` is found; then open the **Story Mode** button
  (book icon, next to Fly-through) → **"Mid-Candidature Review"**.
- A **scene** captures the complete view; applying it writes state through the
  existing render pipeline (filters/layers re-render), moves the camera smoothly,
  sets focus/target, theme, chrome, and text overlays.
- **Non-destructive:** Pause hands full control back; Exit restores the
  pre-story camera/state/theme.

### Scene fields (quick reference)

```jsonc
{
  "id": "intro",
  "title": "Shown in the HUD",
  "caption": "HUD caption text",
  "snap_num": "last",            // int, "first", "last", or "40%"  (per-model)
  "theme": "dos_blue",           // optional per-scene theme

  "camera": "box",               // "box"/"reset" (frame all loaded boxes) OR
                                 // {"position":[x,y,z],"focal_point":[x,y,z],"up":[0,1,0]}

  "state": {                     // any STORY_STATE_KEYS (layers/filters/env)
    "halos_visible": true, "galaxies_visible": true,
    "halo_opacity": 0.12, "galaxy_opacity": 1.0,
    "halo_color_mode": "mvir", "halo_colormap": "viridis",
    "galaxy_color_mode": "structure", "galaxy_colormap": "plasma",
    "filter_gal_smass": [10.0, 14.0], "filter_halo_mvir": [12.0, 15.0]
    // env: env_show_cluster/field/group/isolated/pairs
  },

  "focus": { "kind": "none" },   // none | {"kind":"sphere","center":"box","radius_frac":0.45}
                                 //      | {"kind":"sphere","center":[x,y,z],"radius":30}
                                 //      | {"kind":"box","bounds":[xmin,xmax,ymin,ymax,zmin,zmax]}

  "target": {                    // optional object highlight
    "position": [x,y,z], "radius": 30, "galaxy_index": 81234, "highlight_group": true
  },

  "models": { "primary": "current", "adjacent": ["auto"] },  // optional; see below

  "chrome": { "hide_panel": true },   // hide right panel (Story Mode only)

  "overlays": [ /* see below */ ],

  "transition": { "duration_secs": 5.0, "easing": "smoothstep" }, // fly INTO scene
  "dwell_secs": 6.0,                                              // hold time in Play
  "motion": { "kind": "still" }                                  // still | orbit | snapshot_sweep
}
```

### Symbolic values (portable; resolved at runtime per model)
| Field | Accepts |
|---|---|
| `snap_num`, sweep `from`/`to` | int · `"first"` · `"last"` · `"40%"` |
| `camera` | `"box"` / `"reset"` (frames all loaded boxes) · explicit dict |
| `focus.center` | `"box"` (box centre) · `[x,y,z]` |
| `focus` radius | `radius` (absolute) · `radius_frac` (× box size) |
| `models.primary` | `"current"` (launched) · `"other"`/`"auto"` (another available) · explicit name |
| `models.adjacent` | list of names / `"auto"` (auto-pick a 2nd model for side-by-side) |

### Motion kinds
- `{"kind":"still"}` — hold for `dwell_secs`.
- `{"kind":"orbit","dps":12,"degrees":360,"radius":40}` — spin around target/focus centre.
- `{"kind":"snapshot_sweep","from":"40%","to":"last","fps":4}` — animate through cosmic
  time. In multi-box, advances **all** loaded boxes.
- `{"kind":"flythrough"}` — cinematic tour that **keeps touring groups until Next**
  (reset → approach box centre → biggest group → every cluster with focus → then cycle
  groups forever). See §10. Optional tunables: `approach_secs`, `fly_secs`,
  `group_radius`, `cluster_radius`, `group_dps`, `cluster_dps`.

### Overlays (in-view text & equations)
Rendered over the VTK view by `sage_viewer.js` (outside Vue, so KaTeX can't corrupt
the vDOM). Equations use **vendored KaTeX** (offline, no network).

```jsonc
"overlays": [
  { "kind": "title",    "text": "...", "anchor": "top", "y": 8 },
  { "kind": "heading",  "text": "...", "anchor": "top-left", "color": "#06b6d4" },
  { "kind": "text",     "text": "multi-line\nbody", "anchor": "left" },
  { "kind": "citation", "text": "Croton et al. (2016)", "anchor": "bottom-right" },
  { "kind": "equation", "latex": "\\dot{M}_* = \\alpha\\,M_{\\rm cold}/t_{\\rm dyn}",
    "anchor": "center", "size": 2.0 },  // add "inline": true for inline math
  { "kind": "image", "src": "/sage_static/SAGElogo.jpg", "anchor": "bottom-left",
    "x": 0, "y": 0, "width": 150 }      // logos/wordmarks — see §10
]
```
- `anchor`: 9-grid — `top-left`,`top`,`top-right`,`left`,`center`,`right`,`bottom-left`,`bottom`,`bottom-right`.
- `x`,`y`: nudge from the anchor edges. **Numeric → percentage; string → CSS length**
  (e.g. `"150px"`), so logos pin together at a fixed offset regardless of window width.
- Other overrides: `size` (rem), `color`, `weight`, `align`, `max_width` (vw).
- LaTeX strings are JSON, so backslashes are doubled (`\\dot`, `\\frac`).
- `image` overlays: `src` is served from `sage_viewer/static/` at `/sage_static/<file>`
  (NOT the data Library); use **PNG/JPG/SVG, not PDF**; `width` is px (number) or any CSS
  length; `opacity` optional. Bundled: `SAGElogo.jpg`, `CAS_logo.png`.

## 5. The MCR file

- **Location:** `sage_stories/mcr.json` (tracked on `story-mode` only — a branch
  `.gitignore` exception `!sage_stories/*.json` makes it version-controlled).
- **Current state:** **Slide 1 (title) is built** (see §10) — a right-aligned
  title column (Mid-Candidature Review / Michael Bradley / Supervisors block),
  SAGE + CAS logos pinned bottom-left, story-level `autoplay`, and a `flythrough`
  motion as the moving background. Build the remaining scenes from here.
- **Running it:** launch `sage-viewer` from the **repo root**, open Story Mode →
  "Mid-Candidature Review".

## 6. Available models / data (for authoring camera & snapshots)

Output dir: `/Users/mbradley/Documents/PhD/SAGE26/output/`. Model name = folder name.

| Model (name) | Box size | Snapshots | Centre (for `camera`/`focus`) |
|---|---|---|---|
| `millennium` | 62.5 Mpc/h | 0–63 (z=0 at 63) | (31.25, 31.25, 31.25) |
| `microuchuu` | 100 Mpc/h | 0–49 (z=0 at 49) | (50, 50, 50) |
| variants: `millennium_mbk`, `millennium_vanilla`, `microuchuu_karl`, `microuchuu_vanilla`, `millennium_noFFB`, `millennium_test`, … | as above | as above | |

Prefer **symbolic** values (`"last"`, `"box"`, `"current"`/`"auto"`) so the story
isn't pinned to one model — but for a fixed MCR you can hardcode names/coords.

Colour modes — galaxies: `structure`, `type`, `stellar_mass`, `ssfr`, `sfr`,
`cold_gas`, `bulge_mass`, `bt`, `bh_mass`, `ics_mass`, `age`, `cgm_gas`, `hot_gas`,
`h1_gas`, `h2_gas`, `ejected_mass`, `outflow_rate`. Haloes: `mvir`, `rvir`, `vvir`,
`vmax`. Colormaps: any matplotlib name (`viridis`, `plasma`, `inferno`, `turbo`, …).

## 7. Dev workflow

```bash
git switch story-mode               # always work here
# edit sage_stories/mcr.json  ->  in the app: exit Story Mode + re-open it (NO restart)
# edit Story Mode framework (.py, bug fixes only)  ->  restart sage-viewer
python3 -m pytest -q                # if framework code changed
git add sage_stories/ ...           # stage MCR (+ any in-scope framework fix)
git commit -m "mcr: <what changed>"
git push origin story-mode
```

## 8. Known limitations / gotchas
- **`GalaxyIndex` is per-snapshot**, not stable across snapshots (no merger trees) —
  can't "follow the same galaxy through time" via `target`; use position-based targets
  per scene.
- **Multi-box `snapshot_sweep`** loads the adjacent model's snapshots on demand
  (not preloaded) — first pass may stutter.
- **`sage_stories/` discovery is CWD-based** — run `sage-viewer` from the repo root
  (or wherever `sage_stories/mcr.json` lives) so it's found.
- **Never tag `story-mode` with `v*`** (auto-publishes to PyPI).
- Captured screenshots/recordings reflect the current view; Story Mode overlays are
  HTML over the canvas and are **not** baked into VTK screenshots.
- **Panel toggle reshapes the VTK view.** The right panel is a fixed 300px flex
  child toggled with `v-show` (`display:none`), so showing/hiding it (e.g. when
  pause re-shows it) snaps the canvas width and the remote view re-frames
  (apparent zoom/shift). **Left as-is by author's choice** — a smooth-slide or
  overlay fix would touch out-of-scope general layout (`app.py` panel /
  `VtkRemoteView`).

## 9. Eventual end-state (after the MCR)
Per the author: stash the MCR content and send only the **framework** to `main`/PyPI
later. Because the framework (`sage_viewer/...`) and MCR content (`sage_stories/`) are
cleanly separated, that's a code-only promotion — the MCR JSON never needs to leave
`story-mode`.

> ⚠️ The bundled `CAS_logo.png` (and any personal logo) under `sage_viewer/static/`
> is MCR content, not framework — exclude it (and the `image`/`flythrough`/`autoplay`
> docs examples if undesired) when promoting the framework to `main`/PyPI.

## 10. Framework features added during the MCR build (session log)

All on `story-mode`, in-scope per §3. Framework `.py`/JS changes need a
**`sage-viewer` restart** (with the **editable** install from §2 — otherwise they
won't show up); `mcr.json` reloads on re-open. Tests: `python3 -m pytest -q`.

### Story-level `autoplay`
Top-level boolean in the story JSON (sibling of `scenes`). `true` → entering the
story starts playback immediately (no Play click), so a title scene's motion runs
on open. `Story.autoplay` (`model.py`), applied in `engine._enter_async`.

### Motion kind: `flythrough`
`{"kind":"flythrough"}` — cinematic tour that **keeps touring groups until Next**:
reset camera → approach box centre → orbit the most-massive group → visit every
cluster most→least (with a focus ring) → then cycle the groups forever. Group =
halo Mvir 10^12.5–10^14; cluster = ≥10^14. Drives the camera with the shared
`scene/camera_motion.py` helpers (the same ones the toolbar fly-through uses), so
**`toolbar.py` is not edited**. Optional tunables on the motion object (defaults):
`approach_secs` 8, `fly_secs` 7, `group_radius` 15, `cluster_radius` 30,
`group_dps` 10, `cluster_dps` 8. (`engine._motion_flythrough` /
`_flythrough_targets`.)

### Overlay kind: `image` (logos / wordmarks)
`{ "kind":"image", "src":"/sage_static/<file>", "anchor":"bottom-left", "x":0,
"y":0, "width":150 }`. `src` is served from `sage_viewer/static/` at
`/sage_static/<file>` (**not** the data Library); use **PNG/JPG/SVG, not PDF**.
`width` is px (number) or any CSS length; `opacity` optional. Rendered as an
`<img>` by `sage_viewer.js`; normalised in `engine._normalize_overlay`. Bundled
assets: `SAGElogo.jpg`, `CAS_logo.png`.

### Overlay `x`/`y` accept pixel offsets
For **all** overlay kinds, `x`/`y` are a **percentage when numeric, a CSS length
when a string** (e.g. `"150px"`), so logos pin together at a fixed offset
regardless of window width. (`engine._overlay_position_style`.)

### Pause = hand back full control
Pause now **freezes motion AND re-shows the right panel** (`panels_hidden=False`),
even if the scene set `chrome.hide_panel`. **Play after pause resumes in place** —
it does not re-stage the scene, so the fly-through does **not** restart: it skips
its reset/approach intro (tracked per scene in `_ft_done`) and continues touring,
and the panel re-hides per the scene's chrome. (`engine.play`/`pause`/`_resume`,
`apply_scene`.)

### Compact HUD
The playback HUD (progress + scene title + caption + transport) is now a small
card **pinned lower-right** (was bottom-centre, full-width), panel-aware.
(`ui/story_mode.py`.)
