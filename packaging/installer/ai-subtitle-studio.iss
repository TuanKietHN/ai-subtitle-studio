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
AppMutex=AI-Subtitle-Studio-Runtime
CloseApplications=yes
RestartApplications=no
ExtraDiskSpaceRequired={#TemporarySpaceBytes}

[Tasks]
Name: "desktopicon"; Description: "Tạo biểu tượng ngoài màn hình"; GroupDescription: "Biểu tượng bổ sung:"; Flags: unchecked

[Files]
Source: "..\vendor\7zip\7z.exe"; Flags: dontcopy
Source: "..\vendor\7zip\7z.dll"; Flags: dontcopy
Source: "bits-download.ps1"; Flags: dontcopy

[Icons]
Name: "{group}\AI Subtitle Studio"; Filename: "{app}\runtime\{#AppExeName}"; WorkingDir: "{app}\runtime"
Name: "{group}\Gỡ cài đặt AI Subtitle Studio"; Filename: "{uninstallexe}"
Name: "{autodesktop}\AI Subtitle Studio"; Filename: "{app}\runtime\{#AppExeName}"; WorkingDir: "{app}\runtime"; Tasks: desktopicon

[Run]
Filename: "{app}\runtime\{#AppExeName}"; Description: "Khởi chạy AI Subtitle Studio"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\runtime"
Type: filesandordirs; Name: "{app}\runtime.previous"
Type: filesandordirs; Name: "{app}\runtime.staging"
Type: dirifempty; Name: "{app}"

[Code]
var
  DownloadPage: TDownloadWizardPage;
  DownloadedBytes: Int64;
  TotalRuntimeBytes: Int64;
  CurrentVolumeOffset: Int64;
  CurrentVolumeName: String;
  BundleStartedTick: Int64;
  ActiveRuntime: String;
  PreviousRuntime: String;
  IsUpgrade: Boolean;
  IsRepair: Boolean;
  CleanupPrivateData: Boolean;
  CleanupOwnedOutputs: Boolean;
  UninstallOptionsForm: TSetupForm;
  PrivateDataCheckBox: TNewCheckBox;
  OwnedOutputsCheckBox: TNewCheckBox;
  UninstallOptionsAccepted: Boolean;

function GetTickCount64: Int64;
  external 'GetTickCount64@kernel32.dll stdcall';

type
  TSystemTime = record
    Year: Word;
    Month: Word;
    DayOfWeek: Word;
    Day: Word;
    Hour: Word;
    Minute: Word;
    Second: Word;
    Milliseconds: Word;
  end;

procedure GetSystemTime(var SystemTime: TSystemTime);
  external 'GetSystemTime@kernel32.dll stdcall';

function PadTwoDigits(Value: Word): String;
begin
  if Value < 10 then
    Result := '0' + IntToStr(Value)
  else
    Result := IntToStr(Value);
end;

function UtcNowIso8601: String;
var
  SystemTime: TSystemTime;
begin
  GetSystemTime(SystemTime);
  Result := IntToStr(SystemTime.Year) + '-' + PadTwoDigits(SystemTime.Month) + '-' +
    PadTwoDigits(SystemTime.Day) + 'T' + PadTwoDigits(SystemTime.Hour) + ':' +
    PadTwoDigits(SystemTime.Minute) + ':' + PadTwoDigits(SystemTime.Second) + 'Z';
end;

procedure GetVolumeInfo(Index: Integer; var Name, Hash: String; var Size: Int64);
begin
  case Index of
#if RuntimeVolumeCount >= 1
    1: begin Name := '{#RuntimeVolume1Name}'; Hash := '{#RuntimeVolume1Sha256}'; Size := {#RuntimeVolume1Size}; end;
#endif
#if RuntimeVolumeCount >= 2
    2: begin Name := '{#RuntimeVolume2Name}'; Hash := '{#RuntimeVolume2Sha256}'; Size := {#RuntimeVolume2Size}; end;
#endif
#if RuntimeVolumeCount >= 3
    3: begin Name := '{#RuntimeVolume3Name}'; Hash := '{#RuntimeVolume3Sha256}'; Size := {#RuntimeVolume3Size}; end;
#endif
#if RuntimeVolumeCount >= 4
    4: begin Name := '{#RuntimeVolume4Name}'; Hash := '{#RuntimeVolume4Sha256}'; Size := {#RuntimeVolume4Size}; end;
#endif
#if RuntimeVolumeCount >= 5
    5: begin Name := '{#RuntimeVolume5Name}'; Hash := '{#RuntimeVolume5Sha256}'; Size := {#RuntimeVolume5Size}; end;
#endif
#if RuntimeVolumeCount >= 6
    6: begin Name := '{#RuntimeVolume6Name}'; Hash := '{#RuntimeVolume6Sha256}'; Size := {#RuntimeVolume6Size}; end;
#endif
#if RuntimeVolumeCount >= 7
    7: begin Name := '{#RuntimeVolume7Name}'; Hash := '{#RuntimeVolume7Sha256}'; Size := {#RuntimeVolume7Size}; end;
#endif
#if RuntimeVolumeCount >= 8
    8: begin Name := '{#RuntimeVolume8Name}'; Hash := '{#RuntimeVolume8Sha256}'; Size := {#RuntimeVolume8Size}; end;
#endif
  else
    RaiseException(Format('Chỉ số runtime volume không hợp lệ: %d', [Index]));
  end;
end;

function CacheRoot: String;
begin
  Result := ExpandConstant('{localappdata}\AI Subtitle Studio\installer-cache\{#RuntimeBundleId}');
end;

function RuntimeVolumeNamesJson: String;
begin
  Result := '[';
#if RuntimeVolumeCount >= 1
  Result := Result + '"{#RuntimeVolume1Name}"';
#endif
#if RuntimeVolumeCount >= 2
  Result := Result + ',"{#RuntimeVolume2Name}"';
#endif
#if RuntimeVolumeCount >= 3
  Result := Result + ',"{#RuntimeVolume3Name}"';
#endif
#if RuntimeVolumeCount >= 4
  Result := Result + ',"{#RuntimeVolume4Name}"';
#endif
#if RuntimeVolumeCount >= 5
  Result := Result + ',"{#RuntimeVolume5Name}"';
#endif
#if RuntimeVolumeCount >= 6
  Result := Result + ',"{#RuntimeVolume6Name}"';
#endif
#if RuntimeVolumeCount >= 7
  Result := Result + ',"{#RuntimeVolume7Name}"';
#endif
#if RuntimeVolumeCount >= 8
  Result := Result + ',"{#RuntimeVolume8Name}"';
#endif
  Result := Result + ']';
end;

function RuntimeVolumeHashesJson: String;
begin
  Result := '[';
#if RuntimeVolumeCount >= 1
  Result := Result + '"{#RuntimeVolume1Sha256}"';
#endif
#if RuntimeVolumeCount >= 2
  Result := Result + ',"{#RuntimeVolume2Sha256}"';
#endif
#if RuntimeVolumeCount >= 3
  Result := Result + ',"{#RuntimeVolume3Sha256}"';
#endif
#if RuntimeVolumeCount >= 4
  Result := Result + ',"{#RuntimeVolume4Sha256}"';
#endif
#if RuntimeVolumeCount >= 5
  Result := Result + ',"{#RuntimeVolume5Sha256}"';
#endif
#if RuntimeVolumeCount >= 6
  Result := Result + ',"{#RuntimeVolume6Sha256}"';
#endif
#if RuntimeVolumeCount >= 7
  Result := Result + ',"{#RuntimeVolume7Sha256}"';
#endif
#if RuntimeVolumeCount >= 8
  Result := Result + ',"{#RuntimeVolume8Sha256}"';
#endif
  Result := Result + ']';
end;

function RuntimeMarkerJson: String;
begin
  Result := '{"schema_version":1,' +
    '"runtime_bundle_id":"{#RuntimeBundleId}",' +
    '"volume_names":' + RuntimeVolumeNamesJson + ',' +
    '"volume_sha256":' + RuntimeVolumeHashesJson + ',' +
    '"installed_at_utc":"' + UtcNowIso8601 + '",' +
    '"app_version":"{#AppVersion}"}';
end;

function CacheMetadataJson(
  const Name, ExpectedHash: String;
  ExpectedSize: Int64
): String;
begin
  Result :=
    '{"schema_version":1,"runtime_bundle_id":"{#RuntimeBundleId}","name":"' + Name +
    '","expected_size":' + IntToStr(ExpectedSize) +
    ',"expected_sha256":"' + ExpectedHash + '"}';
end;

function CacheMetadataMatches(
  const MetadataPath, Name, ExpectedHash: String;
  ExpectedSize: Int64
): Boolean;
var
  Metadata: AnsiString;
begin
  Result := LoadStringFromFile(MetadataPath, Metadata) and
    (CompareText(Trim(String(Metadata)), CacheMetadataJson(Name, ExpectedHash, ExpectedSize)) = 0);
end;

function FileMatchesHash(const Path, ExpectedHash: String): Boolean;
begin
  Result := FileExists(Path) and
    (CompareText(GetSHA256OfFile(Path), ExpectedHash) = 0);
end;

function FormatMiB(Value: Int64): String;
begin
  Result := Format('%.1f', [Value / 1048576.0]);
end;

procedure UpdateDownloadProgress(Position, Maximum: Int64; const SourceText: String);
var
  ElapsedSeconds: Extended;
  SpeedBytes: Extended;
  RemainingSeconds: Int64;
  Detail: String;
begin
  if Maximum <= 0 then
    Maximum := TotalRuntimeBytes;
  DownloadPage.SetProgress(Position, Maximum);
  ElapsedSeconds := (GetTickCount64 - BundleStartedTick) / 1000.0;
  SpeedBytes := 0;
  RemainingSeconds := 0;
  if ElapsedSeconds > 0.5 then
    SpeedBytes := Position / ElapsedSeconds;
  if (SpeedBytes > 0) and (Maximum > Position) then
    RemainingSeconds := Round((Maximum - Position) / SpeedBytes);
  Detail := SourceText + ' | ' + FormatMiB(Position) + ' / ' +
    FormatMiB(Maximum) + ' MiB | ' +
    FormatMiB(Round(SpeedBytes)) + ' MiB/s';
  if RemainingSeconds > 0 then
    Detail := Detail + Format(' | còn khoảng %d phút %d giây', [RemainingSeconds div 60, RemainingSeconds mod 60]);
  DownloadPage.SetText(
    Format('Đang chuẩn bị %s', [CurrentVolumeName]),
    Detail
  );
end;

function OnDownloadProgress(
  const Url, FileName: String;
  const Progress, ProgressMax: Int64
): Boolean;
begin
  UpdateDownloadProgress(
    CurrentVolumeOffset + Progress,
    TotalRuntimeBytes,
    'HTTPS dự phòng'
  );
  Result := not DownloadPage.AbortedByUser;
end;

function LoadBitsStatus(
  const StatusPath: String;
  var State: String;
  var Transferred, Total: Int64;
  var ErrorText: String
): Boolean;
var
  Text: AnsiString;
  Fields: TStringList;
begin
  Result := False;
  if not LoadStringFromFile(StatusPath, Text) then
    Exit;
  Fields := TStringList.Create;
  try
    Fields.Delimiter := '|';
    Fields.StrictDelimiter := True;
    Fields.DelimitedText := Trim(Text);
    if Fields.Count < 3 then
      Exit;
    State := Fields[0];
    Transferred := StrToInt64Def(Fields[1], 0);
    Total := StrToInt64Def(Fields[2], 0);
    if Fields.Count > 3 then
      ErrorText := Fields[3]
    else
      ErrorText := '';
    Result := True;
  finally
    Fields.Free;
  end;
end;

function TryBitsDownload(
  const Url, PartPath, StatusPath, JobName: String;
  VolumeSize: Int64;
  ResetExisting: Boolean
): Boolean;
var
  PowerShell: String;
  Helper: String;
  Params: String;
  State: String;
  ErrorText: String;
  Transferred: Int64;
  ReportedTotal: Int64;
  ResultCode: Integer;
  MissingStatusTicks: Integer;
begin
  Result := False;
  DeleteFile(StatusPath);
  ExtractTemporaryFile('bits-download.ps1');
  Helper := ExpandConstant('{tmp}\bits-download.ps1');
  PowerShell := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
  Params := '-NoProfile -ExecutionPolicy Bypass -File ' + AddQuotes(Helper) +
    ' -Uri ' + AddQuotes(Url) +
    ' -Destination ' + AddQuotes(PartPath) +
    ' -JobName ' + AddQuotes(JobName) +
    ' -StatusPath ' + AddQuotes(StatusPath);
  if ResetExisting then
    Params := Params + ' -ResetExisting';
  if not Exec(PowerShell, Params, '', SW_HIDE, ewNoWait, ResultCode) then
  begin
    Log('Không thể khởi động BITS helper; chuyển sang HTTPS dự phòng.');
    Exit;
  end;

  MissingStatusTicks := 0;
  while True do
  begin
    if DownloadPage.AbortedByUser then
      RaiseException('Người dùng đã hủy; phần tải BITS hợp lệ được giữ để tiếp tục lần sau.');
    if LoadBitsStatus(StatusPath, State, Transferred, ReportedTotal, ErrorText) then
    begin
      MissingStatusTicks := 0;
      if ReportedTotal <= 0 then
        ReportedTotal := VolumeSize;
      UpdateDownloadProgress(
        CurrentVolumeOffset + Transferred,
        TotalRuntimeBytes,
        'BITS resume'
      );
      if CompareText(State, 'Completed') = 0 then
      begin
        Result := FileExists(PartPath);
        Exit;
      end;
      if (CompareText(State, 'Error') = 0) or
         (CompareText(State, 'Cancelled') = 0) then
      begin
        Log('BITS không hoàn tất: ' + ErrorText + '; chuyển sang HTTPS dự phòng.');
        Exit;
      end;
    end
    else
    begin
      MissingStatusTicks := MissingStatusTicks + 1;
      if MissingStatusTicks >= 60 then
      begin
        Log('BITS không tạo trạng thái trong 30 giây; chuyển sang HTTPS dự phòng.');
        Exit;
      end;
    end;
    Sleep(500);
  end;
end;

function CacheVerifiedFile(
  const SourcePath, Name, ExpectedHash: String;
  VolumeSize: Int64;
  const SourceText: String
): String;
var
  FinalPath: String;
begin
  if not ForceDirectories(CacheRoot) then
    RaiseException('Không thể tạo installer cache.');
  FinalPath := CacheRoot + '\' + Name;
  if CompareText(SourcePath, FinalPath) <> 0 then
  begin
    DeleteFile(FinalPath);
    if not CopyFile(SourcePath, FinalPath, False) then
      RaiseException('Không thể lưu runtime volume vào cache: ' + Name);
  end;
  if not FileMatchesHash(FinalPath, ExpectedHash) then
  begin
    DeleteFile(FinalPath);
    RaiseException('Runtime volume không đúng SHA-256: ' + Name);
  end;
  DownloadedBytes := DownloadedBytes + VolumeSize;
  UpdateDownloadProgress(DownloadedBytes, TotalRuntimeBytes, SourceText);
  Result := FinalPath;
end;

function ResolveVolume(Index: Integer): String;
var
  Name: String;
  Hash: String;
  Size: Int64;
  LocalPath: String;
  FinalPath: String;
  PartPath: String;
  StatusPath: String;
  MetadataPath: String;
  TempPath: String;
  Url: String;
  ResetBitsJob: Boolean;
  BitsCompleted: Boolean;
begin
  GetVolumeInfo(Index, Name, Hash, Size);
  CurrentVolumeName := Name;
  CurrentVolumeOffset := DownloadedBytes;
  LocalPath := ExpandConstant('{src}\') + Name;
  FinalPath := CacheRoot + '\' + Name;
  PartPath := FinalPath + '.part';
  StatusPath := FinalPath + '.status';
  MetadataPath := FinalPath + '.meta.json';
  Url := '{#RuntimeBaseUrl}/' + Name;

  if not ForceDirectories(CacheRoot) then
    RaiseException('Không thể tạo installer cache.');
  ResetBitsJob := not CacheMetadataMatches(MetadataPath, Name, Hash, Size);
  if ResetBitsJob then
  begin
    Log('Cache metadata thiếu hoặc không hợp lệ; hủy trạng thái tải dở: ' + Name);
    DeleteFile(PartPath);
    DeleteFile(StatusPath);
  end;
  if not SaveStringToFile(MetadataPath, CacheMetadataJson(Name, Hash, Size), False) then
    RaiseException('Không thể ghi cache metadata: ' + Name);

  if FileMatchesHash(LocalPath, Hash) then
  begin
    Result := CacheVerifiedFile(LocalPath, Name, Hash, Size, 'File cạnh Setup');
    Exit;
  end;
  if FileExists(LocalPath) then
    Log('Bỏ qua file cạnh Setup vì SHA-256 không đúng: ' + LocalPath);

  if FileMatchesHash(FinalPath, Hash) then
  begin
    Result := CacheVerifiedFile(FinalPath, Name, Hash, Size, 'Cache đã xác minh');
    Exit;
  end;
  if FileExists(FinalPath) then
    DeleteFile(FinalPath);

  BitsCompleted := TryBitsDownload(
    Url,
    PartPath,
    StatusPath,
    'AI-Subtitle-Studio-{#RuntimeBundleId}-' + IntToStr(Index),
    Size,
    ResetBitsJob
  );
  if BitsCompleted and FileMatchesHash(PartPath, Hash) then
  begin
    DeleteFile(FinalPath);
    if not RenameFile(PartPath, FinalPath) then
      RaiseException('Không thể hoàn tất BITS cache: ' + Name);
    Result := CacheVerifiedFile(FinalPath, Name, Hash, Size, 'BITS đã xác minh');
    Exit;
  end;
  if BitsCompleted and FileExists(PartPath) then
  begin
    Log('BITS báo hoàn tất nhưng SHA-256 sai; xóa phần tải không hợp lệ: ' + Name);
    DeleteFile(PartPath);
  end;

  DownloadPage.SetText(
    'BITS không khả dụng; đang dùng HTTPS dự phòng',
    'File vẫn được kiểm tra SHA-256 trước khi giải nén.'
  );
  DownloadTemporaryFile(Url, Name, Hash, @OnDownloadProgress);
  TempPath := ExpandConstant('{tmp}\') + Name;
  Result := CacheVerifiedFile(TempPath, Name, Hash, Size, 'HTTPS dự phòng đã xác minh');
end;

function SameRuntimeInstalled: Boolean;
var
  Marker: AnsiString;
begin
  Result := False;
  if not FileExists(ActiveRuntime + '\{#AppExeName}') then
    Exit;
  if not LoadStringFromFile(ActiveRuntime + '\.runtime-bundle-id', Marker) then
    Exit;
  Result :=
    (Pos('"schema_version":1', Marker) > 0) and
    (Pos('"runtime_bundle_id":"{#RuntimeBundleId}"', Marker) > 0) and
    (Pos('"volume_names":' + RuntimeVolumeNamesJson, Marker) > 0) and
    (Pos('"volume_sha256":' + RuntimeVolumeHashesJson, Marker) > 0);
end;

procedure DownloadAndActivateRuntime;
var
  Index: Integer;
  FirstVolume: String;
  SevenZip: String;
  StageRoot: String;
  StagedRuntime: String;
  ResultCode: Integer;
begin
  ActiveRuntime := ExpandConstant('{app}\runtime');
  PreviousRuntime := ExpandConstant('{app}\runtime.previous');
  if SameRuntimeInstalled then
  begin
    Log('Runtime bundle {#RuntimeBundleId} đã được cài; bỏ qua download/extraction.');
    Exit;
  end;
  if not ForceDirectories(ExpandConstant('{app}')) then
    RaiseException('Không thể tạo thư mục cài đặt.');

  StageRoot := ExpandConstant('{app}\runtime.staging');
  StagedRuntime := StageRoot + '\ai-subtitle-studio';
  DelTree(StageRoot, True, True, True);
  if not ForceDirectories(StageRoot) then
    RaiseException('Không thể tạo thư mục runtime.staging.');

  DownloadedBytes := 0;
  FirstVolume := '';
  BundleStartedTick := GetTickCount64;
  DownloadPage.Show;
  try
    for Index := 1 to {#RuntimeVolumeCount} do
    begin
      if Index = 1 then
        FirstVolume := ResolveVolume(Index)
      else
        ResolveVolume(Index);
    end;

    ExtractTemporaryFile('7z.exe');
    ExtractTemporaryFile('7z.dll');
    SevenZip := ExpandConstant('{tmp}\7z.exe');
    DownloadPage.SetText('Đang giải nén runtime', 'Archive đã được xác minh SHA-256.');
    if not Exec(
      SevenZip,
      'x -y ' + AddQuotes(FirstVolume) + ' -o' + AddQuotes(StageRoot),
      '',
      SW_HIDE,
      ewWaitUntilTerminated,
      ResultCode
    ) or (ResultCode <> 0) then
      RaiseException(Format('Không thể giải nén runtime (mã %d).', [ResultCode]));
    if not FileExists(StagedRuntime + '\{#AppExeName}') then
      RaiseException('Runtime đã tải không có executable hợp lệ.');
    if not SaveStringToFile(StagedRuntime + '\.runtime-bundle-id', RuntimeMarkerJson, False) then
      RaiseException('Không thể ghi runtime identity marker.');

    DownloadPage.SetText('Đang kiểm tra runtime mới', 'Chưa thay đổi bản đang hoạt động.');
    if not Exec(
      StagedRuntime + '\{#AppExeName}',
      '--smoke-test',
      StagedRuntime,
      SW_HIDE,
      ewWaitUntilTerminated,
      ResultCode
    ) or (ResultCode <> 0) then
      RaiseException(Format('Runtime mới không vượt qua smoke test (mã %d).', [ResultCode]));

    DelTree(PreviousRuntime, True, True, True);
    if DirExists(ActiveRuntime) and not RenameFile(ActiveRuntime, PreviousRuntime) then
      RaiseException('Không thể chuẩn bị bản cài hiện tại để nâng cấp; hãy đóng ứng dụng và thử lại.');
    if not RenameFile(StagedRuntime, ActiveRuntime) then
    begin
      if DirExists(PreviousRuntime) then
        RenameFile(PreviousRuntime, ActiveRuntime);
      if IsUpgrade then
        RaiseException('Không thể kích hoạt runtime mới; bản cũ đã được khôi phục.')
      else
        RaiseException('Không thể kích hoạt runtime mới trong lần cài đầu tiên.');
    end;
    DelTree(PreviousRuntime, True, True, True);
  finally
    DelTree(StageRoot, True, True, True);
    DownloadPage.Hide;
  end;
end;

procedure InitializeWizard;
var
  Index: Integer;
  Name: String;
  Hash: String;
  Size: Int64;
begin
  ActiveRuntime := ExpandConstant('{app}\runtime');
  PreviousRuntime := ExpandConstant('{app}\runtime.previous');
  IsUpgrade := DirExists(ActiveRuntime);
  IsRepair := SameRuntimeInstalled;
  TotalRuntimeBytes := 0;
  for Index := 1 to {#RuntimeVolumeCount} do
  begin
    GetVolumeInfo(Index, Name, Hash, Size);
    TotalRuntimeBytes := TotalRuntimeBytes + Size;
  end;
  DownloadPage := CreateDownloadPage(
    'Tải runtime AI Subtitle Studio',
    'Setup tự tiếp tục qua BITS và luôn kiểm tra SHA-256.',
    nil
  );
  RegisterExtraCloseApplicationsResource(False, ExpandConstant('{app}\runtime\{#AppExeName}'));
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if CheckForMutexes('AI-Subtitle-Studio-Runtime') then
    Result := 'AI Subtitle Studio đang chạy. Hãy đóng ứng dụng rồi bấm Thử lại trước khi nâng cấp.';
end;

function UpdateReadyMemo(
  Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo,
  MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String
): String;
var
  ModeText: String;
begin
  if IsRepair then
    ModeText := 'Sửa chữa AI Subtitle Studio {#AppVersion} (runtime đã có và đúng dấu vân tay)'
  else if IsUpgrade then
    ModeText := 'Nâng cấp AI Subtitle Studio lên {#AppVersion}'
  else
    ModeText := 'Cài mới AI Subtitle Studio {#AppVersion}';
  Result :=
    ModeText + NewLine + NewLine +
    MemoDirInfo + NewLine + NewLine +
    'Runtime bundle: {#RuntimeBundleId}' + NewLine +
    'Tải xuống tối đa: ' + IntToStr(TotalRuntimeBytes div 1048576) + ' MiB' + NewLine +
    'Dung lượng cài đặt: ' + IntToStr({#InstalledSizeBytes} div 1048576) + ' MiB' + NewLine +
    'Dung lượng tạm thời yêu cầu: ' + IntToStr({#TemporarySpaceBytes} div 1048576) + ' MiB' + NewLine + NewLine +
    MemoTasksInfo;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
    DownloadAndActivateRuntime;
end;

procedure UninstallOkClick(Sender: TObject);
begin
  UninstallOptionsAccepted := True;
  UninstallOptionsForm.Close;
end;

procedure UninstallCancelClick(Sender: TObject);
begin
  UninstallOptionsAccepted := False;
  UninstallOptionsForm.Close;
end;

function ReadConfiguredOutputPath: String;
begin
  if not RegQueryStringValue(
    HKCU,
    'Software\AI Subtitle Studio\AI Subtitle Studio',
    'default_output_dir',
    Result
  ) or (Trim(Result) = '') then
    Result := ExpandConstant('{userdocs}\AI Subtitle Studio\outputs');
end;

function ConfirmOutputCleanup: Boolean;
var
  OutputPath: String;
begin
  OutputPath := ReadConfiguredOutputPath;
  Result := MsgBox(
    'CẢNH BÁO: chỉ các file .srt được ứng dụng ghi nhận trong lịch sử sẽ bị xóa.' + #13#10 + #13#10 +
    'Đường dẫn output hiện tại:' + #13#10 + OutputPath + #13#10 + #13#10 +
    'Video nguồn và file không thuộc ứng dụng sẽ được giữ. Bạn có chắc muốn tiếp tục?',
    mbConfirmation,
    MB_YESNO
  ) = IDYES;
end;

function ShowUninstallOptions: Boolean;
var
  InfoLabel: TNewStaticText;
  OkButton: TNewButton;
  CancelButton: TNewButton;
begin
  UninstallOptionsForm := CreateCustomForm(ScaleX(560), ScaleY(230), False, True);
  UninstallOptionsAccepted := False;
  try
    UninstallOptionsForm.Caption := 'Gỡ cài đặt AI Subtitle Studio';
    UninstallOptionsForm.Position := poScreenCenter;

    InfoLabel := TNewStaticText.Create(UninstallOptionsForm);
    InfoLabel.Parent := UninstallOptionsForm;
    InfoLabel.Left := ScaleX(16);
    InfoLabel.Top := ScaleY(16);
    InfoLabel.Width := ScaleX(520);
    InfoLabel.Height := ScaleY(45);
    InfoLabel.AutoSize := False;
    InfoLabel.WordWrap := True;
    InfoLabel.Caption := 'Mặc định chỉ xóa ứng dụng. Model, lịch sử, API key và phụ đề của bạn sẽ được giữ lại.';

    PrivateDataCheckBox := TNewCheckBox.Create(UninstallOptionsForm);
    PrivateDataCheckBox.Parent := UninstallOptionsForm;
    PrivateDataCheckBox.Left := ScaleX(16);
    PrivateDataCheckBox.Top := ScaleY(78);
    PrivateDataCheckBox.Width := ScaleX(520);
    PrivateDataCheckBox.Caption := 'Xóa model, cache, log, lịch sử và API key';
    PrivateDataCheckBox.Checked := False;

    OwnedOutputsCheckBox := TNewCheckBox.Create(UninstallOptionsForm);
    OwnedOutputsCheckBox.Parent := UninstallOptionsForm;
    OwnedOutputsCheckBox.Left := ScaleX(16);
    OwnedOutputsCheckBox.Top := ScaleY(112);
    OwnedOutputsCheckBox.Width := ScaleX(520);
    OwnedOutputsCheckBox.Caption := 'Xóa phụ đề/output đã tạo';
    OwnedOutputsCheckBox.Checked := False;

    OkButton := TNewButton.Create(UninstallOptionsForm);
    OkButton.Parent := UninstallOptionsForm;
    OkButton.Caption := 'Tiếp tục gỡ';
    OkButton.Left := ScaleX(350);
    OkButton.Top := ScaleY(180);
    OkButton.Width := ScaleX(90);
    OkButton.OnClick := @UninstallOkClick;

    CancelButton := TNewButton.Create(UninstallOptionsForm);
    CancelButton.Parent := UninstallOptionsForm;
    CancelButton.Caption := 'Hủy';
    CancelButton.Left := ScaleX(450);
    CancelButton.Top := ScaleY(180);
    CancelButton.Width := ScaleX(90);
    CancelButton.OnClick := @UninstallCancelClick;

    UninstallOptionsForm.ShowModal;
    Result := UninstallOptionsAccepted;
    if Result then
    begin
      CleanupPrivateData := PrivateDataCheckBox.Checked;
      CleanupOwnedOutputs := OwnedOutputsCheckBox.Checked;
      if CleanupOwnedOutputs and not ConfirmOutputCleanup then
        CleanupOwnedOutputs := False;
    end;
  finally
    UninstallOptionsForm.Free;
  end;
end;

function InitializeUninstall: Boolean;
begin
  CleanupPrivateData := False;
  CleanupOwnedOutputs := False;
  Result := ShowUninstallOptions;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppExe: String;
  Params: String;
  ReportPath: String;
  ResultCode: Integer;
begin
  if (CurUninstallStep <> usUninstall) or
     (not CleanupPrivateData and not CleanupOwnedOutputs) then
    Exit;
  AppExe := ExpandConstant('{app}\runtime\{#AppExeName}');
  if not FileExists(AppExe) then
  begin
    MsgBox('Không tìm thấy cleanup helper; dữ liệu người dùng được giữ lại.', mbError, MB_OK);
    Exit;
  end;
  ReportPath := ExpandConstant('{tmp}\ai-subtitle-uninstall-cleanup.json');
  Params := '--cleanup-report ' + AddQuotes(ReportPath);
  if CleanupPrivateData then
    Params := Params + ' --cleanup-private-data';
  if CleanupOwnedOutputs then
    Params := Params + ' --cleanup-owned-outputs';
  if not Exec(AppExe, Params, ExpandConstant('{app}\runtime'), SW_HIDE, ewWaitUntilTerminated, ResultCode) or
     (ResultCode <> 0) then
    MsgBox(
      'Một phần dữ liệu không thể xóa. Ứng dụng đã ghi báo cáo tại:' + #13#10 + ReportPath,
      mbError,
      MB_OK
    );
end;
