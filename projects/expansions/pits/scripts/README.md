# The Pits — scripting workspace
Target language: Skyrim Papyrus, quest aliases and VMAD. No native script has been compiled here. Do not present pseudocode as native source. Individual source projects will be stored here by quest ID with revision metadata, compile outputs kept distinct.

## First implementation contract
Opening quest PT_MQ01 (A Measure of Disorder): initialize once when entry condition satisfied; validate required locations and actors; show objective; support alternative resolution paths; persist completion and transition state; prevent duplicate rewards; allow safe return or recovery. Use target-native records, stable IDs, and saved variables only after schema confirmation. Preserve unrelated vanilla quest state.

## Script work order
- PT_MQ01: Investigate affliction and enter realm; requires entry; pending native stage binding, conditional branches and test fixture.
- PT_MQ02: Learn hazard rules and reach descent gate; requires PT_MQ01; pending native stage binding, conditional branches and test fixture.
- PT_MQ03: Determine why containment fails; requires PT_MQ02; pending native stage binding, conditional branches and test fixture.
- PT_MQ04: Restore or isolate damaged infrastructure; requires PT_MQ03; pending native stage binding, conditional branches and test fixture.
- PT_MQ05: Reconcile competing custodians; requires PT_MQ04; pending native stage binding, conditional branches and test fixture.
- PT_MQ06: Choose regulator policy; requires PT_MQ05; pending native stage binding, conditional branches and test fixture.
- PT_MQ07: Return and observe fictional affliction outcome; requires PT_MQ06; pending native stage binding, conditional branches and test fixture.

## Verification
Chimster native compilation, diagnostics, attachment, save/load, repeat activation, missing dependency and fail-forward checks. No external compiler workaround. Block exports if native support missing.
