# Tooling (reproducibility)

Python helpers used to build this repo. Data sources: Etherscan V2 API (source, ABI, logs,
`eth_call`, storage) and the account-balance module. All chain reads are plain `eth_call` from an
arbitrary unprivileged address — no keys, no funds, current chain state.

| Script | Purpose |
|--------|---------|
| `eslib.py` | Etherscan V2 helpers: `getsource`, `getabi`, `getcode`, `eth_call` (arbitrary `from`), `get_storage`, `get_balance`, `creation`; retries transient rate-limit strings. |
| `fetch_source.py` | Fetch a contract's verified source and unpack it into a real file tree (handles raw / single-JSON / double-brace standard-JSON multi-file). Writes `_abi.json`. |
| `probe.py` | Call every zero-arg address-returning getter in a contract's ABI to resolve live wiring. |
| `read_state.py` | Read live per-asset config, pool balances, oracle, issuance, staking → `state/live_state.json`. |

Env: `ETHERSCAN_KEY` (Etherscan V2). Decompiler (`panoramix`) was installed but unused — nothing
required decompilation. A Python venv with `web3`/`eth-abi`/`eth-utils` is used for ABI encoding.
