# DeFi Franc (DCHF) — Audit Source Repository

**Target:** DeFi Franc, a multi-collateral CDP stablecoin pegged to the Swiss Franc (CHF),
against ETH and WBTC collateral. A Liquity → Vesta → DeFi Franc fork lineage.
**Chain:** Ethereum mainnet (chainid 1). All core contracts created 2022-09-25.
**Purpose of this repo:** everything an auditor needs to reason about the target's security
without returning to a block explorer — full source of the target and every contract it
trusts (in both directions), plus the live authority/configuration state, integrity checks,
and an explicit list of what remains off-chain / unresolved.

> This repo **maps and evidences**; it does **not** judge exploitability. Where a fact is
> security-relevant it is stated plainly, but the "is this exploitable" step is the next stage.

---

## TL;DR — the security-relevant shape of this system

- **The whole graph is verified on-chain.** All 23 contracts reached (target + every
  downstream dependency + every upstream authority) have verified source on Etherscan.
  **Nothing in the value path is unverified** — no decompilation was required. See
  [`contracts/recovered/README.md`](contracts/recovered/README.md) for the explicit
  confirmation of this (it is a result, not an omission).
- **One address rules the system: a 2-of-3 Gnosis Safe** `0x8373…8a69`
  (canonical Safe v1.3.0). It retains ownership of the economic-policy contracts and can,
  among other things: **authorize an arbitrary new DCHF minter**, **swap the price oracle**,
  and **change MCR/CCR/fees**. The pure fund-holding contracts (ActivePool, DefaultPool,
  CollSurplusPool, SortedTroves) have **renounced** ownership — their wiring is locked.
  Full enumeration in [`AUTHORITY_AND_CONFIG.md`](AUTHORITY_AND_CONFIG.md).
- **The peg lives off-chain in a Chainlink CHF/USD feed.** Collateral is priced as
  `(asset/USD) ÷ (CHF/USD)`. The **CHF/USD** feed (`0x449d…b13a`) is the peg anchor for
  *both* collaterals; it, and all price feeds, are controlled by Chainlink — not the DCHF
  team. This is the principal off-chain trust dependency. See [`UNRESOLVED.md`](UNRESOLVED.md).
- **Live state is a quiet, wound-down deployment:** ~52.6k DCHF supply (reconciles exactly to
  recorded debt), **both stability pools hold 0 DCHF deposits** (their liquidation-absorption
  buffer is empty; collateral gains are stranded), and **MON reward emissions are fully
  exhausted**. Numbers in [`AUTHORITY_AND_CONFIG.md`](AUTHORITY_AND_CONFIG.md).
- **Shared building blocks are genuine.** Bundled OpenZeppelin is byte-identical to real
  upstream **v4.3.2/4.3.3**; the Safe singleton is the canonical v1.3.0; Chainlink proxies are
  canonical. No doctored baseline. See [`INTEGRITY.md`](INTEGRITY.md).

---

## How to navigate this repo

| Path | What's there |
|------|--------------|
| `contracts/verified/<Name>/` | Full verified source tree of each in-scope contract (as deployed). Each dir mirrors the exact import layout the compiler saw, plus `_abi.json`. |
| `contracts/upstream/` | Canonical third-party code reached by the target: Gnosis Safe singleton, Chainlink proxies + OCR2 aggregators. |
| `contracts/recovered/` | Recovered behavior for unverified value-path contracts. **Empty by design** — nothing was unverified; the README there says so explicitly. |
| `ARCHITECTURE.md` | The trust graph, both directions, and how the pieces interact (the "map"). |
| `AUTHORITY_AND_CONFIG.md` | Who holds every privileged role **right now**, and every live config parameter + pool balance, with consistency checks. |
| `INTEGRITY.md` | Diff of shared building blocks vs. real upstream. |
| `UNRESOLVED.md` | The explicit list of what is **not** readable on-chain — off-chain components and residual questions. |
| `state/*.json` | Machine-readable evidence backing every claim (registry, verification status, ownership, live state, integrity, oz diff). |
| `scripts/*.py` | The tooling used to gather all of the above (reproducible; Etherscan V2 + eth_call from an arbitrary address). |

---

## Contract inventory (the map, in one table)

Addresses are Ethereum mainnet. "Owner" = live on-chain owner at time of capture.
`Safe` = the 2-of-3 multisig `0x83737eae72ba7597b36494d723fbf58cafee8a69`.

### Target & core CDP engine (DeFi Franc's own code — all VERIFIED)

| Contract | Address | Owner | Role |
|----------|---------|-------|------|
| **DCHFToken** (target) | `0x045da4bFe02B320f4403674B3b7d121737727A36` | Safe | CHF-pegged stablecoin; mint gated to TroveManager + BorrowerOperations |
| ActivePool | `0x77E034c8A1392d99a2C776A6C1593866fEE36a33` | **renounced** | Holds all collateral backing active troves (6.26 ETH + 2.49 WBTC) |
| DefaultPool | `0xC1f785B74a01dd9FAc0dE6070bC583fe9eaC7Ab5` | **renounced** | Holds redistributed collateral/debt from liquidations |
| CollSurplusPool | `0xA622c3bdBFBE749B1984bc127bFB500e196F594b` | **renounced** | Holds claimable collateral surplus |
| StabilityPool (ETH) | `0x6a9f9d6f5d672a9784c5e560a9648de6cbe2c548` | Safe | ETH-trove liquidation absorber (byte-identical to WBTC SP) |
| StabilityPool (WBTC) | `0x04556d845f12ff7d8ff04a37f40387dd1b454c4b` | Safe | WBTC-trove liquidation absorber |
| StabilityPoolManager | `0x202FbFF035188f9f0525E144C8B3F8249a74aD21` | Safe | Registry asset → stability pool |
| TroveManager | `0x99838142189adE67c1951f9c57c3333281334F7F` | Safe | Trove state, liquidation, redemption; DCHF minter |
| TroveManagerHelpers | `0xaaacb8c39bd5acbb0a236112df8d15411161e518` | Safe | Split-out trove math/liquidation; **authorized to move collateral from ActivePool** |
| BorrowerOperations | `0x9eB2Ce1be2DD6947e4f5Aabe33106f48861DFD74` | Safe | Open/adjust/close troves; DCHF minter |
| SortedTroves | `0x1dd69453a685c735f2ab43e2169b57e9edf72286` | **renounced** | Sorted list of troves by collateral ratio |
| DfrancParameters | `0x6f9990b242873d7396511f2630412a3fcecacc42` | Safe | Per-asset MCR/CCR/fees/gas-comp/min-debt/redemption-block |
| AdminContract | `0x2748c55219dca1d9d3c3a57505e99bb04e42f254` | Safe | Adds collateral, deploys/registers pools, funds MON issuance |
| PriceFeed | `0x09ab3c0ce6cb41c13343879a667a6bdad65ee9da` | Safe | `(asset/USD) ÷ (CHF/USD)` via Chainlink |
| CommunityIssuance | `0x0fa46e8cbceff8468db2ec2fd77731d8a11d3d86` | Safe | Distributes MON rewards to stability providers |
| MONStaking | `0x8bc3702c35d33e5df7cb0f06cb72a0c34ae0c56f` | Safe | MON staking earns borrow/redemption fees |
| MONToken | `0x1ea48b9965bb5086f3b468e50ed93888a661fc17` | (no owner) | Fixed-supply 100M governance/reward token; no mint fn |

### Collateral & authority & oracles (third-party — VERIFIED / canonical)

| Contract | Address | Notes |
|----------|---------|-------|
| WBTC (collateral) | `0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599` | Canonical WBTC token |
| Gnosis Safe (owner) | `0x83737eae72ba7597b36494d723fbf58cafee8a69` | 2-of-3 proxy → singleton below |
| Gnosis Safe singleton | `0xd9db270c1b5e3bd161e8c8503c55ceabee709552` | Canonical Safe **v1.3.0** |
| Chainlink ETH/USD | `0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419` | Proxy → `0x7d4e…6fb5` (OCR2) |
| Chainlink BTC/USD | `0xf4030086522a5beea4988f8ca5b36dbc97bee88c` | Proxy → `0x4a34…84f1` (OCR2) |
| Chainlink CHF/USD | `0x449d117117838ffa61263b61da6301aa2a88b13a` | **Peg anchor**; proxy → `0x5763…f9b4` (OCR2) |

### Safe signers (EOAs, 2-of-3 threshold)

`0x8c013078c75e790ffed8e11342ecff53c5cd73a8` · `0x7aff0f97357a7e8b577298f2fe81e6330975e28d` · `0x67733cfa01b42900057759a8eba97afed02c44e8`

---
*Evidence for every statement here is in `state/*.json`. Reproduction scripts in `scripts/`.*
