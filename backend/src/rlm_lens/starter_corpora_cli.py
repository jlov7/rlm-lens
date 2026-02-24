from __future__ import annotations

import argparse
import json

from .config import load_settings
from .starter_corpora import StarterCorpusService


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage RLM-Lens starter corpora")
    parser.add_argument("command", choices=["list", "materialize"], help="Operation to run")
    parser.add_argument("--pack", default="fixture-small", help="Starter corpus pack id")
    parser.add_argument("--force", action="store_true", help="Recreate pack even if already installed")
    args = parser.parse_args()

    settings = load_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    service = StarterCorpusService(settings.data_dir)

    if args.command == "list":
        print(json.dumps(service.list_packs(), indent=2))
        return

    payload = service.materialize(pack_id=args.pack, force=args.force)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
