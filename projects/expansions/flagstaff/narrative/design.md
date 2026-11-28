# Fallout: Flagstaff — narrative design
Review snapshot, 2026-11-28. All additions remain proposals unless creator-locked. Existing canonical quest IDs retained.

## Factions
- **Chartered caravan houses** (caravan): Protect trade contracts and private fortunes; divided over captivity
- **Ranchers' association** (ranch): Resist requisitions without losing livelihoods
- **Legion supply administration** (legion): Meet wartime quotas at civilian expense
- **Captive solidarity networks** (captive): Free separated families and establish safe passage
- **Independent roadside communities** (road): Keep trade roads open without coercion
- **Hidden reconnaissance cell** (survey): Collect intelligence; claims Chicago Enclave ties without settling canon

## Principal cast
- **Vesta Marrow** (vesta): Caravan proprietor; profits from captivity; wants predictable trade. Faction: caravan; home: market.
- **Silvan Rusk** (silvan): Rancher facing destructive requisitions. Faction: ranch; home: ranch.
- **Cassian Vale** (cassian): Quartermaster torn between orders and supplies. Faction: legion; home: depot.
- **Livia Sable** (livia): Clerk with evidence of contracts; values security. Faction: caravan; home: ledger.
- **Ash** (ash): Potential companion seeking separated family. Faction: captive; home: pit.
- **Nell Fallow** (nell): Repair shop owner preserving road heritage. Faction: road; home: repair.
- **Morrow Finch** (finch): Disguised surveyor; optional intelligence lead. Faction: survey; home: surveycamp.
- **Tallow** (tallow): Former guard with escape knowledge. Faction: road; home: service.

## Campaign and optional quests
### CR_MQ01 — The Roman Holiday
main; prerequisites: entry; locations: pit, labor; actors: ash.
Objective: Confiscation receipt and first pit decisions.
Resolution design: record confiscation or learn location through Ash.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_MQ02 — Don't Fence Me In
main; prerequisites: CR_MQ01; locations: store, service, repair; actors: ash, tallow, nell.
Objective: Recover gear; establish cover or leave with others.
Resolution design: repair/service route or bargain; companions may remain behind.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_MQ03 — All Roads Lead to Rome
main; prerequisites: CR_MQ02; locations: market, ledger, ranch; actors: vesta, livia, silvan.
Objective: Trace charter obligations and obtain standing.
Resolution design: trade, speech or evidence route.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_MQ04 — The Best Things in Life Are Free
main; prerequisites: CR_MQ03; locations: depot, stockyard, well; actors: cassian, silvan.
Objective: Resolve immediate shortages.
Resolution design: allocate supplies, negotiate quotas or expose abuse.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_MQ05 — Long Distance Call
main; prerequisites: CR_MQ04; locations: surveycamp, relay, ridge; actors: finch.
Objective: Investigate eastbound surveys.
Resolution design: follow evidence or decline deeper intelligence thread; main story continues.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_MQ06 — The Price of Civilization
main; prerequisites: CR_MQ05; locations: court, market, refuge; actors: cassian, vesta, livia, ash.
Objective: Settle capital politics and road access.
Resolution design: freedom, commerce and provisioning outcomes vary independently.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_MQ07 — East of the Sun
main; prerequisites: CR_MQ06; locations: return, repair; actors: nell.
Objective: Return to Mojave with conditional slides.
Resolution design: leave or remain; vanilla endings untouched.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_SQ01 — Separated
side; prerequisites: CR_MQ02; locations: refuge, clinic; actors: ash.
Objective: Find relatives and decide their route.
Resolution design: rescue, escort or safe contact.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_SQ02 — Mother Road
side; prerequisites: CR_MQ02; locations: museum, motel, station; actors: nell.
Objective: Recover road history.
Resolution design: preserve archive or trade duplicates.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_SQ03 — The Empty Trough
side; prerequisites: CR_MQ03; locations: mill, ranch; actors: silvan.
Objective: Resolve a feed shortage.
Resolution design: repair equipment or barter.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_SQ04 — The Price of a Ledger
side; prerequisites: CR_MQ03; locations: ledger, market; actors: livia, vesta.
Objective: Trace a fraudulent captive transfer and establish who owns the debt.
Resolution design: expose charter fraud or bargain for release.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_SQ05 — A Contract of Our Own
side; prerequisites: CR_SQ04; locations: court, refuge; actors: livia, ash.
Objective: Bring testimony to a civilian hearing; arrange protection for witnesses.
Resolution design: public record or confidential settlement.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_SQ06 — Free Passage
side; prerequisites: CR_SQ05; locations: crossroads, station; actors: ash, tallow.
Objective: Build a durable escape and resettlement route.
Resolution design: negotiate safe stops or fund independent transport.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_SQ07 — The Last Water Truck
side; prerequisites: CR_MQ02; locations: well, station; actors: nell, silvan.
Objective: Find why a rural water shipment never arrived.
Resolution design: repair delivery vehicle or establish alternate supplier.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_SQ08 — Brand of the House
side; prerequisites: CR_MQ03; locations: ranch, stockyard; actors: silvan, vesta.
Objective: Investigate disputed livestock brands and ownership.
Resolution design: return stock or divide the disputed herd.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_SQ09 — The Quartermaster's Table
side; prerequisites: CR_MQ04; locations: depot, clinic; actors: cassian, livia.
Objective: Audit diverted medical provisions.
Resolution design: restore civilian allotments or expose falsified records.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_SQ10 — Dead Letter Office
side; prerequisites: CR_MQ02; locations: motel, culvert; actors: tallow, nell.
Objective: Recover abandoned correspondence and find surviving addressees.
Resolution design: deliver letters or preserve them anonymously.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_SQ11 — Signal Across the Cinders
side; prerequisites: CR_MQ05; locations: relay, ridge; actors: finch.
Objective: Find a second survey signal and decide what to disclose.
Resolution design: share selective findings or seal records.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_SQ12 — An Honest Measure
side; prerequisites: CR_MQ03; locations: mill, market; actors: silvan, vesta.
Objective: Resolve merchants' dispute over rigged grain scales.
Resolution design: demonstrate fraud or negotiate standard weights.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_SQ13 — Cinder Road
side; prerequisites: CR_MQ02; locations: quarry, crossroads; actors: nell.
Objective: Clear an unstable road section without cutting off quarry workers.
Resolution design: repair alternate road or reroute traffic.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_SQ14 — A Bed for the Night
side; prerequisites: CR_MQ02; locations: motel, repair; actors: nell, ash.
Objective: Resolve conflict between travelers and fugitives sharing shelter.
Resolution design: secure new shelter or negotiate protected rooms.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_SQ15 — No One's Property
side; prerequisites: CR_MQ04; locations: labor, refuge; actors: ash, cassian.
Objective: Find a labor group facing transfer and establish their choice of destination.
Resolution design: release via evidence or arrange voluntary transport.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_SQ16 — A Better Bargain
side; prerequisites: CR_MQ04; locations: market, stockyard; actors: vesta, silvan.
Objective: Test a civilian supply agreement independent of coerced labor.
Resolution design: secure voluntary suppliers or expose monopoly.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_SQ17 — The Sound of Home
side; prerequisites: CR_MQ02; locations: museum, station; actors: nell.
Objective: Restore a roadside radio archive using salvaged recordings.
Resolution design: broadcast local stories or preserve a listening room.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_SQ18 — The Other Courier
side; prerequisites: CR_MQ03; locations: crossroads, culvert; actors: tallow.
Objective: Recover an overdue courier's route and finish or return their dispatch.
Resolution design: deliver authenticated message or locate courier.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_SQ19 — Witness for the Road
side; prerequisites: CR_SQ09; locations: court, depot; actors: cassian, livia.
Objective: Investigate reprisals against a supply witness.
Resolution design: secure protection or publish evidence with consent.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CR_SQ20 — The Road After Tomorrow
side; prerequisites: CR_MQ06; locations: repair, crossroads; actors: nell, ash.
Objective: Establish a lasting route after the political outcome.
Resolution design: support independent stops or negotiate conditional access.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

## Writing standards
Maintain character voice, faction knowledge, local lore, branching journal updates and accessibility. Never block campaign on optional content. Individual quest files will use stable IDs.
