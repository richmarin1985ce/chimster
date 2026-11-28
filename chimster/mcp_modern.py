"""Stateless 2026-07-28 core subset. Legacy sessions retain privileged tools."""
VERSION="2026-07-28"
PREFIX="io.modelcontextprotocol/"
METHODS={"server/discover","ping","tools/list","tools/call","resources/list","resources/templates/list","resources/read"}
# Only intrinsically read-only operations with no session state or local UI access.
TOOLS={"chimster_capabilities","project_status","project_artifacts","project_artifact","project_verify",
       "project_read_text","project_revision_diff","project_plugin_inspect","native_record_browse","native_record_detail",
       "fnv_record_inspect","fnv_world_check","asset_inspect_audio","asset_inspect_mesh","asset_inspect_scene","asset_inspect_font",
       "check_quest","check_interior","check_papyrus","check_legacy_script","check_navmesh_registration"}

def error(msg,code,message):
    return {"jsonrpc":"2.0","id":msg.get("id"),"error":{"code":code,"message":message}}

def modern_request(msg):
    params=msg.get("params",{})
    meta=params.get("_meta",{}) if isinstance(params,dict) else {}
    return msg.get("method")=="server/discover" or isinstance(meta,dict) and meta.get(PREFIX+"protocolVersion")==VERSION

def dispatch(bridge,msg):
    method=msg.get("method")
    params=msg.get("params",{})
    if msg.get("jsonrpc")!="2.0" or type(msg.get("id")) not in (int,str) or not isinstance(params,dict):
        return error(msg,-32600,"Invalid request")
    meta=params.get("_meta",{})
    if not isinstance(meta,dict) or meta.get(PREFIX+"protocolVersion")!=VERSION:
        return error(msg,-32022,"Unsupported protocol version")
    if not isinstance(meta.get(PREFIX+"clientCapabilities"),dict):
        return error(msg,-32602,"Missing client capabilities")
    if method not in METHODS:return error(msg,-32601,"Method not found")
    tools=[d for name,(d,_) in bridge.registry.items() if name in TOOLS]
    def capabilities():
        return {"application":"Chimster","transport":bridge.transport,"access":"read-only",
                "protocolVersion":VERSION,"tools":sorted(d["name"] for d in tools),"project_selected":bridge.project is not None,
                "session_operations":False}
    try:
        if method=="server/discover":
            result={"supportedVersions":[VERSION],"capabilities":{"tools":{},"resources":{}},
                    "instructions":"Read-only stateless project access. Use legacy stdio for approved editing."}
        elif method=="ping":result={}
        elif method=="tools/list":result={"tools":tools}
        elif method=="tools/call":
            name=params.get("name")
            if name not in {d["name"] for d in tools}:return error(msg,-32602,"Tool unavailable")
            if name=="chimster_capabilities":
                import json
                result={"content":[{"type":"text","text":json.dumps(capabilities())}]}
            else:result=bridge.call({k:v for k,v in params.items() if k!="_meta"})
        elif method=="resources/list":
            result={"resources":[r for r in bridge.resources() if r["uri"]!="chimster://editor/context"]}
        elif method=="resources/templates/list":result={"resourceTemplates":bridge.resource_templates()}
        else:
            uri=params.get("uri")
            if uri=="chimster://editor/context":return error(msg,-32602,"Resource unavailable")
            if uri=="chimster://capabilities":
                import json
                result={"contents":[{"uri":uri,"mimeType":"application/json","text":json.dumps(capabilities())}]}
            else:result=bridge.read_resource(uri)
    except (ValueError,KeyError,TypeError,OSError):
        return error(msg,-32602,"Invalid params")
    result["resultType"]="complete"
    result["_meta"]={PREFIX+"serverInfo":{"name":"chimster","version":"0.1.0"}}
    if method in ("server/discover","tools/list","resources/list","resources/templates/list","resources/read"):
        result.update(ttlMs=0,cacheScope="private")
    return {"jsonrpc":"2.0","id":msg["id"],"result":result}
