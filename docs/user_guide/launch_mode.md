# Launch Mode (Wizard)

Launch Mode is a guided setup flow for configuring and running SAGE26, accessible without leaving the viewer.

## Entering Launch Mode

```bash
cd /path/to/SAGE26
visage
```

Then open the printed URL in your browser. The wizard launches directly.

You can also enter Launch Mode from inside Explore Mode via the hamburger menu → **Launch Mode**.

## Where visage looks for things

The working directory you launch from is the anchor for the entire session:

| What | Where |
|---|---|
| SAGE26 executable & source | Searched in CWD, parent of CWD, then home folder |
| `.par` files | `<SAGE26>/input/` and `<CWD>/input/` |
| Existing models | `<SAGE26>/output/`, `<CWD>/output/`, `<CWD>/sage_outputs/` |
| Screenshots / recordings / exports | `<CWD>/sage_outputs/session_<timestamp>/` |

**First-time install (no SAGE26 yet):** run `visage` from the folder where you want SAGE26 to live, then use **Clone SAGE26** in the wizard. The wizard will ask which parent directory to clone into (defaulting to your home folder), and will use that cloned directory for the rest of the session.

**Existing SAGE26:** run from the SAGE26 root and the wizard finds everything automatically.

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
