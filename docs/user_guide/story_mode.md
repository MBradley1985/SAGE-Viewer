# Story Mode

Story Mode turns ViSAGE into a presentation tool: a *story* is an ordered
list of scenes — each one a complete captured viewer state (snapshot, camera,
layer visibility, colouring) plus text/media overlays and an optional camera
motion — played back like slides over the live 3D render.

## Running a story

Open the **Story Mode** dropdown in the toolbar and pick a story. The playback
HUD gives Previous / Play / Pause / Next and a scene selector; **Exit Story
Mode** restores the state you were in before. **Capture thumbnails**
screenshots every scene for the scene-menu grid.

Stories are JSON files discovered from two places:

1. `sage_stories/` in the directory you launched `visage` from — your own
   stories live here.
2. The examples bundled with the package (`visage/examples/`).

A story in `sage_stories/` overrides a bundled one with the same title.
Malformed files are skipped silently, so if a story doesn't appear in the
menu, check the JSON parses. Edits to a story file are picked up by exiting
Story Mode and re-opening it — no restart needed.

## Starting from the template

The bundled **Presentation Template** story is a full talk skeleton — title
slide, section cards, a two-column layout over a time sweep, an equation
slide, image/video overlays, fly-through and rewind motion scenes, a
text-heavy summary and a clickable scene menu. To build your own talk:

```bash
cp <package>/visage/examples/presentation_template.json sage_stories/my_talk.json
```

then change the `title` and replace the placeholder text. The template is
model-agnostic (symbolic snapshots, no `requirements`), so it runs on whatever
output is loaded.

## Story file schema

```json
{
  "schema_version": 1,
  "title": "My Talk",
  "author": "Me",
  "description": "Shown as the subtitle in the story menu.",
  "theme": "dos_blue",
  "requirements": {},
  "autoplay": true,
  "scenes": [ ... ]
}
```

| Field | Meaning |
|---|---|
| `title` | Story name in the menu; also the identity used when a local story overrides a bundled one. |
| `theme` | UI theme applied for the whole story (scenes may override with their own `theme`). |
| `requirements` | Optional sandbox hints: `{"models": [...]}` names the model(s) the story was authored against; `{"snapshots": [..]}` or `{"snapshots": {"from": a, "to": b}}` lists snapshots to preload. Omit for a portable story. |
| `autoplay` | Start playback on entry, so a title scene's motion runs without pressing Play. |

## Scene schema

Every scene captures the *complete* state, so scenes can be reordered freely.

```json
{
  "id": "unique-slug",
  "title": "Shown in the HUD and scene menu",
  "caption": "Optional one-liner shown during playback",
  "snap_num": "last",
  "camera": "box",
  "state": { "halos_visible": true, "galaxies_visible": true },
  "focus": { "kind": "none" },
  "chrome": { "hide_panel": true },
  "overlays": [ ... ],
  "transition": { "duration_secs": 4.0, "easing": "smoothstep" },
  "dwell_secs": 6.0,
  "motion": { "kind": "still" },
  "hold": false
}
```

- **`snap_num`** — an absolute snapshot number, or a symbolic reference that
  is resolved against whatever model is loaded: `"first"`, `"last"`, a
  percentage (`"40%"`), or a redshift (`"z=1.5"`, resolved to the closest
  snapshot). Symbolic forms keep a story portable across boxes.
- **`camera`** — `"box"` / `"reset"` frames the whole box (box-size aware);
  `{"frame": "box", "zoom": 1.4}` frames the box then zooms; or an explicit
  `{"position": [...], "focal_point": [...], "up": [...]}` pose as written by
  the in-app capture.
- **`state`** — flat key/value map of layer toggles, filters and environment
  toggles (the same keys the navigation panel drives, e.g. `halos_visible`,
  `galaxies_visible`, `halo_opacity`, `halo_color_mode`, `halo_colormap`,
  `galaxy_color_mode`). Anything omitted keeps its current value, so set every
  key the scene depends on.
- **`focus`** — `{"kind": "none"}`, or a focus region:
  `{"kind": "sphere", "center": "box", "radius_frac": 0.45}` / `{"kind": "box", ...}`.
- **`chrome`** — `{"hide_panel": true}` hides the side panel for a clean
  full-frame slide.
- **`models`** — optional per-scene model layout,
  `{"primary": "<name>", "adjacent": ["<name>", ...]}`. Only use this if the
  story declares the models in `requirements`; omit it to stay on the loaded
  model.
- **`hold`** — `true` means playback never auto-advances off this scene; it
  waits for Next. Otherwise the scene advances after `dwell_secs`.

## Motion

`motion.kind` selects what the camera (or the clock) does while the scene is
on screen:

| Kind | Parameters | Behaviour |
|---|---|---|
| `still` | — | Nothing moves. |
| `orbit` | `dps` (degrees/sec), `degrees` | Orbit the focus/box centre. |
| `snapshot_sweep` | `from`, `to` (same forms as `snap_num`), `fps`, `loop`, `prerender` | Steps through snapshots — cosmic time-lapse. `prerender: true` renders the frames during story load so playback starts instantly. |
| `flythrough` | `targets` (`"halos"` default, or `"galaxies"`/`"ffb"`), `rewind_to`, `rewind_fps`, `style` | Tours the most massive structures, spinning around each. `rewind_to: "z=2"` plays a cached snapshot rewind back to that redshift on arrival at each target. `style: "normal"` is the calmer toolbar-style fly-through — good behind text slides. |

Playback display rate is capped at 30 fps; a higher `fps`/`rewind_fps` is
honoured as frame-skipping (e.g. 60 → 2× speed).

## Overlays

Overlays are positioned on a fixed virtual stage that scales uniformly to fit
the window, so a slide keeps its exact layout on any screen. Common fields:

- `anchor` — nine-grid position: `top-left`, `top`, `top-right`, `left`,
  `center`, `right`, `bottom-left`, `bottom`, `bottom-right`.
- `x`, `y` — offset from the anchor. Numbers are percentages of the stage;
  strings are CSS lengths (`"60px"` pins something at a fixed pixel offset).
- Text kinds also take `size` (rem), `color`, `weight`, `italic`, `align`,
  and `max_width` (% of stage, default 60 — controls line wrapping).

| Kind | Extra fields | Use |
|---|---|---|
| `title` | — | Big slide title (default 2.2 rem, extra bold). |
| `heading` | — | Section heading (default 1.6 rem, bold). |
| `text` | — | Body text; `\n` makes line breaks, blank lines separate bullets. |
| `citation` | — | Small italic grey credit line. |
| `equation` | `latex`, `inline` | KaTeX. Display style by default; `inline: true` for label-sized maths (e.g. an underlined column heading). |
| `image` | `src`, `width`, `opacity` | Logos, figures. |
| `video` | `src`, `width`, `opacity`, `loop`, `autoplay`, `muted`, `controls` | MP4/WebM. With `controls: true` the element is clickable (transport + fullscreen). |
| `audio` | `src`, `loop`, `autoplay`, `muted`, `volume` | Invisible; pauses/resumes with the show. Plays once by default. |
| `scene_menu` | `title`, `cols`, `max_width` | Clickable grid of every scene — put it on the last scene for question time. |

Media `src` paths are served from `/sage_static/`, which maps to the
package's `visage/static/` folder — drop your file in there and
reference it as `/sage_static/<file>`. (Media does **not** load from the data
Library.)

## Authoring workflow

Stories are authored by editing the JSON directly. The fast loop is: edit the
file, exit Story Mode in the app, re-open the story — changes load without a
restart. Keep `transition.duration_secs` at `0` while iterating so you can
step scenes quickly, then add transitions back for the real run.
