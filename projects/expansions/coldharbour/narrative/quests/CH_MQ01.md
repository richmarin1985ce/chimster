# CH_MQ01 — A Place Remembered
Status: detailed design proposal, not native script or verified quest.

## Canon and premise
The rupture deposits the player in a distorted settlement. Existing lore is not rewritten.

## Proposed stage plan
| Stage | Objective / transition |
|---|---|
| 10 | Enter the fragment and register arrival |
| 20 | Find evidence of an inhabited refuge |
| 30 | Help a witness or follow reliable markers to refuge |
| 100 | Meet Nare or reach a refuge notice; unlock CH_MQ02 |

Stage numbers are proposed native bindings; validate target format before writing. Alternatives are mutually compatible where appropriate; completion occurs once. Preserve unrelated vanilla state.

## State contract
arrival_registered; witness_helped; refuge_found. Persistent, quest-scoped state; names are design keys, not compiled variables. Re-entry must be idempotent. Record outcome provenance and verify any references before export.

## Asset and level dependencies
Arrival cell, village, refuge, witness dialogue, original marker props and journal updates.

## Recovery and acceptance
If Nare is unavailable, a refuge notice supplies the same essential direction; no reliance on killing or transformation.
Test entry, both solution paths, save/load at every stage, missing actor/reference, repeated activation, completion and successor availability. No external authoring tools. Native compile and retail verification remain gates.
