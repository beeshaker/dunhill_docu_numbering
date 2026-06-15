import base64
import json
import re
import tempfile
from pathlib import Path

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

from ..utils.document_processors import process_document_file
from ..utils.ai_analyzer import analyze_document


PROPERTY_SCOPE_SELECTION = [
    ("single_property", "Single Property"),
    ("multiple_properties", "Multiple Properties"),
    ("all_properties", "All Properties"),
    ("head_office", "Head Office"),
    ("general", "General"),
    ("third_party", "Third Party"),
    ("none", "None"),
]

STATUS_SELECTION = [
    ("draft", "Draft"),
    ("issued", "Issued"),
    ("cancelled", "Cancelled"),
    ("superseded", "Superseded"),
    ("revised", "Revised"),
]


class DocumentReference(models.Model):
    _name = "document.reference"
    _description = "Document Reference Register"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        string="Reference Number",
        readonly=True,
        copy=False,
        tracking=True,
    )

    company_id = fields.Many2one(
        "document.reference.company",
        string="Company",
        tracking=True,
    )

    department_id = fields.Many2one(
        "document.reference.department",
        string="Department Prefix",
        tracking=True,
    )

    reference_year = fields.Integer(
        string="Reference Year",
        readonly=True,
        copy=False,
    )

    serial_number = fields.Integer(
        string="Serial Number",
        readonly=True,
        copy=False,
    )

    issue_date = fields.Date(
        string="Issue Date",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )

    document_type_id = fields.Many2one(
        "document.reference.type",
        string="Document Type",
        tracking=True,
    )

    property_scope = fields.Selection(
        PROPERTY_SCOPE_SELECTION,
        default="general",
        required=True,
        tracking=True,
    )

    property_ids = fields.Many2many(
        "document.reference.property",
        string="Properties",
    )

    recipient_name = fields.Char()
    recipient_company = fields.Char()
    subject = fields.Text(string="Subject / Particulars")
    prepared_by = fields.Char()
    remarks = fields.Text()

    original_file = fields.Binary(
        string="Original File",
        attachment=True,
        required=True,
    )
    original_file_name = fields.Char()

    generated_file = fields.Binary(
        string="Generated File",
        attachment=True,
        readonly=True,
    )
    generated_file_name = fields.Char(readonly=True)

    file_type = fields.Char(readonly=True)

    status = fields.Selection(
        STATUS_SELECTION,
        default="draft",
        required=True,
        tracking=True,
    )

    previous_reference_id = fields.Many2one(
        "document.reference",
        string="Previous Reference",
    )

    new_reference_id = fields.Many2one(
        "document.reference",
        string="New Reference",
        readonly=True,
    )

    manual_override = fields.Boolean(
        string="Manual Override",
        tracking=True,
    )

    manual_reference = fields.Char(
        string="Manual Reference Number",
    )

    override_reason = fields.Text()

    watermark_applied = fields.Boolean(
        string="Apply Logo Watermark",
        tracking=True,
    )

    apply_letterhead = fields.Boolean(
        string="Apply Letterhead",
        tracking=True,
        help="Merge the company letterhead PDF as a background behind this document's pages. "
             "The letterhead file must be uploaded on the selected Company record.",
    )

    has_letterhead = fields.Boolean(
        string="Force Letterhead Ref Placement",
        tracking=True,
        help="PDFs with a letterhead are detected automatically. Enable this only to force "
             "the reference number below the configured header height when auto-detection "
             "fails (e.g. fully scanned / image-only PDFs).",
    )

    ai_suggested_metadata = fields.Text(
        string="AI Suggested Metadata JSON",
        readonly=True,
    )

    uploaded_by_id = fields.Many2one(
        "res.users",
        string="Uploaded By",
        default=lambda self: self.env.user,
        readonly=True,
    )

    can_generate = fields.Boolean(
        compute="_compute_can_generate",
    )

    _sql_constraints = [
        (
            "reference_unique",
            "unique(name)",
            "Reference number must be unique.",
        )
    ]

    # -------------------------------------------------------------------------
    # Mail / chatter compatibility fix
    # -------------------------------------------------------------------------
    def _mail_get_companies(self, default_company=None):
        """
        Odoo mail.thread expects a field named company_id to point to res.company.

        This module uses company_id for document.reference.company, which is a
        custom master table. Without this override, Odoo 19 mail/chatter may try
        to read mail-related fields such as alias_domain_id from
        document.reference.company and crash.

        This forces chatter/mail to use the active Odoo company instead.
        """
        default_company = default_company or self.env.company
        return {record.id: default_company for record in self}

    def _safe_message_post(self, body):
        """
        Post to chatter when possible.

        If Odoo mail/chatter fails because of alias-domain/company handling,
        do not block the main business action such as reference generation.
        """
        for rec in self:
            try:
                rec.message_post(body=body)
            except AttributeError:
                # Avoid blocking document generation because of mail alias handling.
                pass
            except Exception:
                # Keep business flow working even if chatter has a local config issue.
                pass

    @api.depends("status")
    def _compute_can_generate(self):
        for rec in self:
            rec.can_generate = rec.status == "draft"

    @api.constrains("manual_override", "manual_reference", "override_reason")
    def _check_manual_override(self):
        for rec in self:
            if rec.manual_override:
                if not rec.manual_reference:
                    raise ValidationError(_("Manual reference number is required."))
                if not rec.override_reason:
                    raise ValidationError(_("Override reason is required."))

    @api.constrains("property_scope", "property_ids")
    def _check_properties_required(self):
        for rec in self:
            if rec.property_scope in ["single_property", "multiple_properties"] and not rec.property_ids:
                raise ValidationError(_("Please select at least one property."))

    def _get_serial_digits(self):
        value = self.env["ir.config_parameter"].sudo().get_param(
            "document_reference_management.serial_digits",
            default="5",
        )
        try:
            return int(value)
        except Exception:
            return 5

    def _allow_manual_override(self):
        value = self.env["ir.config_parameter"].sudo().get_param(
            "document_reference_management.allow_manual_override",
            default="True",
        )
        return str(value).lower() in ["true", "1", "yes", "y"]

    def _generate_reference_number(self):
        self.ensure_one()

        if not self.company_id or not self.department_id:
            raise UserError(_("Company and department are required."))

        year_full = self.issue_date.year
        year_short = str(year_full)[-2:]
        digits = self._get_serial_digits()

        seq_obj = self.env["document.reference.sequence"].sudo()
        seq = seq_obj.search([
            ("company_id", "=", self.company_id.id),
            ("department_id", "=", self.department_id.id),
            ("year", "=", year_full),
        ], limit=1)

        if not seq:
            seq = seq_obj.create({
                "company_id": self.company_id.id,
                "department_id": self.department_id.id,
                "year": year_full,
                "next_number": 1,
            })

        # Lock this sequence row while incrementing to reduce duplicate risk.
        self.env.cr.execute(
            "SELECT id FROM document_reference_sequence WHERE id = %s FOR UPDATE",
            [seq.id],
        )

        serial = seq.next_number
        seq.next_number = seq.next_number + 1

        reference_number = "%s/%s/%s%s" % (
            self.company_id.code,
            self.department_id.code,
            year_short,
            str(serial).zfill(digits),
        )

        return reference_number, year_full, serial

    def _parse_manual_reference(self):
        self.ensure_one()

        reference = (self.manual_reference or "").strip()
        if not reference:
            raise UserError(_("Manual reference number is required."))

        year_full = self.issue_date.year

        match = re.search(r"(\d+)$", reference)
        serial = 0
        if match:
            number_part = match.group(1)
            if len(number_part) > 2:
                serial = int(number_part[2:])
            else:
                serial = int(number_part)

        return reference, year_full, serial

    def _property_scope_from_label(self, label):
        if not label:
            return False

        normalized = str(label).strip().lower().replace(" ", "_")
        aliases = {
            "single_property": "single_property",
            "multiple_properties": "multiple_properties",
            "all_properties": "all_properties",
            "head_office": "head_office",
            "general": "general",
            "third_party": "third_party",
            "none": "none",
        }
        return aliases.get(normalized)

    def _apply_ai_suggestions(self, suggestions):
        self.ensure_one()
        values = {}

        company_code = str(suggestions.get("company") or "").strip()
        if company_code and not self.company_id:
            company = self.env["document.reference.company"].search([
                ("code", "=ilike", company_code),
                ("active", "=", True),
            ], limit=1)
            if company:
                values["company_id"] = company.id

        department_code = str(suggestions.get("department_prefix") or "").strip()
        if department_code and not self.department_id:
            department = self.env["document.reference.department"].search([
                ("code", "=ilike", department_code),
                ("active", "=", True),
            ], limit=1)
            if department:
                values["department_id"] = department.id

        document_type_name = str(suggestions.get("document_type") or "").strip()
        if document_type_name and not self.document_type_id:
            document_type = self.env["document.reference.type"].search([
                ("name", "=ilike", document_type_name),
                ("active", "=", True),
            ], limit=1)
            if document_type:
                values["document_type_id"] = document_type.id

        property_scope = self._property_scope_from_label(suggestions.get("property_scope"))

        if suggestions.get("recipient_name") and not self.recipient_name:
            values["recipient_name"] = str(suggestions.get("recipient_name")).strip()

        if suggestions.get("recipient_company") and not self.recipient_company:
            values["recipient_company"] = str(suggestions.get("recipient_company")).strip()

        if suggestions.get("subject") and not self.subject:
            values["subject"] = str(suggestions.get("subject")).strip()

        property_names = suggestions.get("properties")
        if property_names and not self.property_ids:
            if isinstance(property_names, list):
                names = [str(v).strip() for v in property_names if str(v).strip()]
            else:
                names = [v.strip() for v in str(property_names).split(",") if v.strip()]

            if names:
                properties = self.env["document.reference.property"].search([
                    ("name", "in", names),
                    ("active", "=", True),
                ])
                if properties:
                    values["property_ids"] = [(6, 0, properties.ids)]

        if property_scope:
            scope_requires_properties = property_scope in ["single_property", "multiple_properties"]
            has_properties = bool(self.property_ids) or bool(values.get("property_ids"))
            if not scope_requires_properties or has_properties:
                values["property_scope"] = property_scope

        if values:
            self.write(values)

    def action_analyze_document(self):
        for rec in self:
            if not rec.original_file:
                raise UserError(_("Please upload a document first."))

            original_name = rec.original_file_name or "document"

            with tempfile.TemporaryDirectory() as tmpdir:
                input_path = Path(tmpdir) / original_name
                input_path.write_bytes(base64.b64decode(rec.original_file or b""))
                suggestions = analyze_document(input_path, env=self.env)

            rec.ai_suggested_metadata = json.dumps(suggestions, indent=2, ensure_ascii=False)
            rec._apply_ai_suggestions(suggestions)
            rec._safe_message_post(_("Document analysis completed."))

        return True

    def action_generate_reference(self):
        for rec in self:
            if rec.status != "draft":
                raise UserError(_("Only draft records can generate a reference."))

            if not rec.original_file:
                raise UserError(_("Please upload an original file."))

            missing = []
            if not rec.company_id:
                missing.append(_("Company"))
            if not rec.department_id:
                missing.append(_("Department Prefix"))
            if not rec.document_type_id:
                missing.append(_("Document Type"))
            if not rec.subject:
                missing.append(_("Subject / Particulars"))

            if missing:
                raise UserError(_("Please complete these fields before generating: %s") % ", ".join(missing))

            if rec.manual_override:
                if not rec._allow_manual_override():
                    raise UserError(_("Manual override is disabled in settings."))
                reference_number, reference_year, serial_number = rec._parse_manual_reference()
            else:
                reference_number, reference_year, serial_number = rec._generate_reference_number()

            original_name = rec.original_file_name or "document"
            suffix = Path(original_name).suffix.lower()

            if suffix not in [".docx", ".pdf", ".xlsx"]:
                raise UserError(_("Unsupported file type. Please upload .docx, .pdf, or .xlsx."))

            safe_reference = reference_number.replace("/", "_").replace("\\", "_")
            output_name = "%s_%s" % (safe_reference, original_name)

            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)
                input_path = tmpdir_path / original_name
                output_path = tmpdir_path / output_name

                input_path.write_bytes(base64.b64decode(rec.original_file or b""))

                # Resolve letterhead PDF bytes from company when requested.
                letterhead_pdf_bytes = None
                if rec.apply_letterhead:
                    if not rec.company_id:
                        raise UserError(_("Select a Company before applying the letterhead."))
                    if not rec.company_id.letterhead_file:
                        raise UserError(
                            _("Company '%s' has no letterhead PDF uploaded. "
                              "Go to the Company record and upload one first.")
                            % rec.company_id.name
                        )
                    letterhead_pdf_bytes = base64.b64decode(rec.company_id.letterhead_file)

                # Manual height override for scanned PDFs where auto-detection fails.
                letterhead_header_height = 0
                if rec.has_letterhead:
                    height_val = self.env["ir.config_parameter"].sudo().get_param(
                        "document_reference_management.letterhead_header_height",
                        default="130",
                    )
                    try:
                        letterhead_header_height = int(height_val)
                    except Exception:
                        letterhead_header_height = 130

                process_document_file(
                    input_path=input_path,
                    output_path=output_path,
                    reference_number=reference_number,
                    add_watermark=rec.watermark_applied,
                    letterhead_pdf_bytes=letterhead_pdf_bytes,
                    letterhead_header_height=letterhead_header_height,
                )

                rec.generated_file = base64.b64encode(output_path.read_bytes())
                rec.generated_file_name = output_name

            rec.name = reference_number
            rec.reference_year = reference_year
            rec.serial_number = serial_number
            rec.file_type = suffix
            rec.status = "issued"

            if rec.previous_reference_id:
                rec.previous_reference_id.status = "superseded"
                rec.previous_reference_id.new_reference_id = rec.id

            rec._safe_message_post(_("Reference generated: %s") % reference_number)

        return True

    def action_cancel_reference(self):
        for rec in self:
            if rec.status not in ["issued", "revised"]:
                raise UserError(_("Only issued or revised references can be cancelled."))

            rec.status = "cancelled"
            rec._safe_message_post(_("Reference cancelled by %s.") % self.env.user.name)

        return True

    def action_reset_to_draft(self):
        for rec in self:
            if not self.env.user.has_group("document_reference_management.group_document_reference_admin"):
                raise UserError(_("Only Document Reference Admins can reset to draft."))

            rec.status = "draft"
            rec._safe_message_post(_("Reference reset to draft by %s.") % self.env.user.name)

        return True

    def write(self, vals):
        protected_fields = {
            "company_id",
            "department_id",
            "issue_date",
            "document_type_id",
            "property_scope",
            "property_ids",
            "subject",
            "manual_override",
            "manual_reference",
        }

        for rec in self:
            if rec.status in ["issued", "cancelled", "superseded"] and protected_fields.intersection(vals):
                if not self.env.user.has_group("document_reference_management.group_document_reference_admin"):
                    raise UserError(_("Issued, cancelled, and superseded references cannot be edited by normal users."))

        return super().write(vals)