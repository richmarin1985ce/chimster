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

This is a headless view of an explicitly selected on-disk project, not a connection to a running graphical editor. No arbitrary file reads, writes, subprocess execution, network listeners, or implicit project discovery. The client launches the process with the user's OS privileges; this is not an OS sandbox. Project data may contain sensitive or untrusted text. Only register trusted clients and grant a project you intend to share.

## Next
Issue #39 tracks live instance discovery, resources, structured job control, broader editor operations, explicit per-project write grants and transactional preview/apply/undo, installer registration, and independent client testing. Writes must use the existing revision-checked project core. Keep the AI interface provider-neutral and separate from the optional Calipy assistant.
