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

Clients can enumerate/read MCP resources at `chimster://capabilities`, `chimster://project/status` and the `chimster://project/artifacts/{id}` metadata template. No arbitrary URI or file reads are permitted. `project_revision_diff` compares a historical project revision with the current revision, with pagination. `project_plugin_inspect` reads the selected game's plugin header, masters and record counts. For New Vegas projects only, `fnv_record_inspect` reads a record by original plugin identity and local FormID; `fnv_world_check` checks up to eight explicitly ordered project plugins. Original filenames are restored in temporary staging because plugin identity is name-sensitive. Native inputs are bounded (32 MiB per plugin, 64 MiB aggregate for world checks); this is not full-size production load order support. No native plugin is changed. The resource interface supports listing, templates and reading, but not subscriptions yet.

## Active desktop projects and draft replacement
The Project dashboard publishes a per-instance heartbeat every three seconds to the current user's `~/.chimster-editor-instances` directory. POSIX directories and files must be user-owned and private; Windows relies on the user's profile ACL. The presence entry expires after 15 seconds and is removed on normal dashboard destruction. A local client can discover instances with:

    chimster --mcp --discover-active
    chimster --mcp --active
    chimster --mcp --active-instance INSTANCE_ID

`--active` requires exactly one discoverable open project. Selection is resolved once at launch; switching the desktop project does not silently switch the MCP session. Discovery lists paths and selection only to the local caller, without a network listener. The dashboard refreshes when project revisions change; it does not expose or synchronize unsaved edits in other panels. This is local project presence, not live UI command IPC. For durable client configuration use the explicit project path or generate `--client-config` after selecting an instance.

Default sessions remain read-only. Explicitly grant draft replacement with `chimster --mcp --project /path/to/project --allow-edit`. Combine with `--allow-create` if desired. `project_preview_replace` binds a bounded UTF-8 text replacement to the current revision and artifact SHA-256 and returns a capped diff; `project_apply_replace` applies only the matching single-use proposal. Native binaries are excluded. `project_undo` and `project_redo` restore the latest edit made by this MCP session as a new revision, refusing any intervening project revisions. These are single-step, session-local recovery operations, not an arbitrary history rollback. The host flags grant session authority, not per-edit human approval. Discovery-based sessions cannot receive write grants; use an explicit project path. No automatic client settings changes or cloud exposure.
