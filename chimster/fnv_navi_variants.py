"""Explicit, reference-checkable FNV NVMI variants. Island writing stays disabled."""
import math
import struct


def _form(value):
    if type(value) is not int or not 0 < value <= 0xffffffff or not value & 0xffffff:
        raise ValueError('invalid NVMI FormID')
    return value


def _grid(grid, order):
    if order not in ('xy', 'yx'):
        raise ValueError('explicit grid order xy or yx required')
    if len(grid) != 2 or any(type(v) is not int or not -32768 <= v <= 32767 for v in grid):
        raise ValueError('invalid signed exterior grid')
    return tuple(grid if order == 'xy' else reversed(grid))


def ordinary(owner, location, vertices, *, grid=(0, 0), grid_order, preferred_value=0.0):
    """32-byte non-island candidate; preferred value is explicit, not inferred."""
    if not 1 <= len(vertices) <= 32768 or any(len(p) != 3 or not all(type(x) in (int, float) and math.isfinite(x) and abs(x) <= 1e7 for x in p) for p in vertices):
        raise ValueError('invalid NVMI vertices')
    if type(preferred_value) not in (int, float) or not math.isfinite(preferred_value) or not 0 <= preferred_value <= 100:
        raise ValueError('invalid explicit preferred value')
    center = [math.fsum(p[k] for p in vertices) / len(vertices) for k in range(3)]
    return struct.pack('<IIIhh4f', 0, _form(owner), _form(location), *_grid(grid, grid_order), *center, preferred_value)


def decode(raw, *, grid_order):
    """Inspect ordinary and candidate island layout; reject unexplained bytes."""
    if len(raw) < 32:
        raise ValueError('truncated NVMI')
    flags, owner, location, a, b, x, y, z = struct.unpack_from('<IIIhh3f', raw)
    _form(owner); _form(location)
    grid = _grid((a, b), grid_order)
    preferred = struct.unpack_from('<f', raw, len(raw)-4)[0]
    if not all(math.isfinite(v) for v in (x, y, z, preferred)):
        raise ValueError('nonfinite NVMI data')
    result = {'flags': flags, 'mesh': owner, 'location': location, 'grid': grid,
              'approximate_position': (x, y, z), 'preferred_value': preferred}
    if not flags & 0x20:
        if len(raw) != 32:
            raise ValueError('unsupported ordinary NVMI suffix')
        return {**result, 'variant': 'ordinary'}
    if len(raw) < 60:
        raise ValueError('truncated island NVMI')
    bounds = struct.unpack_from('<6f', raw, 28)
    nv, nt = struct.unpack_from('<HH', raw, 52)
    if not 1 <= nv <= 32768 or not 1 <= nt <= 32768 or len(raw) != 60 + nv*12 + nt*6:
        raise ValueError('invalid island counts or trailing data')
    if any(not math.isfinite(v) for v in bounds) or any(bounds[k] > bounds[k+3] for k in range(3)):
        raise ValueError('invalid island bounds')
    end = 56 + nv*12
    vertices = list(struct.iter_unpack('<3f', raw[56:end]))
    triangles = list(struct.iter_unpack('<3H', raw[end:-4]))
    if any(not all(math.isfinite(v) and bounds[k]-0.01 <= v <= bounds[k+3]+0.01 for k, v in enumerate(p)) for p in vertices):
        raise ValueError('island vertices outside declared bounds')
    if any(len(set(t)) != 3 or any(i >= nv for i in t) for t in triangles):
        raise ValueError('invalid island triangle indices')
    return {**result, 'variant': 'island-candidate-layout', 'bounds': bounds, 'vertices': vertices, 'triangles': triangles}


def infer_grid_order(references):
    """Require at least one unequal coordinate and agreement across all references."""
    if not references:
        raise ValueError('native exterior reference required')
    possible = {'xy', 'yx'}
    for raw, expected in references:
        expected = _grid(expected, 'xy')
        possible = {order for order in possible if decode(raw, grid_order=order)['grid'] == expected}
    if len(possible) != 1:
        raise ValueError('ambiguous or conflicting native grid order')
    return possible.pop()


def split_neighbors(actual, preferred):
    """Explicit candidate preferred partition; never classify from slope or flag alone."""
    actual = set(_form(v) for v in actual)
    preferred = set(_form(v) for v in preferred)
    if not preferred <= actual:
        raise ValueError('preferred connection is not an actual NAVM neighbor')
    return sorted(actual-preferred), sorted(preferred)


def island(owner, location, vertices, triangles, *, reference, reference_vertices, reference_triangles,
           grid=(0, 0), grid_order, preferred_value=0.0):
    """Experimental island payload only, gated by a byte-exact local reference.

    A reference must demonstrate that its island geometry is the native NAVM
    geometry verbatim, including indexing and ordering. No assumption about
    the engine's island classification or simplified island shapes is made.
    """
    def encode(owner, location, vertices, triangles, *, grid, preferred_value):
        header = ordinary(owner, location, vertices, grid=grid, grid_order=grid_order,
                          preferred_value=preferred_value)
        vs = [struct.unpack('<3f', struct.pack('<3f', *p)) for p in vertices]
        if not 1 <= len(triangles) <= 32768:
            raise ValueError('invalid island triangle count')
        seen = set()
        for t in triangles:
            if len(t) != 3 or len(set(t)) != 3 or any(type(i) is not int or not 0 <= i < len(vs) for i in t):
                raise ValueError('invalid island triangle indices')
            key = tuple(sorted(t))
            if key in seen:
                raise ValueError('duplicate island triangle')
            seen.add(key)
            a,b,c = [vs[i] for i in t]
            u = [b[k]-a[k] for k in range(3)]; v = [c[k]-a[k] for k in range(3)]
            if math.hypot(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]) <= 1e-10:
                raise ValueError('degenerate island triangle')
        lo = [min(p[k] for p in vs) for k in range(3)]
        hi = [max(p[k] for p in vs) for k in range(3)]
        result = (struct.pack('<I',0x20) + header[4:28] + struct.pack('<6fHH',*lo,*hi,len(vs),len(triangles))
                  + b''.join(struct.pack('<3f',*p) for p in vs)
                  + b''.join(struct.pack('<3H',*t) for t in triangles) + header[28:])
        decode(result,grid_order=grid_order)
        return result
    sample = decode(reference,grid_order=grid_order)
    if sample['variant'] != 'island-candidate-layout' or sample['flags'] != 0x20:
        raise ValueError('requires an ordinary island reference with no other flags')
    reproduced = encode(sample['mesh'],sample['location'],reference_vertices,reference_triangles,
                        grid=sample['grid'],preferred_value=sample['preferred_value'])
    if reproduced != reference:
        raise ValueError('local island reference does not match the candidate serialization convention')
    return encode(owner,location,vertices,triangles,grid=grid,preferred_value=preferred_value)
