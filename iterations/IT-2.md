# IT-2: Fix macOS App Duplicate Instance on Anonymize

## 1. Overview

### 1.1 Purpose

Fix the issue where clicking "Anonymize" in the PyInstaller-bundled macOS app causes a second application instance to open instead of performing the anonymization within the existing window.

### 1.2 Success Criteria

- Clicking "Anonymize" processes the file without opening a second app instance
- The fix works when spaCy models need to be downloaded
- The fix works during normal anonymization operations
- No regression in CLI functionality
- No regression in development mode (`anonymize-gui` command)

### 1.3 Non-Goals

- Changing the threading model of the application
- Bundling spaCy models inside the app
- Modifying Presidio or spaCy library code

---

## 2. Problem Description

### 2.1 Observed Behavior

When clicking the "Anonymize" button in the macOS `.app` bundle:

1. A second instance of `DocumentAnonymizer.app` opens
2. The original window remains, resulting in two app instances
3. The anonymization process may or may not complete

### 2.2 Environment

- **Affected**: PyInstaller-bundled macOS app (`DocumentAnonymizer.app`)
- **Not Affected**: Development mode (`anonymize-gui`), CLI (`anonymize file ...`)

### 2.3 Reproduction Steps

1. Build the macOS app: `pyinstaller build_macos.spec --clean`
2. Launch `dist/DocumentAnonymizer.app`
3. Select an input file
4. Click "Anonymize"
5. Observe: A second app window opens

---

## 3. Root Cause Analysis

### 3.1 Hypothesis 1: Application Code Uses Multiprocessing

**Investigation**: Searched codebase for `multiprocessing` imports.

**Finding**: The application uses `threading.Thread` for background tasks, NOT `multiprocessing`. No direct multiprocessing usage in application code.

**Conclusion**: ❌ Not the direct cause.

### 3.2 Hypothesis 2: Third-Party Libraries Use Subprocess

**Investigation**: Reviewed spaCy model download mechanism.

**Finding**: spaCy's `spacy.cli.download()` uses `subprocess.run([sys.executable, "-m", "pip", "install", ...])` internally. In a frozen app:

1. `sys.executable` points to the app executable, not Python
2. Running `subprocess.run([sys.executable, ...])` re-launches the entire app
3. This causes a second GUI window to open

**Evidence**: When the spaCy model is not installed and Presidio tries to download it, the subprocess call re-executes the app entry point.

**Conclusion**: ✅ **Root cause confirmed** - subprocess with `sys.executable` re-launches the app.

### 3.3 Hypothesis 3: PyInstaller Frozen App + Spawn Method

**Investigation**: Researched PyInstaller multiprocessing behavior on macOS.

**Finding**: On macOS, Python's `multiprocessing` uses the "spawn" start method by default. When spawning:

1. Python creates a new process
2. The new process re-executes the entry point script (`launcher.py`)
3. Without `multiprocessing.freeze_support()`, the child process runs the entire script
4. This causes the GUI to initialize again, opening a duplicate window

**Conclusion**: ✅ Secondary cause - multiprocessing without freeze_support can also cause duplicate windows.

---

## 4. Solution

The fix requires **two complementary approaches**:

1. **freeze_support()** in launcher.py - handles multiprocessing child processes
2. **Custom spaCy download** - avoids subprocess with `sys.executable`

### 4.1 Part 1: freeze_support() in Launcher

Add `multiprocessing.freeze_support()` at the very start of `launcher.py`, before any imports.

**Why**: When any library spawns a child process via multiprocessing, the child re-executes the entry point. `freeze_support()` makes child processes exit early instead of re-running the GUI.

**Modified launcher.py**:

```python
"""Entry point for PyInstaller executable."""
import multiprocessing

if __name__ == "__main__":
    # CRITICAL: Must be called before any other code in frozen apps.
    # This prevents child processes from re-executing the GUI when
    # third-party libraries (spaCy, Presidio) use multiprocessing internally.
    # No-op in non-frozen environments, so safe for development mode.
    multiprocessing.freeze_support()

    from anonymizer.ports.gui.app import main
    main()
```

### 4.2 Part 2: Frozen-App-Aware spaCy Download

The main issue is that spaCy's download mechanism uses `subprocess.run([sys.executable, ...])`, which re-launches the app in frozen environments.

**Solution**: Intercept the download before Presidio calls spaCy's download, and use pip as a library instead of subprocess.

**Implementation in config.py**:

```python
def is_frozen() -> bool:
    """Check if running as a frozen/bundled application."""
    return getattr(sys, "frozen", False)

def _run_pip_install(package_spec: str, timeout: int = 300) -> tuple[bool, str]:
    """
    Install a package using pip.
    In frozen apps, uses pip as a library to avoid subprocess issues.
    """
    if is_frozen():
        # Use pip as a library - avoids re-launching the app
        from pip._internal.cli.main import main as pip_main
        result = pip_main(["install", "--quiet", package_spec])
        return (True, "Installation complete") if result == 0 else (False, f"pip returned {result}")
    else:
        # Normal Python - use subprocess for isolation
        import subprocess
        result = subprocess.run([sys.executable, "-m", "pip", "install", package_spec], ...)
        return (result.returncode == 0, ...)

def _get_spacy_model_download_url(model_name: str) -> str:
    """Construct the download URL for a spaCy model."""
    import spacy.about

    base_url = spacy.about.__download_url__
    spacy_version = spacy.about.__version__
    version_parts = spacy_version.split(".")
    model_version = f"{version_parts[0]}.{version_parts[1]}.0"

    filename = f"{model_name}-{model_version}-py3-none-any.whl"
    return f"{base_url}/{model_name}-{model_version}/{filename}"

def download_spacy_model(model_name: str) -> tuple[bool, str]:
    """Download a spaCy model, works in frozen apps."""
    if is_model_installed(model_name):
        return True, "Already installed"

    if is_frozen():
        # In frozen apps, use pip with direct GitHub URL
        url = _get_spacy_model_download_url(model_name)
        return _run_pip_install(url)
    else:
        # In normal Python, use spacy.cli.download
        from spacy.cli.download import download
        download(model_name)
        return True, "Downloaded successfully"
```

**Key insight**: spaCy models cannot be installed via `pip install model_name` directly - they're hosted on GitHub, not PyPI. The model names on PyPI are stub packages for Dependency Confusion attack protection. We construct the direct GitHub URL using `spacy.about.__download_url__` and the spaCy version to get the compatible model version.

**Implementation in analyzer.py**:

```python
def _ensure_model_available(self, model_name: str) -> None:
    """Ensure model is available, downloading if necessary."""
    if is_model_installed(model_name):
        return

    # Download using our frozen-app-aware function
    success, message = download_spacy_model(model_name)
    if not success:
        raise OSError(f"Failed to download model: {message}")
```

This is called in `_create_spacy_engine()` and `_create_transformers_engine()` **before** Presidio tries to load the model, preventing Presidio from triggering its own subprocess-based download.

### 4.3 Why This Two-Part Solution Works

1. **freeze_support()**: Catches any multiprocessing child processes and makes them exit cleanly
2. **Custom download**: Prevents subprocess calls with `sys.executable` by:
   - Checking if model is installed before Presidio can trigger download
   - Using pip as a library (`pip._internal.cli.main`) instead of subprocess
   - This avoids re-executing the app executable entirely

---

## 5. Testing Strategy

### 5.1 Why Automated Testing Is Not Feasible

This issue **only manifests in PyInstaller-bundled apps**. The `freeze_support()` function is a no-op in normal Python execution, and the pip-as-library approach only differs in frozen environments.

### 5.2 Manual Test Cases

**Test Case TC-IT2-001: Basic Anonymization (model pre-installed)**

```
Precondition: App built with fix, spaCy model already installed

Steps:
1. Launch DocumentAnonymizer.app from dist/
2. Select an input file (any .txt or .md file)
3. Click "Anonymize"

Expected:
- Single app window remains
- Anonymization completes successfully
- No second app instance opens
```

**Test Case TC-IT2-002: Model Download Scenario**

```
Precondition: App built with fix, spaCy model NOT installed

Steps:
1. Remove spaCy model: python -m spacy unlink en_core_web_trf
2. Launch DocumentAnonymizer.app from dist/
3. Select an input file
4. Click "Anonymize"

Expected:
- Single app window remains
- Model downloads in background
- No second app instance opens
- Anonymization completes after model download
```

**Test Case TC-IT2-003: Development Mode Regression**

```
Precondition: Development environment

Steps:
1. Run: anonymize-gui
2. Perform anonymization

Expected:
- Works exactly as before
- No regression in development mode
```

### 5.3 Verification Commands

```bash
# Build the app
pyinstaller build_macos.spec --clean

# Run with console output for debugging
./dist/DocumentAnonymizer.app/Contents/MacOS/DocumentAnonymizer
```

---

## 6. Files Modified

| File                              | Change                                                    |
| --------------------------------- | --------------------------------------------------------- |
| `launcher.py`                     | Added `multiprocessing.freeze_support()` before imports   |
| `src/anonymizer/config.py`        | Added `is_frozen()`, `_run_pip_install()`, `download_spacy_model()` |
| `src/anonymizer/core/analyzer.py` | Added `_ensure_model_available()` to intercept downloads  |

---

## 7. Completion Status

### 7.1 Duplicate Window Issue: FIXED ✅

The duplicate window no longer appears when clicking "Anonymize". The `freeze_support()` call in `launcher.py` successfully prevents child processes from re-executing the GUI.

### 7.2 Model Download in Frozen App: FIXED ✅

The model download functionality now works in frozen apps by:

1. Using `spacy.about.__download_url__` to get the GitHub releases base URL
2. Constructing the model version from `spacy.about.__version__` (models use `{major}.{minor}.0`)
3. Building the full wheel URL: `{base_url}/{model}-{version}/{model}-{version}-py3-none-any.whl`
4. Using pip as a library (`pip._internal.cli.main`) to install the wheel directly

This avoids the Dependency Confusion attack protection on PyPI (where model names are stub packages) and works without subprocess calls that would re-launch the frozen app.

---

## 8. Model Manager Implementation

### 8.1 Overview

After resolving the duplicate window issue, the model download strategy was redesigned to provide a unified approach that works identically in both frozen (PyInstaller) and normal Python environments.

**New approach**:
- Download spaCy models directly from GitHub as `.tar.gz` files
- Extract to local app data folder
- Load models from path using `spacy.load(path)`
- Provide a GUI dialog accessible via File > Model Manager menu

### 8.2 Architecture

The Model Manager follows the MVP (Model-View-Presenter) pattern:

```
src/anonymizer/
├── model_storage.py              # Core download/storage module (NEW)
└── ports/gui/
    ├── views/
    │   └── model_manager_dialog.py   # Tkinter view (NEW)
    └── presenters/
        └── model_manager_presenter.py # Business logic (NEW)
```

### 8.3 Storage Locations

Platform-specific app data folders:
- **macOS**: `~/Library/Application Support/DocumentAnonymizer/models/`
- **Windows**: `%LOCALAPPDATA%/DocumentAnonymizer/models/`
- **Linux**: `~/.local/share/DocumentAnonymizer/models/`

### 8.4 Download URL Pattern

Models are downloaded from GitHub releases:

```
https://github.com/explosion/spacy-models/releases/download/{model}-{version}/{model}-{version}.tar.gz
```

Version is derived from `spacy.about.__version__` → `{major}.{minor}.0`

### 8.5 Tarball Extraction

The tarball structure requires nested extraction:

```
{model}-{version}.tar.gz
└── {model}-{version}/
    └── {model}/
        └── {model}-{version}/  ← actual model files (meta.json, etc.)
```

After extraction, the inner directory is moved to `{models_dir}/{model_name}/`

### 8.6 Key Implementation Details

**model_storage.py**:
```python
def get_app_data_dir() -> Path:
    """Platform-specific app data directory"""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", ...))
    else:
        base = Path.home() / ".local" / "share"
    return base / "DocumentAnonymizer"

def download_spacy_model(model_name: str, progress_callback: ...) -> Tuple[bool, str]:
    """Download .tar.gz from GitHub, extract, store locally"""
```

**analyzer.py** (modified to load from local path):
```python
model_path = get_model_path(model_name)
model_spec = str(model_path) if model_path else model_name
```

**config.py** (modified to check local storage first):
```python
def is_model_installed(model_name: str) -> bool:
    from .model_storage import is_model_downloaded
    if is_model_downloaded(model_name):
        return True
    return spacy.util.is_package(model_name)
```

### 8.7 UI Features

The Model Manager dialog provides:
- Treeview with languages as parents, models as children
- Checkbox selection (click to toggle)
- Columns: Model name, Size (MB), Status
- Progress bar showing download progress (MB downloaded / total MB)
- Download/Delete/Close buttons
- Non-blocking UI with background threading

### 8.8 Language Dropdown Filtering

The main window's Language dropdown only shows languages that have at least one downloaded model:

- If only English models are downloaded, only "en - English" appears
- When models are downloaded/deleted via Model Manager, the dropdown automatically refreshes
- If no models are available, all languages are shown (fallback)

**Implementation**:

- `model_storage.get_available_languages()` returns language codes with downloaded models
- `main_window.refresh_available_languages()` updates the dropdown
- Model Manager calls `notify_models_changed()` callback after download/delete operations

### 8.9 Files Created

| File | Purpose |
| ---- | ------- |
| `src/anonymizer/model_storage.py` | Core download and storage functions |
| `src/anonymizer/ports/gui/views/model_manager_dialog.py` | Tkinter view for Model Manager |
| `src/anonymizer/ports/gui/presenters/model_manager_presenter.py` | Business logic for download/delete |

### 8.10 Files Modified

| File | Change |
| ---- | ------ |
| `src/anonymizer/core/analyzer.py` | Load models from local path when available |
| `src/anonymizer/config.py` | Check local storage first in `is_model_installed()` |
| `src/anonymizer/ports/gui/views/main_window.py` | Added File menu with Model Manager item |
| `src/anonymizer/ports/gui/app.py` | Wired Model Manager dialog |
| `src/anonymizer/ports/gui/views/__init__.py` | Added ModelManagerDialog export |
| `src/anonymizer/ports/gui/presenters/__init__.py` | Added ModelManagerPresenter export |

---

## 9. Configure Models Removal

### 9.1 Overview

The old "Configure Models" button and dialog were removed in favor of the new Model Manager accessible via the File menu.

### 9.2 Files Deleted

| File | Purpose (removed) |
| ---- | ----------------- |
| `src/anonymizer/ports/gui/views/model_config_dialog.py` | Old configuration dialog view |
| `src/anonymizer/ports/gui/presenters/model_config_presenter.py` | Old configuration dialog presenter |

### 9.3 Files Modified

| File | Change |
| ---- | ------ |
| `src/anonymizer/ports/gui/views/main_window.py` | Removed Configure Models button and related callbacks |
| `src/anonymizer/ports/gui/presenters/anonymizer_presenter.py` | Removed `handle_configure_models()` method |
| `src/anonymizer/ports/gui/app.py` | Removed model_config_dialog import and wiring |
| `src/anonymizer/ports/gui/views/__init__.py` | Removed ModelConfigDialog export |
| `src/anonymizer/ports/gui/presenters/__init__.py` | Removed ModelConfigPresenter export |
| `tests/test_gui_presenters.py` | Removed TestModelConfigPresenter test class |

---

## 10. Hierarchical Model Selection

### 10.1 Overview

The flat language dropdown was replaced with a hierarchical model selection menu. Users can now see and select specific downloaded models organized by language.

### 10.2 UI Change

**Before**: Simple combobox showing `en - English`, `es - Spanish`, etc.

**After**: Cascading menu button showing:
```
[English: en_core_web_lg ▼]
    ├── English >
    │   ├── en_core_web_sm (12 MB - Small - CPU optimized)
    │   ├── en_core_web_md (40 MB - Medium - balanced)
    │   └── en_core_web_lg (560 MB - Large - better accuracy)
    ├── Spanish >
    │   └── es_core_news_md (40 MB - Medium - balanced)
    └── German >
        └── de_core_news_sm (12 MB - Small - CPU optimized)
```

### 10.3 Key Features

- **Hierarchical display**: Languages as parent menus, models as children
- **Only downloaded models shown**: Languages without downloaded models are hidden
- **Auto-selection**: First available model is auto-selected on startup
- **Empty state handling**: Shows "No models - use Model Manager" when nothing downloaded
- **Immediate config update**: `set_model_for_language()` is called directly in `_select_model()` to ensure the correct model is used even during initialization (before callbacks are wired)
- **Refresh on download**: Menu updates when models are downloaded/deleted via Model Manager

### 10.4 Critical Fix: Transformer Model Error

**Problem**: In PyInstaller builds, selecting a transformer model (e.g., `en_core_web_trf`) caused error:
```
[E002] Can't find factory for 'curated_transformer' for language English (en)
```

**Root Cause**: The model selection callback wasn't wired when `_populate_model_menu()` auto-selected the first model during `__init__`. This meant `SUPPORTED_LANGUAGES` still contained the default `en_core_web_trf` instead of the selected non-transformer model.

**Fix**: Call `set_model_for_language(lang_code, model_name)` directly in `_select_model()` instead of relying on the callback:

```python
def _select_model(self, lang_code: str, model_name: str) -> None:
    """Handle model selection from menu."""
    self._selected_language.set(lang_code)
    self._selected_model = model_name

    # Update config immediately (important for initialization before callbacks are wired)
    set_model_for_language(lang_code, model_name)

    # Update button text
    lang_name = LANGUAGE_NAMES.get(lang_code, lang_code)
    if self._model_menu_btn:
        self._model_menu_btn.config(text=f"{lang_name}: {model_name}")

    # Notify callbacks (may not be wired yet during __init__)
    if self._on_language_changed:
        self._on_language_changed(lang_code)
    if self._on_model_changed:
        self._on_model_changed(lang_code, model_name)
```

### 10.5 Files Modified

| File | Change |
| ---- | ------ |
| `src/anonymizer/ports/gui/views/main_window.py` | Replaced combobox with `tk.Menubutton` + cascading `tk.Menu`; added `_populate_model_menu()`, `_select_model()` methods; calls `set_model_for_language()` directly |
| `src/anonymizer/ports/gui/app.py` | Fixed import path for `set_model_for_language`; simplified language parsing |
| `src/anonymizer/ports/gui/presenters/anonymizer_presenter.py` | Removed `.split(" - ")[0]` parsing since `selected_language` is now just the code |

---

## 11. References

- [PyInstaller Multiprocessing Recipe](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#multi-processing)
- [Python multiprocessing freeze_support](https://docs.python.org/3/library/multiprocessing.html#multiprocessing.freeze_support)
- [pip as a library](https://pip.pypa.io/en/stable/user_guide/#using-pip-from-your-program)
- [spaCy Models GitHub Releases](https://github.com/explosion/spacy-models/releases)
