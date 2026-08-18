# AGENTS.md

## Repository responsibility

This repository owns primary evidence for autonomous logistics: FAA-regulated UAS package delivery and autonomous trucking operations. Do not reintroduce the former CFD/trading prototype.

## Source hierarchy

1. FAA current Part 135 UAS package-delivery registry
2. Operator official investor relations / press releases for current trucking operations
3. Derived API regenerated from stored raw source bytes

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

Production completion additionally requires the `Autonomous logistics evidence` workflow to pass live source verification, provenance audit, offline rebuild, and main production evidence commit.
