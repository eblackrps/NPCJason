# Skin Packs

Drop additional `.json` skin packs into this folder to make them available in NPCJason at runtime. NPCJason hot-reloads this directory while running, validates every pack before use, and reports non-fatal warnings in the Settings window and diagnostics log.

Each skin file supports:

- `key`: unique identifier
- `label`: display name shown in menus
- `author`: optional creator credit
- `description`: optional summary shown in Settings
- `version`: optional pack version label
- `char_map`: remap base frame palette keys
- `palette`: color overrides
- `tray`: tray icon colors for `hair`, `body`, and `legs`
- `overlay`: 20 strings of 16 characters each, using `.` for transparent pixels

Validation notes:

- `key` must be unique across all loaded packs
- `palette` and `tray` values must be six-digit hex colors like `#2f7d32`
- invalid palette colors are skipped instead of crashing the app
- invalid tray colors fall back to the default tray palette
- malformed or unreadable `.json` files are ignored with a warning so the pet keeps running

Example:

```json
{
  "key": "forest-ranger",
  "label": "Forest Ranger Jason",
  "author": "Example Creator",
  "description": "A mossy outdoors variant for bug-hunting expeditions.",
  "version": "1.0",
  "char_map": {
    "T": "F"
  },
  "palette": {
    "F": "#2f7d32"
  },
  "tray": {
    "hair": "#4a3728",
    "body": "#2f7d32",
    "legs": "#2d4263"
  },
  "overlay": [
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................"
  ]
}
```
