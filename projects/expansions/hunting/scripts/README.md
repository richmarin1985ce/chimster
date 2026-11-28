# The Hunting Grounds — scripting workspace
Target language: TES4 native scripts and quest result scripts. No native script has been compiled here. Do not present pseudocode as native source. Individual source projects will be stored here by quest ID with revision metadata, compile outputs kept distinct.

## First implementation contract
Opening quest HG_MQ01 (The Empty Camp): initialize once when entry condition satisfied; validate required locations and actors; show objective; support alternative resolution paths; persist completion and transition state; prevent duplicate rewards; allow safe return or recovery. Use target-native records, stable IDs, and saved variables only after schema confirmation. Preserve unrelated vanilla quest state.

## Script work order
- HG_MQ01: Trace disappearance in Great Forest; requires entry; pending native stage binding, conditional branches and test fixture.
- HG_MQ02: Reach realm and learn contest terms; requires HG_MQ01; pending native stage binding, conditional branches and test fixture.
- HG_MQ03: Complete trial without mandatory transformation; requires HG_MQ02; pending native stage binding, conditional branches and test fixture.
- HG_MQ04: Investigate pack and hunter conflict; requires HG_MQ03; pending native stage binding, conditional branches and test fixture.
- HG_MQ05: Establish ritual loophole or challenge; requires HG_MQ04; pending native stage binding, conditional branches and test fixture.
- HG_MQ06: Resolve the contested hunt; requires HG_MQ05; pending native stage binding, conditional branches and test fixture.
- HG_MQ07: Return; settle transformation outcome; requires HG_MQ06; pending native stage binding, conditional branches and test fixture.

## Verification
Chimster native compilation, diagnostics, attachment, save/load, repeat activation, missing dependency and fail-forward checks. No external compiler workaround. Block exports if native support missing.
