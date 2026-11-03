# FMCSA Carrier Lookup

Look up a U.S. motor carrier by **USDOT number**, **MC/docket number**, or **name** and save authority status, operating status, insurance filings, and safety rating to an Apify dataset.

The data comes from the **official FMCSA QCMobile API** at [https://mobile.fmcsa.dot.gov/qc/services/](https://mobile.fmcsa.dot.gov/qc/services/). You provide your own free FMCSA WebKey. This Actor calls that API only. It does not read the SAFER website.

FMCSA documents the API here:

- [Getting started / WebKey](https://mobile.fmcsa.dot.gov/QCDevsite/docs/getStarted)
- [API access](https://mobile.fmcsa.dot.gov/QCDevsite/docs/apiAccess)
- [Endpoints](https://mobile.fmcsa.dot.gov/QCDevsite/docs/qcApi)

## Why use the official API

FMCSA publishes carrier registration, licensing, insurance, operating authority, and safety data through QCMobile. Each run sends your WebKey as the `webKey` query parameter, which is how the API authenticates. Apify stores that field encrypted (`isSecret`) and the Actor decrypts it only for the run.

A WebKey is free. Create one with a Login.gov account: open [My WebKeys](https://mobile.fmcsa.dot.gov/QCDevsite/), choose **Get a new WebKey**, and paste the key into the Actor input. Do not share the key. This Actor does not ship a key and does not ask for any other license.

## Input

Provide the WebKey and at least one search field. You can set more than one field in the same run. Each match becomes one dataset item.

USDOT lookup:

```json
{
  "webKey": "YOUR_FMCSA_WEBKEY",
  "dotNumber": "44110"
}
```

MC/docket lookup. `MC-1515`, `MC1515`, and `1515` all query docket `1515`. `FF` and `MX` prefixes are kept in the result query.

```json
{
  "webKey": "YOUR_FMCSA_WEBKEY",
  "docketNumber": "MC-1515"
}
```

Name lookup. The official API returns at most 50 carriers for a name. `maxResults` caps how many of those are saved (default 10).

```json
{
  "webKey": "YOUR_FMCSA_WEBKEY",
  "carrierName": "greyhound",
  "maxResults": 10
}
```

| Field | Required | Description |
| --- | --- | --- |
| `webKey` | yes | Your FMCSA WebKey. Secret input. |
| `dotNumber` | no | U.S. DOT number. A leading `USDOT` label is ignored. |
| `docketNumber` | no | MC, FF, or MX docket number. |
| `carrierName` | no | Legal name or DBA. At least 2 characters. |
| `maxResults` | no | Name-search cap from 1 to 50. Default 10. Ignored for DOT and docket lookups. |

`44110` and `greyhound` are the sample queries from FMCSA's own API docs. They are inputs, not a claim about a carrier's current record.

## Output

Results are written to the run's default dataset. One item is one carrier, or one not-found row when the official API has no match.

The example below is the shape the Actor saves. The numbers are illustrative of the official response, not a live FMCSA record.

```json
{
  "found": true,
  "queryType": "dot",
  "query": "1000001",
  "message": null,
  "dotNumber": "1000001",
  "legalName": "EXAMPLE HAULING LLC",
  "dbaName": null,
  "docketNumbers": ["MC-100001"],
  "allowedToOperate": "Y",
  "operatingStatus": "Allowed to operate",
  "statusCode": "A",
  "statusLabel": "Active",
  "outOfServiceDate": null,
  "carrierOperationCode": "A",
  "carrierOperation": "Interstate",
  "commonAuthorityStatus": "A",
  "commonAuthorityStatusLabel": "Active",
  "contractAuthorityStatus": "I",
  "contractAuthorityStatusLabel": "Inactive",
  "brokerAuthorityStatus": "N",
  "brokerAuthorityStatusLabel": "None",
  "authorityRecords": [
    {
      "prefix": "MC",
      "docketNumber": "100001",
      "commonAuthorityStatus": "A",
      "commonAuthorityStatusLabel": "Active",
      "contractAuthorityStatus": "I",
      "contractAuthorityStatusLabel": "Inactive",
      "brokerAuthorityStatus": "N",
      "brokerAuthorityStatusLabel": "None",
      "authorizedForProperty": "Y",
      "authorizedForPassenger": "N",
      "authorizedForHouseholdGoods": "N",
      "authorizedForBroker": "N"
    }
  ],
  "bipdInsuranceOnFile": "750",
  "bipdInsuranceOnFileUsd": 750000,
  "bipdInsuranceRequired": "Y",
  "bipdInsuranceRequiredLabel": "Yes",
  "bipdRequiredAmount": "750",
  "bipdRequiredAmountUsd": 750000,
  "cargoInsuranceOnFile": "0",
  "cargoInsuranceOnFileUsd": 0,
  "cargoInsuranceRequired": "N",
  "cargoInsuranceRequiredLabel": "No",
  "bondInsuranceOnFile": "0",
  "bondInsuranceOnFileUsd": 0,
  "bondInsuranceRequired": "u",
  "bondInsuranceRequiredLabel": "Unknown",
  "safetyRating": "S",
  "safetyRatingLabel": "Satisfactory",
  "safetyRatingDate": "2019-06-01",
  "safetyReviewDate": "2019-06-01",
  "safetyReviewType": "C",
  "phyStreet": "1 EXAMPLE ST",
  "phyCity": "DALLAS",
  "phyState": "TX",
  "phyZipcode": "75201",
  "phyCountry": "US",
  "totalPowerUnits": 3,
  "totalDrivers": 4,
  "source": "FMCSA QCMobile API",
  "sourceUrl": "https://mobile.fmcsa.dot.gov/qc/services/",
  "retrievalDate": "2026-03-01T00:00:00.000+0000"
}
```

A miss looks like this:

```json
{
  "found": false,
  "queryType": "dot",
  "query": "9999999",
  "message": "No carrier found for that USDOT number.",
  "dotNumber": null,
  "legalName": null,
  "docketNumbers": [],
  "operatingStatus": null,
  "safetyRating": null,
  "safetyRatingLabel": null,
  "source": "FMCSA QCMobile API",
  "sourceUrl": "https://mobile.fmcsa.dot.gov/qc/services/"
}
```

### How to read the fields

| Field | Official meaning |
| --- | --- |
| `allowedToOperate` / `operatingStatus` | `Y` means FMCSA reports the carrier is allowed to operate. `N` means it is not. `outOfServiceDate` is set when FMCSA has an out-of-service date on the carrier record. |
| `statusCode` | Census status. `A` active, `I` inactive. |
| `commonAuthorityStatus`, `contractAuthorityStatus`, `brokerAuthorityStatus` | Operating authority. `A` active, `I` inactive, `N` none. |
| `authorityRecords` | Per-docket authority from `GET /carriers/{dotNumber}/authority`, including property, passenger, household-goods, and broker authorization flags. |
| `bipdInsuranceOnFile` | Bodily injury and property damage insurance **on file with FMCSA**, in **thousands of U.S. dollars**. `750` is $750,000, also stored as `bipdInsuranceOnFileUsd`. |
| `bipdRequiredAmount` | Required BIPD amount, same thousands unit. |
| `cargoInsuranceOnFile`, `bondInsuranceOnFile` | Cargo insurance and broker bond/trust on file, in thousands of dollars. `0` means no filing amount on the record. |
| `*InsuranceRequired` | `Y` yes, `N` no, `u` unknown. |
| `safetyRating` | `S` satisfactory, `C` conditional, `U` unsatisfactory. Null with label `Not rated` means FMCSA has not assigned a rating. Most carriers have no rating because a rating follows a compliance review. |
| `source` | Always `FMCSA QCMobile API`. |

Insurance amounts are filings FMCSA has on record. They are not a certificate of insurance, and a cancellation can reach FMCSA later than the policy change. Confirm coverage with the carrier's insurer before you rely on it.

An invalid WebKey fails the run. FMCSA often returns HTTP 404 with `content: "Webkey not found"` for a bad key. That is an authentication failure, not an empty carrier list. The WebKey is not written to the dataset or the status message.

## What the Actor calls

For a USDOT number:

1. `GET /qc/services/carriers/{dotNumber}?webKey=...`
2. `GET /qc/services/carriers/{dotNumber}/authority?webKey=...`

For a docket number:

1. `GET /qc/services/carriers/docket-number/{docketNumber}?webKey=...`
2. The authority endpoint for each returned USDOT number.

For a name:

1. `GET /qc/services/carriers/name/{name}?webKey=...&start=0&size={maxResults}`
2. The authority endpoint for each returned USDOT number.

The carrier endpoint supplies operating status, insurance filings, and safety rating. The authority endpoint supplies docket-level authority. Both are part of the official QCMobile API.

## Deploy

The Actor source in this folder is ready to push. The Docker image is the Apify Python SDK image (`apify/actor-python:3.14`).

### Apify CLI

```bash
npm install -g apify-cli
apify login
cd apify-actor
apify push
```

`apify push` builds the Dockerfile and creates or updates the Actor on your Apify account. Then:

1. Open the Actor in [Apify Console](https://console.apify.com/).
2. Paste your FMCSA WebKey into **FMCSA WebKey**. The field is secret, so the saved input is encrypted.
3. Enter a USDOT number, an MC/docket number, or a carrier name.
4. Run it. Open the **Output** tab, or fetch `GET https://api.apify.com/v2/datasets/{defaultDatasetId}/items`.

### Git integration

Create an Actor in Apify Console, connect this repository, and set the source directory to `apify-actor`. Push to the branch Apify builds. The Console build uses `.actor/actor.json`, `.actor/input_schema.json`, and the Dockerfile.

### Local run

```bash
cd apify-actor
python -m pip install -r requirements.txt
cat > INPUT.json << 'EOF'
{
  "webKey": "YOUR_FMCSA_WEBKEY",
  "dotNumber": "44110"
}
EOF
python -m fmcsa_actor
```

`INPUT.json` is gitignored. The WebKey stays on your machine. If a local SDK build reads the key-value store instead of the working directory, put the same JSON at `storage/key_value_stores/default/INPUT.json`. Dataset files are written under `storage/`.

## Tests

Unit tests mock the QCMobile HTTP responses. They do not call FMCSA.

```bash
cd apify-actor
python -m unittest discover -s tests -v
```

## Disclaimer

FMCSA is the source of the records. This Actor is not affiliated with the U.S. Department of Transportation or FMCSA. API availability, field presence, and rate limits are controlled by FMCSA. Carrier elements are omitted by the API when they have no value, and a name search is limited to 50 matches per request.
