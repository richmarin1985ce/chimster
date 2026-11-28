# Coldharbour — production and QA plan
No retail game test results recorded. Design review is not runtime verification.

| Gate | Status | Evidence required |
|---|---|---|
| Design inventory | partial | Canonical IDs and reviewed lore |
| Vertical slice | unbuilt | Entry, two resolution routes, exit, save/load |
| World | unbuilt | Native cells, doors, collision, navigation, LOD |
| Original assets | unbuilt | Editable projects, native export and equip/use tests |
| Quests/scripts | unbuilt | Native stages, conditions, compile, attachment, reward guards |
| Full campaign | unbuilt | End-to-end runs, optional content and endings |
| Performance | untested | Target hardware and retail runtime results |
| Distribution | unbuilt | Dependency manifest, clean install/remove, original assets only |

## Key dependencies
Native records, scripts, assets, navigation, independent retail runtime and save/load verification required. Target script: TES3 MWScript and journal/dialogue result scripts. Geography: Committed 129×129 control terrain; volcanic basin. Chimster-only authoring; retail test runtime required. Track blockers explicitly, never substitute source previews for playable content. No measured playtime yet.
