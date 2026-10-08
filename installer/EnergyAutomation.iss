; =====================================================================
; EnergyAutomation — Professional Windows 11 Inno Setup Script
; =====================================================================

#define MyAppName "EnergyAutomation"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Savera Auto Comps Pvt Ltd"
#define MyAppURL "https://savera.biz"
#define MyAppExeName "EnergyAutomation.exe"
#define SourceDistDir "..\dist\EnergyAutomation"

[Setup]
; Unique application GUID for Windows Add/Remove Programs
AppId={{8B454E54-E859-4D6C-A9FE-9BC5A42D7101}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\release
OutputBaseFilename=EnergyAutomation-{#MyAppVersion}-Setup
SetupIconFile=..\assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=no
DisableDirPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
// User Data Cleanup Handling on Uninstall
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{localappdata}\EnergyAutomation');
    if DirExists(DataDir) and not UninstallSilent then
    begin
      if MsgBox('Do you want to completely remove user databases, downloaded reports, and configuration files?' + #13#10 + #13#10 +
                'Click "No" to preserve your user data (Recommended).' + #13#10 +
                'Click "Yes" to delete all application data.',
                mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      begin
        DelTree(DataDir, True, True, True);
      end;
    end;
  end;
end;
