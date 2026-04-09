# NPCJason - Desktop Pet Companion

NPCJason is a Windows desktop pet that lives on top of your desktop, reacts to system events, swaps skins, chats with cloned friends, and ships as a standalone EXE so end users do not need Python installed.

> **Current release target:** `v1.4.0`

---

## What’s New In v1.4.0

This release focuses on making NPCJason feel more alive while keeping the post-refactor structure stable:

- Skin Framework v2 with tags, quote affinity, sound hooks, accessory offsets, and per-skin animation metadata
- Four new built-in skins: Office Jason, Homelab Jason, Network Jason, and Responsible Jason
- A reusable toy system with tricycle rides, rubber duck visits, a tiny homelab server cart, and stress-ball interactions
- Structured quote-pack loading with enable/disable controls, weighting, and repeat suppression
- A dedicated Jason quote pack added exactly as provided
- Stronger tray, quick-menu, and settings controls for skins, toys, quotes, sound, and special behavior toggles
- Lightweight rare events and tighter contextual behavior between skins, toys, and quotes
- Ship-readiness fixes for quote-pack persistence, runtime validation, and release packaging polish

---

## Features

- Multiple skins: Classic Jason, Wizard Jason, Knight Jason, and Astronaut Jason
- Expanded built-in skins: Office Jason, Homelab Jason, Network Jason, and Responsible Jason
- External skin packs that can be dropped into [`skins/`](./skins) and hot-reloaded live
- Skin Framework v2 with tags, quote affinity, sound sets, accessory offsets, and per-skin animation metadata
- Idle breathing and blinking animation
- Mood system: happy, tired, caffeinated
- Event reactions for removable drives, low battery, and focused window changes
- Structured quote packs with enable/disable support and repeat suppression
- Context-aware toy system with tricycle, rubber duck, tiny homelab server cart, and stress ball interactions
- Lightweight rare-event system for low-frequency special moments
- Optional sound effects with mute and volume control
- Quiet hours and fullscreen suppression for automatic chatter
- Custom sayings from `sayings.txt`
- Extra dialogue packs from [`dialogue-packs/`](./dialogue-packs)
- Favorites and recent-saying history
- Settings persistence in `%APPDATA%\NPCJason\settings.json`
- Multi-pet support with light pet-to-pet chatter
- Update checks against the GitHub releases feed
- Diagnostics log output in `%APPDATA%\NPCJason\logs\npcjason.log`

---

## Standalone Builds

Yes: NPCJason can be fully standalone.

- End users can run `NPCJason.exe` with no Python installed
- The installer bundles the standalone app as well
- Python and pip are only needed if you want to run or build from source

The project uses PyInstaller for standalone packaging today. If you ever want an even more native-feeling binary, `Nuitka` would be the next thing to evaluate, but it is not required for end-user distribution.

---

## For Users

### Install the easy way

1. Open the [Releases](../../releases) page
2. Download either:
   - `NPCJason.exe` for the standalone app
   - `NPCJason_Setup_1.4.0.exe` for the installer
3. Launch it and let Jason haunt your desktop

### Controls

| Action | What Happens |
|--------|-------------|
| Left-click | Dance + say something |
| Right-click | Open the quick menu |
| Click + drag | Move Jason anywhere |
| Tray icon | Show/Hide, settings, skins, toys, quote packs, rare events, startup toggle, updates, summon/dismiss pets |

### Custom sayings

Create a `sayings.txt` file next to `NPCJason.exe`. Entries are separated by blank lines.

```text
[any]
{pet_name} is on desktop watch.

[happy]
Everything is coming up {pet_name}.

[tired]
It is {time}. I would like fewer meetings.
```

NPCJason hot-reloads `sayings.txt` while running, so you usually do not need to restart the app.

### Dialogue packs

Add extra `.txt` or `.json` files to [`dialogue-packs/`](./dialogue-packs). Text packs use the same section format as `sayings.txt`; JSON packs add categories, affinity rules, and weighting.

### Skin packs

Add extra `.json` files to [`skins/`](./skins). NPCJason will detect them at runtime, validate them, and add them to the skin menus.

### Saved state

NPCJason stores state in `%APPDATA%\NPCJason\`.

- `settings.json`: position, skin, mood, sound, startup/update preferences, favorites, quiet hours, and reaction toggles
- `shared_state.json`: pet coordination, chatter, and pet-management commands
- `logs\npcjason.log`: diagnostics log
- `sounds/`: generated sound assets used for playback

---

## For Developers

### Prerequisites

- Python 3.8+
- pip
- Windows 10/11

### Run from source

```bat
python -m pip install .
python npcjason.py
```

### Quick start script

```bat
run_npcjason.bat
```

### Run tests

```bat
python -m pip install ".[build]"
python -m unittest discover -s tests -v
python -m compileall npcjason_app tests npcjason.py
```

### Build the standalone EXE

```bat
build.bat
```

This installs dependencies from [`pyproject.toml`](./pyproject.toml), runs tests, generates the icon, and produces `dist\NPCJason.exe`.

### Build the installer

1. Install [Inno Setup 6](https://jrsoftware.org/isinfo.php)
2. Run:

```bat
build_installer.bat
```

This runs tests, builds `dist\NPCJason.exe`, and produces `NPCJason_Setup_1.4.0.exe`.

### Release automation

Publishing a GitHub release triggers [`.github/workflows/release.yml`](./.github/workflows/release.yml), which:

1. Reads the app version from source
2. Installs dependencies and validates them with `pip check`
3. Runs the test suite
4. Compiles the source tree as a packaging sanity check
5. Builds the standalone EXE
6. Builds the installer
7. Generates SHA256 checksums
8. Uploads all release assets to GitHub

### Project layout

| Path | Purpose |
|------|---------|
| `npcjason.py` | Thin launcher entrypoint |
| `npcjason_app/app.py` | Thin application entry wrapper |
| `npcjason_app/app_controller.py` | Main composition root and runtime orchestration |
| `npcjason_app/pet_window.py` | Tk window adapter and on-screen geometry |
| `npcjason_app/runtime_state.py` | Explicit runtime/suppression/pause state model |
| `npcjason_app/scheduler.py` | Managed Tk scheduler and UI dispatch loop |
| `npcjason_app/settings_service.py` | Settings load/save/import/export/reset logic |
| `npcjason_app/persistence.py` | Settings/shared-state schema sanitization |
| `npcjason_app/speech_history.py` | Recent/favorite saying history management |
| `npcjason_app/dialogue.py` | Quote packs, dialogue selection, repeat suppression, event text |
| `npcjason_app/skins.py` | Frame rendering + skin loading |
| `npcjason_app/toys.py` | Toy definitions, cooldowns, and runtime toy behavior |
| `npcjason_app/toy_window.py` | Lightweight companion windows used for toy rendering |
| `npcjason_app/rare_events.py` | Low-frequency contextual event selection |
| `npcjason_app/updates.py` | Update parsing, async checks, and prompt coordination |
| `npcjason_app/tray_controller.py` | System tray adapter and tray-state modeling |
| `npcjason_app/windows_platform.py` | Screen/work-area geometry helpers |
| `npcjason_app/windows_events.py` | Native Windows event hooks |
| `npcjason_app/settings_window.py` | Settings UI |
| `npcjason_app/sound.py` | Sound asset generation + playback |
| `npcjason_app/startup.py` | Windows startup shortcut management |
| `npcjason_app/diagnostics.py` | Diagnostics logging helpers |
| `tests/` | Automated unit tests |
| `skins/` | External skin definitions |
| `dialogue-packs/` | External dialogue packs |
| `.github/workflows/release.yml` | Release automation |

---

## License

MIT - see [LICENSE](LICENSE)
