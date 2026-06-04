"""Pytest configuration for Ecological Environment Monitoring System"""

import sys
from pathlib import Path
import importlib.util

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Add scripts directory to path for dynamic imports
scripts_path = project_root / 'workspace' / 'skills' / 'orchestrator-core' / 'scripts'
if str(scripts_path) not in sys.path:
    sys.path.insert(0, str(scripts_path))
