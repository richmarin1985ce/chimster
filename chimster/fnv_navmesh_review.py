"""Cross-record review for native navigation candidates. No opaque NAVI synthesis."""
from collections import defaultdict
import math,struct,hashlib
from .fnv_navmesh import inspect as inspect_mesh
from .fnv_navi import inspect as inspect_navi

def fields(row):
    return [(tag.encode("ascii"),bytes.fromhex(value)) for tag,value in row["fields"]]

def review(meshes,navi,door_backlinks=(),*,tolerance=.01):
    if type(tolerance) not in (int,float) or not math.isfinite(tolerance) or not 0<tolerance<=1:
        raise ValueError("invalid seam tolerance")
    if not isinstance(meshes,list) or not 1<=len(meshes)<=4096:raise ValueError("mesh count limit")
    parsed={};locations={};issues=[];external=defaultdict(list);doors={}
    for row in meshes:
        fid=row["form_id"]
        if type(fid) is not int or not 0<fid<=0xffffffff or fid in parsed:raise ValueError("invalid mesh identity")
        p=fields(row);r,_=inspect_mesh(p)
        parsed[fid]=r
        location=row.get("location",r["raw_cell"]);grid=row.get("grid",[0,0])
        if type(location) is not int or not 0<location<=0xffffffff or len(grid)!=2 or any(type(v) is not int or not -32768<=v<=32767 for v in grid):
            raise ValueError("invalid expected NAVI location")
        locations[fid]=(location,tuple(grid))
        for issue in r["issues"]:issues.append({"code":"mesh-"+issue[0],"mesh":fid,"detail":list(issue[1:])})
        if len(r.get("grid_candidates",[]))!=1:issues.append({"code":"grid-framing-unverified","mesh":fid})
        for i,neighbors in enumerate(r["neighbors"]):
            for e,j in enumerate(neighbors):
                if r["flags"][i]&(1<<e) and 0<=j<len(r["external"]):
                    edge=r["external"][j]
                    external[(fid,i)].append((e,edge["raw_target"],edge["triangle"]))
        for d in r["doors"]:
            ref=d["raw_target"]
            if ref in doors:issues.append({"code":"duplicate-door-owner","door":ref})
            doors[ref]=(fid,d["triangle"])
    def endpoints(mesh,i,e):
        r=parsed[mesh];t=r["triangles"][i]
        return r["vertices"][t[e]],r["vertices"][t[(e+1)%3]]
    for (fid,i),entries in external.items():
        for e,target,j in entries:
            if target not in parsed or not 0<=j<len(parsed[target]["triangles"]):
                issues.append({"code":"external-target-unavailable","mesh":fid,"target":target,"triangle":j});continue
            reverse=[re for re,back,tri in external.get((target,j),[]) if back==fid and tri==i]
            if len(reverse)!=1:
                issues.append({"code":"external-reciprocity","mesh":fid,"triangle":i,"target":target});continue
            a,b=endpoints(fid,i,e);c,d=endpoints(target,j,reverse[0])
            if max(math.dist(a,d),math.dist(b,c))>tolerance:
                issues.append({"code":"external-seam-mismatch","mesh":fid,"triangle":i,"target":target})
    backlinks={}
    for row in door_backlinks:
        ref=row["reference"];pair=(row["mesh"],row["triangle"])
        if ref in backlinks:raise ValueError("duplicate XNDP backlink")
        backlinks[ref]=pair
    for ref,pair in doors.items():
        if backlinks.get(ref)!=pair:issues.append({"code":"door-backlink-mismatch","door":ref,"expected":pair})
    for ref in set(backlinks)-set(doors):issues.append({"code":"orphan-door-backlink","door":ref})
    index,_=inspect_navi(fields(navi));registered={}
    for e in index["entries"]:
        fid=e["mesh"];registered[fid]=(e["location"],tuple(e["grid"]))
        if fid not in parsed:issues.append({"code":"navi-mesh-outside-review","mesh":fid})
        elif registered[fid]!=locations[fid]:issues.append({"code":"navi-location-mismatch","mesh":fid})
    for fid in set(parsed)-set(registered):issues.append({"code":"navi-registration-missing","mesh":fid})
    for row in index.get("connections",[]):
        fid=row["mesh"]
        if fid not in parsed:continue
        r=parsed[fid]
        expected={e["raw_target"] for e in r["external"]}
        if set(row["standard"])|set(row["preferred"])!=expected:issues.append({"code":"nvci-neighbor-mismatch","mesh":fid})
        if set(row["doors"])!={d["raw_target"] for d in r["doors"]}:issues.append({"code":"nvci-door-mismatch","mesh":fid})
    return {"valid_known_fields":not issues,"issues":issues,"meshes":len(parsed),"doors":len(doors),
            "registered":len(registered),"opaque_navi_fields":index["opaque"],
            "review_required":["NAVI opaque NVMI suffix and NVCI semantics","independent native grid and GECK finalization"],
            "status":"review only; no playable ESP certification"}

def registration_manifest(meshes):
    """Explicit registration requests for a native finalizer; no invented NVMI tails."""
    out=[];seen=set()
    for row in meshes:
        fid=row["form_id"];parts=fields(row);report,_=inspect_mesh(parts)
        if type(fid) is not int or not 0<fid<=0xffffffff or fid in seen or report["issues"]:raise ValueError("invalid mesh candidate")
        seen.add(fid)
        location=row.get("location",report["raw_cell"]);xy=row.get("grid",[0,0])
        if type(location) is not int or not 0<location<=0xffffffff or len(xy)!=2 or any(type(v) is not int or not -32768<=v<=32767 for v in xy):raise ValueError("invalid location")
        out.append({"mesh":fid,"location":location,"grid":list(xy),"payload_sha256":hashlib.sha256(b"".join(k+struct.pack("<I",len(v))+v for k,v in parts)).hexdigest()})
    return {"registrations":out,"status":"NAVI registration manifest; native opaque data must be generated by verified finalizer"}
