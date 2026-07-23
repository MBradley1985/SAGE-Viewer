"""Single source of truth for the state keys a Story scene captures.

Reuses the layer and filter whitelists already defined in ``box_profile`` (they
match the render pipeline registered in ``navigation_panel.on_filter_change``),
and adds the environment toggles.  Colourbar keys are intentionally excluded —
they are *derived* display readouts recomputed when colormap / color-mode are
applied, not control inputs.
"""

from __future__ import annotations

from visage.scene.box_profile import FILTER_KEYS, LAYER_KEYS

# Environment classification toggles (separate from box_profile, which does not
# carry them).
ENV_KEYS: list[str] = [
    "env_show_cluster",
    "env_show_field",
    "env_show_group",
    "env_show_isolated",
    "env_show_pairs",
]

# Every flat reactive state key a scene captures and restores.  Camera, focus,
# target, snapshot, and theme are handled separately (they are not plain state
# or need bespoke application).
STORY_STATE_KEYS: list[str] = list(LAYER_KEYS) + list(FILTER_KEYS) + ENV_KEYS
