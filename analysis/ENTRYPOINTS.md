# Entry-Point Enumeration — every externally-reachable function

Built mechanically from source (193 external/public functions across 17 deployed contracts +
2 token deps), before triage. Each row: guard, and a one-line reason it is not exploitable by an
arbitrary unprivileged caller. Guards empirically confirmed by `eth_call` from `0x…DeaDBeef`
(see `state/audit_simulation.txt` — every value/authority function reverts with the predicted
message).

Legend for guards:
`onlyOwner`=2/3 Safe · `isController`=Safe|AdminContract · `BO`=BorrowerOperations · `TM`=TroveManager ·
`TMH`=TroveManagerHelpers · `SP`=registered StabilityPool · `AP`=ActivePool · `init`=one-time initializer (all confirmed already initialized on-chain).

## ActivePool (holds all collateral)
| Fn | Guard | Why safe |
|----|-------|----------|
| setAddresses | init+onlyOwner | one-time; already initialized; renounces owner after |
| getAssetBalance / getDCHFDebt | view | read-only internal accounting |
| sendAsset | BO\|TM\|TMH\|SP + nonReentrant | only core movers; SP branch asserts asset↔pool match; uses internal balance |
| increaseDCHFDebt | BO\|TM\|TMH | debt bookkeeping only |
| decreaseDCHFDebt | BO\|TM\|TMH\|SP | debt bookkeeping only |
| receivedERC20 | BO\|DefaultPool | credits internal balance; used with actual transfer |
| receive() | BO\|DefaultPool | rejects arbitrary ETH donation (accounting immune) |

## DefaultPool (redistributed coll/debt)
| Fn | Guard | Why safe |
|----|-------|----------|
| setAddresses | init+onlyOwner | one-time; renounces owner |
| getAssetBalance/getDCHFDebt | view | read-only |
| sendAssetToActivePool | TM\|TMH | only core; internal accounting |
| increase/decreaseDCHFDebt | TM\|TMH | bookkeeping |
| receivedERC20 | AP only | credit on real transfer |
| receive() | AP only | donation-immune |

## CollSurplusPool (claimable surplus)
| Fn | Guard | Why safe |
|----|-------|----------|
| setAddresses | init+onlyOwner | one-time; renounces owner |
| getAssetBalance/getCollateral | view | read-only |
| accountSurplus | TM\|TMH | credits a user's claimable surplus |
| claimColl | BO only | BO routes msg.sender; zeroes before send (CEI) |
| receivedERC20 | AP only | credit on real transfer |
| receive() | AP only | donation-immune |

## StabilityPool ×2 (ETH, WBTC — byte-identical)
| Fn | Guard | Why safe |
|----|-------|----------|
| setAddresses | init+onlyOwner | one-time |
| provideToSP / withdrawFromSP | nonReentrant + deposit checks | user acts on own deposit; standard P/S/G math; withdraw blocked if undercollateralized trove exists |
| withdrawAssetGainToTrove | user has deposit+trove+gain | routes own gain to own trove |
| offset | TM\|TMH | only liquidation engine; reverts for others (confirmed) |
| getters (gain/deposit/stake) | view | read-only |
| _requireNoUnderCollateralizedTroves | public | triggers price fetch + reverts; no state/value effect |
| receivedERC20 / receive() | AP only | donation-immune |

## StabilityPoolManager
| Fn | Guard | Why safe |
|----|-------|----------|
| setAddresses/setAdminContract | onlyOwner | admin |
| isStabilityPool/getAssetStabilityPool/unsafeGet | view | read-only |
| addStabilityPool/removeStabilityPool | isController | admin; add checks SP.getAssetType()==asset |

## TroveManager (liquidation/redemption)
| Fn | Guard | Why safe |
|----|-------|----------|
| setAddresses | init+override(onlyOwner path) | one-time |
| liquidate/liquidateTroves/batchLiquidateTroves | permissionless | only liquidates troves actually < MCR; caller earns fixed gas comp; victim is the undercollateralized trove |
| redeemCollateral | permissionless (+whitelist gate if enabled) | swaps DCHF for collateral at oracle price − fee; burns caller's DCHF; standard peg mechanism |
| setRedemptionWhitelistStatus/add/removeUserWhitelist | onlyOwner | admin |
| isContractTroveManager | pure | identity |

## TroveManagerHelpers (trove state; called by TM & BO)
| Fn class | Guard | Why safe |
|----------|-------|----------|
| setAddresses | init (+ internal onlyOwner via setDfrancParameters) | one-time; initialized |
| view getters (ICR, TCR, fees, rates, trove data, snapshots) | view/pure | read-only |
| applyPendingRewards (2), updateTroveRewardSnapshots, addTroveOwnerToArray, setTroveStatus, increase/decreaseTroveColl/Debt, decayBaseRateFromBorrowing | onlyBorrowerOperations | mutators reachable only via BO flows (confirmed revert "WA") |
| removeStake, updateStakeAndTotalStakes | onlyBOorTM | ditto |
| redistributeDebtAndColl, closeTrove(3), updateSystemSnapshots…, updateBaseRateFromRedemption, movePendingTroveRewardsToActivePool, setTroveDeptAndColl, closeTrove(4 via TM) | onlyTroveManager | reachable only via TM liquidation/redemption (confirmed revert "WA") |
| closeTrove (borrower) | onlyBorrowerOperations | via BO.closeTrove |

## BorrowerOperations (user trove ops)
| Fn | Guard | Why safe |
|----|-------|----------|
| setAddresses | init+onlyOwner | one-time |
| openTrove/addColl/withdrawColl/withdrawDCHF/repayDCHF/adjustTrove/closeTrove | msg.sender==borrower | acts on caller's own trove; enforces MCR/CCR/TCR; mints/burns via gated DCHF |
| moveETHGainToTrove | SP only | SP routes a depositor's gain to their trove |
| claimCollateral | permissionless | forwards to CollSurplusPool.claimColl(msg.sender) — pays caller their own surplus |
| getCompositeDebt/isContractBorrowerOps | view/pure | read-only |

## SortedTroves
| Fn | Guard | Why safe |
|----|-------|----------|
| setParams | init+onlyOwner | one-time |
| insert/reInsert | BO\|TM\|TMH | list writes only by core (confirmed revert) |
| remove | TM\|TMH | ditto |
| view getters | view | read-only |

## DCHFToken
| Fn | Guard | Why safe |
|----|-------|----------|
| mint | validBorrowerOps | only BO mints; +emergencyStop flag; confirmed revert |
| burn | BO\|TM\|SP | confirmed revert |
| sendToPool | SP only | confirmed revert |
| returnFromPool | TM\|SP | confirmed revert |
| transfer/transferFrom | valid-recipient guard | blocks sends to system contracts/self/zero; else standard ERC20 |
| addTroveManager/removeTroveManager/addBorrowerOps/removeBorrowerOps/emergencyStopMinting | onlyOwner | admin mint-authority control |
| permit/nonces/chainId | signature/view | recovers `owner`, nonce+deadline; no hardcoded signer |

## MONToken
| Fn | Guard | Why safe |
|----|-------|----------|
| (ERC20 + permit only) | n/a | fixed 100M minted to treasury at construction; no mint fn; immutable treasury |

## DfrancParameters (config)
| Fn | Guard | Why safe |
|----|-------|----------|
| setAddresses | init+onlyOwner | one-time |
| setPriceFeed/setAdminContract/setAsDefault/setCollateralParameters/setMCR/setCCR/setPercentDivisor/setBorrowingFeeFloor/setMaxBorrowingFee/setDCHFGasCompensation/setMinNetDebt/setRedemptionFeeFloor/removeRedemptionBlock | onlyOwner | admin config |
| setAsDefaultWithRemptionBlock | isController | admin |
| sanitizeParameters | **none** | only sets DEFAULT params for an *unconfigured* asset; no-op for ETH/WBTC; can't enable a trove (oracle-not-registered blocks fetchPrice) |
| getters | view | read-only |

## AdminContract
| Fn | Guard | Why safe |
|----|-------|----------|
| setAddresses | init+onlyOwner | one-time |
| addNewCollateral | onlyOwner | admin adds collateral+oracle+SP |

## PriceFeed
| Fn | Guard | Why safe |
|----|-------|----------|
| setAddresses/setAdminContract | onlyOwner | admin |
| addOracle | isController | admin registers Chainlink pair |
| fetchPrice | permissionless (non-view) | only reads Chainlink + stores; no attacker-controllable value; broken/stale detection |
| getDirectPrice | view | read-only |

## CommunityIssuance
| Fn | Guard | Why safe |
|----|-------|----------|
| setAddresses/setAdminContract | init/onlyOwner | admin |
| addFundToStabilityPool/addFundToStabilityPoolFrom | isController | admin funds MON |
| removeFundFromStabilityPool/transferFundToAnotherStabilityPool | onlyOwner | admin |
| issueMON/sendMON | onlyStabilityPool | only SP; capped; sendMON≤balance; confirmed revert |
| setWeeklyDfrancDistribution | isController | admin |

## MONStaking
| Fn | Guard | Why safe |
|----|-------|----------|
| setAddresses | init | one-time; initialized |
| stake | nonReentrant+whenNotPaused | user stakes own MON; pays own gains first |
| unstake | nonReentrant | user unstakes own; pays own gains |
| pause/unpause/changeTreasuryAddress | onlyOwner | admin |
| increaseF_Asset | TM\|TMH | fee accounting; confirmed revert |
| increaseF_DCHF | BO | fee accounting; confirmed revert |
| getPending* | view | read-only |
| receive() | AP only | donation-immune |
