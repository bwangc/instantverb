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
        if word in ('to', 'a', 'an', 'the', 'of', 'or', 'as', 'in', 'on', 'at', 'by', 'for', 'it', 'up'):
            continue
        # Clean punctuation
        word = re.sub(r'[^a-z]', '', word)
        if len(word) >= 2:
            words.append(word)
    return words

# Common English synonyms - bidirectional mapping
SYNONYM_GROUPS = [
    ('start', 'begin', 'commence'),
    ('end', 'finish', 'terminate', 'conclude'),
    ('stop', 'halt', 'cease'),
    ('big', 'large', 'great'),
    ('small', 'little', 'tiny'),
    ('fast', 'quick', 'rapid'),
    ('slow', 'sluggish'),
    ('happy', 'glad', 'joyful'),
    ('sad', 'unhappy', 'sorrowful'),
    ('beautiful', 'pretty', 'lovely', 'gorgeous', 'handsome', 'attractive'),
    ('ugly', 'hideous'),
    ('good', 'fine', 'nice'),
    ('bad', 'poor', 'terrible'),
    ('speak', 'talk', 'converse'),
    ('walk', 'stroll'),
    ('run', 'sprint', 'dash'),
    ('buy', 'purchase'),
    ('sell', 'vend'),
    ('see', 'view', 'observe'),
    ('hear', 'listen'),
    ('smell', 'sniff'),
    ('eat', 'consume', 'devour'),
    ('drink', 'sip', 'gulp'),
    ('give', 'donate', 'grant'),
    ('take', 'grab', 'seize'),
    ('make', 'create', 'produce'),
    ('break', 'shatter', 'smash'),
    ('fix', 'repair', 'mend'),
    ('help', 'assist', 'aid'),
    ('hurt', 'injure', 'harm'),
    ('love', 'adore'),
    ('hate', 'detest', 'loathe'),
    ('want', 'desire', 'wish'),
    ('need', 'require'),
    ('know', 'understand', 'comprehend'),
    ('think', 'believe', 'consider'),
    ('remember', 'recall', 'recollect'),
    ('forget', 'overlook'),
    ('find', 'discover', 'locate'),
    ('lose', 'misplace'),
    ('search', 'seek', 'look for'),
    ('show', 'display', 'exhibit'),
    ('hide', 'conceal'),
    ('open', 'unlock'),
    ('close', 'shut'),
    ('answer', 'reply', 'respond'),
    ('ask', 'inquire', 'question'),
    ('tell', 'inform', 'notify'),
    ('cry', 'weep', 'sob'),
    ('laugh', 'chuckle', 'giggle'),
    ('sleep', 'slumber', 'rest'),
    ('wake', 'awaken', 'rouse'),
    ('live', 'exist', 'dwell'),
    ('die', 'perish', 'expire'),
    ('clean', 'wash', 'cleanse'),
    ('dirty', 'soil', 'stain'),
    ('bike', 'bicycle', 'cycle'),
    ('car', 'automobile', 'vehicle'),
    ('plane', 'airplane', 'aircraft'),
    ('home', 'house', 'dwelling'),
    ('room', 'chamber'),
]

def build_synonym_map():
    """Build bidirectional synonym lookup."""
    syn_map = {}
    for group in SYNONYM_GROUPS:
        for word in group:
            syn_map[word] = set(group) - {word}
    return syn_map

SYNONYMS = build_synonym_map()

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
                    # Also add synonyms of this word with a penalty
                    words_to_index = [(en_word, 0)]  # (word, penalty)
                    if en_word in SYNONYMS:
                        for syn in SYNONYMS[en_word]:
                            words_to_index.append((syn, 80))  # Penalty for synonym match

                    for index_word, syn_penalty in words_to_index:
                        # Calculate relevance score
                        score = -syn_penalty  # Start with synonym penalty (0 for direct match)

                        # PENALTY for interjections (less useful as translations)
                        # e.g., "stop!" for "stop" should prefer "arrêter"
                        if pos == 'intj':
                            score -= 150

                        # PENALTY for loan words (French word same as English query)
                        # But only if not a common French word (in frequency list)
                        # This penalizes "stop", "bicycle" etc. while allowing "fruit", "table"
                        if fr_word.lower() == index_word.lower():
                            if fr_word not in freq_ranks:
                                score -= 100  # Uncommon loan word
                            # Common words like "fruit", "table" get no penalty

                        # BIG bonus for frequency (most important factor)
                        # Top 1000 words get 200+ points, top 10k get 100+ points
                        if fr_word in freq_ranks:
                            rank = freq_ranks[fr_word]
                            score += max(0, 300 - rank // 10)

                        # Bonus for being first extracted word in gloss
                        if i == 0:
                            score += 50

                        # Bonus for being at the start of gloss (must be complete word)
                        # Match "to speak" but not "to speaker" or "to see oneself"
                        # Use en_word (the word actually in gloss) for pattern matching
                        start_patterns = [
                            f'^{en_word}[,;: (]',     # "speak, talk" or "speak (verb)"
                            f'^{en_word}$',            # just "speak"
                            f'^to {en_word}[,;: (]',  # "to speak, talk" or "to see (visually)"
                            f'^to {en_word}$',         # just "to speak"
                        ]
                        # Also match after semicolon: "to purchase; buy" -> matches "buy"
                        alt_patterns = [
                            f'; {en_word}[,;: (]',    # "; buy, purchase"
                            f'; {en_word}$',           # "; buy"
                            f'; to {en_word}[,;: (]', # "; to buy, purchase"
                            f'; to {en_word}$',        # "; to buy"
                        ]
                        # Exclude reflexive patterns, phrasal verbs, and verb+gerund
                        # "to see oneself", "to find out", "to give up", "to find each other", "to stop carrying" etc.
                        phrasal = re.match(f'^to {en_word} (oneself|yourself|himself|herself|itself|ourselves|themselves|each other|one another|out|up|down|in|off|on|away|back|over|around|about|through)\\b', gloss_lower)
                        gerund = re.match(f'^to {en_word} \\w+ing\\b', gloss_lower)

                        is_start_match = not phrasal and not gerund and any(re.match(p, gloss_lower) for p in start_patterns)
                        is_alt_match = any(re.search(p, gloss_lower) for p in alt_patterns)

                        if is_start_match or is_alt_match:
                            # Extra bonus if this is the ONLY meaning (not "to eat; to drink")
                            # Semicolons separate different meanings, commas are usually synonyms
                            # But semicolons inside parentheses are just elaboration
                            gloss_no_parens = re.sub(r'\([^)]*\)', '', gloss)

                            # Penalize specialized usage indicated by contextual parentheticals
                            # e.g., "hello (when answering...)", "find (again)" but not "to come (to move...)"
                            paren_match = re.search(r'\([^)]*\b(when|used|especially|specifically|in|formal|informal|phone|slang|again|back)\b[^)]*\)', gloss_lower)

                            # Calculate base match bonus (reduced for alt matches and later senses)
                            if is_start_match:
                                base_bonus = 200 if ';' not in gloss_no_parens else 100
                            else:  # alt_match (after semicolon)
                                base_bonus = 150 if ';' not in gloss_no_parens else 75

                            # Reduce bonus for later senses (secondary meanings shouldn't beat primary)
                            if sense_idx >= 2:
                                base_bonus = base_bonus // 2
                            elif sense_idx == 1:
                                base_bonus = base_bonus * 3 // 4

                            if paren_match:
                                score += base_bonus // 4  # Specialized usage gets much less
                            else:
                                score += base_bonus
                        elif i < 3:  # Early in the gloss
                            score += 50

                        # Bonus for first sense (primary meaning)
                        # This is important - secondary senses shouldn't beat primary meanings
                        if sense_idx == 0:
                            score += 100
                        elif sense_idx == 1:
                            score += 50
                        elif sense_idx >= 5:
                            score -= 50  # Penalize very late senses (obscure meanings)

                        # Bonus for single-word French
                        if word_count == 1:
                            score += 30

                        # Bonus for verbs when gloss starts with "to" (verb context)
                        if pos == 'verb' and gloss_lower.startswith('to '):
                            score += 30
                        elif pos in ('noun', 'adj'):
                            score += 20
                            # Penalize compound nouns where the word is just a modifier
                            # e.g., "stop sign", "fire engine", "water bottle"
                            compound_suffixes = ['sign', 'mark', 'board', 'line', 'light', 'engine',
                                                'bottle', 'machine', 'box', 'man', 'woman', 'house',
                                                'room', 'car', 'boat', 'plane', 'train', 'station']
                            gloss_words = gloss_lower.split()
                            if len(gloss_words) == 2 and gloss_words[1] in compound_suffixes:
                                score -= 150  # Heavy penalty for compound modifier

                        en_to_fr[index_word].append((fr_word, score))

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
