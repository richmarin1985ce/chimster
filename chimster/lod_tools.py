"""Chimster LOD workflows. No external executable integrations."""
import math

def workflow(game):
    if game in ("newvegas","new-vegas","fallout3"):
        return ["index worldspace and winning LAND records","build native terrain NIF/DDS and LODSettings candidates",
                "build native static object candidates from selected game assets","audit and verify in game"]
    if game=="openmw":return ["write proposed paging settings","benchmark runtime"]
    return ["build portable geometry and texture tiers","game-specific native LOD writer pending"]

def openmw_settings(distance=32768,min_size=.023):
    if not math.isfinite(distance) or distance<=0 or not math.isfinite(min_size) or not 0<min_size<=1:raise ValueError("invalid paging settings")
    return "[Camera]\nviewing distance = "+str(distance)+"\n\n[Terrain]\ndistant terrain = true\nobject paging = true\nobject paging min size = "+str(min_size)+"\n"
