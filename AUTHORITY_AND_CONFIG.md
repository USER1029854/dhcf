# Live Authority & Configuration State

The reality the source code cannot show, captured from mainnet. Backing data:
`state/live_state.json`, `state/ownership.json`, `state/verification_status.json`.
Captured 2026-08-18 against then-current chain state.

## 1. Authority — who holds each privileged role right now

| Contract | `owner()` | Meaning |
|----------|-----------|---------|
| ActivePool, DefaultPool, CollSurplusPool, SortedTroves | `0x0000…0000` | **Renounced** — wiring permanently locked |
| DCHFToken, TroveManager, TroveManagerHelpers, BorrowerOperations, StabilityPool ×2, StabilityPoolManager, DfrancParameters, AdminContract, PriceFeed, CommunityIssuance, MONStaking | `0x8373…8a69` | Owned by the **2-of-3 Gnosis Safe** |
| MONToken | (not Ownable) | Fixed-supply token, no admin |

**The Safe** `0x83737eae72ba7597b36494d723fbf58cafee8a69`:
- Type: Gnosis Safe **v1.3.0** (canonical singleton `0xd9db…9552`).
- **Threshold: 2 of 3.**
- Owners (EOAs): `0x8c013078c75e790ffed8e11342ecff53c5cd73a8`,
  `0x7aff0f97357a7e8b577298f2fe81e6330975e28d`,
  `0x67733cfa01b42900057759a8eba97afed02c44e8`.
- `nonce` = 192 (actively used).
- Exact powers it retains: see `ARCHITECTURE.md` §4.

**DCHF authorized minters (live):** `validTroveManagers` = { `0x9983…4F7F` }, `validBorrowerOps`
= { `0x9eb2…FD74` }. No others. `emergencyStopMinting` = false for both ETH and WBTC.

**No standing ERC20 approvals** exist from any fund-holding contract (probed live; all zero).

**Pausing:** only MONStaking is pausable (owner-only); it is currently **not paused**.

## 2. Per-asset configuration (DfrancParameters `0x6f99…cc42`)

Identical for both collaterals:

| Parameter | ETH | WBTC | Note |
|-----------|-----|------|------|
| MCR (min collateral ratio) | **110%** | **110%** | below this a trove is liquidatable |
| CCR (critical system ratio) | **150%** | **150%** | Recovery Mode threshold |
| MIN_NET_DEBT | 2000 DCHF | 2000 DCHF | minimum borrow |
| Gas compensation | 200 DCHF | 200 DCHF | liquidator reserve, part of debt |
| Borrowing fee floor | 0.50% | 0.50% | |
| Max borrowing fee | 5.0% | 5.0% | |
| Redemption fee floor | 0.50% | 0.50% | |
| PERCENT_DIVISOR | 100 | 100 | coll. surplus / liq. reward divisor |
| Redemption block until | 2022-10-09 | 2022-10-09 | **past → redemptions ENABLED** |

`DECIMAL_PRECISION = 1e18`, `REDEMPTION_BLOCK_DAY = 14`. These are coherent with each other and
with the code's assumptions (MCR<CCR; fee floors ≤ max fee; standard Liquity-family values).

## 3. Pool balances — physical vs. internal accounting

Every pool physically holds **≥** what its books claim (rounding dust from 8-dec WBTC ↔ 18-dec
internal accounting accrues *in the pool's favour*). No shortfall anywhere.

| Pool | Asset | Physical | Internal book | DCHF debt recorded |
|------|-------|----------|---------------|--------------------|
| ActivePool | ETH | 6.2616 | 6.2616 | 7,498.90 |
| ActivePool | WBTC | 2.48580886 | 2.48580603 | 13,511.08 |
| DefaultPool | ETH | 20.3110 | 20.3110 | 24,887.92 |
| DefaultPool | WBTC | 0.08606624 | 0.08606625 | 6,684.13 |
| CollSurplusPool | ETH | 23.7054 | 23.7054 | — |
| CollSurplusPool | WBTC | 2.32048199 | 2.32048204 | — |
| StabilityPool ETH | ETH | 16.4839 | 16.4839 | (deposits: **0**) |
| StabilityPool WBTC | WBTC | 0.23461150 | 0.23460797 | (deposits: **0**) |

**Supply reconciliation:** DCHF `totalSupply` = **52,582.02**; sum of Active+Default recorded
DCHF debt = **52,582.02**; **delta = 0.00**. Token supply is fully backed by recorded trove
debt accounting — no phantom supply.

## 4. State observations worth carrying into the audit

These are live-state facts (not bugs), each of which changes how a reader should weight the code:

1. **Both stability pools hold 0 DCHF deposits.** The liquidation-absorption buffer is empty:
   liquidations now fall entirely to redistribution (DefaultPool) rather than SP offset. The
   16.48 ETH / 0.23 WBTC still in the SPs are **stranded collateral gains** owed to past
   depositors who have not claimed. The SP offset code path is currently exercised against an
   empty pool.
2. **MON reward emissions are exhausted.** For both SPs `totalMONIssued == MONSupplyCap ==
   5,279,579 MON` — the incentive that would attract SP deposits is gone, consistent with (1).
   CommunityIssuance still holds ~108,990 MON; MONStaking holds ~14.6M MON staked.
3. **Oracle fallback cache is stale.** `lastGoodPrice`/`lastGoodIndex` (updated only on
   trove operations) lag live Chainlink (stored ETH 1690.63 CHF vs live-derived ≈1537 CHF). Only
   relevant in the Chainlink-broken fallback branch, but note it: the fallback would price
   collateral off a stale snapshot.
4. **Redemption whitelist is a live lever.** TroveManager/TroveManagerHelpers expose an
   owner-controlled redemption whitelist toggle; capture did not read its current on/off value
   as a headline, but the capability exists and is Safe-controlled (`ARCHITECTURE.md` §4).

## 5. Oracle configuration (PriceFeed `0x09ab…e9da`)

- `status = 0` (Chainlink primary path active).
- `TIMEOUT = 14400s` (4h staleness bound).
- `MAX_PRICE_DEVIATION_FROM_PREVIOUS_ROUND = 50%`; `MAX_PRICE_DIFFERENCE_BETWEEN_ORACLES = 5%`.
- Registered feeds (from `RegisteredNewOracle` events, = live `registeredOracles`):
  - ETH → price `0x5f4e…8419` (ETH/USD), index `0x449d…b13a` (CHF/USD)
  - WBTC → price `0xf403…e88c` (BTC/USD), index `0x449d…b13a` (CHF/USD)
- Live Chainlink at capture: ETH/USD 1892.90, BTC/USD 64071.41, CHF/USD 1.2318 (all fresh,
  updated within the hour).
