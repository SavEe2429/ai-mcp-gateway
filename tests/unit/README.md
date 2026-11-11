# Unit Tests (`tests/unit/`)

Fast, isolated unit tests for individual gateway modules.

## Contents

- `test_config.py`: `GatewayConfig` Pydantic validation and path resolvers.
- `test_database.py`: SQLite audit logging, timestamps, and OAuth token-client binding.
- `test_filesystem_sandbox.py`: Traversal protection, symlink/junction blocking, and protected
  `data/` / `.env` guards.
- `test_instance_lock.py`: `SingleInstanceLock` concurrency conflict detection and duplicate
  `run_server()` exit handling.
- `test_logging_filter.py`: `PollingAccessLogFilter` suppression rules.
- `test_package.py`: App export verification and console secret masking (`_mask_secret`).
- `test_terminal.py`: Subprocess execution, CP874/UTF-8 decoding, and auto-backgrounding on timeout.
- `test_vision.py`: Window enumeration, cropped capture mocks, and Base64 encoding.
