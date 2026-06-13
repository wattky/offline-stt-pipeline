"""
Build script for creating cross-platform standalone executables.
Uses PyInstaller to bundle the application with all dependencies.

Usage:
    python build.py              # Build for current platform
    python build.py --onefile    # Single file executable
    python build.py --clean      # Clean build artifacts first
"""

import os
import sys
import shutil
import platform
import subprocess
import argparse
from pathlib import Path


def get_platform_name() -> str:
    """Get a normalized platform name."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "darwin":
        return f"macos-{machine}"
    elif system == "windows":
        return f"windows-{machine}"
    else:
        return f"linux-{machine}"


def clean_build():
    """Remove previous build artifacts."""
    dirs_to_clean = ["build", "dist", "__pycache__"]
    for d in dirs_to_clean:
        path = Path(d)
        if path.exists():
            shutil.rmtree(path)
            print(f"  Cleaned: {d}/")
    
    # Remove .spec files
    for spec in Path(".").glob("*.spec"):
        spec.unlink()
        print(f"  Cleaned: {spec}")


def build(onefile: bool = False, clean: bool = False):
    """Build the application using PyInstaller."""
    
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    if clean:
        print("Cleaning previous builds...")
        clean_build()
        print()
    
    platform_name = get_platform_name()
    print(f"Building Offline STT Pipeline for {platform_name}...")
    print()
    
    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "offline-stt-pipeline",
        "--noconfirm",
        "--clean",
    ]
    
    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")
    
    # Add icon based on platform
    icon_path = project_dir / "assets" / "icon.ico"
    if icon_path.exists():
        cmd.extend(["--icon", str(icon_path)])
    
    # Add data files (UI templates and static files)
    ui_templates = project_dir / "src" / "ui" / "templates"
    ui_static = project_dir / "src" / "ui" / "static"
    
    separator = ";" if platform.system() == "Windows" else ":"
    
    if ui_templates.exists():
        cmd.extend(["--add-data", f"{ui_templates}{separator}src/ui/templates"])
    if ui_static.exists():
        cmd.extend(["--add-data", f"{ui_static}{separator}src/ui/static"])
    
    # Hidden imports that PyInstaller might miss
    hidden_imports = [
        "faster_whisper",
        "ctranslate2",
        "huggingface_hub",
        "tokenizers",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
    ]
    
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])
    
    # Entry point
    cmd.append("run.py")
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode == 0:
        print()
        print("=" * 60)
        print(f"  BUILD SUCCESSFUL!")
        print(f"  Platform: {platform_name}")
        print(f"  Output:   dist/offline-stt-pipeline/")
        print("=" * 60)
    else:
        print()
        print("BUILD FAILED!")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Build Offline STT Pipeline")
    parser.add_argument("--onefile", action="store_true", help="Create single-file executable")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts first")
    args = parser.parse_args()
    
    build(onefile=args.onefile, clean=args.clean)


if __name__ == "__main__":
    main()
