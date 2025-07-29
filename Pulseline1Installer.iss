[Setup]
AppName=Pulseline1 Visualizer
AppVersion=1.0.0
AppPublisher=Pulseline1
DefaultDirName={autopf}\Pulseline1 Visualizer
DefaultGroupName=Pulseline1 Visualizer
OutputBaseFilename=Pulseline1_Visualizer_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=icons\pulseline1.ico
UninstallDisplayIcon={app}\Pulseline1 Visualizer.exe

[Files]
Source: "dist\Pulseline1\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Pulseline1 Visualizer"; Filename: "{app}\Pulseline1 Visualizer.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Pulseline1 Visualizer"; Filename: "{app}\Pulseline1 Visualizer.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Run]
Filename: "{app}\Pulseline1 Visualizer.exe"; Description: "{cm:LaunchProgram,Pulseline1 Visualizer}"; Flags: postinstall nowait unchecked
