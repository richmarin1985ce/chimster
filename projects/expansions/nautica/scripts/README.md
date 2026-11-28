# Fallout: Nautica — scripting workspace
Target language: FO4 Papyrus, quest aliases and VMAD. No native script has been compiled here. Do not present pseudocode as native source. Individual source projects will be stored here by quest ID with revision metadata, compile outputs kept distinct.

## First implementation contract
Opening quest NA_MQ01 (The Broken Crossing): initialize once when entry condition satisfied; validate required locations and actors; show objective; support alternative resolution paths; persist completion and transition state; prevent duplicate rewards; allow safe return or recovery. Use target-native records, stable IDs, and saved variables only after schema confirmation. Preserve unrelated vanilla quest state.

## Script work order
- NA_MQ01: Survive arrival and learn supply failure; requires entry; pending native stage binding, conditional branches and test fixture.
- NA_MQ02: Restore local signal and locate missing cargo route; requires NA_MQ01; pending native stage binding, conditional branches and test fixture.
- NA_MQ03: Investigate contested wreck cargo; requires NA_MQ02; pending native stage binding, conditional branches and test fixture.
- NA_MQ04: Secure inland supply agreement; requires NA_MQ03; pending native stage binding, conditional branches and test fixture.
- NA_MQ05: Locate missing vessels and restore network; requires NA_MQ04; pending native stage binding, conditional branches and test fixture.
- NA_MQ06: Decide maritime supply governance; requires NA_MQ05; pending native stage binding, conditional branches and test fixture.
- NA_MQ07: Return or stay; show network consequences; requires NA_MQ06; pending native stage binding, conditional branches and test fixture.

## Verification
Chimster native compilation, diagnostics, attachment, save/load, repeat activation, missing dependency and fail-forward checks. No external compiler workaround. Block exports if native support missing.
