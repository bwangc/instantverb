# Kaikki Processing Scripts

Scripts to extract and process language-specific dictionaries from kaikki.org Wiktionary dumps.

## Source Data

Download from https://kaikki.org/dictionary/
- `raw-wiktextract-data.jsonl.gz` - Full English Wiktionary dump (~21 GB uncompressed)
- Place in `kaikki/en-raw-data-gz/`

## Scripts

### `extract_language.py`
Extracts all entries for a specific language from the raw dump. Supports gzipped input.

```bash
python extract_language.py fr          # French -> data/fr.jsonl
python extract_language.py es          # Spanish
python extract_language.py de          # German
```

**Output**: `data/<lang>.jsonl` - One JSON entry per line

### `build_database.py`
Builds a clean, compact dictionary from extracted JSONL.

Filters applied:
- Removes "form-of" entries (e.g., "vis" as "inflection of vivre")
- Removes Louisiana-specific definitions

```bash
python build_database.py fr            # -> data/fr-dict.json
```

**Output**: `data/<lang>-dict.json` - Single JSON with word index

### `build_10k.py`
Builds a subset dictionary from the top 10k most common words (based on frequency list).
Also builds a verb forms index for conjugation lookup.

```bash
python build_10k.py                    # -> data/fr-10k.json, data/fr-10k-forms.json
```

**Outputs**:
- `data/fr-10k.json` - Dictionary subset (~16 MB)
- `data/fr-10k-forms.json` - Conjugated form → infinitive mapping (~2 MB)

## Processed Languages

| Lang | Code | Entries | Words | Dict Size | 10k Size |
|------|------|---------|-------|-----------|----------|
| French | fr | 99,539 | 92,283 | 68 MB | 16 MB |

## Output Format

```json
{
  "lang": "fr",
  "word_count": 9664,
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

## Forms Index Format

```json
{
  "forms": {
    "suis": ["être", "suivre"],
    "vis": ["voir", "vivre"],
    "parle": ["parler"]
  }
}
```

## Notes

- Form-of entries are filtered out to avoid duplicate/redundant definitions
- Louisiana French definitions are excluded
- Verb forms include IPA pronunciation where available
- Audio URLs from Wikimedia Commons included for many words
- 10k subset is designed for fast client-side loading in web apps
