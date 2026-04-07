# NPCJason - Desktop Pet Companion

NPCJason is a Windows desktop pet that lives on top of your desktop, reacts to system events, swaps skins, chats with cloned friends, and ships as a standalone EXE so end users do not need Python installed.

> **Current release target:** `v1.2.0`

---

## What’s New In v1.2.0

This release adds the next 10 quality-of-life passes:

- Custom pet naming, including named summoned friends
- Dialogue placeholders such as `{pet_name}`, `{mood}`, `{time}`, and `{active_window}`
- Quiet hours plus fullscreen do-not-disturb for automatic chatter
- Granular reaction toggles for USB, battery, focus, updates, pet chat, and ambient sayings
- Recent-sayings history and favorite quote templates
- Automatic antics scheduling with configurable timing and dance chance
- Edge snapping plus a reliable “Bring Back On Screen” recovery option
- Settings export, import, and reset flows
- Skin metadata plus validation feedback in Settings
- Diagnostics logging with quick-open shortcuts for the data folder and log file

---

## Features

- Multiple skins: Classic Jason, Wizard Jason, Knight Jason, and Astronaut Jason
- External skin packs that can be dropped into [`skins/`](./skins) and hot-reloaded live
- Idle breathing and blinking animation
- Mood system: happy, tired, caffeinated
- Event reactions for removable drives, low battery, and focused window changes
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
   - `NPCJason_Setup_1.2.0.exe` for the installer
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
{pet_name} is on desktop watch.

[happy]
Everything is coming up {pet_name}.

[tired]
It is {time}. I would like fewer meetings.
```

NPCJason hot-reloads `sayings.txt` while running, so you usually do not need to restart the app.

### Dialogue packs

Add extra `.txt` files to [`dialogue-packs/`](./dialogue-packs). They use the same section format as `sayings.txt` and also support placeholders like `{pet_name}` and `{active_window}`.

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

This runs tests, builds `dist\NPCJason.exe`, and produces `NPCJason_Setup_1.2.0.exe`.

### Release automation

Publishing a GitHub release triggers [`.github/workflows/release.yml`](./.github/workflows/release.yml), which:

1. Reads the app version from source
2. Installs dependencies
3. Runs the test suite
4. Builds the standalone EXE
5. Builds the installer
6. Generates SHA256 checksums
7. Uploads all release assets to GitHub

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
| `npcjason_app/diagnostics.py` | Diagnostics logging helpers |
| `tests/` | Automated unit tests |
| `skins/` | External skin definitions |
| `dialogue-packs/` | External dialogue packs |
| `.github/workflows/release.yml` | Release automation |

---

## License

MIT - see [LICENSE](LICENSE)
