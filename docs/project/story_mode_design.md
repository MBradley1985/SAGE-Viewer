# Story Mode — Design Reference

!!! note "Status"
    Design spec for an unreleased feature. This is the reference for the
    implementation; update it if the schema changes during the build.

## Overview

**Story Mode** turns SAGE-Viewer into a guided, data-driven presentation tool.
A *story* is an ordered set of *scenes* — each a fully captured viewpoint
(camera + render state + narration) — that the viewer steps through with
Next / Previous, or plays back automatically. Stories live as JSON files in a
`sage_stories/` folder so users can author their own; the first shipped story
is the author's PhD Mid-Candidature Review (MCR).

Conceptually, Story Mode is a generalisation of the existing **fly-through**
(`toolbar.py`): the fly-through is a single hard-coded, non-interactive tour;
a story is data-driven, user-steppable, and pausable.

### Design pillars

- **Sandbox** — everything a story needs (model + all referenced snapshots) is
  preloaded before the story starts, using the existing snapshot preload cache.
- **Non-destructive overlay** — Story Mode never locks the UI. All normal
  panels and tools stay live; pausing hands full control back to the user.
- **Smooth & reversible** — transitions reuse the fly-through ease-in/out
  camera mover. Pausing then resuming flies smoothly back to the current scene.
- **Self-contained scenes** — each scene captures the *complete* state, so
  scenes are reorderable with no hidden inter-scene dependencies.
- **Theme-aware** — the active Vuetify theme is already reactive
  (`state.ui_theme`, bound at `app.py`); a story or scene can set it, and exit
  restores the user's prior theme. The DOS-blue palette is not wired in.

## Story file format

One JSON file per story in `sage_stories/` (discovered the same way the Library
tab scans `sage_library/` / `sage_outputs/`).

```jsonc
{
  "schema_version": 1,
  "title": "Mid-Candidature Review",
  "author": "M. Bradley",
  "description": "The SAGE26 galaxy formation story for my MCR.",
  "theme": "dos_blue",              // story-wide default theme
  "requirements": {
    "model": "miniMillennium",      // single-box for MVP
    "snapshots": [63, 50, 40, 32]   // explicit list OR {"from": 0, "to": 63}
  },
  "scenes": [ /* … scene objects … */ ]
}
```

The sandbox uses `requirements` to switch to the right model and warm the
snapshot cache (KDTrees included) before the first scene renders, surfacing the
existing "Loading snapshots… X/Y" chip. Any snapshot referenced by a scene —
including the full range of a `snapshot_sweep` motion — must appear here.

## Scene object

Every scene captures the **complete** state (full snapshot per scene, not a
delta from the previous one).

```jsonc
{
  // ── Identity / narration ────────────────────────────────────
  "id": "intro-box",
  "title": "The cosmic web at z=0",
  "caption": "...markdown narration shown in the HUD...",

  // ── Context (sandbox resolves these to loaded data) ─────────
  "snap_num": 63,
  "theme": "dos_blue",                  // optional; omit = inherit story theme

  // ── Camera (literal pose) ───────────────────────────────────
  "camera": { "position": [..], "focal_point": [..], "up": [0, 1, 0] },

  // ── Full captured state ─────────────────────────────────────
  "layers":  { /* all LAYER_KEYS + cbar keys */ },
  "filters": { /* all FILTER_KEYS */ },
  "environment": {
    "cluster": true, "field": false, "group": true,
    "isolated": false, "pairs": false
  },

  // ── Focus + target ─────────────────────────────────────────
  "focus":  { "kind": "sphere", "center": [..], "radius": 30.0 }, // none|sphere|box
  "target": {
    "position": [40.1, 22.3, 18.7],     // PRIMARY: resolved by nearest-position
    "radius": 30.0,
    "galaxy_index": 81234,              // HINT: used only if data matches
    "highlight_group": true
  },

  // ── Playback ────────────────────────────────────────────────
  "transition": { "duration_secs": 6.0, "easing": "smoothstep" }, // fly INTO scene
  "dwell_secs": 8.0,                     // auto-advance delay in Play
  "motion": { "kind": "still" }          // see Motion below
}
```

### Captured-state keys

Camera, focus, and target are **not** plain state keys — they are captured and
applied via the plotter camera and `scene.set_focus_*` / highlight controllers,
and live in their own scene sub-objects. Everything else is a flat state key,
captured/restored with the `box_profile` save/load pattern.

| Group | Keys |
|---|---|
| **Context** | `snap_num` (model + theme handled at story/scene level) |
| **Layers** (9) | `halos_visible`, `galaxies_visible`, `halo_opacity`, `galaxy_opacity`, `halo_color_mode`, `halo_colormap`, `galaxy_color_mode`, `galaxy_colormap`, `fof_links_on` |
| **Colourbars** (6) | `gal_cbar_min`, `gal_cbar_max`, `gal_cbar_style`, `halo_cbar_min`, `halo_cbar_max`, `halo_cbar_style` |
| **Filters** (43) | 7 × `filter_halo_*` + 36 × `filter_gal_*` — from the canonical list below |
| **Environment** (5) | `env_show_cluster`, `env_show_field`, `env_show_group`, `env_show_isolated`, `env_show_pairs` |

#### Canonical filter-key list

These are the filter keys actually bound in `navigation_panel.py`. The build
must define this list **once** as the single source of truth; the existing
`box_profile.FILTER_KEYS` has drifted (it lists `filter_gal_h2` /
`filter_gal_h1gas`, which are no longer bound) and should be re-pointed at the
canonical list rather than duplicated.

```
# Halo (7)
filter_halo_mvir  filter_halo_rvir  filter_halo_vvir  filter_halo_len
filter_halo_vmax  filter_halo_conc  filter_halo_spin

# Galaxy (36)
filter_gal_smass     filter_gal_sfr        filter_gal_ssfr      filter_gal_coldgas
filter_gal_bulge     filter_gal_bt         filter_gal_bhmass    filter_gal_ics
filter_gal_cgmgas    filter_gal_hotgas     filter_gal_ejected   filter_gal_outflow
filter_gal_massload  filter_gal_cooling    filter_gal_heating   filter_gal_diskrad
filter_gal_bulgerad  filter_gal_mb_mass    filter_gal_mb_rad    filter_gal_ib_mass
filter_gal_ib_rad    filter_gal_sfr_bulge  filter_gal_sfr_disk  filter_gal_sfr_blg_z
filter_gal_sfr_dsk_z filter_gal_met_cg     filter_gal_met_sm    filter_gal_met_bm
filter_gal_met_hg    filter_gal_met_em     filter_gal_met_ics   filter_gal_met_cgm
filter_gal_age       filter_gal_type       filter_gal_ffb       filter_gal_cgm
```

## Targeting resolution (position + index hint)

A scene's `target` is resolved at apply-time, in order:

1. If `galaxy_index` is present **and** a galaxy with that `GalaxyIndex` exists
   in the current `snap_num` data → use it (exact).
2. Otherwise → KDTree nearest-neighbour to `position` within `radius`
   (robust fallback).
3. Otherwise → render the `focus` sphere/box geometry only, no object highlight.

This makes scenes exact on the author's data while surviving data re-runs and
version bumps. Note: `GalaxyIndex` is unique *per snapshot* only — following the
*same* galaxy across snapshots needs merger-tree traversal, which the current
source does not implement (`merger_tree_reader.py` exists only under `build/`).
Cross-time object tracking is therefore out of scope for the MVP.

## Motion

`motion.kind` controls intra-scene animation. `still` is the default.

| kind | fields | behaviour |
|---|---|---|
| `still` | — | hold the captured pose for `dwell_secs` |
| `orbit` | `radius`, `dps`, `degrees`, `axis?` | spin around the `target` / `focus` centre — reuses the fly-through `_orbit_around` helper |
| `snapshot_sweep` | `from`, `to`, `fps?` | step `snap_num` across cosmic time while holding/orbiting the camera — reuses the preloaded cache |

`snapshot_sweep` is the headline capability for the MCR (e.g. "watch this halo
assemble from z = 6 to z = 0"). Every snapshot in `[from, to]` must be declared
in the story's `requirements.snapshots`.

## Playback semantics

- **Next / Previous** — `_smooth_move` the camera to the target scene's pose,
  apply its full state (filters/layers/env), reconstruct focus, set theme.
- **Play** — auto-advance: run each scene's `motion`, wait `dwell_secs`,
  transition to the next.
- **Pause** — stop auto-advance, hand full normal control to the user. The HUD
  remains; nothing is locked.
- **Resume (Play after Pause)** — smoothly fly back to the *current* scene's
  pose/state, then continue.
- **Exit** — restore the user's pre-story state profile and prior theme.

## Capture / restore mechanism

Reuses the `box_profile.py` pattern (a key whitelist plus `save_profile(state)`
/ `load_profile(state, profile)`):

- `STORY_SCENE_KEYS` = layer keys + cbar keys + canonical filter keys + env
  keys. Camera / focus / target are handled separately (they are
  scene/plotter objects, not flat state).
- **Capture scene** (authoring button) → reads `STORY_SCENE_KEYS` + the current
  camera pose + current focus geometry → appends a scene dict → writes JSON.
  This is how the MCR story is authored from inside the app.
- **Enter Story Mode** → `save_profile()` of the user's current state is
  stashed for restore on exit.
- **Apply scene** → `load_profile`-style write of `STORY_SCENE_KEYS`,
  `_smooth_move` the camera, reconstruct focus via `scene.set_focus_sphere` /
  `set_focus_box`, resolve + highlight target, set `ui_theme`.

## UI surface

- A **Story Mode** button next to the fly-through button (`app.py`), opening a
  `VMenu` dropdown of discovered stories (same pattern as the Launch Mode /
  Explore Mode menus).
- A **HUD overlay** while a story is active: Previous / Play / Pause / Next,
  scene title + markdown caption, and progress ("Scene 3 / 12").
- A **Capture scene** authoring affordance for building stories in-app.

## Build-time obligations

1. Define the canonical filter-key list once; re-point `box_profile.FILTER_KEYS`
   at it to end the drift.
2. Capture camera / focus / target outside the flat-state whitelist.
3. Generalise the theme CSS — `_THEME_CSS` / `sage_theme.css` is currently
   scoped almost entirely to `.v-theme--dos_blue`; a second theme needs its own
   block or de-scoping, and additional palettes registered in the Vuetify
   config. (Theme-switching infra itself is already reactive.)
