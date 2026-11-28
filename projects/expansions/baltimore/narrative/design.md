# Fallout: Baltimore — narrative design
Review snapshot, 2026-11-28. All additions remain proposals unless creator-locked. Existing canonical quest IDs retained.

## Factions
- **Harbor Cooperative** (docks): Maintain shared docking and water access
- **Breakwater Crew** (crew): Charge for protection and control transit chokepoints
- **Rowhouse Assembly** (row): Preserve residential autonomy and utilities
- **Eastworks Salvagers** (salvage): Keep industry functioning; divided over exclusive contracts

## Principal cast
- **Mara Bell** (mara): Dock organizer defending shared access. Faction: docks; home: market.
- **Reed Knox** (reed): Protection captain negotiating leverage. Faction: crew; home: checkpoint.
- **Nia Mercer** (nia): Community steward seeking potable supply. Faction: row; home: refuge.
- **Ellis Ward** (ellis): Mechanic tracing failed transit hardware. Faction: salvage; home: yard.
- **Jo Pike** (jo): Warehouse clerk tracking missing provisions. Faction: docks; home: warehouse.
- **Cal Henson** (cal): Medic prioritizing independent routes. Faction: row; home: clinic.
- **Del Finch** (del): Guard willing to change terms. Faction: crew; home: bridge.
- **Ada Wynn** (ada): Engineer seeking a stable utility network. Faction: salvage; home: plant.

## Campaign and optional quests
### BL_MQ01 — A Closed Harbor
main; prerequisites: entry; locations: arrival, market; actors: mara.
Objective: Find why transit failed.
Resolution design: offer aid or trade for information.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_MQ02 — Under the Street
main; prerequisites: BL_MQ01; locations: warehouse, tunnel, refuge; actors: jo, nia.
Objective: Restore a supply route to refuge.
Resolution design: repair, negotiate or use alternate path.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_MQ03 — The Price of Passage
main; prerequisites: BL_MQ02; locations: checkpoint, station, bridge; actors: reed, del.
Objective: Expose competing claims on transit.
Resolution design: bargain, collect records or bypass toll.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_MQ04 — East of the Water
main; prerequisites: BL_MQ03; locations: yard, plant, rail; actors: ellis, ada.
Objective: Diagnose infrastructure failure.
Resolution design: repair with parts or arrange alternative supply.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_MQ05 — A City of Blocks
main; prerequisites: BL_MQ04; locations: rowblock, clinic, water; actors: nia, cal.
Objective: Secure residential agreement.
Resolution design: aid clinic or present reliable trade plan.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_MQ06 — The Harbor Accord
main; prerequisites: BL_MQ05; locations: switch, market, drydock; actors: mara, reed, ada.
Objective: Choose transit governance.
Resolution design: shared access, negotiated tolls or decentralized routes.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_MQ07 — Open Passage
main; prerequisites: BL_MQ06; locations: ferry, exit; actors: mara, nia.
Objective: Leave or continue local work.
Resolution design: report results and preserve original game endings.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_SQ01 — The Missing Crate
side; prerequisites: BL_MQ02; locations: warehouse, arcade; actors: jo.
Objective: Trace a missing shipment.
Resolution design: return goods or compensate owners.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_SQ02 — Above the Grid
side; prerequisites: BL_MQ03; locations: roof, subway; actors: del.
Objective: Find alternate safe crossing.
Resolution design: survey roof or tunnel.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_SQ03 — A Light in the Row
side; prerequisites: BL_MQ04; locations: school, water; actors: cal.
Objective: Restore neighborhood utility.
Resolution design: repair or share generator.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_SQ04 — The Block Committee
side; prerequisites: BL_MQ02; locations: rowblock, refuge; actors: nia, cal.
Objective: Mediate a dispute over a shared rowhouse entrance and water access.
Resolution design: repair communal access or negotiate separate routes.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_SQ05 — The Water Vote
side; prerequisites: BL_SQ04; locations: school, water; actors: nia, ada.
Objective: Organize a neighborhood vote on distribution terms.
Resolution design: shared utility or independent wells.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_SQ06 — A City Connected
side; prerequisites: BL_SQ05; locations: station, switch; actors: nia, mara.
Objective: Establish a cross-neighborhood transit agreement.
Resolution design: open route or rotating access.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_SQ07 — The Crane at the Edge
side; prerequisites: BL_MQ02; locations: crane, yard; actors: ellis.
Objective: Recover cargo stranded at an inoperable crane.
Resolution design: repair machinery or move cargo by ground.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_SQ08 — The Last Tram
side; prerequisites: BL_MQ03; locations: station, rail; actors: ellis, del.
Objective: Investigate abandoned transit equipment.
Resolution design: restore short shuttle route or salvage for roads.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_SQ09 — The Arcade's Secret
side; prerequisites: BL_MQ02; locations: arcade, roof; actors: jo.
Objective: Find a merchant missing after a building collapse.
Resolution design: rescue via roof or service entrance.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_SQ10 — A Bridge Too Far
side; prerequisites: BL_MQ03; locations: bridge, ferry; actors: reed, del.
Objective: Find a safe alternative to an unstable crossing.
Resolution design: organize ferry or negotiate detour.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_SQ11 — The Clinic Ledger
side; prerequisites: BL_MQ02; locations: clinic, warehouse; actors: cal, jo.
Objective: Investigate missing medical deliveries.
Resolution design: return supplies or establish secure procurement.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_SQ12 — The Park After Rain
side; prerequisites: BL_MQ02; locations: park, rowblock; actors: nia.
Objective: Resolve competing uses for a flooded public space.
Resolution design: drain selected paths or establish a garden.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_SQ13 — Eastworks Night Shift
side; prerequisites: BL_MQ04; locations: plant, yard; actors: ada, ellis.
Objective: Identify why machinery fails during shifts.
Resolution design: repair faulty circuit or change work arrangement.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_SQ14 — The Basin's Keepers
side; prerequisites: BL_MQ04; locations: canal, crane; actors: mara.
Objective: Investigate blocked access to industrial basin.
Resolution design: clear obstruction or negotiate shared dock.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_SQ15 — No Fare Today
side; prerequisites: BL_MQ03; locations: checkpoint, subway; actors: del, reed.
Objective: Help travelers unable to pay a toll.
Resolution design: negotiate passes or open alternate route.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_SQ16 — Dry Dock Blues
side; prerequisites: BL_MQ04; locations: drydock, ferry; actors: ellis, mara.
Objective: Restore a maintenance bay for small craft.
Resolution design: repair hoist or build alternate dock.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_SQ17 — A School Again
side; prerequisites: BL_MQ02; locations: school, refuge; actors: cal, nia.
Objective: Turn a shelter room into a shared learning space.
Resolution design: recover books or arrange volunteer teaching.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_SQ18 — A Cargo of Promises
side; prerequisites: BL_MQ05; locations: market, warehouse; actors: mara, jo.
Objective: Audit rival supply agreements.
Resolution design: publish terms or broker compensation.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_SQ19 — The Quiet Hour
side; prerequisites: BL_MQ05; locations: roof, checkpoint; actors: del, cal.
Objective: Resolve a nighttime access restriction affecting medics.
Resolution design: establish exemptions or alternate route.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### BL_SQ20 — The City's Next Morning
side; prerequisites: BL_MQ06; locations: switch, station; actors: ada, nia.
Objective: Restore a public service consistent with the ending.
Resolution design: maintain shared system or build independent backup.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

## Writing standards
Maintain character voice, faction knowledge, local lore, branching journal updates and accessibility. Never block campaign on optional content. Individual quest files will use stable IDs.
