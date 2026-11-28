"""Read-only cell neighborhood to portable viewport scene adapter."""
from math import degrees, isfinite, floor
from .world_browser import PLACED, label
from .scene import Scene, Instance
from .architecture import box_mesh
from .lod import terrain_grid
from .max_height import decode_land

UNITS = 128.0


def preview(browser, key, radius=0, models=None):
    if type(radius) is not int or not 0 <= radius <= 2:
        raise ValueError("Cell radius must be 0, 1 or 2")
    cell = browser.active.get(key)
    if not cell or cell["signature"] != "CELL":
        raise ValueError("Select a live CELL")
    grid = cell.get("grid")
    world = cell.get("world")
    cells = [cell]
    issues = []
    if grid is not None and world is not None:
        for dy in range(-radius, radius+1):
            for dx in range(-radius, radius+1):
                coord = (grid[0]+dx, grid[1]+dy)
                matches = browser.coordinates.get((world, coord), ())
                if len(matches) > 1:
                    issues.append(f"Ambiguous cell {coord}")
                elif len(matches) == 1 and matches[0]["key"] != key:
                    cells.append(matches[0])
    ox, oy = (grid[0]*4096,grid[1]*4096) if grid is not None else (0,0)
    assets = {"reference":box_mesh((-.18,-.18,0),(.18,.18,.65),"proxy")}
    instances = []
    refs = {}
    land_count = 0
    skipped = 0
    model_count = 0
    model_failures = set()
    for row in cells:
        coord = row.get("grid")
        children = browser.children.get(row["key"], ())
        lands = [r for r in children if r["signature"] == "LAND"]
        if coord is not None and len(lands) == 1 and "height_raw" in lands[0]:
            land = lands[0]
            try:
                heights = [[h/UNITS for h in line] for line in decode_land(land["height_raw"])]
                asset = "land:"+label(land["key"])
                assets[asset] = terrain_grid(heights, spacing=1)
                instances.append(Instance(asset,asset,(coord[0]*4096-ox)/UNITS,(coord[1]*4096-oy)/UNITS))
                land_count += 1
            except ValueError as exc:
                issues.append(f"Invalid LAND {label(land['key'])}: {exc}")
        elif len(lands)>1:
            issues.append(f"Ambiguous LAND for {label(row['key'])}")
        for ref in children:
            if ref["signature"] in PLACED:
                # Spatial persistent refs are gathered by coordinates below.
                if coord is not None and world is not None and ref.get("persistent"):
                    continue
                refs[ref["key"]] = ref
        if coord is not None and world is not None:
            for ref in browser.persistent_by_grid.get((world,coord),()):
                refs[ref["key"]] = ref
    for ref in sorted(refs.values(),key=lambda r:r["key"]):
        pos = ref.get("position")
        if pos is None:
            skipped += 1
            continue
        x,y,z = (pos[0]-ox)/UNITS,(pos[1]-oy)/UNITS,pos[2]/UNITS
        yaw = degrees(ref.get("rotation",(0,0,0))[2])
        scale = ref.get("scale",1)
        if not all(isfinite(v) and abs(v)<=1e7 for v in (x,y,z,yaw,scale)) or scale<=0:
            skipped += 1
            continue
        if len(instances)>=5000:
            skipped += 1
            continue
        asset = "reference"
        base = browser.active.get(ref.get("base"),{})
        model = base.get("model")
        if models is not None and model and model not in model_failures:
            candidate = "model:"+model.casefold()
            try:
                if candidate not in assets:
                    assets[candidate] = models(model)
                asset = candidate
                model_count += 1
            except Exception as exc:
                model_failures.add(model)
                issues.append(f"Model {model}: {str(exc)[:200]}")
        instances.append(Instance(label(ref["key"]),asset,x,y,z,yaw,scale))
    environment={}
    if world in browser.worlds and browser.profile=="new-vegas":
        from .world_environment import effective
        environment=effective(browser,world)
    return Scene(assets,instances), {
        "cell":label(key),"cells":len(cells),"grid":grid,"land_tiles":land_count,
        "proxy_references":len(instances)-land_count-model_count,"model_references":model_count,"skipped_references":skipped,
        "origin_game_units":(ox,oy,0),"units_per_preview_unit":UNITS,
        "issues":issues,"environment":environment,"mode":"Read-only LAND and optional static loose NIF geometry; unsupported assets use markers"
    }


class Neighborhood:
    """Camera-driven bounded neighborhood loader. Coordinates are absolute game units."""
    def __init__(self,browser,key,radius=1,models=None):
        row=browser.active.get(key)
        if row is None or row["signature"]!="CELL":
            raise ValueError("Select a live CELL")
        if type(radius) is not int or not 0<=radius<=2:
            raise ValueError("Invalid neighborhood radius")
        self.browser=browser
        self.world=row["world"]
        self.key=key
        self.grid=row.get("grid")
        self.radius=radius
        self.models=models

    def move(self,x,y):
        if self.world is None or self.grid is None or not all(isfinite(v) and abs(v)<=1e9 for v in (x,y)):
            return None
        grid=(floor(x/4096),floor(y/4096))
        if grid==self.grid:return None
        matches=self.browser.coordinates.get((self.world,grid),())
        if len(matches)!=1:return None
        key=matches[0]["key"]
        scene,report=preview(self.browser,key,self.radius,self.models)
        self.key=key
        self.grid=grid
        return scene,report
