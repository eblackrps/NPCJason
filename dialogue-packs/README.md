# Dialogue Packs

Add `.txt` files to this folder to extend NPCJason's quote pool without changing code. NPCJason hot-reloads this directory while running.

Rules:

- Separate sayings with a blank line
- Optional mood sections: `[any]`, `[happy]`, `[tired]`, `[caffeinated]`
- Lines starting with `#` or `;` are treated as comments

Example:

```text
[any]
General line here.

[happy]
Today is a very good patch day.

[tired]
I am approximately 30% caffeine and hope.
```
