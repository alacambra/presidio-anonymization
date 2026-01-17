#!/usr/bin/env python3
"""Create macOS DMG installer.

Creates a DMG disk image containing the application bundle
with a symlink to /Applications for easy installation.

Prerequisites:
    - Run build_macos.py first to create the .app bundle
    - macOS system (uses hdiutil)

Usage:
    python scripts/create_macos_dmg.py
    python scripts/create_macos_dmg.py --version 1.0.0
"""

import argparse
import logging
import shutil
import subprocess
import sys
import tempfile
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


def create_dmg(
    app_bundle: Path,
    output_path: Path,
    volume_name: str,
) -> None:
    """Create DMG using hdiutil."""
    logger.info(f"Creating DMG: {output_path}")

    with tempfile.TemporaryDirectory() as staging_dir:
        staging = Path(staging_dir)

        # Copy app bundle to staging
        logger.info(f"Copying app bundle to staging area")
        dest_app = staging / app_bundle.name
        shutil.copytree(app_bundle, dest_app)

        # Create Applications symlink for drag-to-install
        logger.info("Creating Applications symlink")
        apps_link = staging / "Applications"
        apps_link.symlink_to("/Applications")

        # Remove existing DMG if present
        if output_path.exists():
            output_path.unlink()

        # Create DMG
        logger.info("Running hdiutil to create DMG...")
        result = subprocess.run(
            [
                "hdiutil", "create",
                "-volname", volume_name,
                "-srcfolder", str(staging),
                "-ov",  # Overwrite
                "-format", "UDZO",  # Compressed
                str(output_path),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error(f"hdiutil failed:\n{result.stdout}\n{result.stderr}")
            raise RuntimeError("DMG creation failed")

    logger.info(f"DMG created: {output_path}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Create macOS DMG installer")
    parser.add_argument(
        "--version",
        help="Override app version (default: read from pyproject.toml)",
    )
    parser.add_argument(
        "--app-bundle",
        default=f"build/{APP_NAME}.app",
        help="Path to the .app bundle",
    )
    parser.add_argument(
        "--output-dir",
        default="dist",
        help="Output directory for the DMG",
    )
    args = parser.parse_args()

    project_root = get_project_root()
    version = args.version or get_version_from_pyproject()
    app_bundle = project_root / args.app_bundle
    output_dir = project_root / args.output_dir

    logger.info(f"Creating DMG for {APP_NAME} v{version}")

    # Verify app bundle exists
    if not app_bundle.exists():
        logger.error(f"App bundle not found: {app_bundle}")
        logger.error("Run build_macos.py first to create the app bundle")
        return 1

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create DMG
    dmg_path = output_dir / f"{APP_NAME}-{version}.dmg"
    volume_name = f"{APP_NAME} {version}"

    try:
        create_dmg(app_bundle, dmg_path, volume_name)
    except RuntimeError:
        return 1

    logger.info(f"DMG created: {dmg_path}")
    logger.info(f"To test: open {dmg_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
