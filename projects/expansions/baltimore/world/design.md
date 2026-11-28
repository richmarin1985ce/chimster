# Fallout: Baltimore — world and level design
Terrain: USGS/Census source recipes; 0.35 horizontal scale; actual downloads pending.
Source geometry, authored placement, native records and retail verification are distinct. No fabricated geography or proprietary assets.

## Initial slice
arrival, market, warehouse, tunnel, refuge. Design links are not verified doors.

## Location inventory
- **Arrival approach** (arrival) — slice; transition. Native: unbuilt.
- **Harbor market** (market) — slice; hub. Native: unbuilt.
- **Harbor warehouse** (warehouse) — slice; interior. Native: unbuilt.
- **Service tunnel** (tunnel) — slice; interior. Native: unbuilt.
- **Rowhouse refuge** (refuge) — slice; hub. Native: unbuilt.
- **Eastworks salvage yard** (yard) — east; hub. Native: unbuilt.
- **Utility plant** (plant) — east; interior. Native: unbuilt.
- **Industrial rail spur** (rail) — east; exterior. Native: unbuilt.
- **Crane platform** (crane) — east; exterior. Native: unbuilt.
- **Industrial basin** (canal) — east; exterior. Native: unbuilt.
- **Protection checkpoint** (checkpoint) — downtown; hub. Native: unbuilt.
- **Inland transit station** (station) — downtown; hub. Native: unbuilt.
- **Damaged shopping arcade** (arcade) — downtown; interior. Native: unbuilt.
- **Downtown rooftop route** (roof) — downtown; exterior. Native: unbuilt.
- **Abandoned transit tunnel** (subway) — downtown; interior. Native: unbuilt.
- **Residential clinic** (clinic) — west; interior. Native: unbuilt.
- **Rowhouse block** (rowblock) — west; exterior. Native: unbuilt.
- **Shelter school** (school) — west; interior. Native: unbuilt.
- **Water distribution node** (water) — west; interior. Native: unbuilt.
- **Overgrown neighborhood park** (park) — west; exterior. Native: unbuilt.
- **Harbor crossing approach** (bridge) — south; exterior. Native: unbuilt.
- **Ferry slip** (ferry) — south; exterior. Native: unbuilt.
- **Dry dock** (drydock) — south; interior. Native: unbuilt.
- **Transit switching room** (switch) — core; interior. Native: unbuilt.
- **Capital Wasteland return** (exit) — core; transition. Native: unbuilt.
- **Harbor diner** (int_01) — slice; interior / building; parent market; Local stories. Native: unbuilt.
- **Waterfront general store** (int_02) — slice; interior / building; parent market; Trade and supplies. Native: unbuilt.
- **Dock cooperative office** (int_03) — slice; interior / building; parent market; Cargo claims. Native: unbuilt.
- **Occupied rowhouse** (int_04) — west; interior / building; parent rowblock; Residents and quests. Native: unbuilt.
- **Vacant rowhouse** (int_05) — west; interior / building; parent rowblock; Environmental stories. Native: unbuilt.
- **Shared rowhouse workshop** (int_06) — west; interior / building; parent rowblock; Repairs and utilities. Native: unbuilt.
- **Transit ticket hall** (int_07) — downtown; interior / building; parent station; Routes and maps. Native: unbuilt.
- **Industrial machine shop** (int_08) — east; interior / building; parent yard; Crafting. Native: unbuilt.
- **Clinic treatment annex** (int_09) — west; interior / building; parent clinic; Supply stories. Native: unbuilt.
- **School classroom wing** (int_10) — west; interior / building; parent school; Community restoration. Native: unbuilt.
- **Warehouse cold storage** (int_11) — slice; interior / dungeon; parent warehouse; Power and cargo puzzle. Native: unbuilt.
- **Harbor storm drains** (int_12) — slice; interior / dungeon; parent tunnel; Flooded alternate routes. Native: unbuilt.
- **Abandoned subway platforms** (int_13) — downtown; interior / dungeon; parent subway; Transit exploration. Native: unbuilt.
- **Utility plant basement** (int_14) — east; interior / dungeon; parent plant; Electrical puzzle. Native: unbuilt.
- **Underground shopping concourse** (int_15) — downtown; interior / dungeon; parent arcade; Collapsed shops and rescue. Native: unbuilt.
- **Office tower interior** (int_16) — downtown; interior / dungeon; parent roof; Vertical traversal. Native: unbuilt.
- **Dry dock maintenance tunnels** (int_17) — south; interior / dungeon; parent drydock; Machinery and hidden stores. Native: unbuilt.
- **Freight depot interior** (int_18) — east; interior / dungeon; parent rail; Industrial encounters. Native: unbuilt.
- **Water reservoir chambers** (int_19) — west; interior / dungeon; parent water; Supply routing. Native: unbuilt.
- **Bridge service chambers** (int_20) — south; interior / dungeon; parent bridge; Infrastructure and bypass. Native: unbuilt.
- **Park pavilion** (int_21) — west; interior / building; parent park; Community gatherings. Native: unbuilt.
- **Protection crew office** (int_22) — downtown; interior / building; parent checkpoint; Toll records. Native: unbuilt.
- **Ferry terminal building** (int_23) — south; interior / building; parent ferry; Travel and schedules. Native: unbuilt.
- **Basin maintenance shed** (int_24) — east; interior / building; parent canal; Tools and routes. Native: unbuilt.
- **Neighborhood assembly hall** (int_25) — slice; interior / building; parent refuge; Local decisions. Native: unbuilt.

## Level-design contract
Each destination needs entry/exit, adjacency, room graph, encounter or social purpose, distinct discovery, lighting, loot, collision, native pathgrid/navmesh and accessibility. Each dungeon needs a route variation or puzzle, optional reward and safe return. Parent associations are not runtime links. Native dimensions and performance require target-game testing.
