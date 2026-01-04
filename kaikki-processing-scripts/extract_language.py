#!/usr/bin/env python3
"""
Extract entries for a specific language from kaikki raw dump.

Usage:
    python extract_language.py <lang_code> [--input PATH] [--output PATH]

Examples:
    python extract_language.py fr                    # French
    python extract_language.py es                    # Spanish
    python extract_language.py de                    # German
    python extract_language.py fr --output data/french.jsonl
"""

import argparse
import gzip
import json
import sys
from pathlib import Path

# Common language codes and names
LANGUAGES = {
    'fr': 'French',
    'es': 'Spanish',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'nl': 'Dutch',
    'ru': 'Russian',
    'ja': 'Japanese',
    'zh': 'Chinese',
    'ko': 'Korean',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'sv': 'Swedish',
    'pl': 'Polish',
    'la': 'Latin',
    'grc': 'Ancient Greek',
    'en': 'English',
}

def extract_language(input_path: Path, output_path: Path, lang_code: str, lang_name: str = None):
    """Extract all entries for a language from the raw dump."""

    if lang_name is None:
        lang_name = LANGUAGES.get(lang_code, lang_code)

    print(f"Extracting {lang_name} ({lang_code}) entries...")
    print(f"  Input:  {input_path}")
    print(f"  Output: {output_path}")

    count = 0
    pos_counts = {}

    # Auto-detect gzipped input
    open_func = gzip.open if str(input_path).endswith('.gz') else open

    with open_func(input_path, 'rt', encoding='utf-8') as infile:
        with open(output_path, 'w', encoding='utf-8') as outfile:
            for line in infile:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Match by lang_code (more reliable) or lang name
                if entry.get('lang_code') == lang_code or entry.get('lang') == lang_name:
                    outfile.write(line)
                    count += 1

                    # Track POS distribution
                    pos = entry.get('pos', 'unknown')
                    pos_counts[pos] = pos_counts.get(pos, 0) + 1

                    if count % 50000 == 0:
                        print(f"  {count:,} entries extracted...")

    print(f"\nDone! Extracted {count:,} {lang_name} entries")
    print(f"\nPOS distribution:")
    for pos, cnt in sorted(pos_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {pos}: {cnt:,}")

    # Get file size
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\nOutput file size: {size_mb:.1f} MB")

    return count, pos_counts

def main():
    parser = argparse.ArgumentParser(description='Extract language entries from kaikki dump')
    parser.add_argument('lang_code', help='Language code (e.g., fr, es, de)')
    # Default to .gz file if it exists, otherwise uncompressed
    default_gz = Path(__file__).parent.parent / 'kaikki/en-raw-data-gz/raw-wiktextract-data.jsonl.gz'
    default_plain = Path(__file__).parent.parent / 'kaikki/en-raw-data/raw-wiktextract-data.jsonl'
    default_input = default_gz if default_gz.exists() else default_plain

    parser.add_argument('--input', '-i', type=Path, default=default_input,
                        help='Path to raw kaikki dump (.jsonl or .jsonl.gz)')
    parser.add_argument('--output', '-o', type=Path, default=None,
                        help='Output path (default: data/<lang_code>.jsonl)')
    parser.add_argument('--lang-name', help='Language name (auto-detected from code)')

    args = parser.parse_args()

    if args.output is None:
        args.output = Path(__file__).parent.parent / f'data/{args.lang_code}.jsonl'

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    extract_language(args.input, args.output, args.lang_code, args.lang_name)

if __name__ == '__main__':
    main()
