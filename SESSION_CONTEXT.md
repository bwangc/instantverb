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

5. **Proper noun penalty** - POS='name' entries (place names like "Amour" river)
   - Penalized to avoid geographic terms polluting common word searches
   - Fixed: river→rivière (was amour), ocean→océan

6. **Elaboration word detection** - Expanded compound exclusion list
   - Now includes: to, of, and, or, in, for, as, that, which, with
   - Fixed: field→champ now in top 2 (was missing)

7. **Question words restored** - who/what/which removed from stopwords
   - who→qui, what→quoi, which→quel now work

8. **Time adverbs restored** - always/never removed from stopwords
   - always→toujours, never→jamais now work

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
- **Proper noun**: -200 for POS='name' (place names like "Amour" river)
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

## Test Suite

The test suite (`test_en_fr.py`) checks:
1. **noise_words_removed** - Stopwords like "did", "does", "has" filtered
2. **base_verbs_work** - do→faire, be→être, have→avoir, etc.
3. **common_words_have_results** - 103 common words all return results
4. **top_result_quality** - 67 common words have quality #1 results
5. **conjugated_forms_filtered** - was, were, did, does, has filtered
6. **word_categories** - numbers, days, months, colors, body, family, time_adverbs, questions
7. **polysemous_words** - Words with multiple meanings (bear, field, watch, etc.)
8. **no_junk_entries** - No single-char or numeric junk in top results

## Quality Metrics

For common English words (200+):
- 100% have results
- 99.5% have common French word as #1
- 100% have common French in top 3

## Git Commits

Recent commits:
- "EN→FR: Keep question words (who/what/which) as searchable"
- "EN→FR: Keep 'always'/'never' as searchable words"
- "EN→FR: Add proper noun penalty and polysemous word tests"
- "EN→FR: Add word_categories test and update session context"
- "EN→FR: Fix phrasal adjectives, abbreviations, expand compounds"
