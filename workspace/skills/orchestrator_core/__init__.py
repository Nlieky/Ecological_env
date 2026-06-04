"""Alias for orchestrator-core to allow imports with underscores"""

# Import everything from the actual orchestrator-core package
from importlib import import_module
import sys

# Import the actual module and inject it into sys.modules with the underscore name
try:
    orchestrator_core = import_module('workspace.skills.orchestrator-core')
    sys.modules['workspace.skills.orchestrator_core'] = orchestrator_core
    sys.modules['workspace.skills.orchestrator_core.scripts'] = import_module('workspace.skills.orchestrator-core.scripts')
except ImportError:
    pass
