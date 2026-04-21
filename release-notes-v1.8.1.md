NPCJason v1.8.1 adds a Veeam-flavored content patch on top of the current long-session runtime.

Highlights:

- Adds the new `Veeam Jason` skin pack with Veeam-green styling and matching tray colors
- Adds a Veeam dialogue pack with backup, restore-point, replica, and recovery-themed popup lines
- Extends legacy text dialogue packs with skin-targeted sections like `[skin:veeam]`
- Keeps the newer quote-pack/runtime behavior intact instead of downgrading the current dialogue system

Validation:

- `python -m unittest discover -s tests -v`
- `python -m compileall npcjason_app tests dialogue-packs skins`

Release flow:

- Publishing this release triggers the GitHub Actions `Build Release Assets` workflow
- That workflow builds and attaches the Windows EXE, installer, and SHA256 checksum artifacts
