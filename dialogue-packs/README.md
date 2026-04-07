# Dialogue Packs

Add `.txt` files to this folder to extend NPCJason's quote pool without changing code. NPCJason hot-reloads this directory while running.

Rules:

- Separate sayings with a blank line
- Optional mood sections: `[any]`, `[happy]`, `[tired]`, `[caffeinated]`
- Lines starting with `#` or `;` are treated as comments
- Placeholders like `{pet_name}`, `{mood}`, `{time}`, `{date}`, `{active_window}`, `{battery_percent}`, `{skin}`, and `{other_pet_name}` are filled in automatically when available
- Unknown placeholders are left alone, so literal braces in jokes are still safe

Example:

```text
[any]
{pet_name} is monitoring {active_window}.

[happy]
Today is a very good patch day.

[tired]
I am approximately {battery_percent}% caffeine and hope.
```
