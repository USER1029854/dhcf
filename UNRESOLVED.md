# Unresolved & Off-chain — what is NOT readable on-chain

Everything with EVM bytecode in this system is **verified and present** in `contracts/`. Nothing
required decompilation (see `contracts/recovered/README.md`). What remains genuinely unresolvable
from the destination chain is listed here — each with what it controls and what would go wrong if
it behaved dishonestly. These are holes exactly like an unread contract; they are named, not
filed away.

## Off-chain trust dependencies (highest priority)

### 1. Chainlink CHF/USD feed — the peg anchor  ★ most load-bearing
- **Address (on-chain shell):** proxy `0x449d117117838ffa61263b61da6301aa2a88b13a` →
  aggregator `0x5763fc5fabca9080ad12bcafae7a335023b1f9b4` (`AccessControlledOCR2Aggregator`).
- **What it controls:** the CHF reference for the *entire* system. Collateral is priced as
  `(asset/USD) ÷ (CHF/USD)`, so this feed multiplies every collateral valuation, every trove's
  health, every liquidation and redemption decision, for **both** collaterals at once.
- **What's off-chain:** the value is produced by Chainlink's OCR operator set (off-chain nodes
  signing reports) and the aggregator can be repointed by Chainlink governance
  (`0x21f7…73ca`). Neither is DCHF-controlled or on-chain-auditable.
- **Failure mode:** if CHF/USD reports too high, under-collateralized troves look solvent
  (bad debt accrues silently); too low, healthy troves become liquidatable/redeemable.
- **On-chain evidence gathered:** feed is live, `status=0`, last update fresh (< 1h at capture),
  answer 1.2318 — consistent with a real CHF/USD rate. Deviation guards (50% vs previous round,
  4h timeout, 5% inter-oracle) bound single-round manipulation but not a sustained wrong value.

### 2. Chainlink ETH/USD and BTC/USD feeds
- ETH/USD `0x5f4e…8419`→`0x7d4e…6fb5`; BTC/USD `0xf403…e88c`→`0x4a34…84f1`.
- Same off-chain nature as (1); each governs its own collateral's USD valuation. Live and fresh
  at capture (1892.90 / 64071.41).

### 3. Gnosis Safe signer keys (the 2-of-3 admin)
- **What it controls:** the economic super-admin powers in `ARCHITECTURE.md` §4 — including
  authorizing a new **unlimited DCHF minter**, swapping the **price oracle**, and changing
  **MCR/CCR/fees**. This is the largest single point of control in the system.
- **What's off-chain:** who holds the 3 EOA private keys
  (`0x8c01…73a8`, `0x7aff…5e28d`, `0x6773…44e8`), how they are secured, and whether any 2 are
  co-located. On-chain you can see only the addresses and that the Safe has executed 192 txs.
- **Failure mode:** compromise of any 2 keys = full economic control of the protocol. This is the
  "separate contract holding a key that can act on the token" pattern in its most direct form:
  here the key-holder is the multisig itself, and its power is explicit on-chain.

## Residual on-chain items (named, low residual risk)

- **Redemption whitelist current value.** The Safe-controlled redemption whitelist toggle exists
  on TroveManager/TroveManagerHelpers; its current enabled/disabled state and membership were not
  captured as a headline value. Reading `getRedemptionWhitelistStatus()` / the whitelist mapping
  closes this. (Capability is documented; only the live setting is open.)
- **Stranded StabilityPool collateral.** 16.48 ETH / 0.23 WBTC sit in the SPs with 0 deposits —
  accounting attribution of these gains to specific past depositors was not reconstructed (it is
  a claimable-gains bookkeeping question, not an unread contract).

## Explicitly NOT unresolved (checked, and closed)

- No unverified bytecode anywhere in the graph — nothing to decompile.
- No hardcoded address literals in source (both 40-hex matches were `bytes32` typehash halves).
- Collateral/oracle set is closed at {ETH, WBTC} by event evidence.
- No standing ERC20 approvals from any pool.
- Shared building blocks (OZ, Safe, Chainlink) are genuine (`INTEGRITY.md`).
