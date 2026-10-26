"""Read-only drift check; update the reviewed JSON artifact using apply_patch."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shared.assistant.contract import contract_document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    expected = contract_document()
    if args.check:
        try:
            actual = json.loads((ROOT / 'frontend/src/assistant/contract.generated.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            actual = None
        if actual != expected:
            print('Assistant contract drift; review and regenerate contract.generated.json.')
            return 1
        print('Assistant contract is consistent.')
        return 0
    print(json.dumps(expected, ensure_ascii=True, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
