# Coldharbour — scripting workspace
Target language: TES3 MWScript and journal/dialogue result scripts. No native script has been compiled here. Do not present pseudocode as native source. Individual source projects will be stored here by quest ID with revision metadata, compile outputs kept distinct.

## First implementation contract
Opening quest CH_MQ01 (A Place Remembered): initialize once when entry condition satisfied; validate required locations and actors; show objective; support alternative resolution paths; persist completion and transition state; prevent duplicate rewards; allow safe return or recovery. Use target-native records, stable IDs, and saved variables only after schema confirmation. Preserve unrelated vanilla quest state.

## Script work order
- CH_MQ01: Survive arrival and locate refuge; requires entry; pending native stage binding, conditional branches and test fixture.
- CH_MQ02: Find passage and establish a first obligation; requires CH_MQ01; pending native stage binding, conditional branches and test fixture.
- CH_MQ03: Discover missing contracts; requires CH_MQ02; pending native stage binding, conditional branches and test fixture.
- CH_MQ04: Compare repeated fragments and establish mechanism; requires CH_MQ03; pending native stage binding, conditional branches and test fixture.
- CH_MQ05: Acquire access to the core; requires CH_MQ04; pending native stage binding, conditional branches and test fixture.
- CH_MQ06: Choose what happens to the mechanism; requires CH_MQ05; pending native stage binding, conditional branches and test fixture.
- CH_MQ07: Leave or return to help survivors; requires CH_MQ06; pending native stage binding, conditional branches and test fixture.

## Verification
Chimster native compilation, diagnostics, attachment, save/load, repeat activation, missing dependency and fail-forward checks. No external compiler workaround. Block exports if native support missing.
