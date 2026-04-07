# NPCJason - Desktop Pet Companion

A pixel art NPC that lives on your Windows desktop and system tray.
Click him to make him dance. He says random things throughout the day.

> **Screenshot:** *(add screenshots here)*

---

## Features

- **Pixel art character** rendered in real-time on your desktop
- **System tray icon** - minimize to tray, access menu from notification area
- **Dance animation** - click Jason to watch him bust a move
- **Random sayings** - a mix of NPC humor, motivational quotes, and tech jokes
- **Draggable** - move him anywhere on your desktop
- **Speech bubbles** - floating popups with his wisdom
- **Auto-sayings** - Jason speaks up every 3-8 minutes on his own

---

## For Users: Install the Easy Way

1. Download `NPCJason_Setup_1.0.0.exe` from the [Releases](../../releases) page
2. Run the installer and follow the wizard
3. NPCJason will appear on your desktop - no Python required!

The installer lets you choose:
- Start Menu shortcut (always created)
- Desktop shortcut (default: on)
- Run on Windows startup (default: off)

To uninstall, use **Add or Remove Programs** in Windows Settings.

---

## For Developers: Build from Source

### Prerequisites

- Python 3.8+
- pip
- Windows 10/11

### Run from source

```bash
pip install -r requirements.txt
python npcjason.py
```

### Build the standalone EXE

```bat
build.bat
```

This installs PyInstaller, generates the icon, and produces `dist\NPCJason.exe`.

### Build the installer (EXE + Inno Setup installer)

1. Install [Inno Setup 6](https://jrsoftware.org/isinfo.php)
2. Run:

```bat
build_installer.bat
```

This produces both `dist\NPCJason.exe` and `NPCJason_Setup_1.0.0.exe` in the project root.

You can also compile the installer manually:

```bat
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

### Build files

| File | Purpose |
|------|---------|
| `generate_icon.py` | Creates `npcjason.ico` from pixel art (run before PyInstaller) |
| `npcjason.spec` | PyInstaller spec file (reproducible builds) |
| `installer.iss` | Inno Setup 6 installer script |
| `build.bat` | One-click: install deps, generate icon, build EXE |
| `build_installer.bat` | One-click: build EXE + compile Inno Setup installer |
| `version_info.txt` | Windows EXE version metadata (embedded by PyInstaller) |

---

## Controls

| Action | What Happens |
|--------|-------------|
| Left-click | Jason dances + says something |
| Right-click | Context menu (Dance, Say Something, Quit) |
| Click + Drag | Move Jason anywhere on the desktop |
| System tray icon | Show/Hide, Dance, Say Something, Quit |

---

## Customization

### Add your own sayings

Edit the `SAYINGS` list in `npcjason.py`:

```python
SAYINGS = [
    "Your custom line here.",
    ...
]
```

### Change the pixel art

Edit `FRAME_IDLE`, `FRAME_DANCE1`, `FRAME_DANCE2`, `FRAME_DANCE3` in `npcjason.py`.
Each character maps to a color in the `PALETTE` dict. Use `.` for transparent pixels.

### Adjust timing

| Setting | Location | Default |
|---------|----------|---------|
| Dance frame speed | `_animation_loop`, `after(150, ...)` | 150 ms/frame |
| Auto-saying interval | `_schedule_random_saying` | 3-8 min |
| Speech bubble duration | `SpeechBubble.__init__`, `after(4000 + ...)` | ~4 sec + text |

---

## License

MIT - see [LICENSE](LICENSE)
