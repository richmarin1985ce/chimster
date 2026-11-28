"""Engine-neutral leveled list graph checks; no native layout assumptions."""
def validate(lists,types,allowed):
    """lists maps identity to entries (target, level, count).
    types maps effective identities to record signatures.
    allowed maps list signatures to permitted target signatures.
    """
    issues=[]
    graph={}
    for identity,entries in lists.items():
        graph[identity]=[]
        permitted=allowed.get(types.get(identity),())
        for index,(target,level,count) in enumerate(entries):
            if type(level)!=int or level<1 or type(count)!=int or count<1:
                issues.append((identity,index,"invalid_quantity_or_level"))
            if target not in types:issues.append((identity,index,"unresolved_target"))
            elif types[target] not in permitted:issues.append((identity,index,"incompatible_target"))
            if target in lists:graph[identity].append(target)
    colors={}
    for root in graph:
        if colors.get(root):continue
        colors[root]=1
        stack=[(root,iter(graph[root]))]
        while stack:
            node,edges=stack[-1]
            target=next(edges,None)
            if target is None:
                colors[node]=2;stack.pop();continue
            if colors.get(target)==1:issues.append((node,target,"cycle"))
            elif not colors.get(target):
                colors[target]=1;stack.append((target,iter(graph[target])))
    return issues
