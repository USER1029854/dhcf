# Recovered behavior — (empty by design)

This directory is where decompilation, extracted constants, resolved selectors, guard
analysis, and simulation of **unverified** value-path contracts would live.

**It is empty because there are no unverified contracts anywhere in this system.**

This is a positive result, verified — not an omission:

- Every one of the 23 contracts reached from the target (in both directions) has **verified
  source on Etherscan**, present under `contracts/verified/` and `contracts/upstream/`. See
  `state/verification_status.json` — the `UNVERIFIED` list is empty.
- That includes every contract that holds funds (ActivePool, DefaultPool, CollSurplusPool,
  both StabilityPools), that can mint (DCHFToken via TroveManager/BorrowerOperations), that
  is an authority target (the Gnosis Safe + its v1.3.0 singleton), and every oracle
  (Chainlink proxies + OCR2 aggregators).
- The one proxy in the graph (the Gnosis Safe owner `0x8373…8a69`) was resolved through to its
  implementation (canonical Safe v1.3.0 singleton), which is itself verified.

Empirical confirmation that the (verified) guards actually behave as written — an unprivileged
caller is rejected by every fund-moving and authority function — is in `state/simulation.txt`.

If a future re-scan finds a newly-deployed unverified contract wired into this system, its
decompilation + extracted constants + simulation would be added here.
