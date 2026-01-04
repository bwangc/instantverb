#!/usr/bin/env python3
"""
Build 10k common word dictionary from full dictionary and frequency list.

Usage:
    python build_10k.py
"""

import json
from pathlib import Path

def main():
    base_dir = Path(__file__).parent.parent

    # Load full dictionary
    print("Loading full dictionary...")
    with open(base_dir / 'data/fr-dict.json', 'r', encoding='utf-8') as f:
        full_dict = json.load(f)

    # Load frequency list
    print("Loading frequency list...")
    freq_words = []
    with open(base_dir / 'french_10k_cleaned.tsv', 'r', encoding='utf-8') as f:
        next(f)  # Skip header
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                freq_words.append(parts[1].lower())

    print(f"Frequency list has {len(freq_words)} words")

    # Build 10k dictionary (preserving frequency order)
    words_10k = {}
    found = 0
    missing = []

    for word in freq_words:
        if word in full_dict['words']:
            words_10k[word] = full_dict['words'][word]
            found += 1
        else:
            missing.append(word)

    print(f"Found {found} words in dictionary")
    print(f"Missing {len(missing)} words")
    if missing[:10]:
        print(f"First 10 missing: {missing[:10]}")

    # Add s'en [verb] entries if base verb is in 10k
    sen_added = 0
    for word in full_dict['words']:
        if word.startswith("s'en "):
            # Check if the base verb (first word after s'en) is in 10k
            parts = word.split()
            if len(parts) >= 2:
                base = parts[1]  # e.g., "aller" from "s'en aller"
                if base in words_10k and word not in words_10k:
                    words_10k[word] = full_dict['words'][word]
                    sen_added += 1

    if sen_added:
        print(f"Added {sen_added} s'en [verb] entries")

    # Build output
    output = {
        'lang': 'fr',
        'version': '1.0',
        'word_count': len(words_10k),
        'words': words_10k
    }

    # Write output
    output_path = base_dir / 'data/fr-10k.json'
    print(f"Writing to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, separators=(',', ':'))

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"Done! Output size: {size_mb:.1f} MB")

    # Also build forms index
    print("\nBuilding forms index...")
    forms = {}
    for word, entries in words_10k.items():
        for entry in entries:
            if entry.get('pos') == 'verb' and 'forms' in entry:
                for form_data in entry['forms']:
                    form = form_data.get('form', '').lower()
                    if form and form != word:
                        if form not in forms:
                            forms[form] = []
                        if word not in forms[form]:
                            forms[form].append(word)

    forms_output = {'forms': forms}
    forms_path = base_dir / 'data/fr-10k-forms.json'
    with open(forms_path, 'w', encoding='utf-8') as f:
        json.dump(forms_output, f, ensure_ascii=False, separators=(',', ':'))

    forms_size = forms_path.stat().st_size / (1024 * 1024)
    print(f"Forms index: {len(forms)} forms, {forms_size:.1f} MB")

if __name__ == '__main__':
    main()
