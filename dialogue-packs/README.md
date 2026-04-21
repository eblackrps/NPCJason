# Dialogue Packs

Add `.txt` or `.json` files to this folder to extend NPCJason's quote pool without changing code. NPCJason hot-reloads this directory while running and logs warnings for malformed sections or unknown template tokens instead of breaking the runtime.

Legacy `.txt` packs:

- Separate sayings with a blank line
- Optional mood sections: `[any]`, `[happy]`, `[tired]`, `[caffeinated]`
- Optional skin-only sections: `[skin:veeam]`, using the skin pack `key`
- Lines starting with `#` or `;` are treated as comments
- Placeholders like `{pet_name}`, `{mood}`, `{time}`, `{date}`, `{active_window}`, `{battery_percent}`, `{skin}`, `{companion}`, `{dance_routine}`, `{desk_item}`, and `{other_pet_name}` are filled in automatically when available
- Unknown placeholders are left alone, so literal braces in jokes are still safe
- Unknown section headers are treated as `[any]` and reported as warnings
- Files that cannot be decoded or read are skipped with a warning

Example:

```text
[any]
{pet_name} is monitoring {active_window}.

[happy]
Today is a very good patch day.

[tired]
I am approximately {battery_percent}% caffeine and hope.
```

Structured `.json` packs:

- `key`: unique pack id
- `label`: display name shown in menus
- `description`: optional summary
- `weight`: optional pack weight
- `enabled`: optional default enabled flag
- `categories`: optional pack-wide categories
- `quotes`: list of strings or objects
- quote objects support `text`, `weight`, `moods`, `categories`, `affinity`, and optional `follow_ups`
- follow-up entries support `text`, `delay_ms`, `chance`, `require_contexts`, `exclude_contexts`, and `categories`
- affinity keys can include `skins`, `tags`, `contexts`, `toys`, `moods`, `packs`, and `categories`

Example:

```json
{
  "key": "team-quotes",
  "label": "Team Quotes",
  "description": "Context-aware office lines.",
  "weight": 2,
  "quotes": [
    "Status page is looking at me funny.",
    {
      "text": "Routing day.",
      "categories": ["network"],
      "affinity": {
        "skins": ["network"],
        "contexts": ["focus"]
      },
      "follow_ups": [
        {
          "text": "That sentence got worse the longer I looked at it.",
          "delay_ms": 1400,
          "chance": 0.5
        }
      ]
    }
  ]
}
```
