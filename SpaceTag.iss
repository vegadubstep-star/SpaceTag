#define AppName "Space Tag"
#define AppVersion "0.1.0"
[Setup]
AppId={{D91023EB-7EF4-4FF6-A28D-0BF0D6677C0B}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\Space Tag
DefaultGroupName=Space Tag
OutputDir=dist
OutputBaseFilename=SpaceTag-Setup-0.1.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
[Files]
Source: "dist\SpaceTag.exe"; DestDir: "{app}"; Flags: ignoreversion
[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce
[Icons]
Name: "{autoprograms}\Space Tag"; Filename: "{app}\SpaceTag.exe"
Name: "{autodesktop}\Space Tag"; Filename: "{app}\SpaceTag.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\SpaceTag.exe"; Description: "Launch Space Tag"; Flags: nowait postinstall skipifsilent
