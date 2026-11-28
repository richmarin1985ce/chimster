# Chimster expansion production workspace
Creator mandate: six full DLC-scale expansions, authored entirely in Chimster, no separate external authoring application. All current content is design/prototype unless explicitly marked native-built and retail-tested.

| Project | Target |
|---|---|
| [Fallout: Flagstaff](flagstaff/README.md) | New Vegas |
| [Fallout: Baltimore](baltimore/README.md) | Fallout 3 |
| [Fallout: Nautica](nautica/README.md) | Fallout 4 |
| [Coldharbour](coldharbour/README.md) | Morrowind |
| [The Hunting Grounds](hunting/README.md) | classic Oblivion |
| [The Pits](pits/README.md) | Skyrim |

Each project uses the same layout:
- README.md: production GDD, scope, milestones and locked decisions.
- narrative/: campaign, factions, cast, quest briefs, dialogue and future individual quest documents.
- world/: location register, interiors, dungeons, geographical and layout sources.
- assets/: equipment, architecture, materials and asset work orders.
- scripts/: target-specific script contracts and eventually editable compiled-source projects.
- qa/: acceptance criteria, dependency and native validation reports, actual playtest evidence when available.

Existing structured files in examples/expansions remain canonical for IDs, quest dependencies, item and architecture records. Per-project documents are dated review views and design specifications; changes to identities must first reconcile canonical JSON and then refresh documents. Never silently duplicate or reassign IDs. Preserve creator-locked canon, identify proposals, and distinguish design, portable artifact, native build, and verified retail play. Future binary outputs should be generated from editable Chimster projects and not bundled with proprietary assets. No release is implied.

Flagstaff belongs to the planned Fallout 66 series; its official standalone title is Fallout: Flagstaff. See [series reference policy](fallout66-reference-policy.md). All projects retain individual identity.
