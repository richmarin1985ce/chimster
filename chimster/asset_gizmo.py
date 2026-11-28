"""Selection transforms and screen-axis gesture math for Asset Forge."""
from math import isfinite, radians, sin, cos, exp
from copy import deepcopy
from .flora import cross

def pivot(mesh,ids):
    return tuple(sum(mesh.vertices[i][k] for i in ids)/len(ids) for k in range(3))

def transformed(mesh,ids,operation,axis,amount):
    if operation not in ("move","rotate","scale") or type(axis) is not int or axis not in range(3) or not isfinite(amount):
        raise ValueError("Invalid gizmo transform")
    if operation=="scale" and not .001<=amount<=1000:raise ValueError("Scale outside safe range")
    m=deepcopy(mesh);center=pivot(mesh,ids);a,b=(axis+1)%3,(axis+2)%3
    angle=radians(amount%360);c,s=cos(angle),sin(angle)
    for i in ids:
        v=list(mesh.vertices[i])
        if operation=="move":v[axis]+=amount
        elif operation=="scale":v[axis]=center[axis]+(v[axis]-center[axis])*amount
        else:
            x,y=v[a]-center[a],v[b]-center[b]
            v[a],v[b]=center[a]+c*x-s*y,center[b]+s*x+c*y
        m.vertices[i]=tuple(v)
    for t,_ in m.faces:
        if ids.intersection(t):
            p,q,r=[m.vertices[i] for i in t]
            n=cross(tuple(y-x for x,y in zip(p,q)),tuple(y-x for x,y in zip(p,r)))
            if not any(n):raise ValueError("Transform collapses a triangle")
    return m

def gesture(operation,start,end,axis_pixels):
    dx,dy=axis_pixels;den=dx*dx+dy*dy
    if den<4:raise ValueError("Axis nearly perpendicular to screen; orbit first")
    signed=((end[0]-start[0])*dx+(end[1]-start[1])*dy)/den
    if operation=="move":return signed
    if operation=="rotate":return signed*45
    if operation=="scale":return exp(max(-6.9,min(6.9,signed)))
    raise ValueError("Unknown gizmo operation")
