#!/usr/bin/env python3
"""
Test suite for EN→FR reverse index quality.

Tests focus on catching genuinely bad translations, not just
validating exact expected matches (which can be subjective).

Run: python test_en_fr.py
"""

import json
import gzip
from pathlib import Path


def load_data():
    """Load index and frequency list."""
    base_dir = Path(__file__).parent.parent

    with gzip.open(base_dir / 'web/data/en-fr.json.gz', 'rt') as f:
        index = json.load(f)

    freq = set()
    with open(base_dir / 'french_10k_cleaned.tsv', 'r') as f:
        next(f)
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                word = parts[1].lower()
                freq.add(word)
                # Also add œ/oe variants (freq list uses oe, dict uses œ)
                if 'oe' in word:
                    freq.add(word.replace('oe', 'œ'))

    return index, freq


def test_noise_words_removed(index):
    """Verify that common English function words are not indexed."""
    noise_words = [
        'did', 'does', 'has', 'is', 'are', 'was', 'were',
        'whether', 'usually', 'often', 'especially', 'particularly',
    ]

    failures = []
    for word in noise_words:
        if word in index:
            failures.append(f"{word}: should be filtered, got {index[word][:3]}")

    return "noise_words_removed", len(noise_words) - len(failures), len(noise_words), failures


def test_base_verbs_work(index):
    """Verify that base verb forms return good translations."""
    expected = {
        'do': 'faire',
        'be': 'être',
        'have': 'avoir',
        'go': 'aller',
        'come': 'venir',
        'see': 'voir',
        'know': 'savoir',
        'make': 'faire',
        'say': 'dire',
        'take': 'prendre',
        'give': 'donner',
        'get': 'obtenir',
    }

    failures = []
    passed = 0
    for en, fr in expected.items():
        results = index.get(en, [])
        if not results:
            failures.append(f"{en}: no results")
        elif fr not in results[:3]:
            failures.append(f"{en}: expected '{fr}' in top 3, got {results[:3]}")
        else:
            passed += 1

    return "base_verbs_work", passed, len(expected), failures


def test_common_words_have_results(index):
    """Verify that common English words return results."""
    common = '''
    hello goodbye yes no please thank sorry good bad big small new old
    beautiful ugly hot cold fast slow easy hard happy sad man woman child
    mother father brother sister family friend house room door window table
    chair bed book water food bread milk coffee tea car bus train plane boat
    road street city country school hospital money work time day night week
    month year sun moon star rain fire speak eat drink sleep run walk talk
    see hear think know want love help give take make go find lose win buy
    sell open close start stop read write learn teach ask answer
    '''.split()

    failures = []
    for word in common:
        if word not in index or not index[word]:
            failures.append(f"{word}: no results")

    return "common_words_have_results", len(common) - len(failures), len(common), failures


def test_top_result_quality(index, freq):
    """Check that top results are reasonable (in freq list or common patterns)."""
    common = '''
    hello goodbye good bad big small new old beautiful hot cold fast slow
    easy hard happy sad man woman child house room door window table chair
    water food bread car train city country school money work time day night
    sun moon fire speak eat drink sleep run walk see hear think know want
    love help give take make go find buy open close start stop read write
    '''.split()

    failures = []
    for word in common:
        results = index.get(word, [])
        if not results:
            continue

        top1 = results[0]
        # Check if top result is common OR if it's a phrase with a common word
        is_ok = (
            top1 in freq or
            any(part in freq for part in top1.split()) or
            top1.lower() == word.lower()  # same word (valid for table, fruit, etc)
        )

        # Also check if there's a common word in top 3
        has_common_in_top3 = any(r in freq for r in results[:3])

        if not is_ok and not has_common_in_top3:
            failures.append(f"{word}: top result '{top1}' is rare, no common in top 3: {results[:3]}")

    return "top_result_quality", len(common) - len(failures), len(common), failures


def test_conjugated_forms_filtered(index):
    """Check that problematic English conjugated forms are filtered."""
    # Conjugated forms like "does", "has" often appear in descriptive text
    # and should be filtered as stopwords. Forms like "goes", "tries" are
    # harder to filter but are a known issue - they often return noise.
    must_be_filtered = ['does', 'has', 'did', 'was', 'were']

    failures = []
    for conj in must_be_filtered:
        results = index.get(conj, [])
        if results:
            failures.append(f"{conj}: should be filtered, got {results[:3]}")

    passed = len(must_be_filtered) - len(failures)
    return "conjugated_forms_filtered", passed, len(must_be_filtered), failures


def test_no_junk_entries(index, freq):
    """Check for obviously bad entries (too short, has digits, etc)."""
    failures = []
    checked = 0

    # Single-char French words that are valid (y=there, à=to, etc)
    valid_single_chars = {'y', 'à', 'a', 'ô', 'ù'}

    # Check a sample of the index
    for en_word in list(index.keys())[:1000]:
        results = index.get(en_word, [])
        if not results:
            continue
        checked += 1

        top1 = results[0]

        # Junk patterns
        if len(top1) == 1 and top1 not in valid_single_chars and top1 not in freq:
            failures.append(f"{en_word}: single char result '{top1}'")
        elif top1.isdigit():
            failures.append(f"{en_word}: numeric result '{top1}'")

    return "no_junk_entries", checked - len(failures), checked, failures


def main():
    print("Loading data...")
    index, freq = load_data()
    print(f"  Index has {len(index)} English words")
    print(f"  Frequency list has {len(freq)} French words\n")

    tests = [
        test_noise_words_removed,
        test_base_verbs_work,
        test_common_words_have_results,
        lambda i: test_top_result_quality(i, freq),
        test_conjugated_forms_filtered,
        lambda i: test_no_junk_entries(i, freq),
    ]

    all_passed = True
    for test_fn in tests:
        name, passed, total, failures = test_fn(index)
        status = "PASS" if passed == total else "FAIL"
        print(f"{status}: {name} ({passed}/{total})")

        if failures:
            all_passed = False
            for f in failures[:5]:
                print(f"  - {f}")
            if len(failures) > 5:
                print(f"  ... and {len(failures) - 5} more")
        print()

    print("=" * 50)
    if all_passed:
        print("All tests passed!")
    else:
        print("Some tests failed - see above for details")

    return 0 if all_passed else 1


if __name__ == '__main__':
    exit(main())
