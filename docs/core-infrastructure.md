# Core infrastructure
Local first; no required account or external AI service. The core remains MIT and independent of other projects.
## Shared project
Project folder contains .chimster/project.json, immutable-by-convention objects addressed by SHA-256, and historical JSON manifests in revisions/. Atomic manifest replacement, exclusive writer lock, expected revision checks, batch import/remove, content deduplication and rollback as a new revision. Imported files are copied, originals untouched. Objects are not a security boundary or backup; verify integrity and keep external backups. Failed imports can leave unreferenced objects; no garbage collection yet. Never manually delete the lock without checking another writer is not active.
    chimster project create MyProject Example newvegas
    chimster project add MyProject records records records.json --revision 0
    chimster project build MyProject records records gameplay Gameplay.esp --revision 1
    chimster project export MyProject gameplay Gameplay.esp
    chimster project verify MyProject
    chimster project rollback MyProject 1 --revision 2
Build integrates FNV record and quest projects and stable FormID ledgers. Each build publishes both artifacts in one revision, with ordered master artifact IDs using --master. Other tools can import/export artifacts through the dashboard, but direct edit-session integration is not complete. A project object is content-addressed, not a mutable editor file. Script drafts explicitly require --script-draft and are not deployable.
## Dependency manager
    chimster dependencies pin dependencies.json "NIF bridge" /path/to/nifbridge
    chimster dependencies status --config dependencies.json
Reports discovered vs pinned vs changed/missing tools and optional Python modules. Hash binds the executable file, not its dependencies or runtime version; no automatic downloads, installations, or global tool replacement. Existing integration commands still require explicit paths.
## Extension SDK
Declarative manifest schema 1 remains supported. Local executable receives two positional paths: request.json and response.json. Request has api_version=1, capability and payload. Response has api_version=1, ok=true and result (or ok=false and error). Approve exact executable and manifest hash before invoking:
    chimster extension-approve extension.json /path/to/extension trust.json
    chimster extension-run trust.json validator payload.json --execute
No shell, bounded JSON and timeout, temporary working directory and minimal environment. This is NOT a sandbox: approved local executables have the same OS privileges as the user. Only approve code you trust. No automatic application of returned actions, no remote marketplace.
## Offline application installation and rollback
    chimster app-release build app-folder chimster.zip 0.3.0 chimster
    chimster app-release install local-app chimster.zip --sha256 TRUSTED_DIGEST --activate
    chimster app-release status local-app
    chimster app-release activate local-app 0.3.0
Package manifest validates platform, exact files, size and SHA-256. The entire package digest must be supplied from a separately trusted channel before installing. Version directories are staged and verified, current.json selects the active version, older versions remain for rollback. No elevation, network auto-update, shell association, desktop shortcut or code signing. Launch the active entrypoint explicitly. Integrity hashes alone do not authenticate a publisher.
The installer CI workflow builds a PyInstaller one-file executable for each hosted OS, wraps it in a verified ZIP and smoke-tests the installed executable. Artifacts are CI previews, not a signed production release; no third-party native helper or game assets bundled. Actual host hardware and desktop UI interaction still need independent testing.
