# Section 19: Audio and voice workbench

Run `python -m chimster.audio --help` from a checkout or `chimster-audio --help` after installation.

## Implemented first pass

- Version-one FUZE container packing and unpacking, preserving LIP and xWMA bytes.
- RIFF/XWMA structural validation; PCM WAV metadata and truncation checks.
- Recursive loose-file voice inventory grouped by case-insensitive relative stem; missing expected lines, malformed assets and duplicate names.
- Explicit local executable discovery and subprocess adapters: FFmpeg decode/PCM normalization, xWMAEncode-compatible encode, Rhubarb JSON preview, FaceFXWrapper-compatible native LIP generation.
- Exclusive destination creation; subprocess outputs validated in temporary directories.
- Synthetic regression tests; external tools mocked, not retail game certification.

## Example

```sh
chimster-audio discover
chimster-audio inspect voice.fuz
chimster-audio unpack voice.fuz extracted
chimster-audio inventory Data/Sound/Voice --expected expected.json
chimster-audio decode extracted/voice.xwm voice.wav --tool ffmpeg
chimster-audio normalize voice.wav normalized.wav --tool ffmpeg
chimster-audio preview normalized.wav cues.json --tool rhubarb --transcript "Example dialogue."
chimster-audio native-lip normalized.wav voice.lip --tool FaceFXWrapper --fonix FonixData.cdf --game Skyrim --transcript "Example dialogue."
chimster-audio encode voice.wav voice.xwm --tool xWMAEncode
chimster-audio pack voice.xwm new.fuz --lip voice.lip
```

The expected manifest is a JSON array of relative voice stems (no extension) obtained from the target game's actual dialogue records, e.g. `["Example.esp/VoiceType/QuestTopic__00001234_1"]`. Names are supplied, not inferred by this module. No original assets are overwritten.

## Tool and game constraints

- Skyrim and Fallout 4 native LIP adapters require a separately installed compatible backend and user-supplied licensed data. FaceFXWrapper incorporates Creation Kit code; do not redistribute it or FonixData.cdf with Chimster. https://github.com/Nukem9/FaceFXWrapper
- Rhubarb is MIT licensed; its 2D mouth cues are preview data only, not Bethesda LIP. https://github.com/DanielSWolf/rhubarb-lip-sync
- FFmpeg supports xWMA demuxing; do not assume it can mux xWMA. Use a separately installed compatible encoder. https://ffmpeg.org/general.html
- OpenFaceFX has an experimental Skyrim LIP writer; evaluate separately before integration, and do not represent experimental output as in-game verified. https://openfacefx.com/docs/api/exporters/
- FUZ validation is structural, not compressed-payload decoding or native facial animation validation.
- Skyrim/FO4 paths are expected to be supplied from game-specific records. Older TES/GECK loose WAV/MP3/OGG conventions, Starfield Wwise/WEM, sound descriptors, music, archive-aware resolution, desktop waveform/playback, recording, batch queue and native dialogue linking remain pending.
- No commercial service or proprietary SDK bundled. Generated audio should use recordings and voices for which the mod author has appropriate rights.

Run `python -m unittest discover -s tests -p test_audio.py -v`. Synthetic xWMA fixture bytes are structural only; do not ship them as game audio.

## Dialogue voice manager

The existing Voice containers desktop tab now includes a manifest audit, batch preview and explicit staged build. The standalone CLI is `python -m chimster.voice_manager` or `chimster-voice` after installation.

Example manifest:

```json
{"game":"Skyrim","lines":[{"stem":"Example.esp/VoiceType/QuestTopic__00001234_1","record":"Example.esp:00001234","text":"Example dialogue."}]}
```

```sh
chimster-voice audit Data/Sound/Voice manifest.json
chimster-voice batch Data/Sound/Voice manifest.json --output StagedVoice
chimster-voice batch Data/Sound/Voice manifest.json --output StagedVoice --encoder xWMAEncode --ffmpeg ffmpeg --lip-tool FaceFXWrapper --fonix FonixData.cdf --execute
```

Batch mode defaults to preview, refuses existing outputs, requires separate source and output roots and requires lip payloads unless explicitly allowed. Builds are per-line, not all-or-nothing. Record identities and exact file stems are supplied by the manifest; automatic extraction from native INFO records, validation of record IDs, game verification and archive integration are pending. Existing FUZ files with missing lip data must be unpacked first. External tool availability and normalization requirements may still block execution after preview. No external binaries are bundled.

## Waveform and take editing

Open Assets > Voice containers > Open waveform and lip-sync editor. The separate window accepts mono/stereo PCM16 WAV up to 128 MiB, draws a peak envelope, provides mouse-drag or exact time selection, FFplay playback of the original selection, and exclusive export of trimmed audio with gain and fades. Load Rhubarb JSON for preview mouth cues, edit cue boundaries and shapes, and export full or clipped cue timelines. These are not native Bethesda LIP; regenerate LIP after editing audio. No audio device capture yet.

Local take registry commands:

```sh
python -m chimster.voice_takes register Takes recording.wav --line Example.esp/Voice/Line --performer "Actor A" --rights "Original recording with permission"
python -m chimster.voice_takes list Takes
python -m chimster.voice_takes select Takes TAKE_ID StagedVoiceSource
````

Takes are copied, hash-checked, assigned a unique ID, and include explicit performer and rights metadata. Selection creates a new staged WAV without overwriting other takes. Rights metadata is a user declaration, not independent proof. Automatic native INFO extraction is still pending: the current verified writer covers FNV's generated TRDT/NAM1 layout, while this voice manifest currently covers Skyrim/FO4 and requires exact stems rather than guessed native names. Test execution remains deferred.

## Native FNV dialogue extraction and microphone recording

`python -m chimster.dialogue_audio Quest.esp --output lines.json` extracts supported 24-byte TRDT / NAM1 INFO response pairs from a local FNV plugin, using origin/local FormID identity and response number. Compressed payloads use the existing bounded decoder. Invalid records are reported rather than guessed. Optional `--mapping exact-paths.json` joins each line ID to explicit voice stems. This is not automatic filename resolution, a winning-load-order audit or a Skyrim/FO4 FUZ manifest.

Open Assets > Voice containers > Record and manage takes. Install the optional `recording` extra and platform PortAudio if needed. Select a microphone, specify performer and rights, and confirm a bounded recording (0.1–300 seconds). Cancellation discards capture before registration where possible; import WAV, preview and stage a selected take are also supported. The CLI is `python -m chimster.voice_record devices` or `python -m chimster.voice_record record new.wav --device 0 --seconds 10`. The desktop FUZ tools now use the same strict XWMA validator as batch processing and extract .xwm rather than .bin. Native capture and game compatibility remain untested in this environment.

## Native lip-sync priority and deferred titles

The master checklist already defers Starfield-specific work. Preserve existing implementations; defer new Wwise/WEM development and exclude it from active release readiness.

`python -m chimster.lip_pipeline build voice.wav NewLip --game Skyrim --transcript "Hello" --tool FaceFXWrapper --fonix FonixData.cdf --ffmpeg ffmpeg` creates a new directory containing the native LIP and a provenance receipt. Supply your own licensed backend and Fonix data. The separate experimental MIT OpenFaceFX path is `python -m chimster.lip_pipeline build voice.wav NewLip --game Skyrim --transcript "Hello" --tool openfacefx --backend openfacefx --experimental`. This never implies Fallout 4 compatibility or in-game validation. The upstream Skyrim exporter still needs slot calibration and runtime confirmation: https://github.com/OpenFaceFX/OpenFaceFX/issues/12 .

`python -m chimster.lip_pipeline verify NewLip voice.wav --transcript "Hello"` checks source, transcript and output hashes. `inspect` reports modern LIP header fields; this is not curve-level validation. Generation normalizes PCM to 16 kHz mono when configured. The experimental backend is deliberately separate from the default batch pipeline; no automatic promotion to production FUZ assets. No third-party code, proprietary resources or executable is bundled. Tests are synthetic and execution is deferred.

## Native header correction and regeneration workbench

The 12-byte wrapper interface header differs from the observed 24-byte on-disk FaceFX animation header. Native inspection now checks the observed version, component count, target vocabulary (16 Skyrim / 43 Fallout 4) and game-specific duration-tick relation. These are narrow format checks, not validation of curve data. See https://github.com/OpenFaceFX/OpenFaceFX/issues/12 .

Open Assets > Voice containers > Generate and verify native LIP for local backend generation, optional normalization, header inspection and receipt verification.

`python -m chimster.lip_batch VoiceSource OldReceipts NewReceipts manifest.json` previews stale/missing LIP regeneration. Add `--tool FaceFXWrapper --fonix FonixData.cdf --ffmpeg ffmpeg --execute` to generate staged outputs. The three roots must be disjoint; current matching nonexperimental receipts are skipped. Existing output directories are never overwritten. Hashes prove matching inputs, not engine correctness. Native curve editing, real backend tests, slot calibration, and receipt integration into the FUZ builder remain pending.

## Vendored free native curve codec

Chimster vendors the MIT-licensed OpenFaceFX research codec from https://github.com/OpenFaceFX/OpenFaceFX/blob/main/tools/lip_codec_research.py (source blob 7d0ddb18ea2b2572bcc135dd9f117e526a32594d). Its original copyright and MIT license are retained in `chimster/_openfacefx_lip_codec.py`. No external binary or proprietary asset is needed for raw curve inspection/editing. The upstream research codec is not a stable public API and its four-sample validation is not game certification.

Open the native LIP workbench and choose Native curve editor. Inspect Skyrim and Fallout 4 raw slots, view curves, export CSV, and stage edits to existing nonpaired Skyrim weights only. The CLI is `python -m chimster.lip_curves inspect input.lip`, `python -m chimster.lip_curves csv input.lip out.csv`, or `python -m chimster.lip_curves edit input.lip edits.json new.lip --experimental`. The edits file is an array of objects such as `[{"frame":1,"slot":0,"value":0.5}]`. Both the original and edited payload must roundtrip exactly, and edits that alter routing or create ambiguous token encodings are rejected. Header, raw slot indices, pair flags and marker structure are preserved. Fallout 4 editing, paired tangents, insertion/deletion, slot-to-morph calibration and in-game playback remain pending. No actual retail assets are included. Regression tests are synthetic and not yet executed.

## Custom phonemes, acoustic alignment and calibration

Open Assets > Voice containers > Generate and verify native LIP > Phonemes and calibration. Open a WAV, import JSON (array or segments object), CSV/TSV (phoneme,start,end[,confidence]), or long-format Praat TextGrid with an explicitly chosen interval tier. All timestamps are in seconds. Unicode labels, IPA, ARPAbet stress digits and custom fantasy-language labels are preserved; silence intervals become sil. Add, edit and delete intervals and export JSON. Imports reject overlaps and intervals exceeding the WAV duration.

`python -m chimster.phoneme_import align voice.wav phones.json --transcript "Example" --dictionary local.dict --model local.zip` runs the separately installed Montreal Forced Aligner with local model and dictionary. Uses the MFA 3.x align_one contract; --legacy selects align_one_legacy for newer versions. See https://montreal-forced-aligner.readthedocs.io/en/v3.3.3/user_guide/workflows/alignment.html . Model and dictionary licensing and phoneme inventory compatibility must be checked independently. No models are downloaded or bundled by Chimster. Actual backend execution awaits testing.

`python -m chimster.morph_calibration probes NewProbes --tool openfacefx` wraps the MIT OpenFaceFX Skyrim calibration CLI, structurally checks all 33 probes, and creates observations.json. Test each probe on an isolated voiced line in a disposable game/mod profile and record which morph actually moves. Set observed=true and enter a morph label; use none for inactive slots. Then add a phonemes object mapping exact phoneme strings to raw slot weights, e.g. {"custom":{"22":0.7}} only if slot 22 has been observed and is active. These example values are illustrative, not a calibrated mapping. The preview command joins the validated timeline with the profile and rejects unknown labels or unobserved slots. Preview JSON does not compile native LIP or certify facial animation. Native calibrated curve synthesis, visual profile editing, drag/drop import, real MFA runs, Fallout 4 slot calibration and in-game Skyrim observation remain pending. No proprietary assets or paid services added.

## Native custom phoneme synthesis and shareable profiles

The Phonemes and calibration window now exposes Edit morph profile and Export native Skyrim LIP. A profile can be created from scratch or loaded from observations.json; select a raw slot, record in-game observations and notes, assign one or more observed active slots to arbitrary Unicode phoneme labels and save a new JSON profile. These files are portable between projects but should only be reused for the same calibrated game/rig context. They do not contain audio or executable code.

`python -m chimster.phoneme_synthesis voice.wav phones.json profile.json NewOutput --experimental` maps timed phonemes to a 30fps slot grid with bounded onset/offset ramps (default 0.04 seconds), then encodes it with the vendored OpenFaceFX research codec. A new output directory contains voice.lip and a receipt with SHA-256 hashes of the audio, timeline, calibration profile and result. This receipt is specific to custom synthesis, not the FaceFXWrapper transcript receipt. Exact positional/float round-trip is required; ambiguous adjacent weights and unsupported grids are rejected. This is experimental Skyrim-only output, not proof of correct game animation. The unknown header field follows the upstream research value. No proprietary backend required for this path.

Remaining: real runtime calibration, short-phoneme preservation at native frame rate, coarticulation beyond simple ramps, direct FUZ receipt integration, full character-model preview, actual drag/drop, Fallout 4 writing and executing regression tests.

## Shared desktop drag-and-drop

Install the optional `dragdrop` extra (TkinterDnD2) to enable operating-system file drops. If the extension is absent, the normal file pickers remain available. Dedicated targets now cover Project, native records, Record projects, Record editor, Plugin inspector, Game compatibility, Load order, Worldspace browser and validator, 3D viewport, Landscape budget, Terrain, Interior, Navmesh, Asset Forge, Texture Forge archive input, Quest, Dialogue views, Scripts, Books, Localization source and Minigames. The audio workbenches accept source FUZ/XWM/LIP, WAV, manifests, voice roots, cue JSON, morph profiles and phoneme bundles; model rig JSON drops are supported in character preview. Generic development tools accept recognized input file/folder fields. Each route uses the existing import routine with extension and local-path checks. Replacing editable state prompts for confirmation; ordered plugin/archive additions use the established order review. No drop automatically executes external tools or exports a plugin. NIF asset import retains its trusted-helper confirmation. Not all specialized file dialogs have direct drops: texture source image pairing, compiler executable and flags, output paths, specialized archive builders and localization catalog import still use explicit browsing. Native OS drag testing and regression execution remain pending.
