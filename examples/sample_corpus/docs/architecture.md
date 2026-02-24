# Architecture

## Services
- **gateway**: HTTP entrypoint, request validation, auth
- **orders**: creates and manages orders
- **payments**: charges cards and handles retries

## Data flow
1. gateway receives request
2. orders validates and persists order
3. payments processes charge and emits receipt event
4. orders updates state based on payment outcome

## Retry policy
Retries are implemented in `src/retry_policy.py` and used in `src/api.py`.

