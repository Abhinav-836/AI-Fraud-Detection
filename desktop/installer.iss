; Inno Setup script: turns dist\AIFraudDetection into one setup .exe.
; Built by build_desktop.ps1 (needs Inno Setup 6: https://jrsoftware.org/isdl.php)
; Manual: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" desktop\installer.iss

#define AppName "AI Fraud Detection"
#define AppVersion "2.0.0"
#define AppPublisher "Abhinav"
#define AppExe "AIFraudDetection.exe"

[Setup]
AppId={{6C1F5B0E-6B4E-4C1E-9D3B-AF2D8E1F7A41}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://github.com/Abhinav-836/AI-Fraud-Detection
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; Per-user install by default: no admin prompt. Users can still choose "all users".
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=AIFraudDetection-Setup-{#AppVersion}
SetupIconFile=assets\app.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\AIFraudDetection\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{#AppName} (open in browser)"; Filename: "{app}\{#AppExe}"; Parameters: "--browser"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

; The database, logs and retrained models live in %LOCALAPPDATA%\AIFraudDetection
; and are kept on uninstall, so reinstalling/upgrading keeps your history.
