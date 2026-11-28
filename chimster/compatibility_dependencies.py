"""Read-only dependency validation for explicitly selected game profiles."""
from .compatibility_audit import audit
from .loadorder import plugin_name

def validate(profile,plugins):
    seen=set()
    rows=[]
    issues=[]
    plugins=[(plugin_name(name),data) for name,data in plugins]
    available={name for name,_ in plugins}
    for name,data in plugins:
        if name in seen:
            issues.append((name,"duplicate_plugin",name))
            continue
        row=audit(profile,data)
        for master in row["masters"]:
            key=plugin_name(master)
            if key==name:issues.append((name,"self_dependency",key))
            elif key not in available:issues.append((name,"missing_master",key))
            elif key not in seen:issues.append((name,"late_master",key))
        seen.add(name)
        rows.append({"name":name,**row})
    return {"profile":profile,"plugins":rows,"issues":issues,"dependency_order_valid":not issues}
