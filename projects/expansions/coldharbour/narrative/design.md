# Coldharbour — narrative design
Review snapshot, 2026-11-28. All additions remain proposals unless creator-locked. Existing canonical quest IDs retained.

## Factions
- **Unbound Refuge** (refuge): Free captives without accepting new contracts
- **Ledger Exchange** (market): Trade in obligations; some brokers seek reform
- **Chain Wardens** (wardens): Maintain the repeating fragments; split over their purpose
- **Witness Circle** (witness): Collect testimony and protect memories

## Principal cast
- **Nare Seloth** (nare): Former prisoner, pragmatic healer. Faction: refuge; home: refuge.
- **Vedan Aravel** (vedan): Scribe who records changes between fragments. Faction: witness; home: archive.
- **Mira Othrel** (mira): Broker who can void lesser contracts. Faction: market; home: market.
- **Dren Varo** (dren): Warden who doubts the repetition. Faction: wardens; home: gate.
- **Sena Ralas** (sena): Water keeper seeking lost kin. Faction: refuge; home: well.
- **Orven Thalas** (orven): Cartographer whose maps contradict each other. Faction: witness; home: tower.
- **Thal Varyn** (thal): Custodian offering conditional release. Faction: wardens; home: fort.
- **Ilvi Meren** (ilvi): Debt clerk hiding a missing name. Faction: market; home: count.

## Campaign and optional quests
### CH_MQ01 — A Place Remembered
main; prerequisites: entry; locations: entry, village, refuge; actors: nare.
Objective: Survive arrival and locate refuge.
Resolution design: help witness or follow trail.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_MQ02 — Names in Iron
main; prerequisites: CH_MQ01; locations: shrine, gate; actors: dren, nare.
Objective: Find passage and establish a first obligation.
Resolution design: void bargain through testimony or offer temporary service.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_MQ03 — The Price of a Name
main; prerequisites: CH_MQ02; locations: market, count, well; actors: mira, ilvi, sena.
Objective: Discover missing contracts.
Resolution design: trade, persuade or recover evidence.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_MQ04 — Maps That Lie
main; prerequisites: CH_MQ03; locations: archive, tower, cave; actors: vedan, orven.
Objective: Compare repeated fragments and establish mechanism.
Resolution design: collect testimony or physical markers.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_MQ05 — The Custodian's Offer
main; prerequisites: CH_MQ04; locations: fort, court, foundry; actors: thal, dren.
Objective: Acquire access to the core.
Resolution design: negotiate, expose contradiction or bypass.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_MQ06 — Unwritten
main; prerequisites: CH_MQ05; locations: engine, sanctum; actors: nare, thal, mira.
Objective: Choose what happens to the mechanism.
Resolution design: sever, redirect or accept limited bargain; captive outcomes vary.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_MQ07 — A Road Home
main; prerequisites: CH_MQ06; locations: exit, refuge; actors: nare, vedan.
Objective: Leave or return to help survivors.
Resolution design: return with testimony or leave it archived.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_SQ01 — The Water Keeper
side; prerequisites: CH_MQ01; locations: well, canal; actors: sena.
Objective: Restore access to water.
Resolution design: repair channel or negotiate ration.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_SQ02 — A Missing Name
side; prerequisites: CH_MQ03; locations: count, cellar; actors: ilvi.
Objective: Trace erased captive identity.
Resolution design: recover record or witness account.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_SQ03 — The Honest Map
side; prerequisites: CH_MQ04; locations: tower, road; actors: orven.
Objective: Mark reliable routes.
Resolution design: survey or verify with witnesses.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_SQ04 — The Unclaimed Toll
side; prerequisites: CH_MQ02; locations: bridge, market; actors: mira, dren.
Objective: Investigate a bridge demanding names instead of coin.
Resolution design: void the toll or find an alternate path.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_SQ05 — A Debt Without End
side; prerequisites: CH_SQ04; locations: count, court; actors: mira, ilvi.
Objective: Identify a self-renewing debt contract.
Resolution design: invalidate it by precedent or transfer consented obligations.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_SQ06 — The Last Signature
side; prerequisites: CH_SQ05; locations: archive, sanctum; actors: vedan, mira.
Objective: Establish a voluntary registry for freed captives.
Resolution design: destroy compulsory records or preserve witness copies.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_SQ07 — The Bell That Does Not Ring
side; prerequisites: CH_MQ01; locations: village, shrine; actors: nare.
Objective: Discover why a bell signals different events to different inhabitants.
Resolution design: restore shared timing or silence the false signal.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_SQ08 — A Boat With No River
side; prerequisites: CH_MQ03; locations: docks, canal; actors: sena.
Objective: Help a ferryman locate a usable channel.
Resolution design: clear passage or negotiate land transport.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_SQ09 — Borrowed Faces
side; prerequisites: CH_MQ03; locations: market, crypt; actors: ilvi.
Objective: Investigate identities assigned to strangers.
Resolution design: return records to claimants or preserve anonymity.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_SQ10 — The Ash Orchard
side; prerequisites: CH_MQ02; locations: terrace, well; actors: sena, nare.
Objective: Protect a rare source of refuge supplies.
Resolution design: reroute water or cultivate another sheltered plot.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_SQ11 — A Tower Twice Built
side; prerequisites: CH_MQ04; locations: tower, road; actors: orven.
Objective: Map a watchtower whose stairs lead to contradictory floors.
Resolution design: mark stable path or seal unsafe route.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_SQ12 — The Glass Worker
side; prerequisites: CH_MQ03; locations: quarry, foundry; actors: dren.
Objective: Free a worker bound to replace broken tools indefinitely.
Resolution design: prove contract fulfilled or negotiate release.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_SQ13 — A Witness in Silence
side; prerequisites: CH_MQ04; locations: cave, archive; actors: vedan.
Objective: Recover testimony from a fragment that changes when approached.
Resolution design: record physical clues or interview displaced witnesses.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_SQ14 — The Warden's Kin
side; prerequisites: CH_MQ04; locations: fort, cellar; actors: dren.
Objective: Resolve a warden's family obligation.
Resolution design: secure refuge or arrange protected contact.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_SQ15 — The Empty Seat
side; prerequisites: CH_MQ05; locations: court, fort; actors: thal, ilvi.
Objective: Investigate a tribunal with no judge.
Resolution design: restore voluntary arbitration or expose its invalid judgments.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_SQ16 — Iron Against Iron
side; prerequisites: CH_MQ05; locations: foundry, gate; actors: dren, thal.
Objective: Disable a redundant binding mechanism.
Resolution design: repair release controls or bypass the gate.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_SQ17 — A Map for Tomorrow
side; prerequisites: CH_SQ03; locations: road, docks; actors: orven.
Objective: Create a route guide for new arrivals.
Resolution design: publish verified markers or recruit guides.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_SQ18 — No Names Lost
side; prerequisites: CH_MQ06; locations: archive, refuge; actors: vedan, nare.
Objective: Decide how to preserve memory after the mechanism changes.
Resolution design: archive testimony with consent or return records.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_SQ19 — The Other Door
side; prerequisites: CH_MQ04; locations: crypt, cave; actors: orven, vedan.
Objective: Explore a false exit and rescue a stranded traveler.
Resolution design: find stable return path or open a temporary passage.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

### CH_SQ20 — The First Free Market
side; prerequisites: CH_MQ06; locations: market, refuge; actors: mira, sena.
Objective: Organize exchange without binding contracts.
Resolution design: establish voluntary barter or separate community stalls.
Pending: individual stage script, dialogue, rewards, failure/recovery, consequence state and runtime test.

## Writing standards
Maintain character voice, faction knowledge, local lore, branching journal updates and accessibility. Never block campaign on optional content. Individual quest files will use stable IDs.
