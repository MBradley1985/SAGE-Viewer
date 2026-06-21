# Interface

SAGE-Viewer's browser UI has three main regions and a number of overlays that appear when needed:

```
┌──────────────────────────────────────────────────────────────────┐
│ ☰  SAGE-Viewer  ◀◀ ▶ ⏸ ⏹ 🔁  ──slider──  Snap N│z│a   1×  Off ⤴  │
├──────────────────────────────────────────────────────────────┬───┤
│                                                              │ T │
│                                                              │ a │
│                  PyVista render window                       │ b │
│                                                              │ p │
│                  (overlays appear here:                      │ a │
│                   loading spinner,                           │ n │
│                   warning snackbar,                          │ e │
│                   Galaxy / Group Info card)                  │ l │
├──────────────────────────────────────────────────────────────┴───┤
│ Info bar: position + nearest halo / galaxy on double-click       │
└──────────────────────────────────────────────────────────────────┘
```

## Toolbar (top)

| Control | Action |
|---|---|
| ☰ (hamburger) | Open the dropdown: switch tabs, switch primary model, toggle overlay models |
| Reverse | Play backwards in time |
| Play / Pause / Stop | Snapshot transport. Stop returns to z = 0 |
| Loop | Continue playback past the endpoints |
| Snapshot slider | Jump directly to any snapshot |
| Snapshot chip | `Snap N  \|  z = X.XX  \|  a = X.XXXX` |
| Speed selector | 0.1× / 0.25× / 0.5× / 0.75× / 1× / 2× / 5× |
| Rotate selector | Off / CW / CCW × 15 / 30 / 60 ° s⁻¹ — continuous camera orbit |

## Right tabs panel

Nine tabs across a 3-column wrap layout:

| Tab | Purpose |
|---|---|
| Structure   | Layer visibility, opacity, colour-by mode, colormap (inline colorbar beneath each) |
| Filters     | Range sliders for halo (Mvir / Rvir / Vvir) and galaxy (stellar mass, sSFR, B/T, age, BH mass, ICS mass, type, FFB regime, CGM regime) |
| Record      | Screenshots (PNG / JPG / TIFF) and movies (GIF / MOV / PNG sequence) |
| Target      | Fly to halo / galaxy by index, focus-zoom presets, Galaxy Info, Highlight Galaxy |
| Environment | Halo selector, env-class checkboxes, Group Info, Highlight Members |
| Coords      | Fly to arbitrary (x, y, z); **Draw Sphere** for interactive focus region |
| Box         | Zoom to axis-aligned sub-box; **Draw Box** for interactive focus region |
| Console     | PTY-backed xterm.js terminal + Python REPL + SAGE command mode; multiple sessions; pop-out window |
| Library     | Browse screenshots and movies; double-click a row to open as a floating card over the viewport |

Above the tabs sit three row-spanning controls — **Reset Camera**, **Focus toggle**, and **Centre** — that work regardless of which tab is active.

## Multi-box strip

When two or more SAGE models are loaded side-by-side (via `+SBS` in the hamburger menu), a **box strip** appears at the bottom of the viewport. Each box is shown as a labelled chip:

- Click any chip to make that box **active** (label turns green)
- All right-panel tab controls then target the active box
- **CLR** in the strip resets that box to default settings without affecting others

The box strip is hidden in single-model mode.

## Render-window overlays

| Overlay | When |
|---|---|
| Loading spinner   | Dimmed cover while a new model loads from disk |
| Warning snackbar  | Top of the render view; appears when an overlay attempt is rejected (e.g. incompatible box size) |
| Galaxy Info card  | Top-right of the render view, semi-transparent; closed by × or by switching tabs |
| Group Info card   | Same top-right slot as Galaxy Info; mutually exclusive (opening one closes the other) |

## Info bar (bottom)

Double-click any point in the render window to select the nearest galaxy. The info bar then shows:

* The world-space (x, y, z) you clicked
* Nearest halo Mvir and index
* Nearest galaxy stellar mass / sSFR / central-or-satellite / index

The galaxy index field in the Target and Environment tabs updates automatically so you can immediately follow up with **Galaxy Info**, **Highlight Galaxy**, or **Group Info** without typing.

Single clicks (no double) are treated as pure camera interactions — they don't move selection and don't trigger any overlays.
