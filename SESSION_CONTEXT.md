# EN→FR Search Algorithm Session Context

## Project Overview
This is the `instantverb` project - a French dictionary web app with EN→FR reverse lookup.
The main script is `kaikki-processing-scripts/build_en_fr_index.py` which builds an index from French dictionary glosses.

## Current Status (Jan 2026)

The algorithm is working well. Test suite passes all checks:
- Noise words filtered (did, does, has, etc.)
- Base verbs work (do→faire, be→être, have→avoir)
- Common words return results
- Top results are quality (in frequency list or valid)
- No junk entries

### Recent Improvements Made

1. **Stopword filter** - Added ENGLISH_STOPWORDS set to filter function words
   that appear in explanatory text (e.g., "did" from "but did not generate")
   - Filters: articles, prepositions, conjunctions, pronouns
   - Filters conjugated auxiliary verbs (did, does, has, was, were)
   - Keeps base forms (do, be, have) for valid lookups

2. **Phrase-over-single-word fixes**
   - Detect capitalized description patterns ("Used to introduce...")
   - Detect compound phrases ("salty dog", "smart set", "bathroom break")
   - Penalize these to let common single words rank higher

3. **œ ligature normalization** - Frequency list uses "oe", dictionary uses "œ"
   - Now: eye→œil, sister→sœur, heart→cœur, beef→bœuf, egg→œuf

4. **Compound detection fix** - Strip parentheticals before checking
   - "tool (something...)" was incorrectly detected as compound
   - Now: tool→outil (was échardonnoir)

## Scoring Algorithm Summary

The algorithm extracts English words from French dictionary glosses and scores French words based on:

1. **Frequency bonus**: +0 to +300 based on rank in french_10k_cleaned.tsv
2. **Start match bonus**: +200 if English word at start of gloss, +100 if semicolon present
3. **Alt match bonus**: +75-150 for matches after semicolon (e.g., "purchase; buy")
4. **First sense bonus**: +100 for sense 0, +50 for sense 1, -50 for sense >= 5
5. **Single word bonus**: +30 for single-word French entries
6. **Verb bonus**: +30 for verbs with "to X" glosses
7. **Noun/adj bonus**: +20

Penalties applied:
- **Interjection**: -150 (e.g., "stop!" as intj)
- **Minor POS**: -100 when word has dominant POS elsewhere
- **Loan word**: -100 if French word == English word and not in frequency list
- **Compound noun**: -150 for "X chocolate", "X sign" type compounds
- **Compound phrase in gloss**: -100 for "salty dog" type patterns
- **Synonym match**: -80 when matched via synonym

Exclusions (no start match bonus):
- Phrasal verbs: "to cut out", "to give up"
- Phrasal adjectives: "cut out", "mixed up"
- Reflexives: "to see oneself"
- Gerunds: "to stop carrying"
- Abbreviations: "short for X"
- Multi-word phrases with capitalized descriptions
- Multi-word phrases with long verbose glosses (>50 chars)

## Files

- `kaikki-processing-scripts/build_en_fr_index.py` - Main scoring algorithm
- `kaikki-processing-scripts/test_en_fr.py` - Test suite
- `web/data/en-fr.json.gz` - Output index file (~900KB)

## How to Test

```bash
cd /Users/bwang/Documents/CC/instantverb
python3 kaikki-processing-scripts/build_en_fr_index.py  # Rebuild index
python3 kaikki-processing-scripts/test_en_fr.py          # Run tests
```

## Known Limitations

1. **Conjugated verb forms** - Forms like "goes", "tries" often return noise
   because they only appear in descriptive text, not as direct translations.
   Base forms (go, try) work well.

2. **Edge cases with different conceptual structure** - Some English words
   don't map directly (e.g., "least" → French uses "au moins" phrase)

## Git Commits

Recent commits:
- "EN→FR: Add stopword filter and test suite"
- "EN→FR: Fix phrase-over-single-word issues"
- "EN→FR: Fix œ ligature and compound detection"
