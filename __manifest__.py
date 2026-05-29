{
    "name": "Document Reference Management",
    "version": "1.0.0",
    "category": "Document Management",
    "summary": "Generate, track, stamp, and manage official document reference numbers",
    "author": "Dunhill",
    "depends": [
        "base",
        "mail",
        "web",
    ],
    "external_dependencies": {
        "python": ["docx", "fitz", "openpyxl", "PIL", "requests"],
    },
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "views/document_reference_views.xml",
        "views/document_reference_master_views.xml",
        "views/res_config_settings_views.xml",
        "views/document_reference_menu.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
