# Navigation

## Mouse and keyboard (render window)

PyVista's standard trackball controls apply inside the render window:

| Input | Action |
|---|---|
| Left drag | Rotate |
| Right drag / scroll | Zoom |
| Middle drag | Pan |
| `r` | Reset camera to full box |
| `f` | Focus on the picked point |
| Left click | Pick point → update info bar |

## Navigation panel controls

### Reset Camera

Returns to a full-box view centred on (box/2, box/2, box/2).

### Fly to Halo

Enter a **halo index** (0-based, within the current snapshot) and a **standoff distance** in Mpc/h. Press **Go** to move the camera there.

!!! tip
    Use the info bar (click a halo point) to find the index of a specific halo you've spotted visually.

### Fly to Galaxy

Enter a **galaxy index** (0-based, within the current snapshot). Press **Go**.

### Fly to Coordinates

Enter **X, Y, Z** in Mpc/h and a standoff distance. Press **Go** to point the camera at that location.

### Zoom to Sub-box

Enter an axis-aligned bounding box (Xmin, Xmax, Ymin, Ymax, Zmin, Zmax) in Mpc/h. Press **Zoom** to frame that region.

## Programmatic navigation (Python API)

```python
from sage_viewer.scene.camera import CameraController

# After scene is created:
scene.camera.go_to_coords(30.0, 30.0, 30.0, distance=10.0)
scene.camera.go_to_halo(42)
scene.camera.zoom_to_box(0, 30, 0, 30, 0, 30)
scene.camera.zoom_to_radius(center=(31.25, 31.25, 31.25), radius=10.0)
scene.camera.reset()
```
