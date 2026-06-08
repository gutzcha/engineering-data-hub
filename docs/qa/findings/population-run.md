# Client Readiness Population Run

Run ID: qa-client-readiness-20260608111323106-grdz8h

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
  "dashboardKey": "qa_client_readiness_qa-client-readiness-2026060811132310",
  "folderEvents": [
    {
      "id": 105,
      "path": "QA/QA-CLIENT-READINESS-2026060811132310/ProductDocs/PC_TDS.pdf",
      "reviewStatus": "pending"
    },
    {
      "id": 106,
      "path": "QA/QA-CLIENT-READINESS-2026060811132310/ProductDocs/ABS_COA.pdf",
      "reviewStatus": "pending"
    },
    {
      "id": 107,
      "path": "QA/QA-CLIENT-READINESS-2026060811132310/ProductDocs/duplicate_spec.pdf",
      "reviewStatus": "pending"
    },
    {
      "id": 108,
      "path": "QA/QA-CLIENT-READINESS-2026060811132310/ProductDocs/supplier_letter.pdf",
      "reviewStatus": "pending"
    },
    {
      "id": 109,
      "path": "QA/QA-CLIENT-READINESS-2026060811132310/ProductDocs/accepted_pp_sheet.pdf",
      "reviewStatus": "accepted"
    },
    {
      "id": 110,
      "path": "QA/QA-CLIENT-READINESS-2026060811132310/ProductDocs/ignored_legacy_sheet.pdf",
      "reviewStatus": "ignored"
    }
  ],
  "managedFolders": [
    {
      "id": 1295,
      "recordId": "c5cd26d0-e7e8-4ebb-821b-c4dcbe49f708",
      "relativePath": "QA/QA-CLIENT-READINESS-2026060811132310/ProductDocs"
    }
  ],
  "projectTasks": [
    {
      "id": 275,
      "projectId": "7bcfdbbc-a353-41ab-9bb2-7efbe0350fb0",
      "state": "todo",
      "title": "QA 1 Review resin data sheet"
    },
    {
      "id": 276,
      "projectId": "7bcfdbbc-a353-41ab-9bb2-7efbe0350fb0",
      "state": "in_progress",
      "title": "QA 1 Run first article molding pass"
    },
    {
      "id": 277,
      "projectId": "7bcfdbbc-a353-41ab-9bb2-7efbe0350fb0",
      "state": "blocked",
      "title": "QA 1 Resolve supplier discrepancy"
    },
    {
      "id": 278,
      "projectId": "7bcfdbbc-a353-41ab-9bb2-7efbe0350fb0",
      "state": "done",
      "title": "QA 1 Archive superseded document set"
    },
    {
      "id": 279,
      "projectId": "1498a396-5cea-4f27-bb26-b2978c838a2f",
      "state": "todo",
      "title": "QA 2 Review resin data sheet"
    },
    {
      "id": 280,
      "projectId": "1498a396-5cea-4f27-bb26-b2978c838a2f",
      "state": "in_progress",
      "title": "QA 2 Run first article molding pass"
    },
    {
      "id": 281,
      "projectId": "1498a396-5cea-4f27-bb26-b2978c838a2f",
      "state": "blocked",
      "title": "QA 2 Resolve supplier discrepancy"
    },
    {
      "id": 282,
      "projectId": "1498a396-5cea-4f27-bb26-b2978c838a2f",
      "state": "done",
      "title": "QA 2 Archive superseded document set"
    },
    {
      "id": 283,
      "projectId": "1fc7462c-f259-4c9e-9ea4-f015dca4b968",
      "state": "todo",
      "title": "QA 3 Review resin data sheet"
    },
    {
      "id": 284,
      "projectId": "1fc7462c-f259-4c9e-9ea4-f015dca4b968",
      "state": "in_progress",
      "title": "QA 3 Run first article molding pass"
    },
    {
      "id": 285,
      "projectId": "1fc7462c-f259-4c9e-9ea4-f015dca4b968",
      "state": "blocked",
      "title": "QA 3 Resolve supplier discrepancy"
    },
    {
      "id": 286,
      "projectId": "1fc7462c-f259-4c9e-9ea4-f015dca4b968",
      "state": "done",
      "title": "QA 3 Archive superseded document set"
    },
    {
      "id": 287,
      "projectId": "ab9a3ad4-183f-4beb-815b-fffdc8c30782",
      "state": "todo",
      "title": "QA 4 Review resin data sheet"
    },
    {
      "id": 288,
      "projectId": "ab9a3ad4-183f-4beb-815b-fffdc8c30782",
      "state": "in_progress",
      "title": "QA 4 Run first article molding pass"
    },
    {
      "id": 289,
      "projectId": "ab9a3ad4-183f-4beb-815b-fffdc8c30782",
      "state": "blocked",
      "title": "QA 4 Resolve supplier discrepancy"
    },
    {
      "id": 290,
      "projectId": "ab9a3ad4-183f-4beb-815b-fffdc8c30782",
      "state": "done",
      "title": "QA 4 Archive superseded document set"
    }
  ],
  "projects": [
    {
      "id": "7bcfdbbc-a353-41ab-9bb2-7efbe0350fb0",
      "name": "QA Tooling Transfer QA-CLIENT-READINESS-2026060811132310",
      "recordId": "2f0ad25a-3bd3-4ada-beba-baa7f1d90eb1"
    },
    {
      "id": "1498a396-5cea-4f27-bb26-b2978c838a2f",
      "name": "QA Regrind Qualification QA-CLIENT-READINESS-2026060811132310",
      "recordId": "0577c05e-96c4-4008-ab1d-baa5d3de162a"
    },
    {
      "id": "1fc7462c-f259-4c9e-9ea4-f015dca4b968",
      "name": "QA Supplier Change QA-CLIENT-READINESS-2026060811132310",
      "recordId": "b34854b3-1dbb-43de-b353-2c854511bb52"
    },
    {
      "id": "ab9a3ad4-183f-4beb-815b-fffdc8c30782",
      "name": "QA Document Cleanup QA-CLIENT-READINESS-2026060811132310",
      "recordId": "24ace4f5-b597-4638-9d7b-e4f025669abd"
    }
  ],
  "records": {
    "productRecordId": "c5cd26d0-e7e8-4ebb-821b-c4dcbe49f708",
    "projectRecordIds": [
      "2f0ad25a-3bd3-4ada-beba-baa7f1d90eb1",
      "0577c05e-96c4-4008-ab1d-baa5d3de162a",
      "b34854b3-1dbb-43de-b353-2c854511bb52",
      "24ace4f5-b597-4638-9d7b-e4f025669abd"
    ]
  },
  "runId": "qa-client-readiness-20260608111323106-grdz8h",
  "workflowTasks": [
    {
      "id": 154,
      "relatedRecordId": "c5cd26d0-e7e8-4ebb-821b-c4dcbe49f708",
      "state": "open",
      "title": "QA Review material data QA-CLIENT-READINESS-2026060811132310"
    },
    {
      "id": 155,
      "relatedRecordId": "c5cd26d0-e7e8-4ebb-821b-c4dcbe49f708",
      "state": "open",
      "title": "QA Approve supplier dossier QA-CLIENT-READINESS-2026060811132310"
    },
    {
      "id": 156,
      "relatedRecordId": "c5cd26d0-e7e8-4ebb-821b-c4dcbe49f708",
      "state": "open",
      "title": "QA Release controlled document QA-CLIENT-READINESS-2026060811132310"
    },
    {
      "id": 157,
      "relatedRecordId": "c5cd26d0-e7e8-4ebb-821b-c4dcbe49f708",
      "state": "open",
      "title": "QA Check regrind declaration QA-CLIENT-READINESS-2026060811132310"
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
| 1 | 409 | Plastic-Craft Polycarbonate SDS qa-client-readiness-20260608111323106-grdz8h | extracted |
| 2 | 410 | Plastic-Craft Polystyrene SDS qa-client-readiness-20260608111323106-grdz8h | extracted |
| 3 | 411 | ACRIFIX 2R 0190 SDS qa-client-readiness-20260608111323106-grdz8h | extracted |
| 4 | 412 | ACRIFIX 2R 0190 Technical Information qa-client-readiness-20260608111323106-grdz8h | extracted |
| 5 | 413 | ACRIFIX AC 1010 SDS qa-client-readiness-20260608111323106-grdz8h | extracted |
| 6 | 414 | Primex ABS Data Sheet qa-client-readiness-20260608111323106-grdz8h | unsupported |
| 7 | 415 | Acetal Technical Data qa-client-readiness-20260608111323106-grdz8h | extracted |
| 8 | 416 | HDPE Typical Properties qa-client-readiness-20260608111323106-grdz8h | extracted |
| 9 | 417 | High Impact Polystyrene Technical Data qa-client-readiness-20260608111323106-grdz8h | extracted |
| 10 | 418 | Polycarbonate AR Data Sheet qa-client-readiness-20260608111323106-grdz8h | extracted |
| 11 | 419 | Polycarbonate Physical Properties qa-client-readiness-20260608111323106-grdz8h | extracted |
| 12 | 420 | Polycarbonate GP Product Data qa-client-readiness-20260608111323106-grdz8h | extracted |
| 13 | 421 | King CuttingBoard Physical Properties qa-client-readiness-20260608111323106-grdz8h | extracted |
| 14 | 422 | King KPC HDPE Literature qa-client-readiness-20260608111323106-grdz8h | extracted |
| 15 | 423 | Komatex Foamed PVC Technical Values qa-client-readiness-20260608111323106-grdz8h | extracted |
| 16 | 424 | PVC Sheets Data qa-client-readiness-20260608111323106-grdz8h | extracted |
| 17 | 425 | Polypropylene Data qa-client-readiness-20260608111323106-grdz8h | unsupported |
| 18 | 426 | Vintec PVC Properties qa-client-readiness-20260608111323106-grdz8h | extracted |
| 19 | 427 | SCIGRIP 4SC Technical Data qa-client-readiness-20260608111323106-grdz8h | extracted |
| 20 | 428 | Weld-On 4 Technical Data qa-client-readiness-20260608111323106-grdz8h | extracted |
