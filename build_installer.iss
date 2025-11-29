
[Setup]
AppName=LightClip
AppVersion=1.2.0
DefaultDirName={pf}\LightClip
DefaultGroupName=LightClip
OutputDir=Output
OutputBaseFilename=LightClip_Setup
SetupIconFile=assets\icons\light\icon.ico
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\LightClip\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\LightClip"; Filename: "{app}\LightClip.exe"
Name: "{commondesktop}\LightClip"; Filename: "{app}\LightClip.exe"

[Run]
Filename: "{app}\LightClip.exe"; Description: "啟動 LightClip"; Flags: nowait postinstall
