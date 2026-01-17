#!/usr/bin/env python3
"""Build Windows distribution with embedded Python.

Downloads the official Python Embeddable Package and creates a standalone
distribution with all dependencies pre-installed.

Usage:
    python scripts/build_windows.py
    python scripts/build_windows.py --python-version 3.11.9
    python scripts/build_windows.py --version 1.0.0
"""

import argparse
import logging
import shutil
import subprocess
import sys
import tomllib
import urllib.request
import zipfile
from pathlib import Path

# Configuration
DEFAULT_PYTHON_VERSION = "3.11.9"
PYTHON_EMBED_URL_TEMPLATE = (
    "https://www.python.org/ftp/python/{version}/python-{version}-embed-amd64.zip"
)
APP_NAME = "DocumentAnonymizer"

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


def download_python_embed(version: str, dest_dir: Path) -> Path:
    """Download Python embeddable package."""
    url = PYTHON_EMBED_URL_TEMPLATE.format(version=version)
    zip_path = dest_dir / f"python-{version}-embed-amd64.zip"
    download_file(url, zip_path)
    return zip_path


def extract_python(zip_path: Path, dest_dir: Path) -> Path:
    """Extract Python to destination."""
    python_dir = dest_dir / "python"
    logger.info(f"Extracting Python to {python_dir}")

    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(python_dir)

    # Clean up zip file
    zip_path.unlink()

    return python_dir


def configure_python_pth(python_dir: Path) -> None:
    """Configure python*._pth to enable site-packages and pip."""
    # Find the _pth file (python311._pth, python312._pth, etc.)
    pth_files = list(python_dir.glob("python*._pth"))
    if not pth_files:
        raise FileNotFoundError("Could not find python*._pth file")

    pth_file = pth_files[0]
    logger.info(f"Configuring {pth_file.name}")

    # Read current content
    content = pth_file.read_text()

    # Enable import site (uncomment the line)
    if "#import site" in content:
        content = content.replace("#import site", "import site")
    elif "import site" not in content:
        content += "\nimport site\n"

    # Add paths for site-packages and app
    lines_to_add = [
        "Lib\\site-packages",
        "..\\app",
    ]

    for line in lines_to_add:
        if line not in content:
            content += f"\n{line}"

    pth_file.write_text(content)
    logger.info("Python path configuration updated")


def setup_pip(python_dir: Path) -> None:
    """Install pip using get-pip.py (more reliable than ensurepip for embeddable)."""
    python_exe = python_dir / "python.exe"

    # Create Lib/site-packages directory
    site_packages = python_dir / "Lib" / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)

    # Download get-pip.py
    get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
    get_pip_path = python_dir / "get-pip.py"
    download_file(get_pip_url, get_pip_path)

    # Run get-pip.py
    logger.info("Installing pip...")
    subprocess.run(
        [str(python_exe), str(get_pip_path)],
        check=True,
        cwd=python_dir,
    )

    # Clean up
    get_pip_path.unlink()
    logger.info("pip installed successfully")


def install_dependencies(python_dir: Path, dependencies: list[str]) -> None:
    """Install application dependencies."""
    python_exe = python_dir / "python.exe"

    logger.info(f"Installing {len(dependencies)} dependencies...")
    for dep in dependencies:
        logger.info(f"  Installing {dep}")
        subprocess.run(
            [str(python_exe), "-m", "pip", "install", "--quiet", dep],
            check=True,
        )

    logger.info("All dependencies installed")


def copy_application(project_root: Path, dest_dir: Path) -> None:
    """Copy application code to distribution."""
    app_dir = dest_dir / "app"
    src_dir = project_root / "src" / "anonymizer"

    logger.info(f"Copying application from {src_dir} to {app_dir}")

    if app_dir.exists():
        shutil.rmtree(app_dir)

    shutil.copytree(src_dir, app_dir / "anonymizer")
    logger.info("Application code copied")


def create_launcher(dest_dir: Path, templates_dir: Path) -> None:
    """Create launcher batch file."""
    template_path = templates_dir / "launcher.bat"
    launcher_path = dest_dir / f"{APP_NAME}.bat"

    launcher_content = template_path.read_text()
    launcher_path.write_text(launcher_content)
    logger.info(f"Created launcher: {launcher_path}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build Windows distribution with embedded Python"
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
    args = parser.parse_args()

    project_root = get_project_root()
    app_version = args.version or get_version_from_pyproject()
    output_dir = project_root / args.output / APP_NAME

    logger.info(f"Building {APP_NAME} v{app_version}")
    logger.info(f"Python version: {args.python_version}")
    logger.info(f"Output directory: {output_dir}")

    # Clean output directory
    if output_dir.exists():
        logger.info("Cleaning existing output directory")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    # Create runtime directory
    runtime_dir = output_dir / "runtime"
    runtime_dir.mkdir()

    try:
        # Download and extract Python
        zip_path = download_python_embed(args.python_version, runtime_dir)
        python_dir = extract_python(zip_path, runtime_dir)

        # Configure Python
        configure_python_pth(python_dir)
        setup_pip(python_dir)

        # Install dependencies
        dependencies = get_dependencies_from_pyproject()
        install_dependencies(python_dir, dependencies)

        # Copy application
        copy_application(project_root, output_dir)

        # Create launcher
        templates_dir = project_root / "scripts" / "windows" / "templates"
        create_launcher(output_dir, templates_dir)

        logger.info(f"Build complete: {output_dir}")
        logger.info(f"To test: {output_dir / f'{APP_NAME}.bat'}")

    except Exception as e:
        logger.error(f"Build failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
