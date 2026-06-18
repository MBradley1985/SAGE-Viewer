from __future__ import annotations

import asyncio
import os
import shutil
import sys
from pathlib import Path

_SAGE26_REPO = "https://github.com/MBradley1985/SAGE26.git"

_STEPS = [
    "Scan Environment",
    "Choose Action",
    "Setup SAGE26",
    "Configure Run",
    "Run SAGE26",
    "Launch Explore",
]

_KIND_COLORS = {
    "title": "#FFD700",
    "ok":    "#22c55e",
    "warn":  "#f59e0b",
    "err":   "#ef4444",
    "cmd":   "#06b6d4",
    "out":   "#9ca3af",
    "sep":   "#374151",
    "info":  "#e2e8f0",
}


class WizardController:
    def __init__(
        self,
        server,
        port: int,
        *,
        scene=None,
        on_model_loaded=None,
        auto_start: bool = True,
    ) -> None:
        self._sv             = server
        self._st             = server.state
        self._port           = port
        self._scene          = scene          # None in Launch Mode
        self._on_model_loaded = on_model_loaded  # called on completion in Explore Mode

        self._sage26_dir: Path | None = None
        self._par_path:   Path | None = None
        self._models:     list[dict]  = []

        self._st.wiz_step        = 0
        self._st.wiz_lines       = []
        self._st.wiz_choices     = []
        self._st.wiz_busy        = True
        self._st.wiz_par_show    = False
        self._st.wiz_par_text    = ""
        self._st.wiz_kind_colors = _KIND_COLORS

        server.controller.set("wiz_choose")(self._on_choice)
        server.controller.set("wiz_close")(self._on_close)

        if auto_start:
            asyncio.ensure_future(self._step_scan())

    def reset_and_start(self) -> None:
        """Clear terminal and restart the scan — used when re-opening wizard."""
        self._sage26_dir = None
        self._par_path   = None
        self._models     = []
        self._st.wiz_step     = 0
        self._st.wiz_lines    = []
        self._st.wiz_choices  = []
        self._st.wiz_busy     = True
        self._st.wiz_par_show = False
        self._st.wiz_par_text = ""
        self._st.flush()
        asyncio.ensure_future(self._step_scan())

    def _on_close(self, **_) -> None:
        self._st.wiz_active = False
        self._st.flush()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _emit(self, text: str, kind: str = "info") -> None:
        lines = list(self._st.wiz_lines)
        lines.append({"text": text, "kind": kind})
        self._st.wiz_lines = lines
        self._st.flush()

    def _set_choices(self, choices: list[dict]) -> None:
        self._st.wiz_choices = choices
        self._st.wiz_busy    = False
        self._st.flush()

    def _busy(self) -> None:
        self._st.wiz_choices = []
        self._st.wiz_busy    = True
        self._st.flush()

    async def _run_cmd(self, cmd: list[str], cwd: Path | None = None) -> int:
        self._emit("$ " + " ".join(str(c) for c in cmd), "cmd")
        self._st.flush()
        try:
            proc = await asyncio.create_subprocess_exec(
                *[str(c) for c in cmd],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(cwd) if cwd else None,
            )
            async for raw in proc.stdout:
                self._emit(raw.decode(errors="replace").rstrip(), "out")
                self._st.flush()
            await proc.wait()
            return proc.returncode
        except Exception as exc:
            self._emit(f"Error: {exc}", "err")
            return 1

    # ── discovery ────────────────────────────────────────────────────────────

    def _find_sage26(self) -> Path | None:
        search_roots = [Path.cwd().parent, Path.cwd(), Path.home()]
        names = ["SAGE26", "sage26", "sage-model", "SAGE", "sage"]
        for root in search_roots:
            for name in names:
                candidate = root / name
                if candidate.is_dir() and (candidate / "src").is_dir():
                    return candidate
        return None

    def _sage26_compiled(self, sage26: Path) -> tuple[bool, int]:
        o_files = list(sage26.glob("src/*.o"))
        binary  = sage26 / "bin" / "sage"
        return (len(o_files) > 0 or binary.is_file()), len(o_files)

    def _find_models(self) -> list[dict]:
        from sage_viewer.utils.discover import find_models
        results: list[dict] = []
        checked: set[Path]  = set()
        roots = [Path.cwd(), Path.cwd().parent]
        if self._sage26_dir:
            roots.append(self._sage26_dir.parent)
        for root in roots:
            for out_name in ("sage_outputs", "output", "outputs"):
                out_d = root / out_name
                if out_d in checked or not out_d.is_dir():
                    continue
                checked.add(out_d)
                par_dirs = [root / "input"]
                if self._sage26_dir:
                    par_dirs.append(self._sage26_dir / "input")
                for par_d in par_dirs:
                    if par_d.is_dir():
                        for m in find_models(out_d, par_dir=par_d):
                            if not any(r["par"] == m["par"] for r in results):
                                results.append(m)
        return results

    def _find_par_files(self) -> list[Path]:
        pars: list[Path] = []
        if self._sage26_dir:
            inp = self._sage26_dir / "input"
            if inp.is_dir():
                pars.extend(sorted(inp.glob("*.par")))
        inp_local = Path.cwd() / "input"
        if inp_local.is_dir():
            for p in sorted(inp_local.glob("*.par")):
                if p not in pars:
                    pars.append(p)
        return pars

    # ── state machine ────────────────────────────────────────────────────────

    async def _step_scan(self) -> None:
        self._st.wiz_step = 0
        self._emit("SAGE-Viewer  ::  Launch Mode", "title")
        self._emit("=" * 52, "sep")
        self._emit("Scanning environment...", "info")
        self._emit("", "info")

        self._sage26_dir = self._find_sage26()
        if self._sage26_dir:
            compiled, n_obj = self._sage26_compiled(self._sage26_dir)
            self._emit(f"  SAGE26 found : {self._sage26_dir}", "ok")
            if compiled:
                self._emit(f"  Compiled     : Yes  ({n_obj} object files)", "ok")
            else:
                self._emit("  Compiled     : No   (will compile when needed)", "warn")
        else:
            self._emit("  SAGE26       : Not found in common locations", "warn")

        self._models = self._find_models()
        if self._models:
            self._emit(f"  Models found : {len(self._models)}", "ok")
            for m in self._models:
                self._emit(f"    - {m['name']}   ({m['hdf5'].parent})", "out")
        else:
            self._emit("  Models       : None found", "info")

        self._emit("", "info")
        await self._step_main_choice()

    async def _step_main_choice(self) -> None:
        self._st.wiz_step = 1
        choices = []
        if self._models:
            choices.append({"label": "Load Existing Model", "value": "load",
                            "icon": "mdi-folder-open", "disabled": False})
        choices.append({"label": "Start Fresh", "value": "fresh",
                        "icon": "mdi-plus-circle-outline", "disabled": False})
        self._set_choices(choices)

    def _on_choice(self, value: str, **_) -> None:
        asyncio.ensure_future(self._handle_choice(value))

    async def _handle_choice(self, value: str) -> None:
        self._busy()

        if value == "load":
            await self._step_select_model()

        elif value == "fresh":
            await self._step_fresh_choice()

        elif value.startswith("model:"):
            name  = value[6:]
            model = next((m for m in self._models if m["name"] == name), None)
            if model:
                await self._launch_explore(model["par"])

        elif value == "new_model":
            await self._step_pick_par()

        elif value == "clone_sage26":
            await self._step_clone()

        elif value == "compile_sage26":
            await self._step_compile()

        elif value.startswith("par:"):
            self._par_path = Path(value[4:])
            await self._step_par_edit()

        elif value == "save_run_sage26":
            await self._step_run_sage26()

        elif value == "back_main":
            self._emit("", "info")
            await self._step_main_choice()

        elif value == "back_fresh":
            self._emit("", "info")
            await self._step_fresh_choice()

    async def _step_select_model(self) -> None:
        self._st.wiz_step = 1
        self._emit("Select a model to load:", "info")
        self._emit("", "info")
        choices = [
            {"label": m["name"], "value": f"model:{m['name']}",
             "icon": "mdi-database", "disabled": False}
            for m in self._models
        ]
        choices.append({"label": "Back", "value": "back_main",
                        "icon": "mdi-arrow-left", "disabled": False})
        self._set_choices(choices)

    async def _step_fresh_choice(self) -> None:
        self._st.wiz_step = 2
        choices: list[dict] = []

        if self._sage26_dir:
            compiled, _ = self._sage26_compiled(self._sage26_dir)
            if compiled:
                choices.append({"label": "Run New Model", "value": "new_model",
                                "icon": "mdi-play", "disabled": False})
            else:
                choices.append({"label": "Compile SAGE26", "value": "compile_sage26",
                                "icon": "mdi-cog", "disabled": False})
                choices.append({"label": "Run New Model (after compile)", "value": "new_model",
                                "icon": "mdi-play", "disabled": True})
        else:
            self._emit("SAGE26 not found. Clone it from GitHub to get started.", "info")
            choices.append({"label": "Clone SAGE26 from GitHub", "value": "clone_sage26",
                            "icon": "mdi-git", "disabled": False})

        if self._sage26_dir:
            self._emit("How would you like to proceed?", "info")

        choices.append({"label": "Back", "value": "back_main",
                        "icon": "mdi-arrow-left", "disabled": False})
        self._set_choices(choices)

    async def _step_clone(self) -> None:
        self._st.wiz_step = 2
        parent = Path.cwd().parent
        target = parent / "SAGE26"
        self._emit(f"Cloning SAGE26 into {target} ...", "info")
        rc = await self._run_cmd(
            ["git", "clone", _SAGE26_REPO, str(target)],
            cwd=parent,
        )
        if rc != 0:
            self._emit("Clone failed. Check internet connection and try again.", "err")
            self._set_choices([{"label": "Back", "value": "back_fresh",
                                "icon": "mdi-arrow-left", "disabled": False}])
            return
        self._sage26_dir = target
        await self._step_compile()

    async def _step_compile(self) -> None:
        self._st.wiz_step = 2
        if not self._sage26_dir:
            return
        first_run = self._sage26_dir / "first_run.sh"
        if first_run.is_file():
            self._emit("Running first_run.sh ...", "info")
            await self._run_cmd(["bash", "first_run.sh"], cwd=self._sage26_dir)
        self._emit("Compiling SAGE26 (may take a minute) ...", "info")
        rc = await self._run_cmd(["make"], cwd=self._sage26_dir)
        if rc != 0:
            self._emit("Compilation failed. See output above.", "err")
            self._set_choices([{"label": "Back", "value": "back_fresh",
                                "icon": "mdi-arrow-left", "disabled": False}])
            return
        self._emit("Compilation complete!", "ok")
        await self._step_pick_par()

    async def _step_pick_par(self) -> None:
        self._st.wiz_step = 3
        par_files = self._find_par_files()
        if not par_files:
            self._emit(
                "No .par files found in SAGE26/input/. "
                "Add a parameter file and try again.",
                "err",
            )
            self._set_choices([{"label": "Back", "value": "back_fresh",
                                "icon": "mdi-arrow-left", "disabled": False}])
            return
        if len(par_files) == 1:
            self._par_path = par_files[0]
            await self._step_par_edit()
        else:
            self._emit("Multiple parameter files found. Select one:", "info")
            self._emit("", "info")
            choices = [
                {"label": p.name, "value": f"par:{p}",
                 "icon": "mdi-file-cog", "disabled": False}
                for p in par_files
            ]
            choices.append({"label": "Back", "value": "back_fresh",
                            "icon": "mdi-arrow-left", "disabled": False})
            self._set_choices(choices)

    async def _step_par_edit(self) -> None:
        self._st.wiz_step = 3
        if not self._par_path:
            return
        self._emit(f"Parameter file : {self._par_path}", "info")
        self._emit("Edit the file below, then click Save & Run.", "info")
        self._emit("", "info")
        try:
            text = self._par_path.read_text()
        except Exception as exc:
            self._emit(f"Could not read par file: {exc}", "err")
            return
        self._st.wiz_par_text = text
        self._st.wiz_par_show = True
        self._st.flush()
        self._set_choices([
            {"label": "Save & Run SAGE26", "value": "save_run_sage26",
             "icon": "mdi-play", "disabled": False},
            {"label": "Back", "value": "back_fresh",
             "icon": "mdi-arrow-left", "disabled": False},
        ])

    async def _step_run_sage26(self) -> None:
        self._st.wiz_step = 4
        self._st.wiz_par_show = False
        self._st.flush()

        if self._par_path:
            try:
                self._par_path.write_text(self._st.wiz_par_text)
                self._emit(f"Saved {self._par_path.name}", "ok")
            except Exception as exc:
                self._emit(f"Could not save par file: {exc}", "err")
                return

        # Find binary
        sage_bin: Path | None = None
        if self._sage26_dir:
            for candidate in (
                self._sage26_dir / "bin" / "sage",
                self._sage26_dir / "sage",
            ):
                if candidate.is_file():
                    sage_bin = candidate
                    break
        if sage_bin is None:
            self._emit("SAGE26 binary not found (expected bin/sage).", "err")
            self._set_choices([{"label": "Back", "value": "back_fresh",
                                "icon": "mdi-arrow-left", "disabled": False}])
            return

        self._emit("", "info")
        self._emit("Running SAGE26 — output streams below.", "info")
        self._emit("This may take a while for large simulations.", "info")
        self._emit("", "info")
        rc = await self._run_cmd([str(sage_bin), str(self._par_path)],
                                 cwd=self._sage26_dir)
        if rc != 0:
            self._emit(f"SAGE26 exited with code {rc}. See output above.", "err")
            self._set_choices([{"label": "Back", "value": "back_fresh",
                                "icon": "mdi-arrow-left", "disabled": False}])
            return

        self._emit("", "info")
        self._emit("SAGE26 run complete!", "ok")
        self._models = self._find_models()
        if not self._models:
            self._emit("No models found after run. Check OutputDir in the par file.", "err")
            self._set_choices([{"label": "Back", "value": "back_fresh",
                                "icon": "mdi-arrow-left", "disabled": False}])
            return
        if len(self._models) == 1:
            await self._launch_explore(self._models[0]["par"])
        else:
            await self._step_select_model()

    async def _launch_explore(self, par_path: Path) -> None:
        self._st.wiz_step = 5
        self._emit("", "info")
        self._emit(f"Loading model: {par_path.parent.name}", "title")

        if self._on_model_loaded is not None:
            # Embedded in Explore Mode — load into the existing scene
            self._emit("Adding model to current session...", "info")
            self._st.flush()
            await asyncio.sleep(0.3)
            try:
                self._on_model_loaded(par_path)
                self._emit("Done! Closing wizard.", "ok")
                self._st.flush()
                await asyncio.sleep(0.8)
                self._st.wiz_active = False
                self._st.flush()
            except Exception as exc:
                self._emit(f"Error loading model: {exc}", "err")
        else:
            # Standalone Launch Mode — restart as Explore Mode via execv
            self._emit("Starting Explore Mode...", "info")
            self._emit("Your browser will reconnect in a few seconds.", "info")
            self._st.flush()
            await asyncio.sleep(1.5)
            sage_cmd = shutil.which("sage-viewer")
            if sage_cmd:
                os.execv(sage_cmd, [
                    sage_cmd, "--par", str(par_path), "--port", str(self._port),
                ])
            else:
                os.execv(sys.executable, [
                    sys.executable, "-m", "sage_viewer",
                    "--par", str(par_path), "--port", str(self._port),
                ])
