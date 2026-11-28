# CR_MQ01 — The Roman Holiday
Status: detailed design proposal, not native script or verified quest.

## Canon and premise
Creator-locked mandatory opening title. Independent merchant slavers abduct the Courier in the Mojave; they are not Legion soldiers. A period advertisement may be used as an original optional hook, not a substitute for the established abduction.

## Proposed stage plan
| Stage | Objective / transition |
|---|---|
| 10 | Capture transition and inventory custody |
| 20 | Establish confinement; recover or learn of the confiscation receipt |
| 30 | Talk to Ash or inspect the custody record; both paths establish the equipment recovery lead |
| 100 | Complete the opening and unlock CR_MQ02; do not release the player from captivity prematurely |

Stage numbers are proposed native bindings; validate target format before writing. Alternatives are mutually compatible where appropriate; completion occurs once. Preserve unrelated vanilla state.

## State contract
receipt_recorded; ash_contact; custody_manifest_id. Persistent, quest-scoped state; names are design keys, not compiled variables. Re-entry must be idempotent. Record outcome provenance and verify any references before export.

## Asset and level dependencies
Original advertisement text and voice; custody receipt; pit and labor yard; merchant slaver actor records; safe inventory staging with item identity preservation.

## Recovery and acceptance
If Ash is unavailable, the receipt or custody ledger must supply the essential information. On repeated load, do not confiscate again or duplicate gear.
Test entry, both solution paths, save/load at every stage, missing actor/reference, repeated activation, completion and successor availability. No external authoring tools. Native compile and retail verification remain gates.
