# Model Package (`src/ai_mcp_gateway/model/`)

Pydantic schema models for configuration validation and runtime type safety.

## Contents

- `config.py`: `GatewayConfig` root model (`SessionConfig`, `ServerConfig`, `StorageConfig`,
  `AuthConfig`, `SecurityConfig`) used to validate `config/config.yaml` at startup.
