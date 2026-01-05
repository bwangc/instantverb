# EN→FR Search Algorithm Session Context

## Project Overview
This is the `instantverb` project - a French dictionary web app with EN→FR reverse lookup.
The main script is `kaikki-processing-scripts/build_en_fr_index.py` which builds an index from French dictionary glosses.

## Current Performance (as of last test)
- **88.6% exact match** on 271 common words
- **98.9% top-3**
- **99.6% top-5**

## Scoring Algorithm Summary

The algorithm extracts English words from French dictionary glosses and scores French words based on:

1. **Frequency bonus**: +0 to +300 based on rank in french_10k_cleaned.tsv
2. **Start match bonus**: +200 if English word at start of gloss (e.g., "to speak"), +100 if semicolon present
3. **Alt match bonus**: +75-150 for matches after semicolon (e.g., "purchase; buy")
4. **First sense bonus**: +100 for sense 0, +50 for sense 1, -50 for sense >= 5
5. **Single word bonus**: +30 for single-word French entries
6. **Verb bonus**: +30 for verbs with "to X" glosses
7. **Noun/adj bonus**: +20

Penalties applied:
- **Interjection**: -150 (e.g., "stop!" as intj)
- **Minor POS**: -100 when word has dominant POS elsewhere (e.g., "sortir" noun vs verb)
- **Loan word**: -100 if French word == English word and not in frequency list
- **Compound noun**: -150 for "X chocolate", "X sign" type compounds
- **Synonym**: -80 when matched via synonym (start↔begin, beautiful↔handsome)

Exclusions (no start match bonus):
- Phrasal verbs: "to cut out", "to give up"
- Phrasal adjectives: "cut out", "mixed up"
- Reflexives: "to see oneself"
- Gerunds: "to stop carrying"
- Abbreviations: "short for X"

## Recent Fixes Applied

1. **Synonym detection** - 60+ word groups for cross-referencing
2. **Minor POS penalty** - Pre-computes dominant POS per word
3. **Phrasal adjective exclusion** - "cut out" no longer matches "cut"
4. **Abbreviation exclusion** - "short for radiographie" excluded
5. **Expanded compound list** - Added chocolate, coffee, tea, etc.

## Test Results After Latest Fixes

Fixed cases:
- cut → "couper" (was "fait" from "cut out")
- hot → "chaud" (was "chocolat" from "hot chocolate")
- short → "court" (was "radio" from "short for radiographie")

## Remaining Issues to Investigate

### Cases where #1 is questionable:
- **boat** → "embarcation" #1, "bateau" #3 (embarcation is formal/rare)
- **country** → "campagne" #1, "pays" #2 (campagne=countryside, pays=nation)

### Cases where #1 is valid alternative but not "expected":
These are actually fine - both translations are correct:
- feel: ressentir vs sentir
- teach: apprendre vs enseigner
- dream: rêve (noun) vs rêver (verb)
- return: retour (noun) vs revenir (verb)
- start: début (noun) vs commencer (verb)
- help: aide (noun) vs aider (verb)
- good: bien vs bon
- time: fois vs temps

## Files Modified

- `kaikki-processing-scripts/build_en_fr_index.py` - Main scoring algorithm
- `web/data/en-fr.json.gz` - Output index file

## Next Steps

1. Investigate why "embarcation" beats "bateau" for "boat"
2. Investigate why "campagne" beats "pays" for "country"
3. Run comprehensive test on 500+ words to find more edge cases
4. Consider if noun vs verb preference should be adjusted
5. Push final changes when satisfied

## How to Test

```bash
cd /Users/bwang/Documents/CC/instantverb
python3 kaikki-processing-scripts/build_en_fr_index.py  # Rebuild index
# Then run test script inline or create test file
```

## Git Status

Two commits pushed:
1. "EN→FR search: 88% exact, 97% top-3 on core vocabulary"
2. "EN→FR: Add minor POS penalty for better results"

Uncommitted changes: phrasal adjective exclusion, abbreviation exclusion, expanded compound list
