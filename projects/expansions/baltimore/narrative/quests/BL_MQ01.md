# BL_MQ01 — A Closed Harbor
Status: detailed design proposal, not native script or verified quest.

## Canon and premise
The arrival route reveals broken transit and competing supply interests.

## Proposed stage plan
| Stage | Objective / transition |
|---|---|
| 10 | Register arrival near harbor |
| 20 | Locate the market and investigate the closed route |
| 30 | Offer help or trade for information with Mara |
| 100 | Unlock BL_MQ02 with verified supply route lead |

Stage numbers are proposed native bindings; validate target format before writing. Alternatives are mutually compatible where appropriate; completion occurs once. Preserve unrelated vanilla state.

## State contract
arrival_registered; market_found; supply_lead. Persistent, quest-scoped state; names are design keys, not compiled variables. Re-entry must be idempotent. Record outcome provenance and verify any references before export.

## Asset and level dependencies
Arrival, harbor market, Mara, signage, original cargo objects and FO3 quest records.

## Recovery and acceptance
Notice or records preserve the lead if Mara is unavailable; no hard dependence on a particular build.
Test entry, both solution paths, save/load at every stage, missing actor/reference, repeated activation, completion and successor availability. No external authoring tools. Native compile and retail verification remain gates.
