# Git Sync Guide: Server to Local Transfer

This guide documents how to sync the server-side development work to your local machine and verify that local Claude can understand all changes.

## Quick Summary

The server has completed a major architecture refactor (6-agent → 4-agent) with new modules. All changes are committed to git. This guide ensures smooth transfer to local.

---

## Pre-Sync Checklist (Server Side)

Run these checks on the server before syncing:

```bash
cd /home/NYJ2025/Ecological_env

# 1. Check all changes are committed
git status

# 2. Verify all tests pass
python -m pytest tests/ -v

# 3. Check key files exist
ls -la CHANGELOG.md
ls -la shared/configs/agent_registry.yaml
ls -la shared/configs/consensus_config.yaml
ls -la shared/configs/rule_config.yaml
ls -la subagents/multi-dimensional-data-perception-agent/IDENTITY.md
ls -la subagents/disposition-execution-agent/IDENTITY.md
```

---

## Sync Methods

### Method 1: Git Push/Pull (Recommended)

**On Server:**
```bash
cd /home/NYJ2025/Ecological_env
# Add remote if not already added
git remote add origin <your-github-repo-url>
# Push changes
git push origin main
```

**On Local:**
```bash
cd /path/to/local/Ecological_env
# Pull changes
git pull origin main
# Or if local has uncommitted work:
git stash
git pull origin main
git stash pop
```

### Method 2: Direct Copy (If no git remote)

**On Server:**
```bash
cd /home/NYJ2025
# Create a compressed archive
tar -czf ecological_env_server_backup.tar.gz Ecological_env/
# Transfer via scp or download
```

**On Local:**
```bash
# Backup existing local
mv Ecological_env Ecological_env.local.backup
# Extract server copy
tar -xzf ecological_env_server_backup.tar.gz
```

---

## Post-Sync Verification (Local Side)

After syncing, run these checks on your local machine:

### Step 1: Basic Verification

```bash
cd /path/to/local/Ecological_env

# Check git log synced correctly
git log --oneline -5

# Verify CHANGELOG.md exists
cat CHANGELOG.md | head -20
```

### Step 2: Import Tests

```bash
# Test that new modules can be imported
python -c "
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path.cwd()))

# Test ConsensusEngine import
from subagents.disposition_execution_agent.skills.disposition_executive_core.scripts import ConsensusEngine
print('✅ ConsensusEngine imports successfully')

# Test ViolationDetector import
from subagents.rule_reasoning_agent.skills.rule_reasoning_core.scripts import ViolationDetector
print('✅ ViolationDetector imports successfully')

# Test DataAcquisition import
from subagents.multi_dimensional_data_perception_agent.skills.data_perception_core.scripts import DataAcquisitionModule
print('✅ DataAcquisitionModule imports successfully')

print('All imports successful!')
"
```

### Step 3: Configuration Loading Tests

```bash
# Test configuration files
python -c "
import yaml
from pathlib import Path

configs = [
    'shared/configs/agent_registry.yaml',
    'shared/configs/consensus_config.yaml',
    'shared/configs/rule_config.yaml'
]

for config in configs:
    with open(config, 'r') as f:
        data = yaml.safe_load(f)
        print(f'✅ {config} loads successfully')

print('All configurations load successfully!')
"
```

### Step 4: Test Suite

```bash
# Run all tests
python -m pytest tests/ -v

# Expected results:
# - Consensus engine tests: 10/10 passing
# - E2E architecture tests: 4/4 passing
# - Full pipeline tests: 3/3 passing
```

---

## Troubleshooting

### Issue: Import Errors

**Problem:** `ModuleNotFoundError: No module named '...'`

**Solution:**
```bash
# Check subdirectories exist
ls -la subagents/multi-dimensional-data-perception-agent/
ls -la subagents/disposition-execution-agent/

# Verify __init__.py files exist
find subagents -name "__init__.py"
```

### Issue: Configuration Not Loading

**Problem:** `FileNotFoundError` for config files

**Solution:**
```bash
# Verify files exist
ls -la shared/configs/*.yaml

# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('shared/configs/agent_registry.yaml'))"
```

### Issue: Tests Failing

**Problem:** Tests fail after sync

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Check Python version (needs 3.10+)
python --version

# Run specific failing test with verbose output
python -m pytest tests/path/to/test.py -vv
```

---

## Verification for Local Claude

To ensure local Claude understands the new architecture:

1. **CLAUDE.md Update**: ✅ Already updated with 4-agent architecture
2. **CHANGELOG.md**: ✅ Created with comprehensive change summary
3. **Identity Files**: ✅ All agents have proper IDENTITY.md files
4. **SKILL.md Files**: ✅ All skill packages have SKILL.md documentation

**Test Local Claude Understanding:**
```bash
# On local machine, ask Claude to:
# "Explain the 4-agent architecture of this project"
# "What does ConsensusEngine do?"
# "List the modules in multi-dimensional-data-perception-agent"
```

---

## Rollback Plan

If sync causes issues:

```bash
# Rollback to previous state
git log --oneline -10  # Find pre-sync commit
git checkout <pre-sync-commit-hash>

# Or use backup
mv Ecological_env Ecological_env.broken
mv Ecological_env.local.backup Ecological_env
```

---

## Summary

✅ **Server Side Complete:**
- Architecture refactor (6-agent → 4-agent)
- New modules (ConsensusEngine, ViolationDetector, etc.)
- All tests passing
- Documentation updated (CLAUDE.md, CHANGELOG.md)

✅ **Ready for Sync:**
- All changes committed to git
- CHANGELOG.md provides comprehensive history
- Verification steps documented

📋 **Action Items:**
1. Run pre-sync checklist on server
2. Choose sync method (git push/pull recommended)
3. Run post-sync verification on local
4. Test local Claude understanding

---

**Last Updated:** 2026-06-02
**Server Commit:** 23e2516 (refactor: update integration tests for new agent architecture)
