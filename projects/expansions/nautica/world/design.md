# Fallout: Nautica — world and level design
Terrain: USGS/Census source recipes; 0.70 horizontal scale; actual downloads pending.
Source geometry, authored placement, native records and retail verification are distinct. No fabricated geography or proprietary assets.

## Initial slice
dock, street, lane, boathouse, marsh, beacon. Design links are not verified doors.

## Location inventory
- **Arrival dock** (dock) — slice; transition. Native: unbuilt.
- **Harbor main street** (street) — slice; exterior. Native: unbuilt.
- **Town side lane** (lane) — slice; exterior. Native: unbuilt.
- **Boathouse workshop** (boathouse) — slice; interior. Native: unbuilt.
- **Marsh path** (marsh) — slice; exterior. Native: unbuilt.
- **Beacon station** (beacon) — slice; hub. Native: unbuilt.
- **Town harbor market** (market) — town; hub. Native: unbuilt.
- **Salvage slip** (slip) — town; hub. Native: unbuilt.
- **Cargo warehouse** (warehouse) — town; interior. Native: unbuilt.
- **Town cistern** (cistern) — town; interior. Native: unbuilt.
- **Inland crossroads** (crossroads) — inland; hub. Native: unbuilt.
- **Refuge farm** (farm) — inland; hub. Native: unbuilt.
- **Open moor** (moor) — inland; exterior. Native: unbuilt.
- **Freshwater pond** (pond) — inland; exterior. Native: unbuilt.
- **Old utility bunker** (bunker) — inland; interior. Native: unbuilt.
- **Madaket-inspired fishing community** (west) — west; hub. Native: unbuilt.
- **Western dune trail** (dunes) — west; exterior. Native: unbuilt.
- **Surfside-inspired beach** (surf) — south; exterior. Native: unbuilt.
- **Grounded wreck** (wreck) — south; interior. Native: unbuilt.
- **Sheltered cove** (cove) — south; exterior. Native: unbuilt.
- **Eastern coastal station** (east) — east; hub. Native: unbuilt.
- **Polpis-inspired road junction** (polpis) — east; exterior. Native: unbuilt.
- **Eastern bluff** (cliff) — east; exterior. Native: unbuilt.
- **Navigation relay** (relay) — core; interior. Native: unbuilt.
- **Mainland return crossing** (exit) — core; transition. Native: unbuilt.
- **Harbor general store** (int_01) — town; interior / building; parent market; Trade and stories. Native: unbuilt.
- **Harbor inn** (int_02) — town; interior / building; parent market; Travelers and cargo clues. Native: unbuilt.
- **Town cottage** (int_03) — slice; interior / building; parent lane; Resident stories. Native: unbuilt.
- **Harbor dispatch office** (int_04) — slice; interior / building; parent street; Schedules and records. Native: unbuilt.
- **Salvage repair shed** (int_05) — town; interior / building; parent slip; Crafting and parts. Native: unbuilt.
- **Refuge farmhouse** (int_06) — inland; interior / building; parent farm; Agricultural stories. Native: unbuilt.
- **Farm equipment barn** (int_07) — inland; interior / building; parent farm; Repairs and supplies. Native: unbuilt.
- **Fishing community hall** (int_08) — west; interior / building; parent west; Meetings and trade. Native: unbuilt.
- **Coastal station quarters** (int_09) — east; interior / building; parent east; Rescue watch stories. Native: unbuilt.
- **Beacon keeper house** (int_10) — slice; interior / building; parent beacon; Navigation records. Native: unbuilt.
- **Grounded wreck lower decks** (int_11) — south; interior / dungeon; parent wreck; Ship exploration. Native: unbuilt.
- **Coastal sea cave** (int_12) — south; interior / dungeon; parent cove; Tidal routes and stores. Native: unbuilt.
- **Bunker utility levels** (int_13) — inland; interior / dungeon; parent bunker; Power and water puzzles. Native: unbuilt.
- **Old cistern passages** (int_14) — town; interior / dungeon; parent cistern; Water routing. Native: unbuilt.
- **Buried coastal shelter** (int_15) — west; interior / dungeon; parent dunes; Storm history. Native: unbuilt.
- **Navigation relay service levels** (int_16) — core; interior / dungeon; parent relay; Signal puzzle. Native: unbuilt.
- **Bluff service tunnel** (int_17) — east; interior / dungeon; parent cliff; Vertical route and missing watch. Native: unbuilt.
- **Sealed cargo hold** (int_18) — town; interior / dungeon; parent warehouse; Disputed cargo. Native: unbuilt.
- **Abandoned inland pumping station** (int_19) — inland; interior / dungeon; parent moor; Supply restoration. Native: unbuilt.
- **Storm-wrecked coastal vessel** (int_20) — south; interior / dungeon; parent surf; Wreck salvage and rescue clues. Native: unbuilt.
- **Arrival terminal** (int_21) — slice; interior / building; parent dock; Return passage. Native: unbuilt.
- **Inland meeting hall** (int_22) — inland; interior / building; parent crossroads; Community negotiations. Native: unbuilt.
- **Road junction shelter** (int_23) — east; interior / building; parent polpis; Travel routes and history. Native: unbuilt.
- **Fishing cottage** (int_24) — west; interior / building; parent west; Personal stories. Native: unbuilt.
- **Rescue equipment workshop** (int_25) — east; interior / building; parent east; Boat gear and maintenance. Native: unbuilt.

## Level-design contract
Each destination needs entry/exit, adjacency, room graph, encounter or social purpose, distinct discovery, lighting, loot, collision, native navmesh and accessibility. Each dungeon needs route variation or puzzle, optional reward and safe return. Parent associations are not runtime links. Native dimensions and performance require target-game testing.
