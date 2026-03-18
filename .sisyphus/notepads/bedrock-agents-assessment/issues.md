# Issues & Gotchas - Bedrock Agents Assessment

Session started: 2026-03-18T16:42:35.258Z

## 2026-03-18 Gotcha: local runtime test requires project virtualenv

- `./test_runtime.sh` failed outside virtualenv with `ModuleNotFoundError: No module named 'boto3'`.
- Resolution: run tests via `source venv/bin/activate && ./test_runtime.sh ...` in this repository.
