# npcjason.spec - PyInstaller spec file for NPCJason Desktop Pet
# Run: pyinstaller npcjason.spec --clean --noconfirm

import os

block_cipher = None
datas = []

for source_dir in ['skins', 'dialogue-packs']:
    if os.path.isdir(source_dir):
        for root, _dirs, files in os.walk(source_dir):
            for filename in files:
                source_path = os.path.join(root, filename)
                relative_dir = os.path.dirname(source_path)
                datas.append((source_path, relative_dir))

for filename in ['sayings.txt.example']:
    if os.path.exists(filename):
        datas.append((filename, '.'))

a = Analysis(
    ['npcjason.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'pystray._win32',
        'PIL._tkinter_finder',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='NPCJason',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # No terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='npcjason.ico',
    version='version_info.txt',
)
