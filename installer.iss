[Setup]
AppId={{6C8C6E7A-8C8F-4C5D-9E39-3A6E8F7F8B6E}
AppName=pdfmaker
AppVersion=0.1.2
DefaultDirName={localappdata}\pdfmaker
DisableDirPage=yes
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=pdfmaker-setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\pdfmaker.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userdesktop}\pdfmaker"; Filename: "{app}\pdfmaker.exe"

[Run]
Filename: "{app}\pdfmaker.exe"; Description: "Launch pdfmaker"; Flags: nowait postinstall skipifsilent
