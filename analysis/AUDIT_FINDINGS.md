# DeFi Franc (DCHF) — Security Audit Findings

**Scope:** the 17 deployed DeFi Franc contracts + DCHF/MON tokens (Ethereum mainnet), audited as
configured against live parameters. Method: mechanical enumeration of all 193 external/public
entry points (`ENTRYPOINTS.md`), full read of every value path, a state-dependency/composition
pass (`COMPOSITION_MAP.md`), a secrets/signature sweep, config-coherence review, and empirical
guard simulation from an unprivileged address (`state/audit_simulation.txt`).

## Verdict

**No vulnerability found that meets the bar** — neither an economic exploit (disproportionate,
stake-independent profit) nor an unauthorized-access defect (a fund/authority path reachable by
someone who shouldn't reach it).

DeFi Franc is a faithful multi-collateral fork of Liquity (via Vesta). Its safety-critical
properties hold as deployed:
- **Access control is complete and correct.** Every fund-moving and state-mutating function is
  gated to the exact caller its role requires; all were confirmed reverting for an arbitrary
  caller with the predicted message. All one-time `setAddresses` are already initialized on-chain,
  so wiring cannot be hijacked.
- **Accounting is donation-immune.** Every collateral-ratio / TCR / recovery-mode decision reads
  *internal* accounting (`assetsBalance`, trove structs), never raw `balance`/`balanceOf`, and the
  pools' `receive()`/`receivedERC20` are caller-gated. Forced ETH/token transfers cannot move any
  decision.
- **The mint path is minimal and closed.** Only BorrowerOperations can mint DCHF; only ETH and
  canonical WBTC are registered collaterals (adding either requires the admin *and* a registered
  Chainlink oracle), so no hostile token or transfer-hook reentrancy is reachable.
- **No embedded secrets.** No `delegatecall`/`selfdestruct`; the only `ecrecover` is a standard
  EIP-2612 `permit` that recovers `owner` (no hardcoded signer); the only bytecode constants are
  the public `PERMIT_TYPEHASH` and a stability-pool name hash.

## The dominant risk is authority, not a code bug (out of scope, stated for completeness)

The single largest lever over user funds is the **2-of-3 Gnosis Safe** `0x8373…8a69` that owns the
economic-policy contracts. Through *legitimate* owner functions it can: authorize a new unlimited
DCHF minter (`DCHFToken.addTroveManager/addBorrowerOps`), replace the price oracle
(`PriceFeed.addOracle`, `DfrancParameters.setPriceFeed`), register a stability pool that is then
authorized to pull collateral from ActivePool (`StabilityPoolManager.addStabilityPool`), and change
MCR/CCR/fees. This is "a privileged party using its own powers," explicitly out of audit scope, but
it is the honest answer to "how could value/control be seized": by compromise of ≥2 Safe signer
keys (off-chain), not by any on-chain defect. The pure fund-vaults (ActivePool, DefaultPool,
CollSurplusPool, SortedTroves) have renounced ownership and are immutable.

## Examined and dismissed (benign — do not meet either bar)

1. **WBTC 8→18-decimal truncation dust.** `SafetyTransfer.decimalsCorrection` floors on transfer,
   over-crediting < 1e-8 WBTC (≈ $0.0006) of internal collateral per top-up. Not amplifiable (fixed
   cap per call), and truncated symmetrically on withdrawal so it can't be extracted as tokens —
   only inflates a trove's ICR by sub-cent value. Fails the economic bar; not an access defect.
2. **Static `DOMAIN_SEPARATOR` in ERC20Permit (DCHF & MON).** Computed once at construction, not
   re-derived if `chainid` changes. Standard low-severity cross-fork replay caveat; no mainnet fund
   impact (nonce + deadline + `owner` binding all correct on the live chain).
3. **`withdrawAssetGainToTrove` on the WBTC pool** would revert (needs the SP to have approved BO to
   pull WBTC; no such approval exists). Liveness quirk for one code path — no attacker profit, no
   theft; users can still exit via `withdrawFromSP`.
4. **`DfrancParameters.sanitizeParameters` is unguarded.** It only writes *default* params for an
   *unconfigured* asset (no-op for ETH/WBTC) and cannot enable a trove (the oracle-registration gate
   in `fetchPrice` blocks it). Storage-griefing at most; no value effect.
5. **SP liquidation-backstop profit / redemption arbitrage / staking rewards.** All scale with the
   actor's capital and derive from designed mechanisms (liquidating real undercollateralized troves,
   redeeming at oracle price, earning fees). Not disproportionate.

## Configuration coherence (audited as deployed)

Live params (`state/live_state.json`) are internally coherent and consistent with code assumptions:
MCR 110% < CCR 150%, both > 100%; fee floors (0.5%) ≤ max borrow fee (5%); MIN_NET_DEBT 2000 DCHF >
gas comp 200 DCHF; PERCENT_DIVISOR 100 → 1% liquidation gas comp (code divides by it — coherent);
redemption block elapsed (redemptions live); decimals handled (WBTC 8-dec ↔ 18-dec internal via
SafetyTransfer). DCHF `totalSupply` reconciles exactly to recorded pool debt. No parameter makes a
guard vacuous, a cap unreachable, or an accounting assumption false.

## Assumptions / boundaries
- Correctness of the **Chainlink feeds** (esp. CHF/USD) is assumed; a wrong/manipulated feed
  mis-prices the whole system and is not detectable on-chain (`COMPOSITION_MAP.md` §off-chain).
- Conclusions hold for the **live configuration and initialized wiring** captured here; a future
  admin action (new minter, new oracle, new SP, param change) can change the risk surface.
- All in-scope bytecode is verified source; nothing required decompilation.
