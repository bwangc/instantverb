# Kaikki Processing Scripts

Scripts to extract and process language-specific dictionaries from kaikki.org Wiktionary dumps.

## Source Data

Download from https://kaikki.org/dictionary/
- `raw-wiktextract-data.jsonl` - Full English Wiktionary dump (~21 GB)
- Place in `kaikki/en-raw-data/`

## Scripts

### `extract_language.py`
Extracts all entries for a specific language from the raw dump.

```bash
python extract_language.py fr          # French -> data/fr.jsonl
python extract_language.py es          # Spanish
python extract_language.py de          # German
```

**Output**: `data/<lang>.jsonl` - One JSON entry per line

### `build_database.py`
Builds a clean, compact dictionary from extracted JSONL.

```bash
python build_database.py fr            # -> data/fr-dict.json
```

**Output**: `data/<lang>-dict.json` - Single JSON with word index

## Processed Languages

| Lang | Code | Entries | Words | Raw Size | Dict Size |
|------|------|---------|-------|----------|-----------|
| French | fr | 398,108 | 382,459 | 417 MB | 127 MB |

## Output Format

```json
{
  "lang": "fr",
  "word_count": 382459,
  "words": {
    "parler": [
      {
        "word": "parler",
        "pos": "verb",
        "ipa": "/paʁ.le/",
        "audio": "https://...",
        "etymology": "...",
        "senses": [
          {
            "gloss": "to speak, talk",
            "tags": ["intransitive"],
            "examples": [{"text": "...", "en": "..."}]
          }
        ],
        "forms": [{"form": "parle", "tags": ["first-person", "present"]}]
      }
    ]
  }
}
```

## Notes

- Each language may eventually need custom processing (different POS, gender systems, etc.)
- French has 245k verb entries with full conjugations
- Audio URLs available for many common words
- Examples often include English translations
- 127 MB might need splitting/compression for web use
