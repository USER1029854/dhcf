# Integrity Checks — shared building blocks vs. real upstream

Checked against genuine upstream (npm / canonical deploy addresses), not against copies shipped
with the project — a doctored baseline is exactly what a diff-based review would miss. Backing
data: `state/integrity.json`, `state/oz_integrity.json`.

## OpenZeppelin — GENUINE (v4.3.2 / v4.3.3)

All 12 bundled OZ files were diffed against real upstream pulled from npm
(`@openzeppelin/contracts@<v>` for v4.3.2, 4.3.3, 4.4.0–4.4.2, 4.5.0, 4.6.0, 4.7.0, 4.7.3, 4.8.0).

**Result: every one of the 12 files is byte-identical to genuine upstream v4.3.2/4.3.3** (those
two releases are identical for these files), after accounting for one cosmetic difference:
Etherscan-served sources strip the `// OpenZeppelin Contracts vX.Y.Z (path)` header comment. No
code differs.

Files verified: `access/Ownable.sol`, `proxy/Clones.sol`, `security/Pausable.sol`,
`security/ReentrancyGuard.sol`, `token/ERC20/ERC20.sol`, `token/ERC20/IERC20.sol`,
`token/ERC20/extensions/IERC20Metadata.sol`, `token/ERC20/utils/SafeERC20.sol`,
`utils/Address.sol`, `utils/Context.sol`, `utils/Counters.sol`, `utils/math/SafeMath.sol`.

(The differences seen against newer 4.6–4.8 releases — `sender/recipient`→`from/to` renames,
`extcodesize`→`account.code.length`, comment wording, a `substraction`→`subtraction` typo fix —
are ordinary upstream evolution and confirm an *older genuine* release, not tampering.)

## Gnosis Safe — CANONICAL v1.3.0

- Owner proxy `0x83737eae72ba7597b36494d723fbf58cafee8a69` is a Gnosis Safe proxy; storage slot 0
  (singleton) = `0xd9db270c1b5e3bd161e8c8503c55ceabee709552`.
- `0xd9db270c1b5e3bd161e8c8503c55ceabee709552` **is the canonical Gnosis Safe v1.3.0 L1
  singleton** (deterministic CREATE2 address, identical across chains). `VERSION()` returns
  `"1.3.0"`. Source fetched to `contracts/upstream/GnosisSafe_Singleton/`.
- No custom modules/guards were introduced by the fork at the singleton level — it is stock Safe.

## Chainlink — CANONICAL

- The 3 price feeds are stock `EACAggregatorProxy` contracts (verified). All three are
  **byte-identical** to each other (runtime codehash `ed698309290d`).
- Each proxy points to a verified `AccessControlledOCR2Aggregator` (canonical Chainlink OCR2):
  ETH/USD→`0x7d4e…6fb5`, BTC/USD→`0x4a34…84f1`, CHF/USD→`0x5763…f9b4`.
- Proxy `owner()` = `0x21f73d42eb58ba49ddb685dc29d3bf5c0f0373ca` (**Chainlink's** governance
  multisig), which can repoint the underlying aggregator. This is Chainlink-controlled, not
  DCHF-controlled — see `UNRESOLVED.md`.

## Byte-identity within the deployment

- **StabilityPool (ETH) and StabilityPool (WBTC) are byte-identical** (runtime codehash
  `44b0fdf55afc`). Both source trees are included for completeness; reviewing one covers both.
- WBTC token is the canonical WBTC (verified).

## The DeFi Franc / Vesta / Liquity fork code itself

The core CDP contracts are the project's **own bespoke fork** of Liquity (via Vesta). This code
is *not* a drop-in shared library to diff against a single canonical upstream — the fork *is* the
product, and its full verified source is in `contracts/verified/`. A line-level diff against
Liquity/Vesta upstreams is a code-review exercise (the divergences are the interesting surface),
not an integrity check, and is left to the audit proper. What is confirmed here: the shared
*primitives* the fork builds on (OZ, Safe, Chainlink) are all genuine, so a diff-based review of
the fork rests on a trustworthy baseline.
