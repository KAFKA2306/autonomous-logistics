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
5. Run the smallest relevant checks and verify the exact reviewed revision before merge.
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

## Merge and release are separate

### PR merge conditions

A PR may merge when the deterministic repository-local logistics contract is correct on the exact head revision: identity/status/jurisdiction/provenance semantics hold, focused tests pass, offline rebuild succeeds where affected, and no unresolved review or correctness blocker remains.

A future FAA/operator observation, live source verification after merge, production publication, or commercial-driverless operation is **not** a merge condition unless the PR specifically changes the release/live-acquisition mechanism and that mechanism must be validated before merge.

### Product/data release conditions

Release is a separate post-merge decision. Treat logistics evidence/API as released only after the merged `main` revision is read back and the release requirements in scope are actually executed, including live source verification when required, provenance audit, published/generated artifacts, public surface if any, deployment identity, and rollback/rebuild path.

A merged PR does not prove commercial operation or production release. A release/live-source blocker may block release without invalidating a correctly merged repository change. Report merge and release independently.

## Required checks

```bash
python -m py_compile autonomous_logistics.py test_autonomous_logistics.py
python -m unittest -v test_autonomous_logistics
```

These checks are merge evidence. The `Autonomous logistics evidence` workflow or equivalent live source/provenance run is release evidence when live production acquisition is in scope. A layer that did not run is not PASS.

## Completion report

Report verified logistics evidence Before -> After, primary/raw evidence and canonical artifact, Issue/PR/commit/check evidence, then report `merged` and `released` separately with direct evidence for each. Include duplicate/manual work removed and the remaining verified blocker.