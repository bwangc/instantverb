#!/usr/bin/env python3
"""
Build a clean dictionary database from extracted language JSONL.

Usage:
    python build_database.py <lang_code> [--input PATH] [--output PATH]

Examples:
    python build_database.py fr
    python build_database.py fr --output data/french-dict.json
"""

import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict

def simplify_entry(entry: dict) -> dict:
    """Extract only the fields we need for the dictionary."""
    result = {
        'word': entry.get('word'),
        'pos': entry.get('pos'),
    }

    # Senses (definitions)
    senses = []
    for sense in entry.get('senses', []):
        # Skip Louisiana-specific definitions
        if 'Louisiana' in sense.get('tags', []):
            continue
        s = {}
        if 'glosses' in sense:
            s['gloss'] = sense['glosses'][0] if sense['glosses'] else None
        if 'tags' in sense:
            s['tags'] = [t for t in sense['tags'] if t != 'Louisiana']
        if 'examples' in sense:
            examples = []
            for ex in sense['examples'][:2]:  # Limit to 2 examples
                e = {'text': ex.get('text')}
                if 'english' in ex:
                    e['en'] = ex['english']
                elif 'translation' in ex:
                    e['en'] = ex['translation']
                if e.get('text'):
                    examples.append(e)
            if examples:
                s['examples'] = examples
        if s.get('gloss'):
            senses.append(s)

    if senses:
        result['senses'] = senses

    # Pronunciation (IPA only, skip audio for now)
    for sound in entry.get('sounds', []):
        if 'ipa' in sound:
            result['ipa'] = sound['ipa']
            break

    # Audio URL (first one only)
    for sound in entry.get('sounds', []):
        if 'mp3_url' in sound:
            result['audio'] = sound['mp3_url']
            break

    # Etymology
    if 'etymology_text' in entry:
        result['etymology'] = entry['etymology_text']

    # Forms (for verbs, adjectives, nouns)
    if entry.get('pos') in ('verb', 'adj', 'noun') and 'forms' in entry:
        forms = []
        for form in entry['forms']:
            if 'form' in form:
                # Skip meta entries
                tags = form.get('tags', [])
                if any(t in tags for t in ['table-tags', 'inflection-template']):
                    continue
                if 'multiword-construction' in tags:
                    continue
                f = {'form': form['form']}
                if tags:
                    f['tags'] = tags
                if 'ipa' in form:
                    f['ipa'] = form['ipa']
                forms.append(f)
        if forms:
            result['forms'] = forms

    # Gender for nouns
    if entry.get('pos') == 'noun':
        for cat in entry.get('categories', []):
            if 'masculine' in cat.lower():
                result['gender'] = 'm'
                break
            elif 'feminine' in cat.lower():
                result['gender'] = 'f'
                break

    # Auxiliary and irregularity for verbs
    if entry.get('pos') == 'verb':
        for cat in entry.get('categories', []):
            if 'verbs taking être as auxiliary' in cat.lower():
                result['aux'] = 'être'
            if cat == 'French irregular verbs':
                result['irregular'] = True

    return result

def build_database(input_path: Path, output_path: Path, lang_code: str):
    """Build dictionary database from extracted JSONL."""

    print(f"Building database from {input_path}...")

    # Group entries by word
    words = defaultdict(list)
    count = 0

    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            word = entry.get('word', '').lower()
            if not word:
                continue

            # Skip character entries
            if entry.get('pos') == 'character':
                continue

            # Skip entries where all senses are abbreviations
            senses = entry.get('senses', [])
            if senses and all('abbreviation' in s.get('glosses', [''])[0].lower() for s in senses):
                continue

            # Skip "form-of" entries (e.g., "vis" as verb form of vivre)
            # These just say "inflection of X" rather than actual definitions
            # But keep form-of for determiners and pronouns (vos, mes, ceux, etc.)
            pos = entry.get('pos', '')
            if pos not in ('det', 'pron'):
                is_form_of = False
                for sense in entry.get('senses', []):
                    if 'form-of' in sense.get('tags', []):
                        is_form_of = True
                        break
                if is_form_of:
                    continue

            simplified = simplify_entry(entry)
            if simplified.get('senses'):  # Only keep entries with definitions
                words[word].append(simplified)
                count += 1

            if count % 50000 == 0:
                print(f"  Processed {count:,} entries...")

    print(f"\nProcessed {count:,} entries into {len(words):,} unique words")

    # Build output structure
    database = {
        'lang': lang_code,
        'version': '1.0',
        'entry_count': count,
        'word_count': len(words),
        'words': dict(words)
    }

    # Write output
    print(f"Writing to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(database, f, ensure_ascii=False, separators=(',', ':'))

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"Done! Output size: {size_mb:.1f} MB")

    return database

def main():
    parser = argparse.ArgumentParser(description='Build dictionary database from extracted JSONL')
    parser.add_argument('lang_code', help='Language code (e.g., fr, es, de)')
    parser.add_argument('--input', '-i', type=Path, default=None,
                        help='Input JSONL path (default: data/<lang_code>.jsonl)')
    parser.add_argument('--output', '-o', type=Path, default=None,
                        help='Output JSON path (default: data/<lang_code>-dict.json)')

    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent / 'data'

    if args.input is None:
        args.input = base_dir / f'{args.lang_code}.jsonl'
    if args.output is None:
        args.output = base_dir / f'{args.lang_code}-dict.json'

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        print(f"Run extract_language.py {args.lang_code} first", file=sys.stderr)
        sys.exit(1)

    build_database(args.input, args.output, args.lang_code)

if __name__ == '__main__':
    main()
