# AGENTS.md

## Repository responsibility

This repository owns primary evidence for autonomous logistics: FAA-regulated UAS package delivery and autonomous trucking operations. Do not reintroduce the former CFD/trading prototype.

## Source hierarchy

1. FAA current Part 135 UAS package-delivery registry
2. Operator official investor relations / press releases for current trucking operations
3. Derived API regenerated from stored raw source bytes

## Autonomous execution

1. Re-read current `main`, README, open Issues/PRs, canonical raw/derived data, workflows/tests and public outputs before choosing work.
2. Continue one existing canonical workline for the same operational outcome before creating another collector, dataset, branch or Issue.
3. Prefer newly verified authorization/operation records, identity/status corrections, deterministic rebuild/comparison, public usability, then simplification that removes recurring work.
4. Require definition, unit and jurisdiction comparability before aggregating operators or periods.
5. Run the smallest relevant checks, then exact-revision/production verification when the repository contract requires it.
6. Stop at the fixed point. Do not infer commercial scale from authorization, testing or a planned program, and do not churn a blocked source when external state has not changed.

Cross-repository forecast comparison belongs in `investor2`; do not duplicate ARK or valuation forecast authority here. Do not execute trades, transfers or account actions.

## Evidence rules

- Regulatory authorization is not commercial-operation proof.
- Keep testing, supervised, regulatory_authorization and commercial_driverless distinct.
- Missing operating areas stay null with an explicit source limitation; never infer geography.
- Future/planned driverless routes remain planned/supervised until a primary source states actual commercial driverless operation.
- Preserve original qualifiers such as `nearly`, `more than`, or date scope.
- Every normalized record must resolve to a raw source SHA-256.
- Remove obsolete trading/CFD paths rather than maintaining compatibility fallbacks.

## Required checks

```bash
python -m py_compile autonomous_logistics.py test_autonomous_logistics.py
python -m unittest -v test_autonomous_logistics
```

Production completion additionally requires the `Autonomous logistics evidence` workflow to pass live source verification, provenance audit, offline rebuild, and main production evidence commit. A layer that did not run is not PASS.

## Completion report

Report verified logistics evidence Before -> After, primary/raw evidence and canonical artifact, Issue/PR/commit/check/public evidence when applicable, duplicate/manual work removed, and the remaining verified blocker.