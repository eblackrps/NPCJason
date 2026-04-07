# Skin Packs

Drop additional `.json` skin packs into this folder to make them available in NPCJason at runtime. The app hot-reloads this directory while running.

Each skin file supports:

- `key`: unique identifier
- `label`: display name
- `char_map`: remap base frame palette keys
- `palette`: color overrides
- `tray`: tray icon colors for `hair`, `body`, and `legs`
- `overlay`: 20 strings of 16 characters each, using `.` for transparent pixels

Example:

```json
{
  "key": "forest-ranger",
  "label": "Forest Ranger Jason",
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
