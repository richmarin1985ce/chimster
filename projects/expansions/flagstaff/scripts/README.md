# Fallout: Flagstaff — scripting workspace
Target language: GECK-family native script source and bytecode. No native script has been compiled here. Do not present pseudocode as native source. Individual source projects will be stored here by quest ID with revision metadata, compile outputs kept distinct.

## First implementation contract
Opening quest CR_MQ01 (The Roman Holiday): initialize once when entry condition satisfied; validate required locations and actors; show objective; support alternative resolution paths; persist completion and transition state; prevent duplicate rewards; allow safe return or recovery. Use target-native records, stable IDs, and saved variables only after schema confirmation. Preserve unrelated vanilla quest state.

## Script work order
- CR_MQ01: Confiscation receipt and first pit decisions; requires entry; pending native stage binding, conditional branches and test fixture.
- CR_MQ02: Recover gear; establish cover or leave with others; requires CR_MQ01; pending native stage binding, conditional branches and test fixture.
- CR_MQ03: Trace charter obligations and obtain standing; requires CR_MQ02; pending native stage binding, conditional branches and test fixture.
- CR_MQ04: Resolve immediate shortages; requires CR_MQ03; pending native stage binding, conditional branches and test fixture.
- CR_MQ05: Investigate eastbound surveys; requires CR_MQ04; pending native stage binding, conditional branches and test fixture.
- CR_MQ06: Settle capital politics and road access; requires CR_MQ05; pending native stage binding, conditional branches and test fixture.
- CR_MQ07: Return to Mojave with conditional slides; requires CR_MQ06; pending native stage binding, conditional branches and test fixture.

## Verification
Chimster native compilation, diagnostics, attachment, save/load, repeat activation, missing dependency and fail-forward checks. No external compiler workaround. Block exports if native support missing.
