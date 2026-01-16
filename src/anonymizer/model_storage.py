"""Model storage and download management for spaCy models.

This module handles downloading spaCy models directly from GitHub releases,
extracting them locally, and managing the local model storage. It works
identically in frozen (PyInstaller) and normal Python environments.
"""

import os
import shutil
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from .logger import setup_logger

logger = setup_logger(__name__)


def get_app_data_dir() -> Path:
    """
    Get the application data directory based on platform.

    Returns:
        Path to app data directory:
        - macOS: ~/Library/Application Support/DocumentAnonymizer
        - Windows: %LOCALAPPDATA%/DocumentAnonymizer
        - Linux: ~/.local/share/DocumentAnonymizer
    """
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    else:
        # Linux and other Unix-like systems
        base = Path.home() / ".local" / "share"

    return base / "DocumentAnonymizer"


def get_models_dir() -> Path:
    """Get the models directory, creating if needed."""
    models_dir = get_app_data_dir() / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir


def get_model_path(model_name: str) -> Optional[Path]:
    """
    Get the local path to a downloaded model.

    Args:
        model_name: spaCy model name (e.g., 'en_core_web_lg')

    Returns:
        Path to model directory, or None if not downloaded
    """
    model_path = get_models_dir() / model_name
    if model_path.exists() and (model_path / "meta.json").exists():
        return model_path
    return None


def is_model_downloaded(model_name: str) -> bool:
    """Check if a model is downloaded locally."""
    return get_model_path(model_name) is not None


def _get_model_version() -> str:
    """
    Get the model version matching installed spaCy.

    spaCy models use version format {major}.{minor}.0 matching spaCy version.
    """
    import spacy.about

    spacy_version = spacy.about.__version__
    version_parts = spacy_version.split(".")
    return f"{version_parts[0]}.{version_parts[1]}.0"


def _get_spacy_model_tarball_url(model_name: str) -> str:
    """
    Construct the GitHub release URL for a spaCy model tarball.

    Args:
        model_name: spaCy model name

    Returns:
        URL to .tar.gz file on GitHub
    """
    model_version = _get_model_version()

    # GitHub releases URL pattern
    url = (
        f"https://github.com/explosion/spacy-models/releases/download/"
        f"{model_name}-{model_version}/{model_name}-{model_version}.tar.gz"
    )
    return url


def _download_file(
    url: str,
    dest_path: Path,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    """
    Download a file with optional progress reporting.

    Args:
        url: URL to download
        dest_path: Destination file path
        progress_callback: Optional callback(bytes_downloaded, total_bytes)
    """
    request = urllib.request.Request(url)
    request.add_header("User-Agent", "DocumentAnonymizer/1.0")

    with urllib.request.urlopen(request, timeout=120) as response:
        total_size = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        block_size = 32768  # 32KB chunks

        with open(dest_path, "wb") as f:
            while True:
                chunk = response.read(block_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)

                if progress_callback:
                    progress_callback(downloaded, total_size)


def download_spacy_model(
    model_name: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Tuple[bool, str]:
    """
    Download a spaCy model from GitHub releases.

    Downloads the .tar.gz file, extracts it, and stores in app data folder.
    Works identically in frozen (PyInstaller) and normal Python environments.

    Args:
        model_name: spaCy model name (e.g., 'en_core_web_lg')
        progress_callback: Optional callback(bytes_downloaded, total_bytes)

    Returns:
        Tuple of (success, message)
    """
    if is_model_downloaded(model_name):
        return True, f"Model {model_name} already downloaded"

    try:
        url = _get_spacy_model_tarball_url(model_name)
        logger.info(f"[download_spacy_model] starting download;model:{model_name};url:{url}")

        # Create temp directory for download
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tarball_path = temp_path / f"{model_name}.tar.gz"

            # Download with progress
            _download_file(url, tarball_path, progress_callback)

            logger.info(f"[download_spacy_model] extracting;model:{model_name}")

            # Extract tarball
            with tarfile.open(tarball_path, "r:gz") as tar:
                tar.extractall(temp_path)

            # Find extracted directory
            # Structure: {model_name}-{version}/{model_name}/{model_name}-{version}/
            model_version = _get_model_version()
            extracted_root = temp_path / f"{model_name}-{model_version}"

            if not extracted_root.exists():
                # Try finding any matching directory
                extracted_dirs = list(temp_path.glob(f"{model_name}-*"))
                if not extracted_dirs:
                    return False, "Could not find extracted model directory"
                extracted_root = extracted_dirs[0]

            # The actual model is inside: {root}/{model_name}/{model_name}-{version}/
            model_source = extracted_root / model_name / f"{model_name}-{model_version}"

            if not model_source.exists():
                # Alternative: might be directly in {root}/{model_name}/
                model_source = extracted_root / model_name
                if not model_source.exists():
                    return False, f"Model directory structure not as expected in {extracted_root}"

            # Verify it's a valid model (has meta.json)
            if not (model_source / "meta.json").exists():
                # Check one level deeper
                inner_dirs = list(model_source.glob("*/meta.json"))
                if inner_dirs:
                    model_source = inner_dirs[0].parent

            if not (model_source / "meta.json").exists():
                return False, "Downloaded archive does not contain valid spaCy model"

            # Move to final location
            models_dir = get_models_dir()
            final_path = models_dir / model_name

            if final_path.exists():
                shutil.rmtree(final_path)

            shutil.copytree(str(model_source), str(final_path))

        logger.info(f"[download_spacy_model] download complete;model:{model_name};path:{final_path}")
        return True, f"Model {model_name} downloaded successfully"

    except urllib.error.HTTPError as e:
        logger.error(f"[download_spacy_model] HTTP error;model:{model_name};error:{e}")
        return False, f"Download failed: HTTP {e.code} - {e.reason}"
    except urllib.error.URLError as e:
        logger.error(f"[download_spacy_model] URL error;model:{model_name};error:{e}")
        return False, f"Download failed: {e.reason}"
    except Exception as e:
        logger.error(f"[download_spacy_model] failed;model:{model_name};error:{e}")
        return False, f"Download failed: {str(e)}"


def delete_model(model_name: str) -> Tuple[bool, str]:
    """
    Delete a downloaded model.

    Args:
        model_name: Name of model to delete

    Returns:
        Tuple of (success, message)
    """
    model_path = get_model_path(model_name)
    if model_path is None:
        return False, f"Model {model_name} is not downloaded"

    try:
        shutil.rmtree(model_path)
        logger.info(f"[delete_model] deleted;model:{model_name}")
        return True, f"Model {model_name} deleted"
    except Exception as e:
        logger.error(f"[delete_model] failed;model:{model_name};error:{e}")
        return False, f"Delete failed: {str(e)}"


def get_downloaded_models() -> List[str]:
    """Get list of all downloaded model names."""
    models_dir = get_models_dir()
    downloaded = []

    if not models_dir.exists():
        return downloaded

    for item in models_dir.iterdir():
        if item.is_dir() and (item / "meta.json").exists():
            downloaded.append(item.name)

    return downloaded


def get_available_languages() -> List[str]:
    """
    Get list of language codes that have at least one downloaded model.

    Only checks local model storage (Model Manager downloads), not pip-installed packages.
    This ensures the language dropdown only shows languages the user has explicitly
    downloaded via the Model Manager.

    Returns:
        List of language codes (e.g., ['en', 'de'])
    """
    from .config import AVAILABLE_MODELS

    available = []
    for lang_code, models in AVAILABLE_MODELS.items():
        # Check if any model for this language is downloaded locally
        for model in models:
            if is_model_downloaded(model.name):
                available.append(lang_code)
                break

    return available
