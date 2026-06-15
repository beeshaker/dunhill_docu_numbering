from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    document_ref_serial_digits = fields.Integer(
        string="Serial Digits",
        config_parameter="document_reference_management.serial_digits",
        default=5,
    )

    document_ref_allow_manual_override = fields.Boolean(
        string="Allow Manual Override",
        config_parameter="document_reference_management.allow_manual_override",
        default=True,
    )

    document_ref_use_ai_analysis = fields.Boolean(
        string="Enable AI Document Analysis",
        config_parameter="document_reference_management.use_ai_analysis",
        default=False,
    )

    document_ref_llm_provider = fields.Selection(
        [
            ("ollama", "Ollama"),
        ],
        string="LLM Provider",
        config_parameter="document_reference_management.llm_provider",
        default="ollama",
    )

    document_ref_ollama_base_url = fields.Char(
        string="Ollama Base URL",
        config_parameter="document_reference_management.ollama_base_url",
        default="http://127.0.0.1:11434",
        help="Use 127.0.0.1 if Ollama is installed on the same server as Odoo.",
    )

    document_ref_ollama_model = fields.Char(
        string="Ollama Model",
        config_parameter="document_reference_management.ollama_model",
        default="llama3.1",
        help="Example: llama3.1, qwen2.5, mistral, or the model name installed on your server.",
    )

    document_ref_ollama_temperature = fields.Float(
        string="Ollama Temperature",
        config_parameter="document_reference_management.ollama_temperature",
        default=0.1,
    )

    document_ref_ollama_timeout = fields.Integer(
        string="Ollama Timeout Seconds",
        config_parameter="document_reference_management.ollama_timeout",
        default=60,
    )

    document_ref_letterhead_header_height = fields.Integer(
        string="Letterhead Header Height (pt)",
        config_parameter="document_reference_management.letterhead_header_height",
        default=130,
        help="Height in PDF points of the letterhead header area (1 pt ≈ 0.35 mm, "
             "so 130 pt ≈ 46 mm). When 'Document has Letterhead' is enabled on a record, "
             "the reference number will be placed this many points from the top of the page.",
    )
