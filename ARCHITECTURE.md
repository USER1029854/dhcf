# Architecture & Trust Graph

How the DeFi Franc system is wired, resolved in **both directions** from the DCHF token:
everything the target leans on (downstream), and everything that holds power over it (upstream).
Every address below was discovered by following what the code actually reads/calls/stores —
by calling live getters and reading verified source — not by assuming role names.

## 1. What DeFi Franc is

A Liquity fork (via Vesta) implementing collateralized debt positions ("troves"). Users lock
ETH or WBTC and mint **DCHF**, a stablecoin intended to track the **Swiss Franc**. The peg is
enforced economically (liquidations + redemptions + fees), and the CHF reference itself comes
from a Chainlink CHF/USD feed. Two collaterals are live: **ETH** (`address(0)` internally) and
**WBTC**. There are exactly two — confirmed from the `PriceFeed.RegisteredNewOracle` event log
(2 events) and `StabilityPoolManager` (2 pools). The graph does not grow beyond what is listed.

## 2. Downstream: what the target leans on

```
                          DCHFToken (target)
                          mint/burn gated to:
                     ┌──────────────┴───────────────┐
              TroveManager                    BorrowerOperations
          (liquidate/redeem)                 (open/adjust/close)
                 │  │                              │  │
                 │  └── TroveManagerHelpers ───────┘  │   (shared trove math;
                 │        (also a DCHF-collateral      │    authorized on ActivePool)
                 │         mover on ActivePool)        │
     ┌───────────┼───────────────┬──────────────┬─────┴────────┐
     ▼           ▼               ▼              ▼               ▼
 SortedTroves  ActivePool   DefaultPool   CollSurplusPool   StabilityPoolManager
  (ICR list)   (holds all   (redistrib.   (claimable         │ registry asset→SP
               collateral)   coll/debt)    surplus)          ├── StabilityPool (ETH)
                                                             └── StabilityPool (WBTC)
                 │                                               │
                 ▼                                               ▼
           DfrancParameters ◄──── AdminContract ────► CommunityIssuance ──► MONToken
           (MCR/CCR/fees…)        (add collateral,      (MON rewards to SP)   (fixed 100M)
                 │                 deploy pools)
                 ▼
            PriceFeed ──► Chainlink ETH/USD ─┐
            (asset/CHF)   Chainlink BTC/USD ─┼─► each ÷ Chainlink CHF/USD (peg anchor)
                          Chainlink CHF/USD ─┘
            Fees also flow to MONStaking (stakers earn borrow/redemption fees).
```

**Fund custody.** Collateral physically lives in **ActivePool** (active troves), **DefaultPool**
(pending redistribution), **CollSurplusPool** (claimable surplus), and the two **StabilityPools**
(liquidation gains). DCHF is an ordinary ERC20 balance held by users/pools. **No contract grants
a standing ERC20 approval to any other** (verified: zero `approve` calls in source, and live
`allowance()` probes across every holder × spender pair returned 0). Collateral leaves a pool
only through gated `sendAsset`/`send*` functions using direct transfers.

**Who can move collateral out of ActivePool** (`ActivePool.sendAsset`, `ActivePool.sol`):
`msg.sender ∈ { BorrowerOperations, TroveManager, TroveManagerHelpers, any registered
StabilityPool }`. Note **TroveManagerHelpers is on this list** — its own access control is
therefore part of ActivePool's attack surface, and the set of "registered StabilityPools" is
mutable by the Safe/AdminContract (see §4).

**DCHF mint authority** (`DCHFToken.sol`): `mint` requires `validTroveManagers[msg.sender]` or
`validBorrowerOps[msg.sender]`. Live, exactly two are authorized: TroveManager `0x9983…` and
BorrowerOperations `0x9eb2…`. Owner can add/remove more (see §4). Per-collateral
`emergencyStopMinting` flags are both **false** (minting live for ETH and WBTC).

## 3. The oracle / peg mechanism (the off-chain-anchored core)

`PriceFeed.getDirectPrice(asset)` computes:

```
priceAssetInCHF = scaledChainlink(asset/USD) * 1e18 / scaledChainlink(CHF/USD)
```

i.e. the asset's USD price divided by the CHF's USD price = asset priced in CHF. DCHF is treated
as ≈ 1 CHF. Consequences an auditor should carry forward:

- The **CHF/USD** feed `0x449d…b13a` is a **shared multiplier on every collateral valuation**.
  If it reads high, all collateral looks more valuable (under-collateralized troves look safe);
  if low, the opposite. It is the single most load-bearing oracle and is entirely off-chain
  (Chainlink OCR operators + Chainlink governance). See `UNRESOLVED.md`.
- `PriceFeed` keeps a `lastGoodPrice`/`lastGoodIndex` **cache** updated only on state-changing
  `fetchPrice()` calls, used as a fallback when Chainlink is deemed "broken" (staleness > 4h
  `TIMEOUT`, or > 50% deviation from previous round, or >5% divergence). The cached value can lag
  live Chainlink substantially (captured: stored ETH 1690.63 CHF vs live-derived ≈1537 CHF).
- `PriceFeed.status` is `0` (chainlinkWorking) — the primary path, not a fallback, is active.

## 4. Upstream: what holds power over the target

The direction where the worst cases hide. Resolved by reading `owner()` on every contract and
enumerating every owner/controller-gated function in source.

### The 2-of-3 Gnosis Safe `0x8373…8a69` is the economic super-admin

It owns the policy contracts and, through them, can (each is a real, currently-callable
owner/`isController` function — `isController` = `owner() || adminContract`, and AdminContract
is itself Safe-owned):

| Power | Function | Contract | Why it matters |
|-------|----------|----------|----------------|
| **Authorize a new DCHF minter** | `addTroveManager` / `addBorrowerOps` | DCHFToken | A newly-authorized address can mint DCHF without limit |
| Halt minting | `emergencyStopMinting(asset,bool)` | DCHFToken | Per-collateral mint kill-switch |
| **Replace the price oracle** | `addOracle(token, chainlink, index)` | PriceFeed | Repoint an asset to an attacker-chosen feed |
| **Repoint the whole PriceFeed** | `setPriceFeed(addr)` | DfrancParameters | Swap the entire oracle contract |
| **Change collateral ratios / fees** | `setMCR`,`setCCR`,`setBorrowingFeeFloor`,`setMaxBorrowingFee`,`setRedemptionFeeFloor`,`setMinNetDebt`,`setPercentDivisor`,`setDCHFGasCompensation`,`setCollateralParameters` | DfrancParameters | Redefine solvency thresholds; e.g. raise MCR to make troves liquidatable |
| **Register/deregister a StabilityPool** | `addStabilityPool` / `removeStabilityPool` | StabilityPoolManager | A registered SP is authorized to pull collateral from ActivePool (see §2) |
| Add a new collateral + deploy its SP | `addNewCollateral` | AdminContract | Expands the asset set |
| Gate redemptions to a whitelist | `setRedemptionWhitelistStatus`, `addUserToWhitelistRedemption` | TroveManager, TroveManagerHelpers | Redemptions (the peg-defense) can be restricted to allow-listed addresses |
| Pause MON staking / move its treasury | `pause`, `changeTreasuryAddress` | MONStaking | Halts fee distribution; redirects treasury |

The Safe is also the **MON treasury** (`MONToken.treasury()`), and has executed **192**
transactions (`nonce`), i.e. it is an actively-used key, not a set-and-forget deployer.

### What the Safe cannot do

The fund-custody + list contracts have **renounced ownership** (`owner() == address(0)`):
**ActivePool, DefaultPool, CollSurplusPool, SortedTroves**. Their `setAddresses` wiring ran once
(`isInitialized == true`) and can never be re-pointed. So the Safe cannot directly rewrite which
addresses ActivePool trusts — but it *can* influence that set indirectly via
`StabilityPoolManager.addStabilityPool` (because ActivePool consults
`stabilityPoolManager.isStabilityPool(msg.sender)` live).

## 5. Why the graph is complete

- Every address stored/returned by every core contract was resolved (see `state/registry.json`).
- Source was swept for hardcoded address literals: **none** (the only 40-hex matches were the
  first half of `bytes32` typehash constants — `PERMIT_TYPEHASH`, `STABILITY_POOL_NAME_BYTES`).
- The collateral/oracle set is closed at {ETH, WBTC} by on-chain event evidence.
- The only edges that leave the readable on-chain world are the **Chainlink feeds** and the
  **Safe signer EOAs** — both catalogued in `UNRESOLVED.md`.
