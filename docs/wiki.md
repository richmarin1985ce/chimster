# Local documentation and assistant
Chimster ships an offline manual. No wiki hosting or account is needed. The Wiki tab lists pages and searches them using SQLite FTS5. The page identifier is the exact relative documentation filename, e.g. lod-forge.md. Search and navigation are local; external reference URLs in pages are optional sources, not automatically downloaded or executed. The in-app reader displays plain Markdown text. The canonical content lives in docs/ and is bundled into wheels and executable previews at build time.

## Commands
    python -m chimster wiki list
    python -m chimster wiki search "How do I build terrain LOD?"
    python -m chimster wiki read lod-forge.md
    python -m chimster wiki ask local-model newvegas "How do I build terrain LOD?"

The optional ask command retrieves matching wiki excerpts and supplies them as untrusted reference data to the local Ollama advisory planner. It returns the actual retrieved page IDs alongside the proposal. These are retrieval references, not guaranteed support for every generated statement. It requires an installed and configured model and does not execute instructions or change project files. The manual and search are usable without any AI service.

## Documentation policy
Document each feature's supported engines, input/output formats, examples, dependencies, limitations and verification status. Keep upstream references and license notices; do not mirror entire third-party wikis without permission. Wiki coverage expands as functionality is implemented. Current bundled notes cover existing prototypes, not complete Creation Kit parity. 
