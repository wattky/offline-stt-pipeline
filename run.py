#!/usr/bin/env python3
"""
Offline STT Pipeline - Runner Script

This is the entry point used by PyInstaller and for direct execution.
"""

import sys
from pathlib import Path

# Ensure the project root is in the path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.main import main

if __name__ == "__main__":
    main()
