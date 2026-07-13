"""Pytest configuration for Ecological Environment Monitoring System"""

import sys
from pathlib import Path

# Add project root to Python path (before site-packages)
project_root = Path(__file__).parent.parent
project_root_str = str(project_root)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

# CRITICAL: Ensure local Hermes framework is used instead of system-wide installation
# The editable install hook must not override our local copy
# Remove any Hermes modules that might have been imported from system installation
system_hermes_modules = [
    'run_agent',
    'agent',
    'agent.agent_init',
    'agent.system_prompt',
    'agent.prompt_builder',
    'agent.identity_loader',
    'agent.iteration_budget',
    'hermes_constants',
]

for module in list(sys.modules.keys()):
    # Remove any modules that came from the system Hermes installation
    if 'hermes' in module.lower() or module in system_hermes_modules:
        try:
            mod_file = sys.modules[module].__file__
            if mod_file and 'D:\\Hermes\\hermes-agent' in mod_file:
                del sys.modules[module]
                print(f"Removed system Hermes module: {module}")
        except (AttributeError, KeyError):
            pass

# Add scripts directory to path for dynamic imports
scripts_path = project_root / 'workspace' / 'skills' / 'orchestrator-core' / 'scripts'
if str(scripts_path) not in sys.path:
    sys.path.insert(0, str(scripts_path))
