# Client Readiness Population Run

Run ID: qa-client-readiness-20260608133913096-oxm1hm

## Counts

- Suppliers: 10
- Raw materials: 20
- Products: 15
- Product specs: 12
- Controlled documents: 20

## Seed Manifest

```json
{
  "activeConfigVersion": 4,
  "actor": "client_readiness_seed",
  "dashboardKey": "qa_client_readiness_qa-client-readiness-2026060813391309",
  "folderEvents": [
    {
      "id": 117,
      "path": "QA/QA-CLIENT-READINESS-2026060813391309/ProductDocs/PC_TDS.pdf",
      "reviewStatus": "pending"
    },
    {
      "id": 118,
      "path": "QA/QA-CLIENT-READINESS-2026060813391309/ProductDocs/ABS_COA.pdf",
      "reviewStatus": "pending"
    },
    {
      "id": 119,
      "path": "QA/QA-CLIENT-READINESS-2026060813391309/ProductDocs/duplicate_spec.pdf",
      "reviewStatus": "pending"
    },
    {
      "id": 120,
      "path": "QA/QA-CLIENT-READINESS-2026060813391309/ProductDocs/supplier_letter.pdf",
      "reviewStatus": "pending"
    },
    {
      "id": 121,
      "path": "QA/QA-CLIENT-READINESS-2026060813391309/ProductDocs/accepted_pp_sheet.pdf",
      "reviewStatus": "accepted"
    },
    {
      "id": 122,
      "path": "QA/QA-CLIENT-READINESS-2026060813391309/ProductDocs/ignored_legacy_sheet.pdf",
      "reviewStatus": "ignored"
    }
  ],
  "managedFolders": [
    {
      "id": 1496,
      "recordId": "4d273261-bbf9-4a27-a67d-c74fa9949321",
      "relativePath": "QA/QA-CLIENT-READINESS-2026060813391309/ProductDocs"
    }
  ],
  "projectTasks": [
    {
      "id": 307,
      "projectId": "6dfc8d54-d8fc-4bbe-bdc7-de84d718f464",
      "state": "todo",
      "title": "QA 1 Review resin data sheet"
    },
    {
      "id": 308,
      "projectId": "6dfc8d54-d8fc-4bbe-bdc7-de84d718f464",
      "state": "in_progress",
      "title": "QA 1 Run first article molding pass"
    },
    {
      "id": 309,
      "projectId": "6dfc8d54-d8fc-4bbe-bdc7-de84d718f464",
      "state": "blocked",
      "title": "QA 1 Resolve supplier discrepancy"
    },
    {
      "id": 310,
      "projectId": "6dfc8d54-d8fc-4bbe-bdc7-de84d718f464",
      "state": "done",
      "title": "QA 1 Archive superseded document set"
    },
    {
      "id": 311,
      "projectId": "de452a2f-81e1-4b11-bcd7-5a20f985b18e",
      "state": "todo",
      "title": "QA 2 Review resin data sheet"
    },
    {
      "id": 312,
      "projectId": "de452a2f-81e1-4b11-bcd7-5a20f985b18e",
      "state": "in_progress",
      "title": "QA 2 Run first article molding pass"
    },
    {
      "id": 313,
      "projectId": "de452a2f-81e1-4b11-bcd7-5a20f985b18e",
      "state": "blocked",
      "title": "QA 2 Resolve supplier discrepancy"
    },
    {
      "id": 314,
      "projectId": "de452a2f-81e1-4b11-bcd7-5a20f985b18e",
      "state": "done",
      "title": "QA 2 Archive superseded document set"
    },
    {
      "id": 315,
      "projectId": "f05eddea-6111-4d59-be59-f7b4394511ff",
      "state": "todo",
      "title": "QA 3 Review resin data sheet"
    },
    {
      "id": 316,
      "projectId": "f05eddea-6111-4d59-be59-f7b4394511ff",
      "state": "in_progress",
      "title": "QA 3 Run first article molding pass"
    },
    {
      "id": 317,
      "projectId": "f05eddea-6111-4d59-be59-f7b4394511ff",
      "state": "blocked",
      "title": "QA 3 Resolve supplier discrepancy"
    },
    {
      "id": 318,
      "projectId": "f05eddea-6111-4d59-be59-f7b4394511ff",
      "state": "done",
      "title": "QA 3 Archive superseded document set"
    },
    {
      "id": 319,
      "projectId": "a61bd044-dc35-485a-8e77-64dc59b5a903",
      "state": "todo",
      "title": "QA 4 Review resin data sheet"
    },
    {
      "id": 320,
      "projectId": "a61bd044-dc35-485a-8e77-64dc59b5a903",
      "state": "in_progress",
      "title": "QA 4 Run first article molding pass"
    },
    {
      "id": 321,
      "projectId": "a61bd044-dc35-485a-8e77-64dc59b5a903",
      "state": "blocked",
      "title": "QA 4 Resolve supplier discrepancy"
    },
    {
      "id": 322,
      "projectId": "a61bd044-dc35-485a-8e77-64dc59b5a903",
      "state": "done",
      "title": "QA 4 Archive superseded document set"
    }
  ],
  "projects": [
    {
      "id": "6dfc8d54-d8fc-4bbe-bdc7-de84d718f464",
      "name": "QA Tooling Transfer QA-CLIENT-READINESS-2026060813391309",
      "recordId": "0787a1a6-f6d8-40f7-b4bf-07abac89a50e"
    },
    {
      "id": "de452a2f-81e1-4b11-bcd7-5a20f985b18e",
      "name": "QA Regrind Qualification QA-CLIENT-READINESS-2026060813391309",
      "recordId": "8bbcc9ea-8460-4c4c-a878-33a271e0b413"
    },
    {
      "id": "f05eddea-6111-4d59-be59-f7b4394511ff",
      "name": "QA Supplier Change QA-CLIENT-READINESS-2026060813391309",
      "recordId": "9cbaefa7-9a0c-45a2-aeac-de216de2ea7a"
    },
    {
      "id": "a61bd044-dc35-485a-8e77-64dc59b5a903",
      "name": "QA Document Cleanup QA-CLIENT-READINESS-2026060813391309",
      "recordId": "574a7caf-b9b3-41e1-a348-0bd81c7a484f"
    }
  ],
  "records": {
    "productRecordId": "4d273261-bbf9-4a27-a67d-c74fa9949321",
    "projectRecordIds": [
      "0787a1a6-f6d8-40f7-b4bf-07abac89a50e",
      "8bbcc9ea-8460-4c4c-a878-33a271e0b413",
      "9cbaefa7-9a0c-45a2-aeac-de216de2ea7a",
      "574a7caf-b9b3-41e1-a348-0bd81c7a484f"
    ]
  },
  "runId": "qa-client-readiness-20260608133913096-oxm1hm",
  "workflowTasks": [
    {
      "id": 168,
      "relatedRecordId": "4d273261-bbf9-4a27-a67d-c74fa9949321",
      "state": "open",
      "title": "QA Review material data QA-CLIENT-READINESS-2026060813391309"
    },
    {
      "id": 169,
      "relatedRecordId": "4d273261-bbf9-4a27-a67d-c74fa9949321",
      "state": "open",
      "title": "QA Approve supplier dossier QA-CLIENT-READINESS-2026060813391309"
    },
    {
      "id": 170,
      "relatedRecordId": "4d273261-bbf9-4a27-a67d-c74fa9949321",
      "state": "open",
      "title": "QA Release controlled document QA-CLIENT-READINESS-2026060813391309"
    },
    {
      "id": 171,
      "relatedRecordId": "4d273261-bbf9-4a27-a67d-c74fa9949321",
      "state": "open",
      "title": "QA Check regrind declaration QA-CLIENT-READINESS-2026060813391309"
    }
  ]
}
```

## PDF Sources

| # | Label | Source status | Bytes | SHA-256 | URL |
|---|---|---|---:|---|---|
| 1 | Plastic-Craft Polycarbonate SDS | downloaded | 590552 | `49fccc62b6e59beac5af38926f2d462b787c94e0d2a246ca7eb05a7383866fd2` | https://plastic-craft.com/content/SDS/polycarbonate.pdf |
| 2 | Plastic-Craft Polystyrene SDS | downloaded | 672573 | `9fe445a305970ba8ad6a7c6b1f34815447fd814504df71cb48588b7acb11b891` | https://plastic-craft.com/content/SDS/Polycarbonate/polystyrene.pdf |
| 3 | ACRIFIX 2R 0190 SDS | downloaded | 352530 | `a40ae73f931d5c7c7a5bd037577b0998410b080d678173c3628244128dadca9c` | https://plastic-craft.com/content/SDS/ACRIFIX/ACRIFIX-2R-0190-US-v2.1.pdf |
| 4 | ACRIFIX 2R 0190 Technical Information | downloaded | 67290 | `5fe731db9b9ff72e25bcbae840a37025c6d6a05b7a9fe12d68c1880b7f9db88f` | https://plastic-craft.com/content/TDS/ACRIFIX/ACRIFIX-2R-0190-Clear-Technical-Information.pdf |
| 5 | ACRIFIX AC 1010 SDS | downloaded | 338326 | `f26d65c2bcfb040d808ca2a78d98401557885cbf41aa4808def1aa37b92bacee` | https://plastic-craft.com/content/SDS/ACRIFIX-AC-1010-US-v2.2.pdf |
| 6 | Primex ABS Data Sheet | downloaded | 120130 | `7489646dce3f69b6653a465cfb23e59c9b55d0a5286f5622f80d05d41b0e3882` | https://www.tapplastics.com/image/catalog/pdf/Primex%20ABS.pdf |
| 7 | Acetal Technical Data | downloaded | 48598 | `0e53b4024ea4f8c526088776aceed1070fd00abcca663fdfb8d833acfb8f7beb` | https://www.tapplastics.com/image/pdf/Acetal_Technical_Data.pdf |
| 8 | HDPE Typical Properties | downloaded | 53683 | `ec39d4e03884dbb44e483b0d65e627662655bdb506093f7390fb56716886ec7a` | https://www.tapplastics.com/image/pdf/Typical_Properties_HDPE.pdf |
| 9 | High Impact Polystyrene Technical Data | downloaded | 59975 | `6105e662fbb99df83c3177e33979c6f9d0e9e89e6a1df9a7b9de97c26c8aa60c` | https://www.tapplastics.com/image/pdf/Tech_Data-_Hi-Polystyrenes.pdf |
| 10 | Polycarbonate AR Data Sheet | downloaded | 55390 | `95cde2a488c7633b1b8b2b429973c44ba1a1b00dcf01c1a635557f933b178c67` | https://www.tapplastics.com/image/pdf/Monogal-AR_Data_Sheet-04.19.171.pdf |
| 11 | Polycarbonate Physical Properties | downloaded | 1737484 | `6696b0cd6824e4887ffa80b23daaa139f3a6f9d085a6cc874a5dc908031cf3b1` | https://www.tapplastics.com/image/pdf/Physical-Properties-Polycarbonate.pdf |
| 12 | Polycarbonate GP Product Data | downloaded | 42877 | `074f25cdea47b4754bf3c31d371751dbf3b5e85ea1580d8139a4c31e73f43ede` | https://www.tapplastics.com/image/pdf/Polycarbonate%20GP%20Product%20Data.pdf |
| 13 | King CuttingBoard Physical Properties | downloaded | 103417 | `24e841bbbf8e00a35aa2d8860213cc05a082a371a1e33bd7e322aea572a6e6ff` | https://www.tapplastics.com/image/catalog/King-CuttingBoard-Physical-Properties.pdf |
| 14 | King KPC HDPE Literature | downloaded | 158218 | `932d468bd1b310c6bbe0f934b45339092dd6ce935c39c296a15bbbb1ab231498` | https://www.tapplastics.com/image/pdf/King-KPC-HDPE-Literature.pdf |
| 15 | Komatex Foamed PVC Technical Values | downloaded | 81066 | `261733ec4d582d2fec4fae47279a594ac71904c613cb23f678214351eb9685e4` | https://www.tapplastics.com/image/pdf/komatex_techvalues_07-3.pdf |
| 16 | PVC Sheets Data | downloaded | 50555 | `7c73b4846bc7e6757510cbd98ef5954a8ae4773b60bc0a715c414dcf66c38cb4` | https://www.tapplastics.com/image/pdf/PVC_Sheets_Data-2018.pdf |
| 17 | Polypropylene Data | downloaded | 462544 | `094bf6d7aeb11765e98f49af0297941b65f8c1539be40102b45767a3546cd918` | https://www.tapplastics.com/image/pdf/Polypropylene_Data.pdf |
| 18 | Vintec PVC Properties | downloaded | 141519 | `d1523e784c8ee3b80ea8b9af895cd23fb26307656e5e207d89885fcdea91618b` | https://www.tapplastics.com/image/pdf/vintec_i_properties1.pdf |
| 19 | SCIGRIP 4SC Technical Data | downloaded | 319873 | `e9607c6bd77179176b0ef461241f0f2b62117d88150941e011b5e1f4154a97f3` | https://www.tapplastics.com/image/pdf/4SC_TDS-1112.pdf |
| 20 | Weld-On 4 Technical Data | downloaded | 94280 | `a450f8da2daa41479d181df3b25d4ffc59414e7e615ff3505be0cf9b545027e4` | https://www.tapplastics.com/image/catalog/pdf/ips_weld-on_4_TDS_0120.pdf |

## Uploaded Documents

| # | Document ID | Title | Extraction |
|---|---|---|---|
| 1 | 465 | Plastic-Craft Polycarbonate SDS qa-client-readiness-20260608133913096-oxm1hm | extracted |
| 2 | 466 | Plastic-Craft Polystyrene SDS qa-client-readiness-20260608133913096-oxm1hm | extracted |
| 3 | 467 | ACRIFIX 2R 0190 SDS qa-client-readiness-20260608133913096-oxm1hm | extracted |
| 4 | 468 | ACRIFIX 2R 0190 Technical Information qa-client-readiness-20260608133913096-oxm1hm | extracted |
| 5 | 469 | ACRIFIX AC 1010 SDS qa-client-readiness-20260608133913096-oxm1hm | extracted |
| 6 | 470 | Primex ABS Data Sheet qa-client-readiness-20260608133913096-oxm1hm | unsupported |
| 7 | 471 | Acetal Technical Data qa-client-readiness-20260608133913096-oxm1hm | extracted |
| 8 | 472 | HDPE Typical Properties qa-client-readiness-20260608133913096-oxm1hm | extracted |
| 9 | 473 | High Impact Polystyrene Technical Data qa-client-readiness-20260608133913096-oxm1hm | extracted |
| 10 | 474 | Polycarbonate AR Data Sheet qa-client-readiness-20260608133913096-oxm1hm | extracted |
| 11 | 475 | Polycarbonate Physical Properties qa-client-readiness-20260608133913096-oxm1hm | extracted |
| 12 | 476 | Polycarbonate GP Product Data qa-client-readiness-20260608133913096-oxm1hm | extracted |
| 13 | 477 | King CuttingBoard Physical Properties qa-client-readiness-20260608133913096-oxm1hm | extracted |
| 14 | 478 | King KPC HDPE Literature qa-client-readiness-20260608133913096-oxm1hm | extracted |
| 15 | 479 | Komatex Foamed PVC Technical Values qa-client-readiness-20260608133913096-oxm1hm | extracted |
| 16 | 480 | PVC Sheets Data qa-client-readiness-20260608133913096-oxm1hm | extracted |
| 17 | 481 | Polypropylene Data qa-client-readiness-20260608133913096-oxm1hm | unsupported |
| 18 | 482 | Vintec PVC Properties qa-client-readiness-20260608133913096-oxm1hm | extracted |
| 19 | 483 | SCIGRIP 4SC Technical Data qa-client-readiness-20260608133913096-oxm1hm | extracted |
| 20 | 484 | Weld-On 4 Technical Data qa-client-readiness-20260608133913096-oxm1hm | extracted |
