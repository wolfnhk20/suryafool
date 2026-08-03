# Changelog

## CLI v0.1.0 — Cyberpunk TUI (Ink/React)

### Features Implemented

#### ✅ Working CLI binary
- `bin/suryafool.js` — yargs entry with commands: `scan`, `audit`, `explore`, `agents`, `config`, `doctor`
- Flags: `--interactive/-i`, `--clean` (clean theme), `--hacker-mode` (cyberpunk default), `--no-animation`
- Forks `bin/run.mjs` which renders the Ink `<App>` (reads args via `SURYAFOOL_ARGS` env)
- Fixed `--clean` flag (was reading `cli.argv.clean` from the wrong yargs return value)

#### ✅ Fixed ESM/CJS build chain (Node 22 + Ink 4)
- **Root cause**: Ink 4 is ESM-only with top-level await; esbuild CJS bundles and `require()` of Ink both fail
- **Solution**: bundle as ESM (`dist/index.mjs`, `--format=esm`), externalize `ink`, `react`, `chalk`, `gradient-string`, `yargs`, `adm-zip`
- Removed `ink-gradient` (its CJS `require("ink")` is incompatible with Ink 4's TLA) — logo now uses plain colored text
- Externalized `react-devtools-core` (browser-only, was breaking Node runtime)
- Added `"type": "module"` to `suryafool-cli/package.json`
- `dist/run.mjs` → moved to `bin/run.mjs` (tracked, not a build artifact)

#### ✅ Verified working
- `node bin/suryafool.js --help` — full usage output
- `node bin/suryafool.js --clean agents` — renders logo + executes command
- Interactive mode renders panels (raw-mode error only in non-TTY shells)

### Known Issues / Remaining
- `doctor`/`agents` need Python env with `rich` (`pip install -r requirements.txt`)
- Interactive REPL requires a real TTY
- Real wireless backend (HAL, Scope Guardian, mission agents) — not yet implemented

---

## Bootstrap Agent - Initial Implementation

### Features Implemented

#### ✅ Automatic UTF-16LE Decoding
- **Issue**: Windows WSL commands output UTF-16LE encoded text
- **Solution**: Automatic detection and decoding in `bootstrap/agent.py`
- **Impact**: Enables proper error detection on Windows systems

#### ✅ Automatic Repair for Broken Installations
- **Issue**: WSL distributions can exist but be uninitialized/broken
- **Solution**: Smart repair flow in `bootstrap/agent.py`
  - Detects "already exists" errors
  - Offers automatic repair via `repair_cmd` from manifest
  - Shows clear explanation and requires user confirmation
  - Autonomously unregisters and reinstalls broken installations
- **Impact**: Fully autonomous environment recovery

#### ✅ Real-time Progress Display
- **Feature**: Live output streaming for long-running commands
- **Implementation**: `show_output` parameter in `bootstrap/remediate.py`
- **Impact**: Transparent execution - users see exactly what's happening

#### ✅ Multi-Provider LLM Support with Fallback
- **Primary**: NVIDIA NIM
- **Fallback**: Groq
- **Features**:
  - Automatic timeout detection and provider switching
  - Sliding-window rate limiting (32 req/60s)
  - Correct timeout parameter handling per provider

### Files Modified

- `bootstrap/agent.py` - Smart repair flow, UTF-16LE decoding
- `bootstrap/remediate.py` - Added `show_output` for live progress
- `bootstrap/manifest.yaml` - Added `repair_cmd` for wsl-ubuntu
- `core/llm.py` - Fixed timeout parameters for ChatNVIDIA/ChatGroq
- `.env` - Fixed line break in comment

### Design Principles Maintained

✅ **LLM = Diagnosis Only** - All commands come from human-reviewed manifest
✅ **Provisioning Guardian** - All privileged operations require explicit approval
✅ **Deterministic Safety** - Repair commands are version-controlled, not generated
✅ **Auditability** - All actions logged and traceable

### Key Achievement

**The bootstrap agent successfully demonstrated autonomous remediation:**
1. Detected broken WSL Ubuntu installation
2. Identified "already exists" error despite UTF-16LE encoding
3. Offered automatic repair with clear explanation
4. Required user confirmation (Provisioning Guardian)
5. Executed repair command with live progress
6. Verified the fix worked

This is the **first real autonomous fix** in Suryafool - exactly the behavior we designed for!
