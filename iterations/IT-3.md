# IT-3: Embedded Python Distribution (Replacing PyInstaller)

## 1. Overview

### 1.1 Purpose

Replace the failed PyInstaller approach with embedded Python distributions using native platform installers. This enables full Python functionality including transformer models that require TorchScript.

### 1.2 Previous Approach Failure (IT-2 PyInstaller)

The PyInstaller approach failed for transformer models (`*_trf`) due to fundamental TorchScript limitations:

| Issue | Description | Fixable? |
|-------|-------------|----------|
| `curated_transformer` factory | TorchScript requires `.py` source files which PyInstaller doesn't preserve | ❌ No |
| `sys.executable` mismatch | Points to app executable, not Python interpreter | Workaround existed |
| Presidio conf paths | `__file__` resolution broken in frozen apps | ✅ Was fixed |
| Read-only `_MEIPASS` | Cannot install packages at runtime | ❌ Fundamental limitation |

**Conclusion**: Basic spaCy models (sm/md/lg) worked, but transformer models cannot work in PyInstaller builds. The embedded Python approach solves all these issues.

### 1.3 Success Criteria

- Windows: setup.exe installer installs and runs correctly
- macOS: DMG with drag-to-Applications works
- Both platforms: Transformer models (en_core_web_trf) work
- Both platforms: Model Manager downloads to user data folder
- Both platforms: Uninstall removes application (preserves user data)

### 1.4 Non-Goals

- Code signing (deferred to production release)
- Auto-update mechanism
- Enterprise deployment features (MSI, MDM)

---

## 2. Solution Architecture

### 2.1 Concept

Ship a complete, portable Python installation alongside the application code. Users interact with launcher scripts that invoke this embedded Python.

```text
Analogy:
  Java:   JVM installed → double-click .jar → works
  Python: Embedded Python shipped → double-click launcher → works
```

### 2.2 Windows Structure (After Installation)

```text
C:\Program Files\DocumentAnonymizer\
├── runtime\
│   └── python\
│       ├── python.exe
│       ├── python311.dll
│       ├── python311.zip          # Standard library
│       ├── python311._pth         # Path configuration
│       └── Lib\
│           └── site-packages\     # Pre-installed packages
├── app\
│   ├── anonymizer\                # Application package
│   └── requirements.txt
├── DocumentAnonymizer.bat         # Launcher
└── unins000.exe                   # Uninstaller (Inno Setup)

User data (separate):
%LOCALAPPDATA%\DocumentAnonymizer\
├── models\                        # spaCy models (runtime download)
├── data\                          # User data
└── logs\                          # Application logs
```

### 2.3 macOS Structure (.app Bundle)

```text
DocumentAnonymizer.app/
└── Contents/
    ├── Info.plist
    ├── MacOS/
    │   └── DocumentAnonymizer     # Shell script launcher
    └── Resources/
        ├── app/
        │   ├── anonymizer/        # Application package
        │   └── requirements.txt
        └── runtime/
            └── python/            # Embedded Python

User data (separate):
~/Library/Application Support/DocumentAnonymizer/
├── models/                        # spaCy models
├── data/                          # User data
└── logs/                          # Application logs
```

### 2.4 Key Benefits

| Benefit | Description |
|---------|-------------|
| Real Python interpreter | `sys.executable` works correctly |
| Writable site-packages | pip install works normally |
| Persistent storage | Models survive app restarts |
| No user installation | Download, install/extract, run |
| Updateable | Replace `app/` folder for updates |
| Debuggable | Standard Python tools work |
| Full model support | Transformer models work |

---

## 3. Implementation Plan

### Phase 1: Cleanup (Remove PyInstaller Artifacts)

**Files to delete:**
- `hooks/hook-presidio_analyzer.py`
- `hooks/rthook_presidio.py`
- `hooks/__pycache__/`
- `hooks/` directory
- `build_macos.spec`
- `build_windows.spec`
- `launcher.py`

**Code to revert:**
- `src/anonymizer/config.py`: Remove `is_frozen()`, simplify `_run_pip_install()`
- `src/anonymizer/core/analyzer.py`: Remove frozen checks, `_ensure_transformer_factories_registered()`
- `src/anonymizer/ports/gui/views/main_window.py`: Remove debug logging

### Phase 2: Build Scripts

**`scripts/build_windows.py`**:
1. Download Python Embeddable Package from python.org
2. Extract to `build/DocumentAnonymizer/runtime/python/`
3. Configure `python311._pth` to enable site-packages (`import site`)
4. Create `Lib/site-packages/` directory
5. Install pip with `ensurepip`
6. Install application dependencies from requirements.txt
7. Copy application code to `build/DocumentAnonymizer/app/`
8. Create launcher batch file

**`scripts/build_macos.py`**:
1. Download python-build-standalone from GitHub releases
2. Extract to `build/DocumentAnonymizer.app/Contents/Resources/runtime/python/`
3. Install application dependencies
4. Copy application code to `build/DocumentAnonymizer.app/Contents/Resources/app/`
5. Create `.app` bundle structure with Info.plist
6. Create launcher shell script in `Contents/MacOS/`

### Phase 3: Installer Creation

**`scripts/create_windows_installer.py`**:
1. Generate Inno Setup script from template
2. Run ISCC.exe to compile `DocumentAnonymizer-{version}-Setup.exe`

**`scripts/create_macos_dmg.py`**:
1. Create DMG staging directory
2. Copy .app bundle
3. Create symlink to /Applications
4. Run hdiutil to create `DocumentAnonymizer-{version}.dmg`

### Phase 4: CI/CD Integration

**`.github/workflows/build-release.yml`**:
- Windows job: Build + Inno Setup on `windows-latest`
- macOS ARM64 job: Build + DMG on `macos-latest`
- macOS x64 job: Build + DMG on `macos-13` (Intel runner)
- Publish artifacts to GitHub release

---

## 4. Files to Create

### Windows (`scripts/windows/`)

| File | Purpose |
|------|---------|
| `scripts/windows/build.py` | Build Windows distribution with embedded Python |
| `scripts/windows/create_installer.py` | Generate Inno Setup installer (setup.exe) |
| `scripts/windows/templates/installer.iss` | Inno Setup script template |
| `scripts/windows/templates/launcher.bat` | Windows launcher script |

### macOS (`scripts/macos/`)

| File | Purpose |
|------|---------|
| `scripts/macos/build.py` | Build macOS .app bundle with embedded Python |
| `scripts/macos/create_dmg.py` | Generate DMG disk image |
| `scripts/macos/templates/Info.plist` | macOS Info.plist template |
| `scripts/macos/templates/launcher.sh` | macOS launcher script |

### Shared

| File | Purpose |
|------|---------|
| `.github/workflows/build-release.yml` | CI/CD workflow for releases |

---

## 5. Files to Delete

| File | Reason |
|------|--------|
| `hooks/hook-presidio_analyzer.py` | PyInstaller-specific hook |
| `hooks/rthook_presidio.py` | PyInstaller runtime hook |
| `hooks/` directory | No longer needed |
| `build_macos.spec` | PyInstaller spec file |
| `build_windows.spec` | PyInstaller spec file |
| `launcher.py` | PyInstaller entry point |

---

## 6. Files to Modify

| File | Change |
|------|--------|
| `src/anonymizer/config.py` | Remove `is_frozen()` function, simplify `_run_pip_install()` to always use subprocess |
| `src/anonymizer/core/analyzer.py` | Remove frozen app checks, conditional transformer imports, `_ensure_transformer_factories_registered()` |
| `src/anonymizer/ports/gui/views/main_window.py` | Remove debug logging from `_select_model()` |
| `pyproject.toml` | Update build dependencies (remove PyInstaller, add build tools) |

---

## 7. Python Sources

### Windows

**Official Python Embeddable Package**:
- Download: https://www.python.org/ftp/python/{version}/python-{version}-embed-amd64.zip
- Size: ~15MB compressed, ~40MB extracted
- Requires: Enable site-packages via `python311._pth` modification

### macOS

**python-build-standalone** (recommended):
- Repository: https://github.com/indygreg/python-build-standalone
- Releases: ARM64 and x86_64 variants available
- Size: ~25MB compressed, ~80MB extracted
- License: PSF License (free for commercial use)

---

## 8. Launcher Scripts

### Windows (DocumentAnonymizer.bat)

```batch
@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PYTHON_HOME=%SCRIPT_DIR%runtime\python"
set "PYTHON_EXE=%PYTHON_HOME%\python.exe"
set "PATH=%PYTHON_HOME%;%PYTHON_HOME%\Scripts;%PATH%"
set "APP_DIR=%SCRIPT_DIR%app"

"%PYTHON_EXE%" -m anonymizer.ports.gui.app %*

endlocal
```

### macOS (Contents/MacOS/DocumentAnonymizer)

```bash
#!/bin/bash

BUNDLE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RESOURCES="$BUNDLE_DIR/Resources"

export PYTHON_HOME="$RESOURCES/runtime/python"
export PATH="$PYTHON_HOME/bin:$PATH"
export PYTHONPATH="$RESOURCES/app"

exec "$PYTHON_HOME/bin/python3" -m anonymizer.ports.gui.app "$@"
```

---

## 9. Verification

### Windows

```bash
# Build
python scripts/build_windows.py
python scripts/create_windows_installer.py

# Test installer
dist/DocumentAnonymizer-1.0.0-Setup.exe

# Verify:
# 1. Install to C:\Program Files\DocumentAnonymizer
# 2. Launch from Start Menu
# 3. Open Model Manager, download en_core_web_trf
# 4. Select transformer model and anonymize a file
# 5. Uninstall from Add/Remove Programs
```

### macOS

```bash
# Build
python scripts/build_macos.py
python scripts/create_macos_dmg.py

# Test DMG
open dist/DocumentAnonymizer-1.0.0.dmg
# Drag to Applications
open /Applications/DocumentAnonymizer.app

# Verify:
# 1. App launches (after right-click > Open for Gatekeeper)
# 2. Download transformer model via Model Manager
# 3. Anonymize with transformer model - should work!
```

---

## 10. Size Estimates

| Component | Windows | macOS |
|-----------|---------|-------|
| Embedded Python | ~40 MB | ~80 MB |
| Application code | ~5 MB | ~5 MB |
| Pre-installed deps | ~50 MB | ~50 MB |
| **Base installer** | **~95 MB** | **~135 MB** |
| Each language model | ~12-60 MB | ~12-60 MB |

**Note**: Users download only the language models they need via Model Manager.

---

## 11. Gatekeeper / SmartScreen Notes

### Windows (Without Code Signing)

Users will see SmartScreen warning:
> "Windows protected your PC - Microsoft Defender SmartScreen prevented an unrecognized app from starting."

Click "More info" → "Run anyway" to proceed.

### macOS (Without Code Signing)

Users will see Gatekeeper warning:
> "DocumentAnonymizer can't be opened because it is from an unidentified developer."

**User workaround**:
1. Right-click (or Control-click) on the application
2. Select "Open" from the context menu
3. Click "Open" in the dialog that appears
4. This only needs to be done once

---

## 12. Acceptance Criteria

### Functional
- [ ] Windows installer installs cleanly
- [ ] Windows app launches from Start Menu
- [ ] macOS DMG mounts correctly
- [ ] macOS app launches after Gatekeeper bypass
- [ ] Model Manager downloads models to user data folder
- [ ] Transformer models (en_core_web_trf) work on both platforms
- [ ] Anonymization completes successfully
- [ ] Uninstall removes application files

### Technical
- [ ] PyInstaller artifacts removed from codebase
- [ ] Frozen app checks removed from code
- [ ] Build scripts create correct directory structures
- [ ] Launchers set correct environment variables
- [ ] Tests pass after code cleanup

---

## 13. Definition of Done

- [ ] All PyInstaller-related files deleted
- [ ] Code reverted to remove frozen app workarounds
- [ ] Build scripts created and tested
- [ ] Windows installer (setup.exe) works
- [ ] macOS DMG works
- [ ] Transformer models verified working
- [ ] IT-3.md completed with results
- [ ] Tests pass

---

## 14. References

- [Python Embeddable Package](https://www.python.org/downloads/windows/)
- [python-build-standalone](https://github.com/indygreg/python-build-standalone)
- [Inno Setup](https://jrsoftware.org/isinfo.php) (free, BSD-like license)
- [hdiutil](https://ss64.com/osx/hdiutil.html) (macOS built-in)
- Distribution Strategy Document: `docs/distribution-strategy.md`

---

## 15. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-16 | Initial version - replacing failed PyInstaller approach |
