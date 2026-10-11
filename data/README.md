# Document data layout

Documents are organized by document type. The **folder name determines the `document_type`** passed to the document-driven ingestion pipeline.

```text
data/documents/
├── regulation/
│   └── *.pdf
├── control/
│   └── *.pdf
├── evidence/
│   └── *.pdf
├── policy/
│   └── *.pdf
└── assessment/
    └── *.pdf
```

## Folder → ingestion type

| Folder | `document_type` |
|---|---|
| `regulation/` | `REGULATION` |
| `control/` | `CONTROL` |
| `evidence/` | `EVIDENCE` |
| `policy/` | `POLICY` |
| `assessment/` | `ASSESSMENT` |

The ingestion runner recursively handles every PDF in these supported folders. Adding a new PDF does **not** require editing Python code.

Current synthetic documents:

- `regulation/mock_regulation_2025.pdf` — baseline requirements.
- `regulation/mock_regulation_2026.pdf` — effective July 1, 2026; supersedes 2025 version.
- `control/mock_bank_controls.pdf` — bank's initial control design.
- `evidence/mock_control_evidence.pdf` — evidence showing the existing annual review.

The `policy/` and `assessment/` folders are intentionally ready for additional documents.

These documents are fictional and must not be treated as regulatory advice or actual RBI requirements.
