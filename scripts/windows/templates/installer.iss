; Inno Setup Script for Document Anonymizer
; This template is processed by create_windows_installer.py
; Placeholders: __VERSION__, __SOURCE_DIR__, __OUTPUT_DIR__

#ifndef AppVersion
  #define AppVersion "__VERSION__"
#endif
#ifndef SourceDir
  #define SourceDir "__SOURCE_DIR__"
#endif
#ifndef OutputDir
  #define OutputDir "__OUTPUT_DIR__"
#endif

[Setup]
AppName=Document Anonymizer
AppVersion={#AppVersion}
AppPublisher=Document Anonymizer
DefaultDirName={autopf}\DocumentAnonymizer
DefaultGroupName=Document Anonymizer
OutputDir={#OutputDir}
OutputBaseFilename=DocumentAnonymizer-{#AppVersion}-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\runtime\python\python.exe
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Document Anonymizer"; Filename: "{app}\DocumentAnonymizer.bat"; IconFilename: "{app}\runtime\python\python.exe"
Name: "{group}\Uninstall Document Anonymizer"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Document Anonymizer"; Filename: "{app}\DocumentAnonymizer.bat"; IconFilename: "{app}\runtime\python\python.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\DocumentAnonymizer.bat"; Description: "{cm:LaunchProgram,Document Anonymizer}"; Flags: nowait postinstall skipifsilent shellexec
