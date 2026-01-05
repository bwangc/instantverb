#!/usr/bin/env python3
"""
Build English → French reverse index from dictionary.

Prioritizes:
1. Single-word French entries over phrases
2. Glosses that start with the English word
3. Common/frequent French words (using frequency list)

Usage:
    python build_en_fr_index.py
"""

import json
import gzip
import re
from pathlib import Path
from collections import defaultdict

def extract_english_words(gloss):
    """Extract meaningful English words from a gloss."""
    # Remove parenthetical content like "(something)"
    gloss = re.sub(r'\([^)]*\)', '', gloss)
    # Remove quotes
    gloss = re.sub(r'["\']', '', gloss)
    # Split on common delimiters
    gloss = re.sub(r'[,;:]', ' ', gloss)

    words = []
    for word in gloss.lower().split():
        # Skip very short words and common particles
        if len(word) < 2:
            continue
        if word in ('to', 'a', 'an', 'the', 'of', 'or', 'be', 'is', 'as', 'in', 'on', 'at', 'by', 'for', 'it', 'up'):
            continue
        # Clean punctuation
        word = re.sub(r'[^a-z]', '', word)
        if len(word) >= 2:
            words.append(word)
    return words

def load_frequency_ranks(base_dir):
    """Load French word frequency ranks (lower = more common)."""
    freq_path = base_dir / 'french_10k_cleaned.tsv'
    if not freq_path.exists():
        return {}

    ranks = {}
    with open(freq_path, 'r', encoding='utf-8') as f:
        next(f)  # Skip header
        for i, line in enumerate(f):
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                ranks[parts[1].lower()] = i
    return ranks

def main():
    base_dir = Path(__file__).parent.parent

    # Load frequency list for scoring
    print("Loading frequency list...")
    freq_ranks = load_frequency_ranks(base_dir)
    print(f"  Loaded {len(freq_ranks)} frequency ranks")

    # Load full dictionary
    print("Loading dictionary...")
    with gzip.open(base_dir / 'web/data/fr-dict.json.gz', 'rt', encoding='utf-8') as f:
        full_dict = json.load(f)

    # Build reverse index with scoring
    # Structure: english_word -> [(french_word, score), ...]
    print("Building reverse index...")
    en_to_fr = defaultdict(list)

    for fr_word, entries in full_dict['words'].items():
        # Skip multi-word French entries (phrases) - allow up to 2 words for phrasal verbs
        word_count = len(fr_word.split())
        if word_count > 2:
            continue
        # Skip entries with special characters (likely junk)
        if any(c in fr_word for c in ['/', '(', ')']):
            continue

        for entry in entries:
            pos = entry.get('pos', '')
            senses = entry.get('senses', [])
            for sense_idx, sense in enumerate(senses):
                gloss = sense.get('gloss', '')
                if not gloss:
                    continue

                # Extract English words
                en_words = extract_english_words(gloss)
                gloss_lower = gloss.lower()

                for i, en_word in enumerate(en_words):
                    # Calculate relevance score
                    score = 0

                    # BIG bonus for frequency (most important factor)
                    # Top 1000 words get 200+ points, top 10k get 100+ points
                    if fr_word in freq_ranks:
                        rank = freq_ranks[fr_word]
                        score += max(0, 300 - rank // 10)  # Top words get up to 300

                    # Bonus for being at the start of gloss (must be complete word)
                    # Match "to speak" but not "to speaker" or "to see oneself"
                    start_patterns = [
                        f'^{en_word}[,;: (]',     # "speak, talk" or "speak (verb)"
                        f'^{en_word}$',            # just "speak"
                        f'^to {en_word}[,;: (]',  # "to speak, talk" or "to see (visually)"
                        f'^to {en_word}$',         # just "to speak"
                    ]
                    # Exclude reflexive patterns and phrasal verbs
                    # "to see oneself", "to find out", "to give up" etc.
                    phrasal = re.match(f'^to {en_word} (oneself|yourself|himself|herself|itself|ourselves|themselves|out|up|down|in|off|on|away|back|over|around|about|through)\\b', gloss_lower)
                    if not phrasal and any(re.match(p, gloss_lower) for p in start_patterns):
                        # Extra bonus if this is the ONLY meaning (not "to eat; to drink")
                        # Semicolons separate different meanings, commas are usually synonyms
                        # But semicolons inside parentheses are just elaboration
                        gloss_no_parens = re.sub(r'\([^)]*\)', '', gloss)
                        if ';' not in gloss_no_parens:
                            score += 200  # Very specific translation
                        else:
                            score += 100  # Primary but not sole meaning
                    elif i < 3:  # Early in the gloss
                        score += 50

                    # Bonus for first sense (primary meaning)
                    if sense_idx == 0:
                        score += 50

                    # Bonus for single-word French
                    if word_count == 1:
                        score += 30

                    # Bonus for common POS (verb, noun, adj)
                    if pos in ('verb', 'noun', 'adj'):
                        score += 20

                    en_to_fr[en_word].append((fr_word, score))

    # Deduplicate and sort by score
    print("Sorting and deduplicating...")
    final_index = {}
    for en_word, fr_list in en_to_fr.items():
        # Group by French word, keep max score
        best_scores = {}
        for fr_word, score in fr_list:
            if fr_word not in best_scores or score > best_scores[fr_word]:
                best_scores[fr_word] = score

        # Sort by score descending, limit to top 10
        sorted_fr = sorted(best_scores.items(), key=lambda x: -x[1])[:10]
        final_index[en_word] = [fr for fr, _ in sorted_fr]

    print(f"Index has {len(final_index)} English words")

    # Show sample
    print("\nSample entries:")
    for word in ['speak', 'eat', 'house', 'beautiful', 'love']:
        if word in final_index:
            print(f"  {word}: {final_index[word][:5]}")

    # Write compressed output
    output_path = base_dir / 'web/data/en-fr.json.gz'
    print(f"\nWriting to {output_path}...")
    with gzip.open(output_path, 'wt', encoding='utf-8') as f:
        json.dump(final_index, f, ensure_ascii=False, separators=(',', ':'))

    size_kb = output_path.stat().st_size / 1024
    print(f"Done! Output size: {size_kb:.1f} KB")

if __name__ == '__main__':
    main()
