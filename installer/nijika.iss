#ifndef AppVersion
  #define AppVersion "0.1.6"
#endif
#ifndef SourceDir
  #error SourceDir must point to the clean staging directory
#endif
#ifndef OutputDir
  #define OutputDir "..\dist-release\installer"
#endif
#ifndef LanguageFile
  #define LanguageFile "ChineseSimplified.isl"
#endif

[Setup]
AppId={{D72B6BFA-8D47-46B7-8F5D-CBBF16BB68A0}
AppName=虹夏桌宠
AppVersion={#AppVersion}
AppVerName=虹夏桌宠 {#AppVersion}
AppPublisher=CY-YI
AppPublisherURL=https://github.com/CY-YI/nijika-desktop-pet
AppSupportURL=https://github.com/CY-YI/nijika-desktop-pet
AppUpdatesURL=https://github.com/CY-YI/nijika-desktop-pet
DefaultDirName={localappdata}\NijikaDesktopPet\app
DefaultGroupName=虹夏桌宠
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputDir}
OutputBaseFilename=虹夏桌宠-Setup-{#AppVersion}
SetupIconFile={#SourceDir}\assets\icons\nijika-shortcut.ico
UninstallDisplayIcon={app}\assets\icons\nijika-shortcut.ico
UninstallDisplayName=虹夏桌宠
VersionInfoVersion={#AppVersion}
VersionInfoCompany=CY-YI
VersionInfoDescription=虹夏桌宠 Windows 安装程序
VersionInfoProductName=虹夏桌宠
VersionInfoProductVersion={#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no
AllowNoIcons=yes
UsePreviousAppDir=yes
UsePreviousTasks=yes

[Languages]
Name: "chinesesimplified"; MessagesFile: "{#LanguageFile}"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："
Name: "autostart"; Description: "登录 Windows 时启动虹夏桌宠"; GroupDescription: "启动选项："; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\虹夏桌宠"; Filename: "{app}\dist\虹夏桌宠.exe"; WorkingDir: "{app}\dist"; IconFilename: "{app}\assets\icons\nijika-shortcut.ico"
Name: "{group}\虹夏桌宠设置"; Filename: "{app}\dist\虹夏桌宠.exe"; Parameters: "--control-panel"; WorkingDir: "{app}\dist"; IconFilename: "{app}\assets\icons\nijika-shortcut.ico"
Name: "{userdesktop}\虹夏桌宠"; Filename: "{app}\dist\虹夏桌宠.exe"; WorkingDir: "{app}\dist"; IconFilename: "{app}\assets\icons\nijika-shortcut.ico"; Tasks: desktopicon
Name: "{userdesktop}\虹夏桌宠设置"; Filename: "{app}\dist\虹夏桌宠.exe"; Parameters: "--control-panel"; WorkingDir: "{app}\dist"; IconFilename: "{app}\assets\icons\nijika-shortcut.ico"; Tasks: desktopicon
Name: "{userstartup}\虹夏桌宠"; Filename: "{app}\dist\虹夏桌宠.exe"; WorkingDir: "{app}\dist"; IconFilename: "{app}\assets\icons\nijika-shortcut.ico"; Tasks: autostart

[Run]
Filename: "{app}\dist\虹夏桌宠.exe"; WorkingDir: "{app}\dist"; Description: "启动虹夏桌宠"; Flags: nowait postinstall skipifsilent unchecked

[UninstallDelete]
; Only remove generated logs. Messages, skins, Agent profiles and client
; configuration live outside {app} and are deliberately never listed here.
Type: files; Name: "{app}\dist\nijika-notice.log"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ManifestPath: String;
  Manifest: TArrayOfString;
  ExecutablePath: String;
  I: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    ManifestPath := ExpandConstant('{app}\plugins\nijika-work-local\mcp.json');
    if LoadStringsFromFile(ManifestPath, Manifest) then
    begin
      ExecutablePath := ExpandConstant('{app}\dist\虹夏MCP-v2.exe');
      StringChangeEx(ExecutablePath, '\', '\\', True);
      for I := 0 to GetArrayLength(Manifest) - 1 do
        StringChangeEx(Manifest[I], 'AUTO_LOCAL_MCP', ExecutablePath, True);
      if not SaveStringsToUTF8FileWithoutBOM(ManifestPath, Manifest, False) then
        RaiseException('无法写入 Work MCP 路径，请在设置中心重新接入 Work。');
    end else
      RaiseException('无法读取 Work MCP 配置，请在设置中心重新接入 Work。');
  end;
end;
