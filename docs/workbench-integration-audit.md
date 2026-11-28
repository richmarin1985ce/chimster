# Workbench integration audit
Source inspection only; no new runtime or retail verification. Existing GUI forms are not equivalent to dedicated editors. Section 3 remains overriding.
| Section | Next integration gate |
|---|---|
| 1 Core | Shared project/session lifecycle, revision events |
| 2 Compatibility | Central profile aliases and capability gates |
| 3 Records | Native typed field controls, condition registry, remap and dependency review |
| 4 Mod management | Shared load order and master resolution |
| 5 World | Native cell and placement selection in viewport |
| 6 Landscape | Shared terrain revision and texture budget |
| 7 Validation | Common diagnostics with record navigation |
| 8 Rendering | Shared scene selection and streaming |
| 9 Mesh | Asset registry and preview |
| 10 Collision | Overlay and property editing |
| 11 Texture | Material assignment and asset registry |
| 12 LOD | Dirty tiles from world changes |
| 13 Version control | Shared transaction history and semantic diff |
| 14 Quests | Native actor/topic/stage references and conditions |
| 15 Scripting | Source and compiled artifact bindings |
| 16 Books | Native record selection and placement |
| 17 Characters | Typed NPC fields and inventory |
| 18 Gameplay | Typed item, faction, perk and list editors |
| 19 Audio | FUZ panel, dialogue line bindings |
| 20 Localization | Stable string IDs and native dialogue |
| 21 Interface | Shared project asset paths and preview |
| 22 Testing | GUI launch and menu smoke tests, diagnostics |
| 23 AI | Review-only proposals through transaction layer |
| 24 Wiki | Contextual help per editor |
| 25 Distribution | Validated project export and manifests |
| 26 Expansions | Shared terrain recipes, project templates and validation |
Corrected portfolio: Coldharbour, Hunting Grounds, The Pits (impact-scarred central abyss), Baltimore, Route 66 Flagstaff, Nautica. Baltimore/Nautica USGS acquisition pending. Procedural terrain files not yet in repo.
This pass connects native profile selection, guards empty actions, isolates two optional panel initialization failures, adds scrollable generated forms and fixes list default delimiter. Remaining: full session integration, generated form argument ordering and validation tests, native schema provenance and retail verification. No section marked complete.
