#!/bin/bash
# Offline STT Pipeline - Installation Script (Linux/macOS)
# This script installs the application and its dependencies.

set -e

echo "╔══════════════════════════════════════════════════════╗"
echo "║     Offline STT Pipeline - Installer                 ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Check Python version
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "ERROR: Python 3.10+ is required but not found."
    echo "Please install Python from https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo "ERROR: Python 3.10+ is required. Found: $PYTHON_VERSION"
    exit 1
fi

echo "Found Python $PYTHON_VERSION"
echo ""

# Create virtual environment
INSTALL_DIR="${HOME}/.local/share/offline-stt-pipeline"
VENV_DIR="${INSTALL_DIR}/venv"

echo "Installing to: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

echo "Creating virtual environment..."
$PYTHON_CMD -m venv "$VENV_DIR"

# Activate venv
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet

# Install the package
echo "Installing Offline STT Pipeline..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pip install -e "$SCRIPT_DIR" --quiet

echo ""
echo "Installation complete!"
echo ""
echo "To start the server:"
echo "  offline-stt"
echo ""
echo "Or activate the virtual environment first:"
echo "  source $VENV_DIR/bin/activate"
echo "  offline-stt --help"
echo ""

# Create a launcher script
LAUNCHER="${HOME}/.local/bin/offline-stt"
mkdir -p "$(dirname "$LAUNCHER")"
cat > "$LAUNCHER" << EOF
#!/bin/bash
source "$VENV_DIR/bin/activate"
exec python -m src.main "\$@"
EOF
chmod +x "$LAUNCHER"

echo "Launcher created at: $LAUNCHER"
echo "Make sure ~/.local/bin is in your PATH"
echo ""
echo "Quick start:"
echo "  1. Download a model:  curl -X POST http://localhost:8000/v1/models/download/base"
echo "  2. Start the server:  offline-stt"
echo "  3. Open the UI:       http://localhost:8000"
