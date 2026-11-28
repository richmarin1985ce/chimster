# PT_MQ01 — A Measure of Disorder
Status: detailed design proposal, not native script or verified quest.

## Canon and premise
Fictional affliction and entry into Peryite's realm; six districts remain proposals.

## Proposed stage plan
| Stage | Objective / transition |
|---|---|
| 10 | Investigate the mortal shrine |
| 20 | Gather clues or offer aid |
| 30 | Enter realm and reach quarantine refuge |
| 100 | Unlock PT_MQ02 after entry and a usable refuge lead |

Stage numbers are proposed native bindings; validate target format before writing. Alternatives are mutually compatible where appropriate; completion occurs once. Preserve unrelated vanilla state.

## State contract
shrine_investigated; aid_offered; refuge_found. Persistent, quest-scoped state; names are design keys, not compiled variables. Re-entry must be idempotent. Record outcome provenance and verify any references before export.

## Asset and level dependencies
Shrine, refuge, Iven and Svala, original notes and protective equipment preview; native aliases and Papyrus.

## Recovery and acceptance
Avoid real medical claims. Refuge guidance remains accessible independently of optional aid.
Test entry, both solution paths, save/load at every stage, missing actor/reference, repeated activation, completion and successor availability. No external authoring tools. Native compile and retail verification remain gates.
