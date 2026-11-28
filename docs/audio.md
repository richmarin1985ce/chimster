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
