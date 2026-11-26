# Oblivion Remastered, Fallout 76 and future releases
Oblivion Remastered is a hybrid of legacy gameplay data and Unreal Engine 5 presentation. Treat TES4R plugin records and Unreal cooked content as distinct format families. The compatibility module identifies candidate legacy 20/24-byte record layouts by structural scanning, refusing ambiguity; this is not semantic validation. It classifies ESP/ESM/ESL/BSA versus PAK/UCAS/UTOC destinations and checks IoStore pairs, without installation. Unreal package parsing/cooking, asset mapping, TES4R-specific writing and independently tested multi-target deployment are next. Use separately installed xEdit TES4R for independent validation. Do not assume classic Oblivion NIF output is native Unreal content.
Fallout 76 scope is strictly offline client-file research: copied ESM/BA2 structural metadata and version inspection, later licensed local asset extraction, NIF/BGSM/BGEM viewing and standalone previews. Bethesda does not support mods or third-party programs in Fallout 76. Chimster will not emulate servers or backend services, manipulate accounts, network traffic, entitlements or gameplay, inject into the client, bypass anti-cheat, or activate mods in the live online game. No live Fallout 76 installation/launch functionality is intended.
Release snapshots record an explicit user-supplied release label and bounded head/tail sample hashes with sizes. Compare versions and flag changes. A sample digest cannot establish equality of the full file; unknown formats require new adapters, pinned fixtures, full independent validation, and explicit promotion before writers are enabled. Never automatically treat new releases as compatible.
References:
- https://github.com/TES5Edit/TES5Edit
- https://www.nexusmods.com/site/news/15252
- https://github.com/wrye-bash/wrye-bash/issues/699
- https://help.bethesda.net/app/answers/detail/a_id/44429/
- https://github.com/fo76utils/fo76utils
