#include "generated-release-values.iss"

#define AppName "AI Subtitle Studio"
#define AppExeName "ai-subtitle-studio.exe"
#define StableAppId "{{BCA6E6C9-93AD-4A97-B176-B846A1F4D4EC}"

[Setup]
AppId={#StableAppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DefaultDirName={localappdata}\Programs\AI Subtitle Studio
DefaultGroupName=AI Subtitle Studio
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\release
OutputBaseFilename=AI-Subtitle-Studio-Setup-v{#AppVersion}
SetupIconFile=..\assets\app.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\runtime\{#AppExeName}
VersionInfoVersion={#AppVersionNumeric}
VersionInfoProductName={#AppName}
VersionInfoDescription={#AppName} online installer
MinVersion=10.0
SetupLogging=yes

[Tasks]
Name: "desktopicon"; Description: "Tạo biểu tượng ngoài màn hình"; GroupDescription: "Biểu tượng bổ sung:"; Flags: unchecked

[Files]
Source: "..\vendor\7zip\7z.exe"; Flags: dontcopy
Source: "..\vendor\7zip\7z.dll"; Flags: dontcopy

[Icons]
Name: "{group}\AI Subtitle Studio"; Filename: "{app}\runtime\{#AppExeName}"; WorkingDir: "{app}\runtime"
Name: "{autodesktop}\AI Subtitle Studio"; Filename: "{app}\runtime\{#AppExeName}"; WorkingDir: "{app}\runtime"; Tasks: desktopicon

[Run]
Filename: "{app}\runtime\{#AppExeName}"; Description: "Khởi chạy AI Subtitle Studio"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\runtime"
Type: filesandordirs; Name: "{app}\runtime.previous"
Type: dirifempty; Name: "{app}"

[Code]
var
  DownloadedBytes: Int64;

function OnDownloadProgress(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  if ProgressMax > 0 then
    WizardForm.StatusLabel.Caption :=
      Format('Đang tải %s: %.1f%%', [FileName, Progress * 100.0 / ProgressMax])
  else
    WizardForm.StatusLabel.Caption :=
      Format('Đang tải %s: %d byte', [FileName, Progress]);
  Result := True;
end;

function DownloadVolume(Index: Integer): String;
var
  Name: String;
  Hash: String;
begin
  case Index of
#if RuntimeVolumeCount >= 1
    1: begin Name := '{#RuntimeVolume1Name}'; Hash := '{#RuntimeVolume1Sha256}'; end;
#endif
#if RuntimeVolumeCount >= 2
    2: begin Name := '{#RuntimeVolume2Name}'; Hash := '{#RuntimeVolume2Sha256}'; end;
#endif
#if RuntimeVolumeCount >= 3
    3: begin Name := '{#RuntimeVolume3Name}'; Hash := '{#RuntimeVolume3Sha256}'; end;
#endif
#if RuntimeVolumeCount >= 4
    4: begin Name := '{#RuntimeVolume4Name}'; Hash := '{#RuntimeVolume4Sha256}'; end;
#endif
#if RuntimeVolumeCount >= 5
    5: begin Name := '{#RuntimeVolume5Name}'; Hash := '{#RuntimeVolume5Sha256}'; end;
#endif
#if RuntimeVolumeCount >= 6
    6: begin Name := '{#RuntimeVolume6Name}'; Hash := '{#RuntimeVolume6Sha256}'; end;
#endif
#if RuntimeVolumeCount >= 7
    7: begin Name := '{#RuntimeVolume7Name}'; Hash := '{#RuntimeVolume7Sha256}'; end;
#endif
#if RuntimeVolumeCount >= 8
    8: begin Name := '{#RuntimeVolume8Name}'; Hash := '{#RuntimeVolume8Sha256}'; end;
#endif
  else
    RaiseException(Format('Chỉ số runtime volume không hợp lệ: %d', [Index]));
  end;
  DownloadedBytes := DownloadedBytes +
    DownloadTemporaryFile('{#RuntimeBaseUrl}/' + Name, Name, Hash, @OnDownloadProgress);
  Result := ExpandConstant('{tmp}\') + Name;
end;

function UpdateReadyMemo(
  Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo,
  MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
begin
  Result :=
    MemoDirInfo + NewLine + NewLine +
    'Phiên bản: {#AppVersion}' + NewLine +
    'Kênh: {#ReleaseChannel}' + NewLine +
    'Tải xuống tối đa: ' + IntToStr(({#TemporarySpaceBytes} - {#InstalledSizeBytes}) div 1048576) + ' MiB' + NewLine +
    'Dung lượng cài đặt: ' + IntToStr({#InstalledSizeBytes} div 1048576) + ' MiB' + NewLine +
    'Dung lượng tạm thời yêu cầu: ' + IntToStr({#TemporarySpaceBytes} div 1048576) + ' MiB' + NewLine + NewLine +
    MemoTasksInfo;
end;

procedure DownloadAndActivateRuntime;
var
  Index: Integer;
  FirstVolume: String;
  SevenZip: String;
  StageRoot: String;
  StagedRuntime: String;
  ActiveRuntime: String;
  PreviousRuntime: String;
  ResultCode: Integer;
begin
  DownloadedBytes := 0;
  FirstVolume := '';
  for Index := 1 to {#RuntimeVolumeCount} do
  begin
    if Index = 1 then
      FirstVolume := DownloadVolume(Index)
    else
      DownloadVolume(Index);
  end;

  ExtractTemporaryFile('7z.exe');
  ExtractTemporaryFile('7z.dll');
  SevenZip := ExpandConstant('{tmp}\7z.exe');
  StageRoot := ExpandConstant('{tmp}\runtime-staging');
  StagedRuntime := StageRoot + '\ai-subtitle-studio';
  ActiveRuntime := ExpandConstant('{app}\runtime');
  PreviousRuntime := ExpandConstant('{app}\runtime.previous');
  DelTree(StageRoot, True, True, True);
  ForceDirectories(StageRoot);
  if not Exec(
    SevenZip,
    'x -y "' + FirstVolume + '" -o"' + StageRoot + '"',
    '',
    SW_HIDE,
    ewWaitUntilTerminated,
    ResultCode
  ) or (ResultCode <> 0) then
    RaiseException(Format('Không thể giải nén runtime (mã %d).', [ResultCode]));
  if not FileExists(StagedRuntime + '\{#AppExeName}') then
    RaiseException('Runtime đã tải không có executable hợp lệ.');

  DelTree(PreviousRuntime, True, True, True);
  if DirExists(ActiveRuntime) and not RenameFile(ActiveRuntime, PreviousRuntime) then
    RaiseException('Không thể chuẩn bị bản cài hiện tại để nâng cấp.');
  if not RenameFile(StagedRuntime, ActiveRuntime) then
  begin
    if DirExists(PreviousRuntime) then
      RenameFile(PreviousRuntime, ActiveRuntime);
    RaiseException('Không thể kích hoạt runtime mới; bản cũ đã được giữ lại.');
  end;
  DelTree(PreviousRuntime, True, True, True);
  DelTree(StageRoot, True, True, True);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
    DownloadAndActivateRuntime;
end;
