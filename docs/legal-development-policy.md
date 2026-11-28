# Legal and development safeguards

Initial policy review: 2026-11-27. This is an engineering policy, not legal clearance.

Chimster is an independent MIT-licensed content authoring and plugin editing tool. No affiliation or endorsement is claimed.

## Development boundaries
- Implement original parsers, serializers, editors and synthetic fixtures from publicly available format information.
- Do not decompile game executables, derive proprietary source, bypass access controls, use leaked SDKs or redistribute proprietary assets.
- Require authorized user-supplied game installations/data. Keep original game data local; do not upload or bundle it.
- Prefer new plugins and original assets; preserve original masters and notices.
- Require separate license review before script bytecode decompilation, archive export, cross-game asset conversion, bulk copyrighted text extraction or proprietary SDK integration.
- Use game names only for accurate compatibility descriptions. No official logos, copied artwork or claims of endorsement.
- Document source URLs, versions, licenses and whether a reference supplies format facts or incorporated code. Public availability is not permission.
- Review dependencies and copied/adapted code at file level before distribution; preserve notices and meet source obligations. Do not assume GPL/MPL code can be relicensed MIT.
- Use synthetic or expressly licensed fixtures and audit release archives for proprietary material.
- Review title, edition, storefront and editor-specific agreements before certifying support. Escalate uncertainty to qualified counsel; community practice is not legal authorization.

## Initial sources
- https://bethesda.net/data/eula/en.html
- https://bethesda.net/data/tos/en.html
- https://store.steampowered.com/eula/1946180_eula_0
- https://store.steampowered.com/eula/eula_202480
- https://github.com/TES5Edit/TES5Edit (current repository MPL-2.0; older documentation MPL-1.1)
- https://github.com/OpenMW/openmw (GPLv3 repository license)
- https://github.com/wrye-bash/wrye-bash (GPLv3 repository license)
- https://github.com/loot/loot (GPLv3 repository license)
- NifTools components and Mutagen: exact license files not yet verified.
- Chimster LICENSE: MIT.

## Release gate
Record provenance, dependency notices, game-specific EULA review, asset/fixture audit, trademark review and unresolved risks before public release. This policy does not establish that existing code has passed those checks. No claim of Bethesda approval or comprehensive enforcement-history review.
