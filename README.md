# Document Reference Management - Odoo Module

This module converts the Streamlit Document Reference Management app into a native Odoo module.

## Current features

- Master document reference register
- Company, department, document type, property setup
- Reference format like `DCL/COO/2600001`
- Year-based serial tracking per company and department
- Upload original Word/PDF/Excel file
- Stamp reference numbers into DOCX, PDF, and XLSX files
- Optional logo watermark support if `static/src/img/dunhill_logo.png` is added
- Manual reference override with reason
- Previous/new reference relationship for revisions
- Statuses: Draft, Issued, Cancelled, Superseded, Revised
- Odoo groups:
  - Document References / Viewer
  - Document References / User
  - Document References / Admin
- Pivot and graph reporting views
- Ollama-based AI document analysis

## Ollama settings

The module reads Ollama settings from Odoo Settings > Document References:

- Enable AI Document Analysis
- LLM Provider: Ollama
- Ollama Base URL, default: `http://127.0.0.1:11434`
- Ollama Model, default: `llama3.1`
- Temperature, default: `0.1`
- Timeout, default: `60`

If Ollama is installed on the same server as Odoo, keep the base URL as:

```bash
http://127.0.0.1:11434
```

Confirm Ollama is reachable from the Odoo server:

```bash
curl http://127.0.0.1:11434/api/tags
```

Confirm the model exists:

```bash
ollama list
```

If needed, pull a model:

```bash
ollama pull llama3.1
```

## Python dependencies

Install these inside the Odoo virtual environment:

```bash
/opt/odoo/venv/bin/pip install python-docx PyMuPDF openpyxl pillow requests
```

## Installation

Copy the folder into your Odoo custom addons path, for example:

```bash
sudo cp -r document_reference_management /opt/odoo/custom_addons/
sudo chown -R odoo:odoo /opt/odoo/custom_addons/document_reference_management
sudo systemctl restart odoo
```

Then update the app list and install **Document Reference Management**.

Or from command line:

```bash
/opt/odoo/venv/bin/python3 /opt/odoo/odoo-server/odoo-bin \
  -c /etc/odoo.conf \
  -d YOUR_DATABASE \
  -u document_reference_management \
  --stop-after-init
```

Then restart Odoo:

```bash
sudo systemctl restart odoo
```

## Logo watermark

Add your logo here if you want watermarking:

```text
document_reference_management/static/src/img/dunhill_logo.png
```
