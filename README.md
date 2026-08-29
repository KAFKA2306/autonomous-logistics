https://kafka2306.github.io/autonomous-logistics/

# Autonomous Logistics Primary Evidence

[![Autonomous logistics evidence](https://github.com/KAFKA2306/autonomous-logistics/actions/workflows/autonomous-logistics-evidence.yml/badge.svg)](https://github.com/KAFKA2306/autonomous-logistics/actions/workflows/autonomous-logistics-evidence.yml)

Drone package deliveryとautonomous truckingを、**規制認可・試験・supervised operation・commercial operationを混同せず**一次情報で追跡するdatasetです。`api/v1/autonomous-logistics/` が正準成果物です。

公開ダッシュボードは正準APIを直接読み込みます。FAA Part 135掲載をcommercial operationと同義にせず、商用無人トラック、確認済みoperation event、一次情報URLとSHA-256を同じ画面から確認できます。

## 正準data

- [dataset index](api/v1/autonomous-logistics/index.json)
- [FAA Part 135 UAS package-delivery operators](api/v1/autonomous-logistics/drone-part135.json)
- [autonomous trucking operators](api/v1/autonomous-logistics/trucking.json)
- [operation / authorization events](api/v1/autonomous-logistics/events.json)
- [registry](api/v1/autonomous-logistics/registry.json)
- [raw provenance](api/v1/autonomous-logistics/provenance.json)

## Drone package delivery

FAAの現行Part 135 UAS package-delivery operator一覧を`drone-part135.json`の正準registryとして使います。Part 135掲載は**規制認可の証拠**であり、それだけで現在commercial flightを運航しているとは扱いません。

FAA pageの更新より新しいoperator一次情報でPart 135認可が確認できた場合は、FAA-listed viewを書き換えず`events.json`へ別のauthorization eventとして保持します。2026-07-29のDoorDash Air発表はこの境界に該当し、FAA pageが7社表示の間はDoorDashをFAA-listed rowへ追加しません。また、その発表だけからDoorDash自身のcommercial flight開始も主張しません。

現行FAA pageが直接示すoperator membershipとcertificate timingだけを正規化します。certificate timingが月単位なら`part135_certificate_period: YYYY-MM`として保持し、日付を推測しません。Flytrexのようにcertificate holderではなくpartner/UASとして言及される組織をoperator rowへ昇格させません。

commercial service eventは、一次sourceが実際の開始を明記した場合だけ別eventとして保存します。`effective_at`はsource精度をそのまま使い、`YYYY-MM`または`YYYY-MM-DD`とします。`will conduct`などfuture wordingはactual operationへ昇格させません。

current FAA pageが**current operating area**を公開していないoperatorは、`operating_area: null` と `operating_area_status: not_listed_as_current_operating_area_on_faa_page` を保持します。launch時・過去のservice areaをcurrent areaとして穴埋めしません。

operatorが公開するcapacity/R&D testの実測値はeventとして保存できますが、`operation_status: testing`のまま保持し、commercial serviceの証拠へ昇格させません。

## Autonomous trucking

current primary-source operation evidenceをoperator別に保持します。

- Aurora Innovation
- Gatik
- Kodiak AI

`operation_status`は証拠の意味を分離します。

```text
regulatory_authorization
testing
supervised
commercial
commercial_driverless
```

`commercial`はdrone package-deliveryの実運行、`commercial_driverless`は無人commercial truckingに使います。future planやdriverless validation予定をcurrent commercial operationへ昇格させません。`human_driver_in_cab` / `safety_observer_required` / geography / source qualifierも別fieldで保持します。

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
