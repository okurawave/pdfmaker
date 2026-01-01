[Setup]
AppId={{6C8C6E7A-8C8F-4C5D-9E39-3A6E8F7F8B6E}
AppName=pdfmaker
AppVersion=0.1.4
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

[Code]
var
  OutputDirPage: TInputDirWizardPage;

procedure InitializeWizard();
begin
  OutputDirPage := CreateInputDirPage(
    wpSelectDir,
    'Output Folder',
    'Select a default output folder',
    'PDFs will be saved to this folder by default. You can change this later in Settings.',
    False,
    ''
  );
  OutputDirPage.Add(ExpandConstant('{localappdata}\pdfmaker\output'));
  OutputDirPage.Values[0] := ExpandConstant('{localappdata}\pdfmaker\output');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  SettingsDir: string;
  SettingsFile: string;
  OutputDir: string;
  Json: string;
begin
  if CurStep = ssPostInstall then
  begin
    OutputDir := OutputDirPage.Values[0];
    SettingsDir := ExpandConstant('{userappdata}\pdfmaker');
    SettingsFile := SettingsDir + '\settings.json';
    CreateDir(SettingsDir);
    CreateDir(OutputDir);
    Json :=
      '{' + #13#10 +
      '  "use_fixed_output": true,' + #13#10 +
      '  "fixed_output_dir": "' + OutputDir + '"' + #13#10 +
      '}' + #13#10;
    SaveStringToFile(SettingsFile, Json, False);
  end;
end;
