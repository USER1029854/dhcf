# State-Dependency & Composition Map

Enumeration is the inventory; this is where the audit lives. For each shared state variable:
who writes it, who reads-and-trusts it, and whether an attacker can write-then-read (or split /
cross a boundary) for profit. Every composition below was worked and did not yield an exploit;
the reasoning is given so the verdict is checkable.

## Shared state → writers → readers

| State | Written by | Read/trusted by | Attacker can bias the write? |
|-------|-----------|-----------------|------------------------------|
| `assetsBalance` / `DCHFDebts` (ActivePool, DefaultPool) | gated pool ops (open/adjust/close/liquidate/redeem) | `getEntireSystemColl/Debt` → TCR, recovery mode | **No** — internal accounting, not `balance`/`balanceOf`; raw donations don't count (receive() gated) |
| Trove `coll/debt/stake` (TMH.Troves) | BO (own trove), TM (liquidate/redeem) | ICR/TCR, liquidation eligibility | Only own trove, always coll↔debt consistent + MCR/CCR enforced |
| `baseRate` (TMH) | redemptions (↑), borrows (decay) | borrowing fee, redemption fee | Bumping it costs a real redemption/borrow; decays; floors bound it |
| `P,S,G, epoch, scale` (SP) | offset (TM), deposits/withdrawals | depositor gain/compounded deposit | offset only via TM on real liquidations; error-feedback favors pool |
| `L_ASSETS/L_DCHFDebts` (TMH) | redistribute (TM) | pending trove rewards | only real liquidation redistribution; proportional to own stake |
| `F_ASSETS/F_DCHF` (MONStaking) | increaseF_* (TM/BO on fees) | staker gains | proportional to own stake; fees are real borrow/redeem fees |
| `totalMONIssued/MONSupplyCaps` (CI) | issueMON (SP), admin | MON payout | capped; issueMON only via SP; currently exhausted |
| `lastGoodPrice/index/status` (PriceFeed) | fetchPrice (anyone) | every CR/liquidation/redemption | value comes only from Chainlink; attacker cannot set it |
| DCHF `balanceOf` | mint/burn/transfers (gated) | repayment/redemption sufficiency checks | can only hold DCHF it legitimately obtained |

## Sequences examined (single actor, atomic or multi-tx, flash-loan-funded)

1. **provideToSP → liquidate → withdrawFromSP (atomic).** SP depositor absorbs a liquidation and
   takes the collateral "bonus" (coll worth up to MCR×debt for `debt` DCHF). Not a finding: this is
   the designed liquidation backstop reward; value comes from the *undercollateralized* trove
   (ICR<MCR is a real state, permissionless to trigger), profit scales with capital deposited, and
   `withdrawFromSP` is blocked while an under-collateralized trove remains at the list tail.

2. **buy DCHF below peg → redeemCollateral (cash-out via market).** Standard peg arbitrage:
   redemption pays oracle-priced collateral − fee for 1 DCHF. In-scope only if a *code* bug exists;
   there is none — redemption is at oracle price, hits lowest-ICR troves first (no target choice),
   burns the redeemer's DCHF. Profit = market discount, scales with capital. Not a finding.

3. **Split a redemption into N calls.** Base rate rises by `redeemedFraction/BETA` per call and is
   read by the *next* call, so later chunks pay a *higher* rate; splitting is weakly worse, never
   cheaper. `_updateLastFeeOpTime` (≥60s) blocks decay-clock griefing. No split advantage.

4. **Split a deposit / stake into N.** SP and MONStaking take a fresh snapshot per deposit; no
   retroactive gain; no share-token → no first-depositor inflation. No advantage.

5. **Split collateral top-ups to farm WBTC decimals truncation.** `SafetyTransfer.decimalsCorrection`
   floors 18→8 dec: a top-up credits internal `_amount` but transfers `floor(_amount/1e10)`,
   over-crediting < 1e10 internal units (< 1e-8 WBTC ≈ $6e-4) per call. **Bounded dust, not
   amplifiable** (fixed cap per call regardless of size), and it is truncated *symmetrically* on
   withdrawal (`sendAsset` also floors), so it cannot be extracted as tokens — only inflates ICR by
   sub-cent value per trove. Fails the economic bar decisively.

6. **Cross-asset confusion (use ETH price/SP against a WBTC trove).** `_asset` is threaded through
   every op; troves keyed by (asset,borrower); liquidation sources `getAssetStabilityPool(_asset)`
   and per-asset price; `sendAsset` asserts SP↔asset. No path mixes assets.

7. **Open a trove with a hostile/fake collateral token.** `openTrove(fakeAsset)` calls
   `sanitizeParameters` (sets defaults) but then `fetchPrice(fakeAsset)` reverts
   ("Oracle is not registered!"). Only ETH + canonical WBTC are registered (admin-gated), so no
   hostile-token / transfer-hook reentrancy is reachable.

8. **Reentrancy on ETH sends (redeem / SP withdraw / claim).** All accounting is completed before
   the ETH `.call` (CEI); `sendAsset`, SP `provide/withdraw`, MONStaking `stake/unstake` are
   `nonReentrant`. `SP.offset` is not nonReentrant but is TM-only and adds coll *into* the pool on
   already-settled accounting; a reentered `offset` pays the redeemer/withdrawer nothing. No
   double-withdraw or half-updated read is reachable.

9. **Balance-donation to skew TCR/recovery mode.** All CR math uses internal `assetsBalance`, never
   `address(this).balance`/`balanceOf`; pool `receive()` is caller-gated. Donations are inert.

10. **totalStakes / stake-snapshot manipulation to inflate redistribution rewards.** `totalStakes`
    and `totalStakesSnapshot/totalCollateralSnapshot` move only through gated ops; an attacker
    cannot shrink others' stakes, and own rewards stay proportional to own stake.

11. **Base-rate `assert(newBaseRate>0)` bricking.** For any redemption with `totalAssetDrawn>0`,
    `redeemedFraction/BETA ≥ 1`, so `newBaseRate > 0`; the assert cannot be forced to revert
    redemptions. (Checked arithmetically at current supply.)

12. **MONStaking stake→fee→unstake (atomic).** Gain = own stake × ΔF; proportional to capital;
    fees are genuine borrow/redeem fees. Not disproportionate.

## Off-chain boundary (stated, not assumed sound)
The peg and all liquidation/redemption pricing depend on Chainlink **ETH/USD, BTC/USD, and CHF/USD**
feeds (the CHF/USD "index" multiplies every collateral valuation). These are off-chain-fed and
Chainlink-governed; the contract's freshness/deviation guards (4h timeout, 50% inter-round, 5%
inter-oracle) bound single-round manipulation but not a sustained wrong value. A dishonest or
compromised CHF/USD feed would mis-price the entire system; this is invisible from the destination
chain and out of the contracts' control. See `UNRESOLVED.md`.
