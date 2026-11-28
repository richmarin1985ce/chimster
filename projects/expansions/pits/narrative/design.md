# The Pits — narrative design
Review snapshot, 2026-11-28. All additions remain proposals unless creator-locked. Existing canonical quest IDs retained.

## Factions
- **Quarantine refuge** (quarantine): Protect inhabitants with voluntary safeguards
- **Salt custodians** (terrace): Favor strict containment and measurement
- **Mineral works collective** (works): Restore failing infrastructure
- **Abyssal custodians** (keepers): Disagree over the proper order of the realm

## Principal cast
- **Iven Dreth** (iven): Mortal investigator of fictional affliction. Faction: quarantine; home: shrine.
- **Svala Renn** (svala): Refuge steward balancing limited supplies. Faction: quarantine; home: refuge.
- **Mereth Vale** (mereth): Custodian who prioritizes isolation. Faction: terrace; home: salt.
- **Tovan Glass** (tovan): Mechanic who wants access to flooded works. Faction: works; home: pump.
- **Hessa Moor** (hessa): Herbalist cataloging environmental effects. Faction: quarantine; home: fungus.
- **Keld Windscar** (keld): Guide who challenges imposed rules. Faction: keepers; home: ledge.
- **Naris Venn** (naris): Gatekeeper demanding proof of containment. Faction: keepers; home: gate.
- **Orl Silt** (orl): Worker arguing for restoration rather than abandonment. Faction: works; home: foundry.

## Campaign and optional quests
### PT_MQ01 — A Measure of Disorder
main; prerequisites: entry; locations: shrine, refuge; actors: iven, svala.
Objective: Investigate affliction and enter realm.
Resolution design: trace clues or aid refuge.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_MQ02 — The Air Below
main; prerequisites: PT_MQ01; locations: terrace, gate, hazard; actors: naris, hessa.
Objective: Learn hazard rules and reach descent gate.
Resolution design: protective equipment or safe detour.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_MQ03 — Salt and Ash
main; prerequisites: PT_MQ02; locations: salt, lab, ash; actors: mereth.
Objective: Determine why containment fails.
Resolution design: test fictional samples or recover records.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_MQ04 — The Drowned Works
main; prerequisites: PT_MQ03; locations: works, pump, foundry; actors: tovan, orl.
Objective: Restore or isolate damaged infrastructure.
Resolution design: repair, reroute or close works.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_MQ05 — Six Measures
main; prerequisites: PT_MQ04; locations: fungus, ledge, clinic; actors: hessa, keld, svala.
Objective: Reconcile competing custodians.
Resolution design: consult witnesses or negotiate district protections.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_MQ06 — At the Rim
main; prerequisites: PT_MQ05; locations: rim, core; actors: naris, mereth, keld.
Objective: Choose regulator policy.
Resolution design: contain, redirect or dismantle with consequences.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_MQ07 — The Last Measure
main; prerequisites: PT_MQ06; locations: exit, refuge; actors: iven, svala.
Objective: Return and observe fictional affliction outcome.
Resolution design: report outcome or remain to aid restoration.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_SQ01 — A Breath of Relief
side; prerequisites: PT_MQ02; locations: clinic, stores; actors: svala.
Objective: Restore protective supply.
Resolution design: craft or recover gear.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_SQ02 — The White Ledger
side; prerequisites: PT_MQ03; locations: cistern, lab; actors: mereth.
Objective: Find missing measurement records.
Resolution design: recover journal or question worker.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_SQ03 — A Place Above
side; prerequisites: PT_MQ04; locations: spire, shelter; actors: keld.
Objective: Establish safe trail along ledges.
Resolution design: clear route or signal alternate.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_SQ04 — The Salt Line
side; prerequisites: PT_MQ02; locations: salt, terrace; actors: mereth, hessa.
Objective: Find why boundary markers no longer correspond to hazards.
Resolution design: resurvey and replace markers or establish safe route.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_SQ05 — A Better Measure
side; prerequisites: PT_SQ04; locations: lab, cistern; actors: mereth, iven.
Objective: Resolve conflicting containment records.
Resolution design: reconcile evidence or conduct fictional comparison.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_SQ06 — The Sixth Standard
side; prerequisites: PT_SQ05; locations: clinic, refuge; actors: svala, mereth.
Objective: Establish a common safety protocol across districts.
Resolution design: voluntary agreement or independent safeguards.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_SQ07 — The Kiln's Shadow
side; prerequisites: PT_MQ03; locations: kiln, ash; actors: orl.
Objective: Investigate a failing kiln that blocks a route.
Resolution design: repair vents or divert travel.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_SQ08 — The Obsidian Span
side; prerequisites: PT_MQ03; locations: bridge, ash; actors: keld.
Objective: Restore passage over a hazardous channel.
Resolution design: repair support or mark detour.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_SQ09 — A Garden Sealed
side; prerequisites: PT_MQ02; locations: garden, fungus; actors: hessa.
Objective: Recover fictional plant records without spreading hazards.
Resolution design: isolate chamber or establish remote sampling.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_SQ10 — The Hollow Choir
side; prerequisites: PT_MQ03; locations: hollow, fungus; actors: hessa.
Objective: Trace strange resonance and recover trapped supplies.
Resolution design: solve sound puzzle or open bypass.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_SQ11 — A Pump Without Water
side; prerequisites: PT_MQ04; locations: pump, works; actors: tovan.
Objective: Diagnose abandoned pumping circuit.
Resolution design: repair mechanism or isolate damaged branch.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_SQ12 — The Last Furnace
side; prerequisites: PT_MQ04; locations: foundry, works; actors: orl, tovan.
Objective: Resolve worker dispute over restarting a furnace.
Resolution design: restore controlled operation or convert to salvage.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_SQ13 — Wind Above the Rim
side; prerequisites: PT_MQ04; locations: spire, ledge; actors: keld.
Objective: Find missing trail markers exposed to high winds.
Resolution design: rebuild sheltered markers or route through cave.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_SQ14 — The Empty Storehouse
side; prerequisites: PT_MQ02; locations: stores, clinic; actors: svala.
Objective: Investigate supplies recorded but not delivered.
Resolution design: recover stock or organize substitute supplies.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_SQ15 — The Gatekeeper's Exception
side; prerequisites: PT_MQ05; locations: gate, refuge; actors: naris, svala.
Objective: Arrange safe passage for a group stranded outside.
Resolution design: negotiate conditional entry or build alternative shelter.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_SQ16 — The White Mirror
side; prerequisites: PT_MQ03; locations: cistern, salt; actors: mereth.
Objective: Explore a reflective mineral chamber and interpret its markings.
Resolution design: solve light puzzle or recover a guide.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_SQ17 — A Place to Stand
side; prerequisites: PT_MQ05; locations: rim, shelter; actors: keld.
Objective: Survey safe ledges for evacuation.
Resolution design: secure multiple routes or establish rope access.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_SQ18 — The Keeper's Record
side; prerequisites: PT_MQ05; locations: gate, lab; actors: naris, iven.
Objective: Investigate contradictory regulator instructions.
Resolution design: compare witnesses or recover original records.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_SQ19 — The Refuge's Choice
side; prerequisites: PT_SQ06; locations: refuge, clinic; actors: svala, hessa.
Objective: Decide allocation of protective supplies among districts.
Resolution design: negotiate sharing or establish local production.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### PT_SQ20 — A Measure of Tomorrow
side; prerequisites: PT_MQ06; locations: core, stores; actors: iven, tovan.
Objective: Establish maintenance plan after regulator decision.
Resolution design: train volunteers or leave independent controls.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

## Writing standards
Maintain character voice, faction knowledge, local lore, branching journal updates and accessibility. Never block campaign on optional content. Individual quest files will use stable IDs.
