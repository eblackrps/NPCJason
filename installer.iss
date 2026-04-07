; installer.iss - Inno Setup 6 script for NPCJason Desktop Pet
; Compile with: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
; Or open in the Inno Setup IDE and press Ctrl+F9

#define MyAppName "NPCJason"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "NPCJason"
#define MyAppExeName "NPCJason.exe"

[Setup]
AppId={{A7C3E1F2-84D5-4B9A-B3E6-1D2F5A8C9E0B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=
AppSupportURL=
AppUpdatesURL=
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Output installer to the project root
OutputDir=.
OutputBaseFilename=NPCJason_Setup_{#MyAppVersion}
SetupIconFile=npcjason.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Require admin only if installing to Program Files; use lowest if user dir preferred
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce
Name: "startup"; Description: "Start {#MyAppName} when &Windows starts"; GroupDescription: "Startup options:"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "npcjason.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "sayings.txt.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "skins\*"; DestDir: "{app}\skins"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dialogue-packs\*"; DestDir: "{app}\dialogue-packs"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\npcjason.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\npcjason.ico"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "&Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Kill the running process before uninstall so files can be removed cleanly
Filename: "taskkill.exe"; Parameters: "/F /IM {#MyAppExeName}"; Flags: runhidden; RunOnceId: "KillNPCJason"
