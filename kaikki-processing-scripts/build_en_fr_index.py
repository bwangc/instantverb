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

# Tags that indicate vulgar/offensive content in dictionary entries
# Note: 'derogatory' is too broad (638 words including bled, bœuf, aboyer)
VULGAR_TAGS = {'vulgar', 'offensive', 'slur', 'ethnic'}

# English vulgar words that unlock vulgar French results
# If someone searches these, they want the vulgar translations
VULGAR_ENGLISH = {
    # Direct vulgar words
    'fuck', 'fucking', 'fucked', 'fucker', 'shit', 'shitty', 'bullshit',
    'ass', 'asshole', 'arse', 'arsehole', 'bitch', 'whore', 'slut', 'cunt',
    'cock', 'dick', 'piss', 'pissed', 'bastard', 'damn', 'damned',
    'crap', 'crappy', 'screw', 'screwed', 'balls', 'butt', 'butthole',
    # Body parts (vulgar context)
    'penis', 'vagina', 'testicle', 'testicles', 'anus',
    # Related words
    'prostitute', 'brothel', 'whorehouse', 'pimp',
    'defecate', 'urinate', 'fart', 'cum', 'ejaculate',
    'bugger', 'bum', 'turd', 'prick', 'jerk',
}

# English words that commonly appear in explanatory gloss text but aren't translations
# These get false matches from phrases like "but did not", "whether by", "is used when"
ENGLISH_STOPWORDS = {
    # Articles and determiners
    'a', 'an', 'the', 'this', 'that', 'these', 'those',
    # Prepositions
    'of', 'in', 'on', 'at', 'by', 'for', 'to', 'from', 'with', 'into', 'onto',
    'about', 'after', 'before', 'between', 'through', 'during', 'without',
    'under', 'over', 'above', 'below', 'against', 'among', 'within',
    # Conjunctions
    'and', 'or', 'but', 'if', 'than', 'as', 'so', 'yet', 'nor',
    'whether', 'either', 'neither', 'both',
    # Pronouns (but keep who→qui, what→quoi, which→lequel)
    'it', 'its', 'he', 'she', 'they', 'we',
    # Auxiliary/modal verbs - conjugated forms are noise, but keep base forms
    # (people search "be" for être, "have" for avoir, "do" for faire)
    'is', 'are', 'was', 'were', 'been', 'being',  # but keep 'be'
    'has', 'had', 'having',  # but keep 'have'
    'does', 'did', 'doing', 'done',  # but keep 'do'
    'will', 'would', 'shall', 'should', 'may', 'might', 'must', 'can', 'could',
    # Common adverbs in explanations (but keep 'always'→toujours, 'never'→jamais)
    'not', 'also', 'often', 'usually', 'especially', 'particularly',
    'generally', 'typically', 'sometimes',
    # Other noise words
    'such', 'some', 'any', 'each', 'every', 'other', 'another',
    'up', 'out', 'off',  # phrasal verb particles
}

def extract_english_words(gloss):
    """Extract meaningful English words from a gloss."""
    # Remove parenthetical content like "(something)"
    gloss_clean = re.sub(r'\([^)]*\)', '', gloss)
    # Remove quotes
    gloss_clean = re.sub(r'["\']', '', gloss_clean)
    # Split on common delimiters
    gloss_clean = re.sub(r'[,;:]', ' ', gloss_clean)

    gloss_words = gloss_clean.split()

    words = []
    for i, word in enumerate(gloss_words):
        original_word = word  # Keep case for proper noun check
        word = word.lower()
        # Skip very short words
        if len(word) < 2:
            continue
        # Clean punctuation
        word = re.sub(r'[^a-z]', '', word)
        # Skip stopwords UNLESS it's a capitalized proper noun (e.g., "May" the month)
        # Detect proper nouns: capitalized AND either alone or all other words are lowercase
        is_proper_noun = (
            original_word and
            original_word[0].isupper() and
            len(gloss_words) == 1  # Single-word gloss like "May"
        )
        if word in ENGLISH_STOPWORDS and not is_proper_noun:
            continue
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
                word = parts[1].lower()
                ranks[word] = i
                # Also add œ/oe variants (freq list uses oe, dict uses œ)
                if 'oe' in word:
                    ranks[word.replace('oe', 'œ')] = i
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

    # Build set of vulgar French words from dictionary tags
    print("Identifying vulgar words from tags...")
    vulgar_french = set()
    for fr_word, entries in full_dict['words'].items():
        for entry in entries:
            # Check entry-level tags
            entry_tags = set(entry.get('tags', []))
            if entry_tags & VULGAR_TAGS:
                vulgar_french.add(fr_word)
                break
            # Check sense-level tags
            for sense in entry.get('senses', []):
                sense_tags = set(sense.get('tags', []))
                if sense_tags & VULGAR_TAGS:
                    vulgar_french.add(fr_word)
                    break
    print(f"  Found {len(vulgar_french)} vulgar/offensive words")

    # Pre-compute dominant POS for each word
    # e.g., "sortir" is mostly a verb (2 entries) vs noun (1 entry)
    print("Computing dominant POS...")
    dominant_pos = {}
    for fr_word, entries in full_dict['words'].items():
        pos_counts = {}
        for entry in entries:
            pos = entry.get('pos', '')
            pos_counts[pos] = pos_counts.get(pos, 0) + 1
        if pos_counts:
            # Find the most common POS
            max_pos = max(pos_counts, key=pos_counts.get)
            max_count = pos_counts[max_pos]
            # Only mark as dominant if it has more entries than others
            if max_count > 1 or len(pos_counts) == 1:
                dominant_pos[fr_word] = max_pos

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

                        # PENALTY for proper nouns (POS='name')
                        # These are place names like "Amour" (Amur River) whose glosses
                        # contain common words like "river", "ocean", "country" etc.
                        if pos == 'name':
                            score -= 200

                        # PENALTY for minor POS usage
                        # e.g., "sortir" is mostly a verb, so penalize the noun sense
                        if fr_word in dominant_pos and pos != dominant_pos[fr_word]:
                            score -= 100  # Minor POS penalty

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
                        phrasal_particles = r'(oneself|yourself|himself|herself|itself|ourselves|themselves|each other|one another|out|up|down|in|off|on|away|back|over|around|about|through)'
                        phrasal_verb = re.match(f'^to {en_word} {phrasal_particles}\\b', gloss_lower)
                        # Also catch adjective/noun phrasal forms: "cut out", "mixed up"
                        phrasal_adj = re.match(f'^{en_word} {phrasal_particles}\\b', gloss_lower)
                        gerund = re.match(f'^to {en_word} \\w+ing\\b', gloss_lower)
                        # Catch "short for X" abbreviation patterns
                        abbreviation = re.match(f'^short for ', gloss_lower)

                        is_excluded = bool(phrasal_verb or phrasal_adj or gerund or abbreviation)
                        is_start_match = not is_excluded and any(re.match(p, gloss_lower) for p in start_patterns)
                        is_alt_match = any(re.search(p, gloss_lower) for p in alt_patterns)

                        # For multi-word French phrases, be stricter about start matches
                        # Glosses like "Used to introduce..." or "Eventually safe from..."
                        # are descriptions, not translations
                        if word_count > 1 and is_start_match:
                            # Check if original gloss starts with capital (description pattern)
                            # e.g., "Used to introduce" vs "because"
                            first_word = gloss.split()[0] if gloss else ''
                            if first_word and first_word[0].isupper() and first_word.lower() != 'i':
                                is_start_match = False  # Likely a description, not translation
                            # Also reject if gloss is long (descriptions tend to be verbose)
                            if len(gloss) > 50 and ';' not in gloss and ',' not in gloss[:30]:
                                is_start_match = False

                        # Check for compound phrase patterns in gloss
                        # e.g., "salty dog", "smart set", "bathroom break"
                        # If English word is followed by another word before comma, it's a modifier
                        # Remove parentheticals first: "tool (something)" -> "tool"
                        first_segment = re.split(r'[,;]', re.sub(r'\s*\([^)]*\)', '', gloss_lower))[0].strip()
                        segment_words = first_segment.split()
                        if len(segment_words) >= 2:
                            # Check if en_word is first and followed by another content word
                            # Exclude function words that introduce elaboration (not compounds)
                            elaboration_words = ('to', 'of', 'and', 'or', 'in', 'for', 'as', 'that', 'which', 'with')
                            if segment_words[0] == en_word and segment_words[1] not in elaboration_words:
                                # This is a compound like "salty dog" - penalize heavily
                                is_start_match = False
                                score -= 100

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
                            # e.g., "stop sign", "fire engine", "hot chocolate"
                            compound_suffixes = [
                                # Objects
                                'sign', 'mark', 'board', 'line', 'light', 'engine', 'bottle',
                                'machine', 'box', 'man', 'woman', 'house', 'room', 'car', 'boat',
                                'plane', 'train', 'station', 'shop', 'store', 'office', 'school',
                                # Food/drink compounds
                                'chocolate', 'coffee', 'tea', 'water', 'juice', 'wine', 'beer',
                                'milk', 'cake', 'pie', 'cream', 'sauce', 'soup', 'salad', 'bread',
                                # Other common compounds
                                'wave', 'storm', 'day', 'night', 'time', 'year', 'week', 'month',
                                'war', 'game', 'show', 'film', 'movie', 'book', 'story', 'song',
                            ]
                            gloss_words = gloss_lower.split()
                            if len(gloss_words) == 2 and gloss_words[1] in compound_suffixes:
                                score -= 150  # Heavy penalty for compound modifier

                        en_to_fr[index_word].append((fr_word, score))

    # Deduplicate and sort by score
    print("Sorting and deduplicating...")
    final_index = {}
    for en_word, fr_list in en_to_fr.items():
        # Skip junk English entries
        # - Very long words (often concatenated or URL fragments)
        # - Entries that look like URLs or file paths
        if len(en_word) > 30:
            continue
        if 'www' in en_word or 'pdf' in en_word or 'http' in en_word:
            continue

        # Group by French word, keep max score
        best_scores = {}
        for fr_word, score in fr_list:
            if fr_word not in best_scores or score > best_scores[fr_word]:
                best_scores[fr_word] = score

        # Filter vulgar French words unless English query is vulgar
        # e.g., "cow" shouldn't show "putain", but "whore" should show "pute"
        if en_word not in VULGAR_ENGLISH:
            best_scores = {fr: score for fr, score in best_scores.items()
                          if fr not in vulgar_french}

        # Sort by score descending, limit to top 10
        sorted_fr = sorted(best_scores.items(), key=lambda x: -x[1])[:10]
        if sorted_fr:  # Only add if there are non-vulgar results
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
