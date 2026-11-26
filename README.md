# Chimster

Independent hobby project: an AI-assisted Bethesda modding workshop from Morrowind through Starfield. No WorkKit or Endable dependency. Manual workflows must remain available.

## Architecture
Game-specific record adapters; isolated workspaces; semantic version control; fragment ownership and compilation; launch and supported runtime reload; native localization; audio and lip-sync; SWF/GFx and map-marker editing; validation and release packaging. AI operations are staged and reversible.

## Licensing
No third-party executables, assets or code are bundled by default. Evaluate OpenMW/OpenMW-CS (GPLv3) for reuse, and JPEXS (GPLv3+, library LGPLv3+) for UI editing. Original Chimster code is MIT licensed. Combined derivative distributions incorporating GPL-covered code must comply with the applicable GPL; separately installed tools retain their licenses. See LICENSE and docs/licensing.md. Proprietary tools remain separately installed.

See docs/roadmap.md for scope and source references. This is early development, not a complete Creation Kit replacement.

## Run the prototype

```sh
git clone https://github.com/richmarin1985ce/chimster.git
cd chimster
python -m unittest discover -s tests -v
python -m chimster tools --game openmw
python -m chimster ui
```

The desktop shell requires Tkinter. The catalog contains 61 tool entries; cataloging is not integration. If Git is unavailable due to DNS or sandbox restrictions, use an authorized GitHub API client to read and commit files, or download a source ZIP on a network-enabled machine. Do not disable TLS or hard-code GitHub IP addresses.

## OpenMW bridge
See [OpenMW integration](docs/openmw.md). Use the desktop OpenMW bridge tab or `python -m chimster openmw discover`. The editor is separately installed; game launch uses an explicit profile. Tests use mocks and synthetic inputs until a real installation is available.

## Load order and AutoPatch
See [architecture and limitations](docs/loadorder.md). `python -m chimster loadorder profile.json --cache cache.sqlite` reads a JSON profile containing game, data_dirs (low to high priority), plugins (active order) and optional after pairs. `python -m chimster autopatch snapshot.json` produces a review-only consolidation plan from externally normalized plugin and record evidence. It does not write or deactivate plugins. Full libloot integration and native patch writing are future work.

## Experimental quick-win pass
See [quick wins](docs/quick-wins.md). Run `python -m chimster --help` for new commands: tool discovery, isolated mod ZIP installs, profiles, TES3 inventory and narrow static overrides, loose-asset audit, FOMOD metadata, Git history/branches, FFDec command previews. These are experimental; do not use with original game files or production saves. Cross-platform portable builds are proposed through CI, not yet released.
