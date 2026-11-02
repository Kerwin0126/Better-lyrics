; Author: Kerwin
#ifndef AppVersion
  #define AppVersion "0.6.0"
#endif
#ifndef ProjectRoot
  #define ProjectRoot ".."
#endif

[Setup]
AppId={{083CF7A5-247A-4AE0-8D71-3CD18567C900}
AppName=浮词
AppVersion={#AppVersion}
AppVerName=Better lyrics | 浮词 {#AppVersion}
AppPublisher=kerwin
AppPublisherURL=https://github.com/Kerwin0126/Better-lyrics
AppSupportURL=https://github.com/Kerwin0126/Better-lyrics/issues
AppUpdatesURL=https://github.com/Kerwin0126/Better-lyrics/releases
DefaultDirName={localappdata}\Programs\BetterLyrics
DefaultGroupName=浮词
DisableProgramGroupPage=yes
DisableDirPage=no
DisableWelcomePage=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19041
OutputDir={#ProjectRoot}\.release
OutputBaseFilename=BetterLyrics-Setup-{#AppVersion}-x64
SetupIconFile={#ProjectRoot}\assets\floating-lyrics.ico
UninstallDisplayIcon={app}\浮词.exe
LicenseFile={#ProjectRoot}\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern light windows11
WizardSizePercent=110,110
WizardImageFile={#ProjectRoot}\assets\installer-sidebar.bmp
WizardSmallImageFile={#ProjectRoot}\assets\installer-small.bmp
WizardImageStretch=yes
ShowLanguageDialog=no
CloseApplications=yes
RestartApplications=no
UninstallDisplayName=Better lyrics | 浮词
VersionInfoCompany=Kerwin
VersionInfoDescription=Better lyrics | 浮词 安装程序
VersionInfoCopyright=Copyright © 2026 Kerwin
VersionInfoVersion={#AppVersion}.0

[Languages]
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："
Name: "startmenuicon"; Description: "创建开始菜单快捷方式"; GroupDescription: "快捷方式："

[Files]
Source: "{#ProjectRoot}\浮词.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectRoot}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ProjectRoot}\installer\installed.flag"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectRoot}\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectRoot}\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectRoot}\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userdesktop}\浮词"; Filename: "{app}\浮词.exe"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userprograms}\浮词\浮词"; Filename: "{app}\浮词.exe"; WorkingDir: "{app}"; Tasks: startmenuicon
Name: "{userprograms}\浮词\卸载浮词"; Filename: "{uninstallexe}"; Tasks: startmenuicon

[Run]
Filename: "{app}\浮词.exe"; Description: "启动浮词"; Flags: nowait postinstall skipifsilent

[Code]
var
  AuthorLink: TNewStaticText;
  SchoolLine: TNewStaticText;

procedure OpenAuthorProfile(Sender: TObject);
var
  ErrorCode: Integer;
begin
  ShellExec('open', 'https://github.com/Kerwin0126', '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
end;

procedure InitializeWizard();
begin
  WizardForm.Font.Name := 'Microsoft YaHei UI';
  WizardForm.WelcomeLabel1.Font.Name := 'Microsoft YaHei UI';
  WizardForm.PageNameLabel.Font.Name := 'Microsoft YaHei UI';
  WizardForm.WelcomeLabel1.Caption := '欢迎，让歌词来到桌面';
  WizardForm.WelcomeLabel2.Caption := '即将安装 Better lyrics | 浮词。'+#13#10+#13#10+
    '透明歌词、逐字变色、四向透视与柔和动效。'+#13#10+
    'Python、Qt 及所需运行库已包含在安装包中。';
  AuthorLink := TNewStaticText.Create(WizardForm);
  AuthorLink.Parent := WizardForm.WelcomePage;
  AuthorLink.Left := WizardForm.WelcomeLabel2.Left;
  AuthorLink.Top := WizardForm.WelcomeLabel2.Top + ScaleY(156);
  AuthorLink.Caption := '作者：kerwin';
  AuthorLink.Font.Color := $00AB566F;
  AuthorLink.Font.Style := [fsUnderline];
  AuthorLink.Cursor := crHand;
  AuthorLink.OnClick := @OpenAuthorProfile;
  SchoolLine := TNewStaticText.Create(WizardForm);
  SchoolLine.Parent := WizardForm.WelcomePage;
  SchoolLine.Left := AuthorLink.Left;
  SchoolLine.Top := AuthorLink.Top + ScaleY(24);
  SchoolLine.Width := WizardForm.WelcomeLabel2.Width;
  SchoolLine.AutoSize := False;
  SchoolLine.Height := ScaleY(42);
  SchoolLine.WordWrap := True;
  SchoolLine.Caption := '@ KUST (Kunming University of Science and Technology)';
  WizardForm.FinishedLabel.Caption := '浮词已经准备就绪。'+#13#10+#13#10+
    '打开音乐播放器，在浮词顶部选择歌词来源。'+#13#10+
    '用户设置保存在当前用户的数据目录，升级时会继续保留。';
end;
