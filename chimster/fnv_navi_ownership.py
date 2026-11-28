"""Verify new NAVM cell/world ownership for native NAVI staging."""
import math
import struct


def registration(mesh, cell, report, cell_fields, groups, records):
    """Resolve one new mesh's registration from its actual group ancestry.

    Records and groups are indexed by raw FormID and byte offset respectively.
    The stage is restricted to new cells and worldspaces in one slot space.
    """
    def ancestor(row, kind, required=True):
        labels = [bytes.fromhex(groups[g]['label']) for g in row['groups'] if groups[g]['type'] == kind]
        if len(labels) != (1 if required else 0):
            raise ValueError('missing or ambiguous group ancestry')
        return labels[0] if required else None

    cid = report['raw_cell']
    if records.get(cid) != cell or cell['signature'] != 'CELL' or cell['flags'] & 0x420:
        raise ValueError('expected new nonpersistent active CELL')
    for kind in (6, 9):
        if ancestor(mesh, kind) != struct.pack('<I', cid):
            raise ValueError('NAVM group owner differs from DATA cell')
    if len(cell_fields.get(b'DATA', b'')) != 1:
        raise ValueError('invalid CELL flags')
    if cell_fields[b'DATA'][0] & 1:
        for row in (cell, mesh):
            ancestor(row, 1, False)
            ancestor(row, 4, False)
            ancestor(row, 5, False)
        if b'XCLC' in cell_fields:
            raise ValueError('interior CELL has exterior coordinates')
        return {}
    world_label = ancestor(cell, 1)
    world = struct.unpack('<I', world_label)[0]
    parent = records.get(world)
    if not parent or parent['signature'] != 'WRLD' or parent['flags'] & 0x20 or world == cid:
        raise ValueError('expected new active parent WRLD')
    if ancestor(mesh, 1) != world_label:
        raise ValueError('NAVM and CELL worldspace differ')
    coords = cell_fields.get(b'XCLC', b'')
    if len(coords) not in (8, 12):
        raise ValueError('missing or malformed exterior XCLC')
    x, y = struct.unpack_from('<ii', coords)
    if not all(-32768 <= v <= 32767 for v in (x, y)):
        raise ValueError('exterior coordinates exceed NVMI range')
    for row in (cell, mesh):
        for kind, size in ((4, 32), (5, 8)):
            if ancestor(row, kind) != struct.pack('<hh', y//size, x//size):
                raise ValueError('exterior block or sub-block mismatch')
    for v in report['vertices']:
        if len(v) != 3 or not all(math.isfinite(k) for k in v):
            raise ValueError('invalid NAVM vertex')
        if not (x*4096-0.01 <= v[0] <= (x+1)*4096+0.01 and y*4096-0.01 <= v[1] <= (y+1)*4096+0.01):
            raise ValueError('NAVM vertex outside owning exterior cell')
    return {'world': world, 'grid': [x, y]}
