from __future__ import annotations
import argparse
from .settings import load_settings
from .pipeline import run

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--year", type=int, default=2025)
    args = p.parse_args()
    settings = load_settings(args.config)
    result = run(settings, args.year)
    print("✅ Completed. Table:", result["table"])

if __name__ == "__main__":
    main()
