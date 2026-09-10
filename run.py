"""CLI entry point — the synthesis step of the benchmark.

Examples:
    python run.py                                   # defaults: gtts, lang=en
    python run.py --names data/names.csv --lang en  # explicit
    python run.py --engine gtts --lang yo           # try a Yoruba voice

Run `python run.py --help` to see all options.
"""
import argparse
from pathlib import Path

from ttsbench.dataset import load_names
from ttsbench.engines import ENGINES
from ttsbench.synth import synthesize_all


def main():
    parser = argparse.ArgumentParser(
        description="AI name-pronunciation fairness benchmark — synthesis step")
    parser.add_argument("--names", type=Path, default="data/names.csv",
                        help="CSV of names to synthesize (default: data/names.csv)")
    parser.add_argument("--engine", choices=sorted(ENGINES), default="gtts",
                        help="which TTS engine to use (default: gtts)")
    parser.add_argument("--lang", default="en",
                        help="TTS voice language code (default: en)")
    parser.add_argument("--out", type=Path, default="outputs",
                        help="output directory (default: outputs)")
    args = parser.parse_args()

    names = load_names(args.names)
    engine = ENGINES[args.engine](lang=args.lang)

    print(f"Synthesizing {len(names)} names | engine={engine.name} "
          f"({engine.version}) | lang={args.lang}\n")
    manifest_path, rows = synthesize_all(names, engine, args.out)

    ok = sum(r["status"] == "ok" for r in rows)
    print(f"\nDone: {ok}/{len(rows)} succeeded.")
    print(f"Audio:    {args.out}/audio/")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
