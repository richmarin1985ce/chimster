"""Use project artifacts as inputs and publish plugin + FormID ledger together."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
from .project import identifier,read_json
from .formids import FormIDs
def build(project,kind,source_key,output_key,filename,expected,master_keys=(),script_draft=False):
    manifest=project.read()
    if manifest["revision"]!=expected:raise ValueError("stale project revision")
    if manifest["game"]!="newvegas":raise ValueError("native project build currently supports New Vegas")
    if kind not in {"records","quest"}:raise ValueError("unsupported project build kind")
    identifier(output_key);ledger_key=identifier(output_key+".ids")
    if not isinstance(filename,str) or Path(filename).name!=filename or any(c in filename for c in "/\\:") or not filename.lower().endswith(".esp"):raise ValueError("new ESP filename required")
    if source_key in {output_key,ledger_key} or set(master_keys)&{output_key,ledger_key}:raise ValueError("input and output keys overlap")
    if manifest["artifacts"][source_key]["kind"]!=kind:raise ValueError("wrong source artifact kind")
    if output_key in manifest["artifacts"] and (manifest["artifacts"][output_key]["kind"]!="plugin" or manifest["artifacts"][output_key]["filename"]!=filename or ledger_key not in manifest["artifacts"]):raise ValueError("previous output requires matching ledger and plugin name")
    if ledger_key in manifest["artifacts"] and manifest["artifacts"][ledger_key]["kind"]!="ledger":raise ValueError("wrong ledger kind")
    prior=read_json(project.object(ledger_key)) if ledger_key in manifest["artifacts"] else None
    if ledger_key in manifest["artifacts"] and output_key not in manifest["artifacts"]:raise ValueError("ledger without plugin")
    ids=FormIDs(filename,prior)
    spec=read_json(project.object(source_key))
    with TemporaryDirectory(prefix="chimster-build-") as d:
        p=Path(d);masters=[];names={filename.casefold()}
        for k in master_keys:
            a=manifest["artifacts"][k]
            if a["kind"]!="plugin" or a["filename"].casefold() in names:raise ValueError("invalid or duplicate master artifact")
            names.add(a["filename"].casefold());target=p/a["filename"];project.export(k,target);masters.append(target)
        output=p/filename
        if kind=="records":
            from .record_project import export
            result=export(spec,output,masters,ids)
        else:
            from .fnv_quest import export
            result=export(spec,output,masters,ids,script_draft=script_draft)
        ledger=p/(filename+".formids.json");ledger.write_text(json.dumps(ids.snapshot(),indent=2),encoding="utf-8")
        after=project.batch([{"op":"add","id":output_key,"kind":"plugin","source":str(output),"replace":output_key in manifest["artifacts"]},{"op":"add","id":ledger_key,"kind":"ledger","source":str(ledger),"replace":ledger_key in manifest["artifacts"]}],expected)
    result.pop("output",None)
    return {"revision":after["revision"],"plugin_artifact":output_key,"ledger_artifact":ledger_key,"build":result}
