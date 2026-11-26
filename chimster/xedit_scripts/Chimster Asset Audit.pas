unit UserScript;

// Original MIT-licensed Chimster audit script. Read-only.
// Select the records/plugins to audit in xEdit and Apply Script.
function CleanField(s: string): string;
begin
  Result := StringReplace(s, '|', '/', [rfReplaceAll]);
  Result := StringReplace(Result, #13, ' ', [rfReplaceAll]);
  Result := StringReplace(Result, #10, ' ', [rfReplaceAll]);
end;

function Process(e: IInterface): integer;
var sig, model, win: string;
begin
  Result := 0;
  sig := Signature(e);
  if (sig <> 'STAT') and (sig <> 'TREE') and (sig <> 'FLOR') and (sig <> 'GRAS') and (sig <> 'ACTI') and (sig <> 'MSTT') then
    Exit;
  model := GetElementEditValues(e, 'Model\MODL');
  if model = '' then model := GetElementEditValues(e, 'MODL');
  win := '0';
  if IsWinningOverride(e) then win := '1';
  AddMessage('CHIMSTER_AUDIT|' + sig + '|' +
    CleanField(GetFileName(GetFile(e))) + '|' +
    IntToHex(GetLoadOrderFormID(e), 8) + '|' +
    CleanField(EditorID(e)) + '|' + CleanField(model) + '|' + win);
end;

end.
