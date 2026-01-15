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

def download_spacy_model(model_name: str) -> tuple[bool, str]:
    """Download a spaCy model, works in frozen apps."""
    if is_model_installed(model_name):
        return True, "Already installed"

    # Get download URL and use pip directly
    download_url = ...  # construct from spacy.about
    return _run_pip_install(download_url)
```

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

### 7.2 Model Download in Frozen App: IN PROGRESS

The model download functionality using pip-as-library needs the correct spaCy API. The error `'function' object has no attribute 'get_version'` indicates the spaCy internal API has changed.

---

## 8. References

- [PyInstaller Multiprocessing Recipe](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#multi-processing)
- [Python multiprocessing freeze_support](https://docs.python.org/3/library/multiprocessing.html#multiprocessing.freeze_support)
- [pip as a library](https://pip.pypa.io/en/stable/user_guide/#using-pip-from-your-program)
