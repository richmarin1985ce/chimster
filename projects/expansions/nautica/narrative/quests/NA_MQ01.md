# NA_MQ01 — The Broken Crossing
Status: detailed design proposal, not native script or verified quest.

## Canon and premise
The failed crossing exposes the island's supply problem.

## Proposed stage plan
| Stage | Objective / transition |
|---|---|
| 10 | Register arrival at dock |
| 20 | Explore town streets and learn why supply failed |
| 30 | Help or exchange information with Iris |
| 100 | Unlock NA_MQ02 with beacon or boathouse lead |

Stage numbers are proposed native bindings; validate target format before writing. Alternatives are mutually compatible where appropriate; completion occurs once. Preserve unrelated vanilla state.

## State contract
arrival_registered; supply_failure_known; beacon_lead. Persistent, quest-scoped state; names are design keys, not compiled variables. Re-entry must be idempotent. Record outcome provenance and verify any references before export.

## Asset and level dependencies
Arrival dock, street and lane, Iris, original maritime signs and notices; FO4 aliases and Papyrus.

## Recovery and acceptance
Avoid a fabricated mainland bridge. Preserve an alternate notice-based lead and avoid duplicate arrival rewards.
Test entry, both solution paths, save/load at every stage, missing actor/reference, repeated activation, completion and successor availability. No external authoring tools. Native compile and retail verification remain gates.
