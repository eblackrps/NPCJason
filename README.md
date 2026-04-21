# NPCJason - Desktop Pet Companion

NPCJason is a Windows desktop pet that lives on top of your desktop, reacts to system events, swaps skins, chats with cloned friends, and ships as a standalone EXE so end users do not need Python installed.

> **Current release target:** `v1.8.1`

---

## What’s New In v1.8.1

This patch release adds Veeam-flavored content without disturbing the newer runtime systems:

- New `Veeam Jason` skin pack with branded green styling and tray colors
- A Veeam-themed dialogue pack with backup, recovery, and restore-point jokes
- Support for skin-targeted legacy text sections like `[skin:veeam]` so a quote pack can follow a specific skin
- Tests covering skin-targeted legacy dialogue parsing and the new Veeam assets

---

## Features

- Multiple skins: Classic Jason, Wizard Jason, Knight Jason, and Astronaut Jason
- Expanded built-in skins: Office Jason, Homelab Jason, Network Jason, and Responsible Jason
- Included external skin pack: Veeam Jason
- External skin packs that can be dropped into [`skins/`](./skins) and hot-reloaded live
- Skin Framework v2 with tags, quote affinity, sound sets, accessory offsets, and per-skin animation metadata
- Idle breathing and blinking animation
- Mood system: happy, tired, caffeinated
- Personality state system with idle, curious, smug, busy, annoyed, celebrating, confused, sneaky, and exhausted behavior
- Lightweight relationship/familiarity tracking so Jason greets you a little differently over time without getting weird about it
- Autonomous desktop movement with pacing, hesitation, edge inspection, and better recovery from awkward pathing
- Local companion framework with the pet mouse sidekick, follow/wait/react states, and menu-triggered interactions
- Cheese feeding and the mouse backflip routine with the exact `Ansible Chris made me do it` payoff
- Extra mouse life bits including Crumb Heist, Mug Recon, Zip Tie Recovery, and quieter ambient sidekick activity
- Three dance routines with contextual variety instead of a single repeated dance loop
- Event reactions for removable drives, low battery, and focused window changes
- Desk-item framework with coffee mug, keyboard, and tiny network rack interactions
- Structured quote packs with enable/disable support and repeat suppression
- Greeting/sign-off behavior, daily vibe surfacing, theme spotlights, ambient world moments, and milestone beats for longer-running sessions
- Lighter achievement-style unlock surfacing so new discoveries do not disappear into the background
- Clearer success/failure/confusion reactions so interrupted or completed bits feel intentional instead of accidental
- Quote follow-up chaining for short secondary punchlines and mini conversational beats
- App-title humor and Cisco joke packs integrated into the contextual quote system
- Networking Meltdown & Helpdesk Chaos pack for helpdesk, routing, and patch-panel suffering
- Context-aware mini-scenarios and gag chains such as Busy IT Morning, Homelab Troubleshooting, Network Victory Lap, Responsible Adult Moment, and Office Chaos
- Context-aware toy system with tricycle, rubber duck, tiny homelab server cart, and stress ball interactions
- Lightweight rare-event system for low-frequency special moments
- Favorites that bias skins, toys, scenarios, and quote packs toward your preferred flavor of desktop menace
- Unlockable discoveries including bonus quote/scenario content and Astronaut Jason
- Seasonal and special modes such as April Fools, Patch Day Panic, Homelab Weekend, and Monday Morning Survival
- Behavior tuning controls for activity level, quote frequency, and companion frequency
- Optional sound effects with mute and volume control
- Quiet hours and fullscreen suppression for automatic chatter
- Custom sayings from `sayings.txt`
- Extra dialogue packs from [`dialogue-packs/`](./dialogue-packs)
- Favorites and recent-saying history
- Settings persistence in `%APPDATA%\NPCJason\settings.json`, including selected skin, quote packs, discoveries, favorites, mute state, and recent scenario continuity
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
   - `NPCJason_Setup_1.8.1.exe` for the installer
3. Launch it and let Jason haunt your desktop

### Controls

| Action | What Happens |
|--------|-------------|
| Left-click | Dance + say something |
| Right-click | Open the quick menu |
| Click + drag | Move Jason anywhere |
| Tray icon | Show/Hide, settings, skins, companion controls, toys, scenarios, quote packs, discoveries, mute, special modes, updates, summon/dismiss pets |

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
Text packs also support placeholders like `{pet_name}` and `{active_window}`, plus skin-targeted sections like `[skin:veeam]`.

### Skin packs

Add extra `.json` files to [`skins/`](./skins). NPCJason will detect them at runtime, validate them, and add them to the skin menus.

### Saved state

NPCJason stores state in `%APPDATA%\NPCJason\`.

- `settings.json`: position, skin, mood, sound, startup/update preferences, favorites, quiet hours, and reaction toggles
- `settings.json` also stores companion familiarity, streaks, theme rotation, milestone history, and unlock announcement memory
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

This runs tests, builds `dist\NPCJason.exe`, and produces `NPCJason_Setup_1.8.1.exe`.

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
| `npcjason_app/companion_presence.py` | Familiarity, greetings/sign-offs, milestones, daily vibe, and theme spotlight logic |
| `npcjason_app/speech_history.py` | Recent/favorite saying history management |
| `npcjason_app/dialogue.py` | Quote packs, dialogue selection, repeat suppression, event text |
| `npcjason_app/personality.py` | Personality states, moodful transitions, and quote/movement bias |
| `npcjason_app/movement.py` | Autonomous desktop movement planning and recovery |
| `npcjason_app/scenarios.py` | Gag-chain and mini-scenario definitions/runtime |
| `npcjason_app/desk_items.py` | Desk-item definitions, cooldowns, and runtime prop behavior |
| `npcjason_app/notifications.py` | Context-reaction rules for title-aware behavior beats |
| `npcjason_app/seasonal.py` | Seasonal and special-mode activation rules |
| `npcjason_app/unlocks.py` | Discoveries, unlockables, and progress tracking |
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
