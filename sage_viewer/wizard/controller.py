from __future__ import annotations

import asyncio
import base64 as _b64
import os
import shutil
import sys
from pathlib import Path

_SAGE26_REPO = "https://github.com/MBradley1985/SAGE26.git"

import html as _html_mod
import re as _re

# ANSI SGR codes for each wizard message kind — used when writing directly to
# the xterm.js terminal instead of the old HTML line list.
_KIND_ANSI: dict[str, str] = {
    "title": "\x1b[1;36m",  # bold cyan
    "ok": "\x1b[32m",  # green
    "warn": "\x1b[33m",  # yellow
    "err": "\x1b[1;31m",  # bold red
    "cmd": "\x1b[36m",  # cyan
    "out": "",  # white (default)
    "sep": "",  # white (default)
    "info": "",  # default
}

# ── legacy ANSI → HTML converter (kept for reference, no longer used) ─────────
_ANSI_CSI = _re.compile(r"\x1b\[([0-9;]*)([A-Za-z])")  # all CSI sequences
_ANSI_OTHER = _re.compile(r"\x1b[^[]")  # ESC + non-[

_ANSI_FG = {
    "30": "#4a4a4a",
    "31": "#ef4444",
    "32": "#22c55e",
    "33": "#f59e0b",
    "34": "#60a5fa",
    "35": "#a855f7",
    "36": "#06b6d4",
    "37": "#e2e8f0",
    "90": "#6b7280",
    "91": "#f87171",
    "92": "#4ade80",
    "93": "#fbbf24",
    "94": "#93c5fd",
    "95": "#c084fc",
    "96": "#67e8f9",
    "97": "#f9fafb",
}


def _ansi_to_html(text: str) -> str:
    """Convert ANSI SGR codes to HTML spans; escape all other HTML."""
    # Strip non-SGR control sequences (cursor movement, clear, etc.)
    text = _ANSI_OTHER.sub("", text)

    out: list[str] = []
    in_span = False
    pos = 0

    for m in _ANSI_CSI.finditer(text):
        # Emit plain text before this escape sequence (HTML-escaped)
        out.append(_html_mod.escape(text[pos : m.start()]))
        pos = m.end()

        cmd = m.group(2)
        if cmd != "m":
            continue  # not a colour code — skip

        codes = m.group(1).split(";") if m.group(1) else ["0"]
        if in_span:
            out.append("</span>")
            in_span = False

        bold = "1" in codes
        color = next((c for c in codes if c in _ANSI_FG), None)
        reset = "0" in codes or "" in codes

        if not reset and color:
            style = f"color:{_ANSI_FG[color]}"
            if bold:
                style += ";font-weight:700"
            out.append(f'<span style="{style}">')
            in_span = True

    out.append(_html_mod.escape(text[pos:]))
    if in_span:
        out.append("</span>")
    return "".join(out)


_STEPS = [
    "Scan Environment",
    "Choose Action",
    "Setup SAGE26",
    "Configure Run",
    "Run SAGE26",
    "Launch Explore",
]

_MILLENNIUM_PAR_TEMPLATE = """\
%------------------------------------------
%----- SAGE output file information -------
%------------------------------------------

FileNameGalaxies   model
%OutputDir         /<absolute>/<path>/SAGE26/output/millennium/
OutputDir   {output_dir}

FirstFile         0
LastFile          7

%------------------------------------------
%----- Snapshot output list ---------------
%------------------------------------------

NumOutputs        -1  % sets the desired number of galaxy outputs; use -1 for all outputs

% List your output snapshots after the arrow, highest to lowest (ignored when NumOutputs=-1).
-> 63 37 32 27 23 20 18 16

OutputFormat      sage_hdf5 % sets the desired output format. Either 'sage_binary' or 'sage_hdf5'.

%------------------------------------------
%----- Simulation information  ------------
%------------------------------------------

TreeName              trees_063   % assumes the trees are named TreeName.n where n is the file number
TreeType              lhalo_binary % 'genesis_lhalo_hdf5', 'lhalo_binary', 'consistentrees_ascii', 'consistentrees_hdf5', 'lhalo_ascii', 'lhalo_hdf5'
NumSimulationTreeFiles 8 % Number of files the trees are split over. This can be different to `FirstFile` -> `LastFile` range.

%SimulationDir      /<absolute>/<path>/SAGE26/input/millennium/trees/
SimulationDir   {sim_dir}
%FileWithSnapList   /<absolute>/<path>/SAGE26/input/millennium/trees/millennium.a_list
FileWithSnapList {snaplist}
LastSnapShotNr        63

Omega           0.25
OmegaLambda     0.75
BaryonFrac      0.17
Hubble_h        0.73
PartMass        0.086
BoxSize         62.5 % Size of the simulation box in Mpc/h.

%------------------------------------------
%----- SAGE recipe options ----------------
%------------------------------------------

SFprescription              1   %0: original Croton et al. 2006; 1: BR06 H2 Stars; 2: Somerville et al. 2025 SFR; 3: Somerville et al. 2025 SFR + H2; 4: KD12 H2 Stars; 5: KMT09; 6: K13; 7: GD14
AGNrecipeOn                 2   %0: switch off; 1: empirical model; 2: Bondi-Hoyle model; 3: cold cloud accretion model
SupernovaRecipeOn           1   %0: switch off; 1: original Croton et al. 2016
ReionizationOn              1   %0: switch off
DiskInstabilityOn           1   %0: switch off; 1: bulge and BH growth through instabilities w. instability starbursts

CGMrecipeOn                 1   %0: switch off
FIREmodeOn                  1   %0: switch off

ConcentrationOn             3   %0: off; 1: Ishiyama+21 lookup table; 2: Vmax/Vvir from simulation; 3: Vmax/Vvir + infall freeze for satellites
FeedbackFreeModeOn          1   %0: off; 1: Li+24 sigmoid; 2: BK25 (Ishiyama+21 conc); 3: BK25 (ConcentrationOn method); 4: BK25 + log-normal c scatter; 5: Li+24 sharp; 6: Li+24 sigmoid + H2 SF; 7: BK25 log-normal c scatter + H2 SF

SaveFullSFH                 1   %0: switch off
TrackICSAssembly            1   %0: switch off; 1: track ICS_disrupt and ICS_accrete

%------------------------------------------
%----- SAGE model parameters --------------
%------------------------------------------

SfrEfficiency               0.05    %efficiency of SF; unused for SFprescription=3,6
FFBMaxEfficiency            0.2     %0.2 fits observations best, 1.0 is theoretical maximum

FeedbackReheatingEpsilon    2.9     %mass of cold gas reheated due to SF (see Martin 1999) (SupernovaRecipeOn=1)
FeedbackEjectionEfficiency  0.3     %mixing efficiency of SN energy with hot gas to unbind and eject some (SupernovaRecipeOn=1)

ReIncorporationFactor       0.15    %fraction of ejected mass reincorporated per dynamical time to hot

RadioModeEfficiency         0.08    %AGN radio mode efficiency (AGNrecipeOn=2)
QuasarModeEfficiency        0.005   %AGN quasar mode wind heating efficiency (AGNrecipeOn>0)
BlackHoleGrowthRate         0.015   %fraction of cold gas added to the BH during mergers (AGNrecipeOn>0)

ThreshMajorMerger           0.3     %major merger when mass ratio greater than this
ThresholdSatDisruption      1.0     %Mvir-to-baryonic mass ratio threshold for satellite merger or disruption

Yield                       0.025   %fraction of SF mass produced as metals
RecycleFraction             0.43    %fraction of SF mass instantaneously recycled back to cold
FracZleaveDisk              0.0     %fraction of metals produced directly to hot component

Reionization_z0             8.0     %these parameter choices give the best fit to Genedin (2000)...
Reionization_zr             7.0     %using the analytic fit of Kravtsov et al. 2004 (ReionizationOn=1)

EnergySN                    1.0e51  %energy per supernova
EtaSN                       5.0e-3  %supernova efficiency

%------------------------------------------
%----- Other code-related information -----
%------------------------------------------

%% The following two parameters determine how forests are distributed over MPI tasks
%% The scheme determines the computing cost for processing each forest
%% uniform_in_forests -> every forest has the same cost, regardless of the size of the forest
%% linear_in_nhalos -> the cost scales linearly with the forest size
%% quadratic_in_nhalos -> the cost scales quadratically with forest size
%% exponent_in_nhalos -> the cost scales to some (integer) power of forest size, the exponent is given by the (integral) value of 'ExponentForestDistributionScheme'
%% generic_power_in_nhalos -> the cost is directly scaled by  pow(forest size, 'ExponentForestDistributionScheme')
ForestDistributionScheme                    generic_power_in_nhalos  % options are 'uniform_in_forests', 'linear_in_nhalos',
ExponentForestDistributionScheme            0.7 % only relevant for the last two schemes


UnitLength_in_cm          3.08568e+24 %WATCH OUT: Mpc/h
UnitMass_in_g             1.989e+43   %WATCH OUT: 10^10Msun
UnitVelocity_in_cm_per_s  100000      %WATCH OUT: km/s
"""

_KIND_COLORS = {
    "title": "#06b6d4",
    "ok": "#22c55e",
    "warn": "#f59e0b",
    "err": "#ef4444",
    "cmd": "#06b6d4",
    "out": "#9ca3af",
    "sep": "#374151",
    "info": "#e2e8f0",
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
        standalone: bool = False,
    ) -> None:
        self._sv = server
        self._st = server.state
        self._port = port
        self._standalone = standalone
        self._scene = scene  # None in Launch Mode
        self._on_model_loaded = (
            on_model_loaded  # called on completion in Explore Mode
        )

        self._sage26_dir: Path | None = None
        self._par_path: Path | None = None
        self._models: list[dict] = []
        self._wiz_seq: int = 0
        self._wiz_buf: bytearray = (
            bytearray()
        )  # replay buffer for late-mounting xterm
        self._back: str = "back_fresh"  # Back target for par/compile steps

        self._st.wiz_step = 0
        self._st.wiz_lines = []  # kept for compat; no longer populated
        self._st.wiz_choices = []
        self._st.wiz_busy = True
        self._st.wiz_par_show = False
        self._st.wiz_par_text = ""
        self._st.wiz_filename_show = False
        self._st.wiz_filename = "millennium"
        self._st.wiz_kind_colors = _KIND_COLORS
        self._st.wiz_pty_data = ""  # base64 PTY chunk → xterm.js
        self._st.wiz_pty_seq = 0  # monotonically increasing
        self._st.wiz_pty_buf = ""  # base64 full replay buffer
        self._st.wiz_clone_dir_show = False
        self._st.wiz_clone_dir = str(Path.home())

        server.controller.set("wiz_choose")(self._on_choice)
        server.controller.set("wiz_close")(self._on_close)
        server.controller.set("wiz_rescan")(self._on_rescan)

        if auto_start:
            asyncio.ensure_future(self._step_scan())

    def reset_and_start(self) -> None:
        """Clear terminal and restart the scan — used when re-opening wizard."""
        self._sage26_dir = None
        self._par_path = None
        self._models = []
        self._wiz_buf = bytearray()
        self._back = "back_fresh"
        self._st.wiz_step = 0
        self._st.wiz_lines = []
        self._st.wiz_choices = []
        self._st.wiz_busy = True
        self._st.wiz_par_show = False
        self._st.wiz_par_text = ""
        self._st.wiz_filename_show = False
        self._st.wiz_filename = "millennium"
        self._st.wiz_pty_buf = ""
        self._st.wiz_clone_dir_show = False
        self._st.wiz_clone_dir = str(Path.home())
        # Push a clear sequence as the first "chunk" so a late-mounting xterm
        # clears itself before replaying buffered output.
        self._push_bytes(b"\x1b[2J\x1b[H")
        self._st.flush()
        asyncio.ensure_future(self._step_scan())

    def _on_close(self, **_) -> None:
        if self._standalone:
            asyncio.ensure_future(self._sv.stop())
        else:
            self._st.wiz_active = False
            self._st.flush()

    def _on_rescan(self, **_) -> None:
        self.reset_and_start()

    # ── helpers ──────────────────────────────────────────────────────────────

    _WIZ_BUF_CAP = 512 * 1024  # 512 KB replay buffer cap

    def _push_bytes(self, data: bytes) -> None:
        """Push raw bytes to the wizard xterm.js terminal.

        Maintains a rolling replay buffer (wiz_pty_buf) so a late-mounting
        xterm can reconstruct the full session history on first paint.
        """
        self._wiz_buf.extend(data)
        if len(self._wiz_buf) > self._WIZ_BUF_CAP:
            # Keep the most recent half so the display stays coherent.
            self._wiz_buf = self._wiz_buf[len(self._wiz_buf) // 2 :]
        self._wiz_seq = (self._wiz_seq + 1) % 10**9
        self._st.wiz_pty_data = _b64.b64encode(data).decode()
        self._st.wiz_pty_seq = self._wiz_seq
        self._st.wiz_pty_buf = _b64.b64encode(bytes(self._wiz_buf)).decode()
        self._st.flush()

    def _emit(self, text: str, kind: str = "info") -> None:
        code = _KIND_ANSI.get(kind, "")
        line = (code + text + ("\x1b[0m" if code else "") + "\r\n").encode()
        self._push_bytes(line)

    def _set_choices(self, choices: list[dict]) -> None:
        self._st.wiz_choices = choices
        self._st.wiz_busy = False
        self._st.flush()

    def _busy(self) -> None:
        self._st.wiz_choices = []
        self._st.wiz_busy = True
        self._st.wiz_par_show = False
        self._st.wiz_filename_show = False
        self._st.wiz_clone_dir_show = False
        self._st.flush()

    async def _run_cmd(self, cmd: list[str], cwd: Path | None = None) -> int:
        """Run a command in a PTY so ANSI colors and \\r progress bars work."""
        import pty as _pty, select as _select, subprocess as _subprocess
        import fcntl as _fcntl, struct as _struct, termios as _termios

        self._push_bytes(
            (
                "\x1b[36m$ " + " ".join(str(c) for c in cmd) + "\x1b[0m\r\n"
            ).encode()
        )

        master_fd = slave_fd = -1
        try:
            master_fd, slave_fd = _pty.openpty()
            try:
                _fcntl.ioctl(
                    slave_fd,
                    _termios.TIOCSWINSZ,
                    _struct.pack("HHHH", 24, 220, 0, 0),
                )
            except Exception:
                pass

            proc = _subprocess.Popen(
                [str(c) for c in cmd],
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                cwd=str(cwd) if cwd else None,
                preexec_fn=os.setsid,
            )
            os.close(slave_fd)
            slave_fd = -1

            loop = asyncio.get_running_loop()

            def _read_chunk() -> bytes | None:
                try:
                    r, _, _ = _select.select([master_fd], [], [], 1.0)
                except (OSError, ValueError):
                    return b""
                if not r:
                    return None  # timeout
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError:
                    return b""
                if not chunk:
                    return b""
                buf = bytearray(chunk)
                while True:
                    try:
                        r2, _, _ = _select.select([master_fd], [], [], 0)
                        if not r2:
                            break
                        more = os.read(master_fd, 4096)
                        if not more:
                            break
                        buf.extend(more)
                    except OSError:
                        break
                return bytes(buf)

            while True:
                data = await loop.run_in_executor(None, _read_chunk)
                if data is None:
                    if proc.poll() is not None:
                        break
                    continue
                if not data:
                    break
                self._push_bytes(data)

            proc.wait()
            return proc.returncode or 0
        except Exception as exc:
            self._push_bytes(f"\x1b[1;31mError: {exc}\x1b[0m\r\n".encode())
            return 1
        finally:
            for fd in (master_fd, slave_fd):
                if fd >= 0:
                    try:
                        os.close(fd)
                    except OSError:
                        pass

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
        binary = sage26 / "bin" / "sage"
        return (len(o_files) > 0 or binary.is_file()), len(o_files)

    def _find_models(self, verbose: bool = False) -> list[dict]:
        from sage_viewer.utils.discover import find_models

        results: list[dict] = []
        checked: set[Path] = set()

        # Candidate (output_dir, par_dir) pairs to scan
        pairs: list[tuple[Path, Path]] = []

        # If SAGE26 is known, its output/ + input/ is the primary pair
        if self._sage26_dir:
            sage_out = self._sage26_dir / "output"
            sage_par = self._sage26_dir / "input"
            if sage_out.is_dir():
                pairs.append((sage_out, sage_par))

        # Also scan common names relative to cwd and parent
        roots = [Path.cwd(), Path.cwd().parent]
        if self._sage26_dir:
            roots.append(self._sage26_dir.parent)
        for root in roots:
            for out_name in ("sage_outputs", "output", "outputs"):
                out_d = root / out_name
                if out_d in checked or not out_d.is_dir():
                    continue
                checked.add(out_d)
                for par_name in ("input", "input/millennium", "."):
                    par_d = root / par_name
                    if par_d.is_dir():
                        pairs.append((out_d, par_d))

        for out_d, par_d in pairs:
            if verbose:
                self._emit(f"  scanning {out_d}", "out")
                self._emit(f"  par dir  {par_d}", "out")
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
                self._emit(
                    f"  Compiled     : Yes  ({n_obj} object files)", "ok"
                )
            else:
                self._emit(
                    "  Compiled     : No   (will compile when needed)", "warn"
                )
        else:
            self._emit(
                "  SAGE26       : Not found in common locations", "warn"
            )

        self._emit("  Scanning for models...", "info")
        self._models = self._find_models(verbose=True)
        if self._models:
            self._emit(f"  Models found : {len(self._models)}", "ok")
            for m in self._models:
                self._emit(f"    - {m['name']}   ({m['hdf5'].parent})", "out")
        else:
            self._emit("  Models       : None found", "warn")

        self._emit("", "info")
        await self._step_main_choice()

    async def _step_main_choice(self) -> None:
        self._st.wiz_step = 1
        choices = []
        if self._models:
            choices.append(
                {
                    "label": "Load Existing Model",
                    "value": "load",
                    "icon": "mdi-folder-open",
                    "disabled": False,
                }
            )
        if self._sage26_dir:
            choices.append(
                {
                    "label": "Run SAGE26",
                    "value": "run_sage26",
                    "icon": "mdi-play-circle-outline",
                    "disabled": False,
                }
            )
        choices.append(
            {
                "label": "Start Fresh",
                "value": "fresh",
                "icon": "mdi-git",
                "disabled": False,
            }
        )
        self._set_choices(choices)

    def _on_choice(self, value: str, **_) -> None:
        asyncio.ensure_future(self._handle_choice(value))

    async def _handle_choice(self, value: str) -> None:
        self._busy()

        if value == "load":
            await self._step_select_model()

        elif value == "run_sage26":
            await self._step_run_sage26_existing()

        elif value == "fresh":
            await self._step_fresh_choice()

        elif value.startswith("model:"):
            name = value[6:]
            model = next((m for m in self._models if m["name"] == name), None)
            if model:
                await self._launch_explore(model["par"], model_name=name)

        elif value == "new_model":
            await self._step_pick_par()

        elif value == "clone_sage26":
            await self._step_clone()

        elif value == "confirm_clone":
            await self._do_clone()

        elif value == "compile_sage26":
            await self._step_compile()

        elif value == "create_par":
            await self._step_create_par()

        elif value == "do_create_par":
            await self._do_create_par()

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

    async def _step_run_sage26_existing(self) -> None:
        """Run SAGE26 with the existing local installation — no clone step."""
        self._back = "back_main"
        self._st.wiz_step = 2
        if not self._sage26_dir:
            self._emit("SAGE26 not found locally.", "err")
            self._emit(
                "Use 'Start Fresh' to clone it from GitHub first.", "info"
            )
            self._set_choices(
                [
                    {
                        "label": "Back",
                        "value": "back_main",
                        "icon": "mdi-arrow-left",
                        "disabled": False,
                    }
                ]
            )
            return

        compiled, n_obj = self._sage26_compiled(self._sage26_dir)
        if compiled:
            self._emit(
                f"SAGE26 found at {self._sage26_dir}  ({n_obj} object files)",
                "ok",
            )
            self._emit("Select a parameter file to run:", "info")
            self._emit("", "info")
            await self._step_pick_par()
        else:
            self._emit(f"SAGE26 found at {self._sage26_dir}", "ok")
            self._emit(
                "Not yet compiled — compile it first, then select a par file.",
                "warn",
            )
            self._set_choices(
                [
                    {
                        "label": "Compile SAGE26",
                        "value": "compile_sage26",
                        "icon": "mdi-cog-outline",
                        "disabled": False,
                    },
                    {
                        "label": "Back",
                        "value": "back_main",
                        "icon": "mdi-arrow-left",
                        "disabled": False,
                    },
                ]
            )

    async def _step_select_model(self) -> None:
        self._st.wiz_step = 1
        self._emit("Select a model to load:", "info")
        self._emit("", "info")
        choices = [
            {
                "label": m["name"],
                "value": f"model:{m['name']}",
                "icon": "mdi-database",
                "disabled": False,
            }
            for m in self._models
        ]
        choices.append(
            {
                "label": "Back",
                "value": "back_main",
                "icon": "mdi-arrow-left",
                "disabled": False,
            }
        )
        self._set_choices(choices)

    async def _step_fresh_choice(self) -> None:
        self._back = "back_fresh"
        self._st.wiz_step = 2
        choices: list[dict] = []

        # Clone is always the first option — full fresh start from GitHub
        choices.append(
            {
                "label": "Clone SAGE26",
                "value": "clone_sage26",
                "icon": "mdi-git",
                "disabled": False,
            }
        )

        if self._sage26_dir:
            compiled, _ = self._sage26_compiled(self._sage26_dir)
            if compiled:
                choices.append(
                    {
                        "label": "Run New Model",
                        "value": "new_model",
                        "icon": "mdi-play",
                        "disabled": False,
                    }
                )
            else:
                choices.append(
                    {
                        "label": "Compile SAGE26",
                        "value": "compile_sage26",
                        "icon": "mdi-cog",
                        "disabled": False,
                    }
                )
                choices.append(
                    {
                        "label": "Run New Model (after compile)",
                        "value": "new_model",
                        "icon": "mdi-play",
                        "disabled": True,
                    }
                )
        else:
            self._emit("SAGE26 not found locally — clone it first.", "info")

        choices.append(
            {
                "label": "Back",
                "value": "back_main",
                "icon": "mdi-arrow-left",
                "disabled": False,
            }
        )
        self._set_choices(choices)

    async def _step_clone(self) -> None:
        self._st.wiz_step = 2
        self._emit("Choose where to clone SAGE26:", "info")
        self._emit("  A 'SAGE26' folder will be created inside the chosen directory.", "info")
        self._emit("", "info")
        self._st.wiz_clone_dir = str(Path.home())
        self._st.wiz_clone_dir_show = True
        self._st.flush()
        self._set_choices(
            [
                {
                    "label": "Clone Here",
                    "value": "confirm_clone",
                    "icon": "mdi-git",
                    "disabled": False,
                },
                {
                    "label": "Back",
                    "value": self._back,
                    "icon": "mdi-arrow-left",
                    "disabled": False,
                },
            ]
        )

    async def _do_clone(self) -> None:
        self._st.wiz_step = 2
        raw_dir = str(self._st.wiz_clone_dir or "").strip() or str(Path.home())
        parent = Path(raw_dir).expanduser().resolve()
        if not parent.is_dir():
            self._emit(f"Directory not found: {parent}", "err")
            self._emit("Please enter a valid directory path.", "info")
            self._st.wiz_clone_dir_show = True
            self._st.flush()
            self._set_choices(
                [
                    {
                        "label": "Clone Here",
                        "value": "confirm_clone",
                        "icon": "mdi-git",
                        "disabled": False,
                    },
                    {
                        "label": "Back",
                        "value": self._back,
                        "icon": "mdi-arrow-left",
                        "disabled": False,
                    },
                ]
            )
            return
        target = parent / "SAGE26"
        self._emit(f"Cloning SAGE26 into {target} ...", "info")
        rc = await self._run_cmd(
            ["git", "clone", _SAGE26_REPO, str(target)],
            cwd=parent,
        )
        if rc != 0:
            self._emit(
                "Clone failed. Check internet connection and try again.", "err"
            )
            self._set_choices(
                [
                    {
                        "label": "Back",
                        "value": self._back,
                        "icon": "mdi-arrow-left",
                        "disabled": False,
                    }
                ]
            )
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
            self._set_choices(
                [
                    {
                        "label": "Back",
                        "value": self._back,
                        "icon": "mdi-arrow-left",
                        "disabled": False,
                    }
                ]
            )
            return
        self._emit("Compilation complete!", "ok")
        await self._step_pick_par()

    async def _step_pick_par(self) -> None:
        self._st.wiz_step = 3
        par_files = self._find_par_files()
        _create_choice = {
            "label": "Create config file",
            "value": "create_par",
            "icon": "mdi-file-plus-outline",
            "disabled": False,
        }
        if not par_files:
            self._emit("No .par files found.", "warn")
            self._emit(
                "Use 'Create config file' below, or add a .par file "
                "to SAGE26/input/ and rescan.",
                "info",
            )
            self._emit("", "info")
            self._set_choices(
                [
                    _create_choice,
                    {
                        "label": "Back",
                        "value": self._back,
                        "icon": "mdi-arrow-left",
                        "disabled": False,
                    },
                ]
            )
            return
        if len(par_files) == 1:
            self._par_path = par_files[0]
            await self._step_par_edit()
        else:
            self._emit("Multiple parameter files found. Select one:", "info")
            self._emit("", "info")
            choices = [
                {
                    "label": p.name,
                    "value": f"par:{p}",
                    "icon": "mdi-file-cog",
                    "disabled": False,
                }
                for p in par_files
            ]
            choices.append(_create_choice)
            choices.append(
                {
                    "label": "Back",
                    "value": self._back,
                    "icon": "mdi-arrow-left",
                    "disabled": False,
                }
            )
            self._set_choices(choices)

    async def _step_create_par(self) -> None:
        """Show filename input then wait for the user to confirm."""
        self._st.wiz_step = 3
        self._emit("Enter a name for the new config file:", "info")
        self._st.wiz_filename_show = True
        self._st.wiz_filename = "millennium"
        self._st.flush()
        self._set_choices(
            [
                {
                    "label": "Create",
                    "value": "do_create_par",
                    "icon": "mdi-check",
                    "disabled": False,
                },
                {
                    "label": "Back",
                    "value": self._back,
                    "icon": "mdi-arrow-left",
                    "disabled": False,
                },
            ]
        )

    async def _do_create_par(self) -> None:
        """Create the par file using the user-supplied filename."""
        raw = (
            str(self._st.wiz_filename or "millennium").strip() or "millennium"
        )
        name = raw if raw.endswith(".par") else raw + ".par"
        self._st.wiz_filename_show = False
        self._st.flush()
        if self._sage26_dir:
            inp_dir = self._sage26_dir / "input"
        else:
            inp_dir = Path.cwd() / "input"
        inp_dir.mkdir(parents=True, exist_ok=True)
        dest = inp_dir / name
        self._emit(f"Creating config file: {dest}", "info")
        sage26 = self._sage26_dir or Path.cwd()
        content = _MILLENNIUM_PAR_TEMPLATE.format(
            output_dir=sage26 / "output" / "millennium" / "",
            sim_dir=sage26 / "input" / "millennium" / "trees" / "",
            snaplist=sage26 / "input" / "millennium" / "trees" / "millennium.a_list",
        )
        dest.write_text(content)
        self._par_path = dest
        self._emit(
            "Template written. Edit the paths to the right, then Save & Run.",
            "ok",
        )
        self._emit("", "info")
        await self._step_par_edit()

    async def _step_par_edit(self) -> None:
        self._st.wiz_step = 3
        if not self._par_path:
            return
        self._emit(f"Parameter file : {self._par_path}", "info")
        self._emit(
            "Edit the file to the right, then click Save & Run.", "info"
        )
        self._emit("", "info")
        try:
            text = self._par_path.read_text()
        except Exception as exc:
            self._emit(f"Could not read par file: {exc}", "err")
            return
        self._st.wiz_par_text = text
        self._st.wiz_par_show = True
        self._st.flush()
        self._set_choices(
            [
                {
                    "label": "Save & Run SAGE26",
                    "value": "save_run_sage26",
                    "icon": "mdi-play",
                    "disabled": False,
                },
                {
                    "label": "Back",
                    "value": self._back,
                    "icon": "mdi-arrow-left",
                    "disabled": False,
                },
            ]
        )

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

            # Create OutputDir before SAGE26 runs — it won't create it itself.
            try:
                from sage_viewer.io.par_reader import parse_par

                cfg = parse_par(self._par_path)
                cfg.output_dir.mkdir(parents=True, exist_ok=True)
                self._emit(f"Output dir ready: {cfg.output_dir}", "ok")
            except Exception as exc:
                self._emit(
                    f"Warning: could not create OutputDir — {exc}", "warn"
                )

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
            self._set_choices(
                [
                    {
                        "label": "Back",
                        "value": self._back,
                        "icon": "mdi-arrow-left",
                        "disabled": False,
                    }
                ]
            )
            return

        self._emit("", "info")
        self._emit("Running SAGE26 — output follows.", "info")
        self._emit("This may take a while for large simulations.", "info")
        self._emit("", "info")
        rc = await self._run_cmd(
            [str(sage_bin), str(self._par_path)], cwd=self._sage26_dir
        )
        if rc != 0:
            self._emit(
                f"SAGE26 exited with code {rc}. See output above.", "err"
            )
            self._set_choices(
                [
                    {
                        "label": "Back",
                        "value": self._back,
                        "icon": "mdi-arrow-left",
                        "disabled": False,
                    }
                ]
            )
            return

        self._emit("", "info")
        self._emit("SAGE26 run complete!", "ok")
        self._models = self._find_models()
        if not self._models:
            self._emit(
                "No models found after run. Check OutputDir in the par file.",
                "err",
            )
            self._set_choices(
                [
                    {
                        "label": "Back",
                        "value": self._back,
                        "icon": "mdi-arrow-left",
                        "disabled": False,
                    }
                ]
            )
            return
        if len(self._models) == 1:
            m = self._models[0]
            await self._launch_explore(m["par"], model_name=m["name"])
        else:
            await self._step_select_model()

    async def _launch_explore(
        self, par_path: Path, model_name: str | None = None
    ) -> None:
        name = model_name or par_path.stem
        self._st.wiz_step = 5
        self._emit("", "info")
        self._emit(f"Loading model: {name}", "title")
        self._emit(
            "Starting Explore Mode — refresh your browser when ready.", "info"
        )
        self._st.flush()
        await asyncio.sleep(1.0)

        sage_cmd = shutil.which("sage-viewer")
        if sage_cmd:
            os.execv(
                sage_cmd,
                [
                    sage_cmd,
                    "--par",
                    str(par_path),
                    "--port",
                    str(self._port),
                ],
            )
        else:
            os.execv(
                sys.executable,
                [
                    sys.executable,
                    "-m",
                    "sage_viewer.cli",
                    "--par",
                    str(par_path),
                    "--port",
                    str(self._port),
                ],
            )
