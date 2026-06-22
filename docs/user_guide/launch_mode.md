# Launch Mode (Wizard)

Launch Mode is a guided setup flow for configuring and running SAGE26, accessible without leaving the viewer.

## Entering Launch Mode

Run `sage-viewer` from your SAGE26 root directory so the wizard can find your `.par` files and executable automatically:

```bash
cd /path/to/SAGE26
sage-viewer
```

Then open the printed URL in your browser. The wizard launches directly.

You can also enter Launch Mode from inside Explore Mode via the hamburger menu → **Launch Mode**.

## Step indicator

A row of chips in the header tracks progress through the wizard:

| Chip colour | Meaning |
|---|---|
| Cyan / elevated | Current step |
| Green | Completed step |
| White / outlined | Pending step |

## Steps

### 1 — Scan environment

The wizard checks for a SAGE26 executable, locates any existing `.par` files under your SAGE root, and reports what it finds.

### 2 — Choose action

| Option | Description |
|---|---|
| **Use existing par file** | Select from the list of discovered `.par` files to edit and run |
| **Create new config file** | Generates a new `.par` from the built-in millennium.par template; you choose the filename before writing |

### 3 — Edit par file (when needed)

The par file editor opens side-by-side with the terminal output. Both panels are visible simultaneously — make your edits on the right while reading feedback on the left.

### 4 — Run SAGE26

The wizard creates the `OutputDir` declared in the `.par` file (if it doesn't exist), then launches SAGE26 and streams all output into the terminal.

**Back** at this step returns to the par-file selection step, not to the start of the wizard.

## Rescan

The **Rescan** button (top-right of the header) re-runs the environment scan from scratch at any point — useful if you've just compiled SAGE26 or moved files.

## Closing the wizard

The **×** button in the header closes the wizard and returns to Explore Mode. The wizard always resets cleanly when reopened.
