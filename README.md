# Autonomous Logistics Primary Evidence

[![Autonomous logistics evidence](https://github.com/KAFKA2306/autonomous-logistics/actions/workflows/autonomous-logistics-evidence.yml/badge.svg)](https://github.com/KAFKA2306/autonomous-logistics/actions/workflows/autonomous-logistics-evidence.yml)

Drone package deliveryとautonomous truckingを、**規制認可・試験・supervised operation・commercial driverless operationを混同せず**一次情報で追跡するdatasetです。旧CFD/trading snapshotではなく、`api/v1/autonomous-logistics/` が正準成果物です。

## 正準data

- [dataset index](api/v1/autonomous-logistics/index.json)
- [FAA Part 135 UAS package-delivery operators](api/v1/autonomous-logistics/drone-part135.json)
- [autonomous trucking operators](api/v1/autonomous-logistics/trucking.json)
- [2024+ operation / authorization events](api/v1/autonomous-logistics/events.json)
- [registry](api/v1/autonomous-logistics/registry.json)
- [raw provenance](api/v1/autonomous-logistics/provenance.json)

## Drone package delivery

FAAの現行Part 135 UAS package-delivery operator一覧を正準registryとして使います。Part 135掲載は**規制認可の証拠**であり、それだけで現在commercial flightを運航しているとは扱いません。

current FAA pageがoperating areaを公開していないoperatorは、`operating_area: null` と `operating_area_status: not_listed_on_current_faa_page` を保持します。推測したservice areaで穴埋めしません。

## Autonomous trucking

current primary-source operation evidenceをoperator別に保持します。

- Aurora Innovation
- Gatik
- Kodiak AI

`operation_status`は明示的に分離します。

```text
regulatory_authorization
testing
supervised
commercial_driverless
```

future planやdriverless validation予定をcurrent commercial operationへ昇格させません。`human_driver_in_cab` / `safety_observer_required` / geography / source qualifierも別fieldで保持します。

## Provenance

```text
FAA / operator official source
  ↓
data/autonomous-logistics/raw/objects/<sha256>.*
  ↓
data/autonomous-logistics/raw/latest-manifest.json
  ↓
api/v1/autonomous-logistics/*.json
```

workflowは一次source本文をlive取得し、必要markerを検証してSHA-256固定します。保存済みraw evidenceだけからoffline再生成し、live生成APIとbyte diffします。

## 実行

標準ライブラリのみです。

```bash
python autonomous_logistics.py
python -m unittest -v test_autonomous_logistics
```

offline再生成:

```bash
python autonomous_logistics.py --offline
```

Tracking issue: https://github.com/KAFKA2306/autonomous-logistics/issues/5
