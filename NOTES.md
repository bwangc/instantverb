# Instantdict Data Processing Notes

## Source Data
- **File**: `kaikki/en-raw-data/raw-wiktextract-data.jsonl`
- **Size**: 21.5 GB (JSON Lines format)
- **Source**: English Wiktionary extracted by kaikki.org

## French Entry Structure

Each French entry has:
- `word`: the headword
- `lang`: "French"
- `lang_code`: "fr"
- `pos`: part of speech (verb, noun, adj, adv, etc.)
- `senses[]`: array of definitions
  - `glosses[]`: English definitions
  - `examples[]`: usage examples with `text`, `translation`, `english`
  - `tags[]`: grammatical tags like "intransitive", "transitive"
  - `categories[]`
  - `links[]`: cross-references
- `forms[]`: inflected forms with tags
  - For verbs: full conjugation with person/number/tense/mood tags
  - Each form can have `ipa` pronunciation
- `sounds[]`: pronunciation info
  - `ipa`: IPA transcription
  - `audio`, `mp3_url`, `ogg_url`: audio file URLs
  - `rhymes`, `homophone`
- `etymology_text`: etymology as readable text
- `derived[]`: derived words
- `related[]`: related words
- `descendants[]`: descendant words in other languages

## Statistics (from raw data)
- **Total French entries**: 398,184
- **POS distribution**:
  - verb: 245,684 (62%)
  - noun: 88,637 (22%)
  - adj: 45,983 (12%)
  - name: 9,323
  - adv: 4,533
  - others: ~4,000

## Processing Plan
1. Extract all French entries to `french.jsonl`
2. Build word index: word -> [entries] (multiple POS per word)
3. Build form index: conjugated form -> [infinitive/lemma]
4. Generate clean JSON for web frontend

## Key Fields for MVP
- word
- pos
- senses[].glosses (definitions)
- senses[].examples (with translations)
- sounds[].ipa
- sounds[].mp3_url (audio)
- forms[] (for verb conjugations)

## Notes
- 245k verb entries = lots of conjugated forms already indexed
- Audio available for many common words
- Examples often include English translations
- Can cross-reference with our Instantverb conjugator
