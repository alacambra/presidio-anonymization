#!/usr/bin/env python3
"""Build macOS .app bundle with embedded Python.

Downloads python-build-standalone and creates a macOS application bundle
with all dependencies pre-installed.

Usage:
    python scripts/build_macos.py
    python scripts/build_macos.py --python-version 3.11
    python scripts/build_macos.py --arch aarch64
    python scripts/build_macos.py --version 1.0.0
"""

import argparse
import logging
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tomllib
import urllib.request
from pathlib import Path

# Configuration
DEFAULT_PYTHON_VERSION = "3.11"
APP_NAME = "DocumentAnonymizer"

# python-build-standalone release info
# See: https://github.com/indygreg/python-build-standalone/releases
PBS_RELEASE = "20241016"
PBS_URL_TEMPLATE = (
    "https://github.com/indygreg/python-build-standalone/releases/download/"
    "{release}/cpython-{version}.{patch}+{release}-{arch}-apple-darwin-install_only.tar.gz"
)

# Python version to patch version mapping for the release
PYTHON_PATCH_VERSIONS = {
    "3.11": "10",
    "3.12": "7",
    "3.13": "0",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def get_version_from_pyproject() -> str:
    """Parse version from pyproject.toml."""
    pyproject_path = get_project_root() / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def get_dependencies_from_pyproject() -> list[str]:
    """Parse dependencies from pyproject.toml."""
    pyproject_path = get_project_root() / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["dependencies"]


def get_architecture() -> str:
    """Detect current architecture."""
    machine = platform.machine()
    if machine == "arm64":
        return "aarch64"
    elif machine == "x86_64":
        return "x86_64"
    else:
        raise RuntimeError(f"Unsupported architecture: {machine}")


def download_file(url: str, dest: Path) -> None:
    """Download a file with progress reporting."""
    logger.info(f"Downloading {url}")

    def report_progress(block_num: int, block_size: int, total_size: int) -> None:
        if total_size > 0:
            percent = min(100, block_num * block_size * 100 // total_size)
            if block_num % 100 == 0:
                logger.info(f"  Progress: {percent}%")

    urllib.request.urlretrieve(url, dest, reporthook=report_progress)
    logger.info(f"Downloaded to {dest}")


def download_python(version: str, arch: str, dest_dir: Path) -> Path:
    """Download python-build-standalone."""
    patch = PYTHON_PATCH_VERSIONS.get(version)
    if patch is None:
        raise ValueError(
            f"Unsupported Python version: {version}. "
            f"Supported: {list(PYTHON_PATCH_VERSIONS.keys())}"
        )

    url = PBS_URL_TEMPLATE.format(
        release=PBS_RELEASE,
        version=version,
        patch=patch,
        arch=arch,
    )

    tarball_path = dest_dir / f"python-{version}-{arch}.tar.gz"
    download_file(url, tarball_path)
    return tarball_path


def extract_python(tarball_path: Path, dest_dir: Path) -> Path:
    """Extract Python to destination."""
    logger.info(f"Extracting Python to {dest_dir}")

    with tarfile.open(tarball_path, "r:gz") as tf:
        tf.extractall(dest_dir)

    # Clean up tarball
    tarball_path.unlink()

    return dest_dir / "python"


def install_dependencies(python_dir: Path, dependencies: list[str]) -> None:
    """Install application dependencies."""
    python_exe = python_dir / "bin" / "python3"

    logger.info(f"Installing {len(dependencies)} dependencies...")
    for dep in dependencies:
        logger.info(f"  Installing {dep}")
        subprocess.run(
            [str(python_exe), "-m", "pip", "install", "--quiet", dep],
            check=True,
        )

    logger.info("All dependencies installed")


def create_app_bundle(
    output_dir: Path,
    app_version: str,
    python_dir: Path,
    app_code_dir: Path,
    templates_dir: Path,
) -> Path:
    """Create macOS .app bundle structure."""
    app_bundle = output_dir / f"{APP_NAME}.app"
    contents = app_bundle / "Contents"
    macos = contents / "MacOS"
    resources = contents / "Resources"

    logger.info(f"Creating app bundle: {app_bundle}")

    # Create directories
    macos.mkdir(parents=True)
    resources.mkdir()

    # Copy Python runtime
    runtime_dest = resources / "runtime" / "python"
    logger.info(f"Copying Python runtime to {runtime_dest}")
    shutil.copytree(python_dir, runtime_dest)

    # Copy application code
    app_dest = resources / "app" / "anonymizer"
    logger.info(f"Copying application code to {app_dest}")
    shutil.copytree(app_code_dir, app_dest)

    # Create Info.plist
    info_plist_template = templates_dir / "Info.plist"
    info_plist_content = info_plist_template.read_text()
    info_plist_content = info_plist_content.replace("__VERSION__", app_version)
    (contents / "Info.plist").write_text(info_plist_content)
    logger.info("Created Info.plist")

    # Create launcher script
    launcher_template = templates_dir / "launcher.sh"
    launcher_content = launcher_template.read_text()
    launcher_path = macos / APP_NAME
    launcher_path.write_text(launcher_content)
    launcher_path.chmod(0o755)
    logger.info(f"Created launcher: {launcher_path}")

    return app_bundle


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build macOS app bundle with embedded Python"
    )
    parser.add_argument(
        "--python-version",
        default=DEFAULT_PYTHON_VERSION,
        help=f"Python version to embed (default: {DEFAULT_PYTHON_VERSION})",
    )
    parser.add_argument(
        "--version",
        help="Override app version (default: read from pyproject.toml)",
    )
    parser.add_argument(
        "--output",
        default="build",
        help="Output directory (default: build)",
    )
    parser.add_argument(
        "--arch",
        choices=["aarch64", "x86_64"],
        help="Target architecture (default: auto-detect)",
    )
    args = parser.parse_args()

    project_root = get_project_root()
    app_version = args.version or get_version_from_pyproject()
    arch = args.arch or get_architecture()
    output_dir = project_root / args.output

    logger.info(f"Building {APP_NAME} v{app_version}")
    logger.info(f"Python version: {args.python_version}")
    logger.info(f"Architecture: {arch}")
    logger.info(f"Output directory: {output_dir}")

    # Clean output directory
    if output_dir.exists():
        logger.info("Cleaning existing output directory")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    try:
        # Download and extract Python
        tarball = download_python(args.python_version, arch, output_dir)
        python_dir = extract_python(tarball, output_dir)

        # Install dependencies into the embedded Python
        dependencies = get_dependencies_from_pyproject()
        install_dependencies(python_dir, dependencies)

        # Create app bundle
        templates_dir = project_root / "scripts" / "macos" / "templates"
        app_code_dir = project_root / "src" / "anonymizer"

        app_bundle = create_app_bundle(
            output_dir,
            app_version,
            python_dir,
            app_code_dir,
            templates_dir,
        )

        # Clean up extracted python directory (now copied into app bundle)
        shutil.rmtree(python_dir)

        logger.info(f"Build complete: {app_bundle}")
        logger.info(f"To test: open {app_bundle}")

    except Exception as e:
        logger.error(f"Build failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
