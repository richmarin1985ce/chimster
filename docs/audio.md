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
