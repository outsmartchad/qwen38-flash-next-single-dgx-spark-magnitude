# Raw artifact compression

Large captured text artifacts are stored as deterministic gzip files to keep the repository practical. Compression is lossless. Restore original bytes with gzip -dk FILE.gz. Embedded paths in result.json and the original harness logs intentionally retain the filenames recorded during the run.

Compressed captures include tuning.jsonl.gz, thermal.jsonl.gz, rendered/rendered.jsonl.gz, and templates/f67f31e10d8a2109.json.gz. The template is the exact rendered benchmark prompt and can contain substantial text.
