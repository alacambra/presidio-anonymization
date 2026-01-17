#!/usr/bin/env python3
"""Create Windows installer using Inno Setup.

Generates an Inno Setup script from a template and compiles it
into a Windows installer executable.

Prerequisites:
    - Inno Setup 6 installed (https://jrsoftware.org/isinfo.php)
    - Run build_windows.py first to create the distribution

Usage:
    python scripts/create_windows_installer.py
    python scripts/create_windows_installer.py --version 1.0.0
"""

import argparse
import logging
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

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


def find_inno_setup() -> Path | None:
    """Find Inno Setup compiler (ISCC.exe)."""
    # Common installation paths
    iscc_paths = [
        Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe"),
        Path("C:/Program Files/Inno Setup 6/ISCC.exe"),
        Path("C:/Program Files (x86)/Inno Setup 5/ISCC.exe"),
        Path("C:/Program Files/Inno Setup 5/ISCC.exe"),
    ]

    # Check PATH
    iscc_in_path = shutil.which("ISCC")
    if iscc_in_path:
        return Path(iscc_in_path)

    # Check common paths
    for path in iscc_paths:
        if path.exists():
            return path

    return None


def generate_iss_script(
    template_path: Path,
    output_path: Path,
    version: str,
    source_dir: Path,
    output_dir: Path,
) -> None:
    """Generate Inno Setup script from template."""
    logger.info(f"Generating Inno Setup script from {template_path}")

    template = template_path.read_text()

    script = template.replace("__VERSION__", version)
    script = script.replace("__SOURCE_DIR__", str(source_dir.resolve()))
    script = script.replace("__OUTPUT_DIR__", str(output_dir.resolve()))

    output_path.write_text(script)
    logger.info(f"Generated script: {output_path}")


def run_inno_setup(iscc_path: Path, script_path: Path) -> None:
    """Run Inno Setup compiler."""
    logger.info(f"Running Inno Setup compiler: {iscc_path}")
    logger.info(f"Script: {script_path}")

    result = subprocess.run(
        [str(iscc_path), str(script_path)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        logger.error(f"Inno Setup failed:\n{result.stdout}\n{result.stderr}")
        raise RuntimeError("Inno Setup compilation failed")

    logger.info("Inno Setup compilation successful")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Create Windows installer using Inno Setup"
    )
    parser.add_argument(
        "--version",
        help="Override app version (default: read from pyproject.toml)",
    )
    parser.add_argument(
        "--build-dir",
        default="build/DocumentAnonymizer",
        help="Build directory containing the distribution",
    )
    parser.add_argument(
        "--output-dir",
        default="dist",
        help="Output directory for the installer",
    )
    args = parser.parse_args()

    project_root = get_project_root()
    version = args.version or get_version_from_pyproject()
    build_dir = project_root / args.build_dir
    output_dir = project_root / args.output_dir

    logger.info(f"Creating installer for {APP_NAME} v{version}")

    # Verify build directory exists
    if not build_dir.exists():
        logger.error(f"Build directory not found: {build_dir}")
        logger.error("Run build_windows.py first to create the distribution")
        return 1

    # Find Inno Setup
    iscc_path = find_inno_setup()
    if iscc_path is None:
        logger.error("Inno Setup (ISCC.exe) not found")
        logger.error("Install Inno Setup from https://jrsoftware.org/isinfo.php")
        return 1
    logger.info(f"Found Inno Setup: {iscc_path}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate ISS script
    template_path = project_root / "scripts" / "windows" / "templates" / "installer.iss"
    iss_path = output_dir / "installer.iss"

    generate_iss_script(
        template_path,
        iss_path,
        version,
        build_dir,
        output_dir,
    )

    # Run Inno Setup
    try:
        run_inno_setup(iscc_path, iss_path)
    except RuntimeError:
        return 1

    installer_name = f"{APP_NAME}-{version}-Setup.exe"
    installer_path = output_dir / installer_name
    logger.info(f"Installer created: {installer_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
