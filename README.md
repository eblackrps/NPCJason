# NPCJason - Desktop Pet Companion

NPCJason is a Windows desktop pet that lives on top of your desktop, reacts to system events, swaps skins, chats with cloned friends, and ships as a standalone EXE so end users do not need Python installed.

> **Current release target:** `v1.1.0`

---

## What’s New In v1.1.0

This release adds the next major wave of polish and maintainability work:

- External skin packs loaded from [`skins/`](./skins)
- A real settings window for sound, startup, updates, reactions, and skin selection
- `Start With Windows` management from inside the app
- Generated `.wav` sound assets with volume control
- Better multi-pet management, including dismissing specific pets or all friends
- Event-driven Windows hooks for USB, power, and foreground-window reactions
- Hot-reload for `sayings.txt` and [`dialogue-packs/`](./dialogue-packs)
- Release automation that builds both the standalone EXE and the installer
- A modular codebase plus automated unit tests
- Auto-update checking with release notifications

---

## Features

- Multiple skins: Classic Jason, Wizard Jason, Knight Jason, and Astronaut Jason
- External skin packs that can be dropped into [`skins/`](./skins) and hot-reloaded live
- Idle breathing and blinking animation
- Mood system: happy, tired, caffeinated
- Event reactions for removable drives, low battery, and focused window changes
- Optional sound effects with mute and volume control
- Custom sayings from `sayings.txt`
- Extra dialogue packs from [`dialogue-packs/`](./dialogue-packs)
- Settings persistence in `%APPDATA%\NPCJason\settings.json`
- Multi-pet support with light pet-to-pet chatter
- Update checks against the GitHub releases feed

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
   - `NPCJason_Setup_1.1.0.exe` for the installer
3. Launch it and let Jason haunt your desktop

### Controls

| Action | What Happens |
|--------|-------------|
| Left-click | Dance + say something |
| Right-click | Open the quick menu |
| Click + drag | Move Jason anywhere |
| Tray icon | Show/Hide, settings, skins, startup toggle, updates, summon/dismiss pets |

### Custom sayings

Create a `sayings.txt` file next to `NPCJason.exe`. Entries are separated by blank lines.

```text
[any]
General line here.

[happy]
Everything is coming up Jason.

[tired]
I am approximately 40% yawns.
```

NPCJason hot-reloads `sayings.txt` while running, so you usually do not need to restart the app.

### Dialogue packs

Add extra `.txt` files to [`dialogue-packs/`](./dialogue-packs). They use the same section format as `sayings.txt` and are also hot-reloaded.

### Skin packs

Add extra `.json` files to [`skins/`](./skins). NPCJason will detect them at runtime and add them to the skin menus.

### Saved state

NPCJason stores state in `%APPDATA%\NPCJason\`.

- `settings.json`: position, skin, mood, sound, startup/update preferences
- `shared_state.json`: pet coordination, chatter, and pet-management commands
- `sounds/`: generated sound assets used for playback

---

## For Developers

### Prerequisites

- Python 3.8+
- pip
- Windows 10/11

### Run from source

```bat
python -m pip install -r requirements.txt
python npcjason.py
```

### Quick start script

```bat
run_npcjason.bat
```

### Run tests

```bat
python -m unittest discover -s tests
```

### Build the standalone EXE

```bat
build.bat
```

This installs dependencies, runs tests, generates the icon, and produces `dist\NPCJason.exe`.

### Build the installer

1. Install [Inno Setup 6](https://jrsoftware.org/isinfo.php)
2. Run:

```bat
build_installer.bat
```

This runs tests, builds `dist\NPCJason.exe`, and produces `NPCJason_Setup_1.1.0.exe`.

### Release automation

Publishing a GitHub release triggers [`.github/workflows/release.yml`](./.github/workflows/release.yml), which:

1. Installs dependencies
2. Runs the test suite
3. Builds the standalone EXE
4. Builds the installer
5. Generates SHA256 checksums
6. Uploads all release assets to GitHub

### Project layout

| Path | Purpose |
|------|---------|
| `npcjason.py` | Thin launcher entrypoint |
| `npcjason_app/app.py` | Main runtime app |
| `npcjason_app/dialogue.py` | Sayings, dialogue packs, event text |
| `npcjason_app/skins.py` | Frame rendering + skin loading |
| `npcjason_app/windows_events.py` | Native Windows event hooks |
| `npcjason_app/settings_window.py` | Settings UI |
| `npcjason_app/sound.py` | Sound asset generation + playback |
| `npcjason_app/startup.py` | Windows startup shortcut management |
| `tests/` | Automated unit tests |
| `skins/` | External skin definitions |
| `dialogue-packs/` | External dialogue packs |
| `.github/workflows/release.yml` | Release automation |

---

## License

MIT - see [LICENSE](LICENSE)
