# Fallout: Nautica — narrative design
Review snapshot, 2026-11-28. All additions remain proposals unless creator-locked. Existing canonical quest IDs retained.

## Factions
- **Harbor Cooperative** (harbor): Share marine supply access and keep harbor safe
- **Salvage Flotilla** (flotilla): Claim wreck cargo; disputes over obligations
- **Inland Refuge** (inland): Keep food and water supplies independent
- **Beacon Keepers** (beacon): Maintain navigation stations and rescue obligations

## Principal cast
- **Iris Coffin** (iris): Harbor dispatcher investigating missing cargo. Faction: harbor; home: dock.
- **Wade Sloane** (wade): Salvage captain torn between debt and rescue. Faction: flotilla; home: slip.
- **Mabel Finch** (mabel): Refuge organizer seeking reliable supplies. Faction: inland; home: crossroads.
- **Otto Pike** (otto): Station keeper protecting navigation records. Faction: beacon; home: beacon.
- **June Reed** (june): Mechanic who can restore marine hardware. Faction: harbor; home: boathouse.
- **Silas Marsh** (silas): Grower defending local water supply. Faction: inland; home: farm.
- **Bea Vale** (bea): Diver who disputes ownership claims. Faction: flotilla; home: wreck.
- **Ruth Hale** (ruth): Rescue volunteer tracking missing boats. Faction: beacon; home: east.

## Campaign and optional quests
### NA_MQ01 — The Broken Crossing
main; prerequisites: entry; locations: dock, street, lane; actors: iris.
Objective: Survive arrival and learn supply failure.
Resolution design: offer help or exchange information.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_MQ02 — A Light in the Fog
main; prerequisites: NA_MQ01; locations: boathouse, marsh, beacon; actors: june, otto.
Objective: Restore local signal and locate missing cargo route.
Resolution design: repair, retrieve parts or bargain.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_MQ03 — Claims on the Tide
main; prerequisites: NA_MQ02; locations: slip, warehouse, wreck; actors: wade, bea.
Objective: Investigate contested wreck cargo.
Resolution design: recover manifest or negotiate salvage rights.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_MQ04 — Beyond the Harbor
main; prerequisites: NA_MQ03; locations: crossroads, farm, pond; actors: mabel, silas.
Objective: Secure inland supply agreement.
Resolution design: restore water or arrange transport.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_MQ05 — The Eastern Signal
main; prerequisites: NA_MQ04; locations: east, polpis, relay; actors: ruth, otto.
Objective: Locate missing vessels and restore network.
Resolution design: repair relay or establish alternate signal.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_MQ06 — Who Owns the Water
main; prerequisites: NA_MQ05; locations: market, slip, west; actors: iris, wade, mabel.
Objective: Decide maritime supply governance.
Resolution design: cooperative, regulated salvage or decentralized routes.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_MQ07 — A Safe Crossing
main; prerequisites: NA_MQ06; locations: beacon, exit; actors: ruth, iris.
Objective: Return or stay; show network consequences.
Resolution design: leave with safe passage or continue settlement work.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_SQ01 — A Boat for Two
side; prerequisites: NA_MQ02; locations: boathouse, cove; actors: june.
Objective: Repair rescue craft as authored travel point.
Resolution design: repair or source replacement parts.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_SQ02 — The Dry Well
side; prerequisites: NA_MQ04; locations: farm, cistern; actors: silas.
Objective: Restore community water supply.
Resolution design: repair or barter.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_SQ03 — The Lost Watch
side; prerequisites: NA_MQ03; locations: cliff, east; actors: ruth.
Objective: Investigate missing rescue watch.
Resolution design: follow signs or recover log.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_SQ04 — The Harbor Bell
side; prerequisites: NA_MQ02; locations: beacon, dock; actors: otto, iris.
Objective: Recover missing navigation signal equipment.
Resolution design: repair bell or establish alternate signal.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_SQ05 — A Captain's Oath
side; prerequisites: NA_SQ04; locations: slip, market; actors: wade, iris.
Objective: Investigate a broken rescue agreement.
Resolution design: reconcile testimony or renegotiate rescue duties.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_SQ06 — The Common Tide
side; prerequisites: NA_SQ05; locations: west, crossroads; actors: mabel, wade.
Objective: Create a shared maritime aid pact.
Resolution design: mutual aid agreement or independent routes.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_SQ07 — The Dune House
side; prerequisites: NA_MQ02; locations: dunes, west; actors: june.
Objective: Find a storm-damaged shelter and stranded occupant.
Resolution design: repair shelter or escort to town.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_SQ08 — The Moor's Old Road
side; prerequisites: NA_MQ04; locations: moor, polpis; actors: mabel, silas.
Objective: Reopen a blocked inland road without harming water supply.
Resolution design: clear selected route or mark detour.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_SQ09 — The Wreck's Second Name
side; prerequisites: NA_MQ03; locations: wreck, warehouse; actors: bea.
Objective: Identify conflicting ownership records for cargo.
Resolution design: return verified belongings or mediate distribution.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_SQ10 — The Empty Lobster Pot
side; prerequisites: NA_MQ02; locations: cove, slip; actors: wade.
Objective: Investigate disappearing fishing gear.
Resolution design: recover equipment or negotiate shared waters.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_SQ11 — A Town of Roofs
side; prerequisites: NA_MQ02; locations: street, lane; actors: iris, june.
Objective: Help a town block establish storm shelters.
Resolution design: repair common roof or organize alternate lodging.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_SQ12 — A Lantern in the Marsh
side; prerequisites: NA_MQ02; locations: marsh, beacon; actors: otto.
Objective: Find lost trail markers and guide a traveler.
Resolution design: restore lamps or mark safer path.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_SQ13 — The Bunker's Water
side; prerequisites: NA_MQ04; locations: bunker, pond; actors: silas.
Objective: Inspect abandoned utilities for safe fictional supply use.
Resolution design: repair pumps or reject contamination risk.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_SQ14 — The Eastern Watch
side; prerequisites: NA_MQ05; locations: east, cliff; actors: ruth.
Objective: Locate a missing lookout and recover their log.
Resolution design: rescue or establish alternate watch.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_SQ15 — The Shore That Moves
side; prerequisites: NA_MQ03; locations: surf, dunes; actors: bea, june.
Objective: Survey a route altered by erosion.
Resolution design: mark stable path or relocate cache.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_SQ16 — A Cargo of Seeds
side; prerequisites: NA_MQ04; locations: farm, market; actors: silas, mabel.
Objective: Resolve disputed agricultural shipment.
Resolution design: share seeds or negotiate exchange.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_SQ17 — The Signal Book
side; prerequisites: NA_MQ05; locations: relay, beacon; actors: otto, ruth.
Objective: Reconstruct lost navigation schedules.
Resolution design: recover pages or establish new signal protocol.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_SQ18 — The Salt Cellar
side; prerequisites: NA_MQ03; locations: cistern, warehouse; actors: iris.
Objective: Investigate a damaged storage room and protect fresh water.
Resolution design: repair barrier or relocate stock.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_SQ19 — A Boat Called Home
side; prerequisites: NA_MQ05; locations: boathouse, slip; actors: wade, bea.
Objective: Resolve claim on a craft used as shelter.
Resolution design: mediate ownership or arrange replacement housing.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### NA_SQ20 — The Last Ferry Out
side; prerequisites: NA_MQ06; locations: dock, exit; actors: ruth, iris.
Objective: Establish a reliable return crossing after faction outcome.
Resolution design: maintain shared schedule or support independent service.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

## Writing standards
Maintain character voice, faction knowledge, local lore, branching journal updates and accessibility. Never block campaign on optional content. Individual quest files will use stable IDs.
