"""Explicit local git operations; no force pushes or automatic resets."""
from .workspace import git
def branches(root):
    return git(root,"branch","--format=%(refname:short)").splitlines()
def create_branch(root,name):
    if not isinstance(name,str) or not name or name.startswith("-"):raise ValueError("invalid branch name")
    git(root,"check-ref-format","--branch",name)
    return git(root,"branch",name)
def diff(root,paths=()):
    for p in paths:
        if not p or p.startswith(("/", "\\")) or ".." in p.replace("\\","/").split("/") or ":" in p:raise ValueError("relative path required")
    return git(root,"--literal-pathspecs","diff","HEAD","--",*paths)
def history(root,path,limit=25):
    if not 1<=limit<=1000 or not path or path.startswith(("/", "\\")) or ".." in path.replace("\\","/").split("/") or ":" in path:raise ValueError("invalid history request")
    return git(root,"--literal-pathspecs","log","-n",str(limit),"--format=%h %ad %s","--date=iso","--",path).splitlines()
