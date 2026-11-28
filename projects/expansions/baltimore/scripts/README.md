# Fallout: Baltimore — scripting workspace
Target language: FO3 native script source and bytecode. No native script has been compiled here. Do not present pseudocode as native source. Individual source projects will be stored here by quest ID with revision metadata, compile outputs kept distinct.

## First implementation contract
Opening quest BL_MQ01 (A Closed Harbor): initialize once when entry condition satisfied; validate required locations and actors; show objective; support alternative resolution paths; persist completion and transition state; prevent duplicate rewards; allow safe return or recovery. Use target-native records, stable IDs, and saved variables only after schema confirmation. Preserve unrelated vanilla quest state.

## Script work order
- BL_MQ01: Find why transit failed; requires entry; pending native stage binding, conditional branches and test fixture.
- BL_MQ02: Restore a supply route to refuge; requires BL_MQ01; pending native stage binding, conditional branches and test fixture.
- BL_MQ03: Expose competing claims on transit; requires BL_MQ02; pending native stage binding, conditional branches and test fixture.
- BL_MQ04: Diagnose infrastructure failure; requires BL_MQ03; pending native stage binding, conditional branches and test fixture.
- BL_MQ05: Secure residential agreement; requires BL_MQ04; pending native stage binding, conditional branches and test fixture.
- BL_MQ06: Choose transit governance; requires BL_MQ05; pending native stage binding, conditional branches and test fixture.
- BL_MQ07: Leave or continue local work; requires BL_MQ06; pending native stage binding, conditional branches and test fixture.

## Verification
Chimster native compilation, diagnostics, attachment, save/load, repeat activation, missing dependency and fail-forward checks. No external compiler workaround. Block exports if native support missing.
