# Native AI interoperability (experimental)
Chimster includes a provider-neutral MCP stdio server. No Chimster plugin, model, API key, external service, or additional Python package is required for this server. Select a project explicitly when configuring a trusted local client.

    chimster --mcp --project /path/to/project
    chimster --mcp --project /path/to/project --describe

From a source checkout use `python -m chimster --mcp --project /path/to/project`. Without a project only the capability-discovery tool is exposed. The describe flag prints JSON and exits; do not use it in a client server configuration.

Example local MCP client configuration (adjust executable and project to absolute paths on your machine):
```json
{"mcpServers":{"chimster":{"command":"chimster","args":["--mcp","--project","/path/to/project"]}}}
```
Use the client's own registration/approval mechanism. An ordinary chat prompt cannot grant local application access. Cloud clients require separately authorized connectivity. No HTTP server, tunnel, remote exposure, or automatic configuration is provided by this implementation.

After registration ask: "Connect to Chimster, enumerate its tools, and inspect my selected project."

## Current capabilities
- chimster_capabilities: implemented command discovery and access mode.
- project_status: project name, game, current revision and artifact count.
- project_artifacts: bounded metadata pagination.
- project_artifact: metadata for a single artifact ID.
- project_verify: object integrity check and bounded issue summary (may be slow for large projects).
- MCP handshake-era protocols through 2025-11-25; JSON-RPC stdio, initialize, ping, tools/list and tools/call. Newer protocol eras require compatibility work. No certification or cross-client test claim.

This is a headless view of an explicitly selected on-disk project, not a connection to a running graphical editor. No arbitrary file reads or writes, subprocess execution, network listeners, or implicit project discovery. Default access is read-only; explicit create-only opt-in is described below. The client launches the process with the user's OS privileges; this is not an OS sandbox. Project data may contain sensitive or untrusted text. Only register trusted clients and grant a project you intend to share.

## Next
Issue #39 tracks live instance discovery, resources, structured job control, broader editor operations, explicit per-project write grants and transactional preview/apply/undo, installer registration, and independent client testing. Writes must use the existing revision-checked project core. Keep the AI interface provider-neutral and separate from the optional Calipy assistant.

## Scoped diagnostics and optional creation
The server now exposes `project_read_text` (bounded UTF-8 artifact content) and `check_quest`, `check_interior`, `check_papyrus`, `check_legacy_script`, `check_navmesh_registration`. These call existing editor validators, not native game compilers. Inputs use project artifact IDs, not filesystem paths. Results carry the project revision; inspect the current revision before making decisions.

All clients can call `project_preview_create` with id, kind, filename, text, and revision. It does not change the project. To let a trusted local client create **new** text artifacts only, the host explicitly launches:

    chimster --mcp --project /path/to/project --allow-create

The preview returns a one-use session token in this mode. `project_apply_create` accepts that token, not arbitrary data. The proposal is revision-bound; stale revisions and existing artifact IDs are rejected. The token is not human approval: the launch flag grants creation authority for the session. No remote exposure, replacement, deletion, automatic execution, or AI-triggered rollback is provided. Use the existing project revision rollback workflow for recovery after reviewing intervening edits. Restart without the flag to revoke the grant. Newly created artifacts are drafts, not validated native records.

## Client configuration and native inspection
Generate a copyable local MCP configuration with `chimster --mcp --project /path/to/project --client-config`. It prints JSON and does not change any client settings. For source checkouts the fallback is the current Python interpreter with `-m chimster`; ensure Chimster is installed or importable in the client's working environment. A frozen executable uses its own absolute path.

Clients can enumerate/read MCP resources at `chimster://capabilities`, `chimster://project/status` and the `chimster://project/artifacts/{id}` metadata template. No arbitrary URI or file reads are permitted. `project_revision_diff` compares a historical project revision with the current revision, with pagination. `project_plugin_inspect` reads the selected game's plugin header, masters and record counts. For New Vegas projects only, `fnv_record_inspect` reads a record by original plugin identity and local FormID; `fnv_world_check` checks up to eight explicitly ordered project plugins. Original filenames are restored in temporary staging because plugin identity is name-sensitive. Native inputs are bounded (32 MiB per plugin, 64 MiB aggregate for world checks); this is not full-size production load order support. No native plugin is changed. The resource interface supports listing, templates and reading, and subscriptions (see below).

## Active desktop projects and draft replacement
The Project dashboard publishes a per-instance heartbeat every three seconds to the current user's `~/.chimster-editor-instances` directory. POSIX directories and files must be user-owned and private; Windows relies on the user's profile ACL. The presence entry expires after 15 seconds and is removed on normal dashboard destruction. A local client can discover instances with:

    chimster --mcp --discover-active
    chimster --mcp --active
    chimster --mcp --active-instance INSTANCE_ID

`--active` requires exactly one discoverable open project. Selection is resolved once at launch; switching the desktop project does not silently switch the MCP session. Discovery lists paths and selection only to the local caller, without a network listener. The dashboard refreshes when project revisions change; it does not expose or synchronize unsaved edits in other panels. This is local project presence, not live UI command IPC. For durable client configuration use the explicit project path or generate `--client-config` after selecting an instance.

Default sessions remain read-only. Explicitly grant draft replacement with `chimster --mcp --project /path/to/project --allow-edit`. Combine with `--allow-create` if desired. `project_preview_replace` binds a bounded UTF-8 text replacement to the current revision and artifact SHA-256 and returns a capped diff; `project_apply_replace` applies only the matching single-use proposal. Native binaries are excluded. `project_undo` and `project_redo` restore the latest edit made by this MCP session as a new revision, refusing any intervening project revisions. These are now bounded, session-local recovery operations (up to twenty steps), not arbitrary history rollback. The host flags grant session authority, not per-edit human approval. Discovery-based sessions cannot receive write grants; use an explicit project path. No automatic client settings changes or cloud exposure.

## Asset Forge and background diagnostics
The bridge now exposes `asset_inspect_audio` (WAV/XWM/FUZ metadata), `asset_inspect_mesh` (triangulated OBJ geometry and material groups), `asset_inspect_scene` (portable scene counts and geometry workload), and `asset_inspect_font` (TrueType metadata when fontTools is installed). Inputs are selected project artifact IDs; no direct paths, audio playback, native export or renderer invocation. A 16 MiB artifact limit applies. FontTools remains optional; the bridge omits its tool if the library is unavailable.

`diagnostic_start` accepts an artifact ID and one supported operation: quest, interior, papyrus, legacy-script, navmesh-registration, audio, mesh, scene, font (if available), or plugin. It returns a session-local job ID. Use `diagnostic_status`, `diagnostic_result`, `diagnostic_cancel`, and `diagnostic_discard` to poll and manage work. The queue has one worker and at most eight retained jobs. Queued jobs can be cancelled; running validators cannot yet be interrupted. Results are bounded and discarded on intervening project revision changes during execution. A completed result remains tied to its reported revision. These are Chimster-specific polling tools, not MCP Tasks or push notifications.

## Subscription notifications and installer registration
Subscribe to a supported resource using MCP `resources/subscribe` and stop with `resources/unsubscribe`. The server polls subscribed resources approximately once a second and emits `notifications/resources/updated` when committed metadata changes. A session can hold up to 32 subscriptions. Read the resource again after receiving an update. This monitors saved project data, not arbitrary unsaved editor controls or native MCP Tasks.

With the local AI client closed, a user or installer can explicitly register a read-only project connection in a compatible JSON config file:

    chimster --mcp --project /path/to/project --register-client-config /path/to/client_config.json

The command preserves unrelated settings and other MCP server entries, creates a backup of existing configuration, and refuses to overwrite a different Chimster entry. It does not discover or modify arbitrary clients automatically. The client must support the mcpServers configuration format and be closed to avoid concurrent writes; the preflight check is not a cross-process lock. Review the backup and restart the client after registration. The command deliberately refuses write-enabled registration; use separately approved manual configuration for write grants. No additional Chimster plugin is required.

The standalone installer build now includes an installed-executable smoke test for MCP configuration generation, protocol initialization, tool enumeration, project status and resource enumeration. This is a test implementation, not evidence that a platform build or third-party client test has passed.

## Native record editing (experimental)
For Fallout: New Vegas projects, `fnv_record_preview_edit` stages a single typed field edit using Chimster's existing record editor. It requires artifact ID, original plugin identity, local FormID, field tag, JSON-encoded value, current project revision, plugin SHA-256 and record payload SHA-256. It restores the original filename in isolated temporary staging, checks existing schema constraints, verifies unchanged record payloads and masters, and returns before/after values and the staged digest. Only owned records in ESP artifacts are supported; masters, overrides, unsupported fields and cross-cell moves are excluded. Maximum plugin size is 32 MiB. No source or game install file is modified.

Read-only sessions can preview but cannot apply. To grant a trusted local client native edits explicitly:

    chimster --mcp --project /path/to/project --allow-edit --allow-native-edit

`fnv_record_apply_edit` consumes a matching single-use token and publishes the staged bytes as a new project revision. The same session undo/redo can restore the prior revision, provided no intervening edit occurred. This is a session grant rather than human approval of each edit. Game testing is still required; no claim of runtime compatibility or support for native editing in other games is made.

## Authenticated local HTTP and editor context
The stdio transport remains the default. An opt-in, read-only, IPv4 loopback HTTP endpoint implements handshake-era MCP JSON responses (2025-03-26 through 2025-11-25). Create a private bearer token file, then start the endpoint on a chosen port:

    chimster --mcp --create-token /path/to/private-token
    chimster --mcp --project /path/to/project --http 8765 --token-file /path/to/private-token

A compatible local client uses `http://127.0.0.1:8765/mcp`, the token from the file in its Authorization: Bearer header, and the negotiated session/version headers. The token is not printed. Keep it private, stop the server when finished, and rotate by creating a new file and restarting. Host headers must match localhost or the bound loopback address and port; all browser Origin headers are rejected. Sessions expire after 15 minutes of inactivity, with at most eight retained sessions. HTTP does not offer writes, SSE, push subscriptions, public binds, TLS, OAuth or automatic tunnels. Do not expose it directly to the internet. Cloud clients require a separately reviewed authenticated TLS/OAuth gateway; this implementation is not a complete ChatGPT connector. Later protocol revisions have not been verified.

The `editor_context` tool and `chimster://editor/context` resource report the dashboard instance and selected artifact for the explicitly scoped project, without exposing other project paths. Stdio clients can subscribe to this resource for selection updates. This is not arbitrary GUI automation or access to unsaved panel content. Existing project revision synchronization remains unchanged.

## Opt-in dashboard commands
For a trusted local stdio client, launch `chimster --mcp --project /path/to/project --allow-ui`. The `editor_request` tool queues a `refresh` or `select` action for a specified live instance and current revision. A selection requires an existing artifact ID. The editor consumes requests on its Tk event loop, checking project identity, revision and a 15-second expiry. The response confirms queuing only; inspect or subscribe to editor context to observe the result. No arbitrary input simulation, file mutations, shell calls, or access to unsaved data. The same-user filesystem mailbox relies on the operating system's user isolation, not a sandbox against other processes running under that account. HTTP and automatic config registration do not grant these commands.

## Dedicated verification environment
Run the focused regression suite from an installed source checkout:

    python -m pip install .
    python -m unittest discover -s tests -p "test_mcp*.py" -v

The repository's `MCP interoperability tests` GitHub Actions workflow is available for manual dispatch and relevant pull requests. It compiles sources and runs the focused suite on Windows, macOS and Linux with Python 3.10 and 3.12. The existing application-installer workflow separately builds the frozen executable and checks its MCP handshake. These tests are synthetic and do not require a retail game installation, AI account, or provider plugin. GUI interaction, real-world game records, third-party MCP clients, and deployment security still require separate acceptance testing. No passing run is implied by adding the workflow.

## Cross-game native browsing and asset transformation
`native_record_browse` exposes the existing NativeSession structural catalogs for Morrowind/OpenMW, Oblivion, Fallout 3/New Vegas, Skyrim/SE/VR, and Fallout 4/VR. The selected project profile determines availability; Starfield and Oblivion Remastered remain excluded from this native adapter. The report includes paginated signature, persistent identity where supported, field/reference counts, opaque field counts, and optional aggregate validation. It does not claim that opaque fields are safe, that runtime slots are verified, or that retail files have passed. Input is bounded to 8 MiB. Native typed field editing remains the separately granted FNV subset; a separate reference retargeting adapter is described below. The `native` diagnostic job uses this adapter when available.

`asset_preview_transform` uses Asset Forge's existing intermediate OBJ session to stage scale (1–1000 percent), yaw (-360 to 360 degrees), and ground alignment. It requires the original artifact SHA-256, expected revision, and a new output artifact ID. The preview supplies geometry reports and a staged digest. With `--allow-create`, `asset_apply_transform` publishes only that exact staged OBJ as a separate artifact, leaving the source intact. Input and output limits are 8 MiB and 16 MiB respectively. Session undo requires `--allow-edit`. No native NIF, material binding, collision, or animation export is implied.

The focused suite includes independent subprocess handshakes for all four advertised protocol versions, verifying stdout framing, negotiation, discovery and read-only capabilities. These are synthetic transport tests, not certification against Claude, ChatGPT, or any other vendor's client.

## Production operations and extended native references
`production_preview` exposes supported operations for the selected project and installed libraries: `native-build` (New Vegas records/quest JSON to staged ESP and FormID ledger, without uncompiled script drafts), `navmesh` (portable heightfield mesh), `font` (original polygon glyph JSON to TTF, requires fontTools), `fuz` (existing XWM and optional LIP to FUZ, no LIP generation or codec conversion), `texture-material` (height and mask inputs to normal/specular PNG and DDS, requires Pillow), `mesh-lod` (intermediate OBJ simplification), and `mesh-preview` (flat-color orthographic PNG, not full scene rendering). Inputs are project artifact IDs, not arbitrary paths. The preview returns output hashes and metadata; `production_apply` requires `--allow-create` and publishes the exact staged artifacts as a single new revision, without replacing existing artifacts. `production_discard` clears the staged result. Inputs and outputs are bounded. Native build uses a disposable project, and is for new output IDs only; generated filenames have a `generated-` prefix. No automatic game install or distribution.

`native_record_detail` exposes bounded subrecord and typed reference metadata for a persistent identity. `native_reference_preview` stages retargeting of known reference fields in owned full-slot ESP records to other owned records in the same plugin. It checks the expected old identity, type, revision and plugin digest and verifies unrelated records remain byte-identical. Supported candidate profiles: Oblivion, Fallout 3, New Vegas, Skyrim, Skyrim SE and Fallout 4. Masters, light plugins, VR, opaque layouts, null targets, arbitrary FormID changes and relocation are excluded. `native_reference_apply` requires `--allow-edit --allow-native-edit`; the native grant now supports these reference profiles, while the separate FNV typed field adapter remains FNV-only. Real game validation is required.

Session history now retains up to twenty consecutive transactions across text, native edits, mesh outputs and production bundles. `project_history_status` reports available steps. Undo and redo restore snapshots as new revisions and refuse intervening external changes. History is not a persistent agent audit log and does not grant arbitrary historical rollback.

## Privileged operation approval and durable audit records
CLI sessions launched with `--allow-create`, `--allow-edit`, `--allow-native-edit`, or `--allow-ui` now require a separate local approval for each privileged operation. Earlier sections describing session-only grants refer to the previous implementation; grants are necessary but no longer sufficient for CLI tool calls. Preview the operation, call its apply tool (or request undo/redo/UI action), and the response supplies a request ID. In a separate interactive local terminal, review:

    chimster --mcp --project /path/to/project --review-approval REQUEST_ID

Type `APPROVE` only after inspecting the displayed metadata, hashes and available before/after details. Text preview is capped at 8192 characters; inspect the full staged content separately when truncated. Repeat the identical tool call after approval. Consent is bound to session, exact arguments, preview summary and revision, expires after five minutes, and is consumed once. There is no MCP tool that approves a request. The mechanism is not a sandbox against software with the same OS user privileges. Keep `.chimster/mcp-approvals` private and do not sync/share it; pending summaries can contain project content. Stale request files may require local cleanup. Privileged MCP calls create durable separate records in `.chimster/mcp-audit` (request, start and outcome), excluding proposal tokens, arguments and content. Audit start failure prevents execution; a completion logging failure is reported separately. A queued UI command's completed audit event means the queue submission returned, not that the editor executed it. Logs are not cryptographically tamper-evident and require operator retention management.

## Operator-configured cloud-client endpoint (experimental)
The optional `--remote-config` mode exposes a read-only MCP HTTPS resource with externally provisioned TLS and OAuth token introspection. There is no bundled authorization server, automatic account registration, public hosting, tunnel, certificate issuance or provider plugin. The configuration is an operator-owned private JSON file, with keys `resource` (public HTTPS URL ending `/mcp`), `issuer` (HTTPS authorization-server issuer), `introspection_endpoint` (trusted HTTPS RFC 7662 endpoint), `client_id`, `client_secret`, `certfile`, `keyfile`, optional IPv4 `bind` (default `127.0.0.1`) and optional `port`. Use an authorization server that returns active, issuer, audience, expiration, subject and `chimster:read` scope claims; the audience must include the exact resource URL. Tokens are validated for every request, with no redirect or unsigned JWT fallback. MCP HTTP sessions are bound to the exact token hash. Protected resource discovery is provided at `/.well-known/oauth-protected-resource/mcp`. Only TLS 1.2+ is enabled. Remote writes, UI actions, SSE and subscriptions remain unavailable; the server implements the previously documented JSON-only protocol versions.

    chimster --mcp --project /path/to/project --remote-config /path/to/private-oauth.json

Do not place real credentials in the repository or client prompts. An operator must provision and secure the authorization server, registered client flow, certificate and network path, add connection/rate limits at a trusted gateway, and verify the target AI client's supported connector flow before exposure. No deployed or vendor-certified connection is implied. Loopback stdio remains the default, and local HTTP bearer mode remains available. Earlier references to public remote access being disabled describe the default, not this explicit operator-configured option.

## Live viewport controls
With `--allow-ui`, the editor request tool now also accepts `viewport-show`, `viewport-fit`, `viewport-left`, `viewport-right`, `viewport-up`, `viewport-down`, `viewport-zoom-in`, and `viewport-zoom-out`. These are fixed camera commands on the Tk event loop for the current viewport; they do not open or replace a scene, modify objects, or reveal unsaved data. They require the same local per-operation approval as other privileged calls. The request returns queued, not execution confirmation. The currently displayed scene may differ from the saved project; camera commands only alter its view.

## Native structure operations and full-scene rendering
`native_structure_preview` now supports `duplicate-global` (simple owned GLOB records, new editor ID, fresh plugin-relative FormID, updated HEDR count and allocation cursor), `set-global` (typed numeric GLOB value), and `relocate-reference` (New Vegas only). The first two are candidates for Oblivion, Fallout 3, New Vegas, Skyrim, Skyrim SE and Fallout 4, using exact three-field GLOB layouts in unflagged full-slot ESPs. Relocation is restricted to simple unlinked owned static REFRs in existing temporary exterior cell groups within the same New Vegas worldspace; specify a destination cell identity and integer game-unit coordinates inside that cell. It preserves the reference FormID, rotation, scale and base record, removes the source group entry, inserts into the destination group, and validates unrelated records remain unchanged. It does not create cells, move persistent references, relocate quests/actors, duplicate arbitrary records or rewrite external references. All changes require the existing native grant, preview token and local per-operation approval for `native_structure_apply`; undo restores a previous project snapshot. Native outputs require retail/game testing.

The `scene-render` production operation is advertised when ModernGL is installed. It loads an explicitly selected portable scene artifact, fits a camera to all transformed instances, renders the entire scene through the existing depth-tested GPU renderer at 960x540, and stages a PNG with render statistics. It uses default materials, not external material paths or live desktop screenshots. It requires a compatible graphics context; unsupported GPU environments fail rather than silently substitute a flat mesh preview. The existing production preview/apply permission and approval flow applies. Regression fixtures cover six synthetic GLOB profiles, New Vegas exterior relocation and the screenshot adapter with a mocked GPU renderer. Actual GPU images and retail game files still require runtime verification.
