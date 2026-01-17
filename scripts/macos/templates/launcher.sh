#!/bin/bash

BUNDLE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RESOURCES="$BUNDLE_DIR/Resources"

export PYTHON_HOME="$RESOURCES/runtime/python"
export PATH="$PYTHON_HOME/bin:$PATH"
export PYTHONPATH="$RESOURCES/app"

exec "$PYTHON_HOME/bin/python3" -m anonymizer.ports.gui.app "$@"
