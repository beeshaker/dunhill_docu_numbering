from odoo import models, fields


class DocumentReferenceCompany(models.Model):
    _name = "document.reference.company"
    _description = "Document Reference Company"
    _order = "code"

    code = fields.Char(required=True)
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    letterhead_file = fields.Binary(
        string="Letterhead PDF",
        attachment=True,
        help="Upload a PDF containing the company letterhead. "
             "It will be merged as a background when 'Apply Letterhead' is enabled on a document.",
    )
    letterhead_file_name = fields.Char(string="Letterhead File Name")

    _sql_constraints = [
        ("code_unique", "unique(code)", "Company code must be unique."),
    ]


class DocumentReferenceDepartment(models.Model):
    _name = "document.reference.department"
    _description = "Document Reference Department Prefix"
    _order = "code"

    code = fields.Char(required=True)
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("code_unique", "unique(code)", "Department prefix must be unique."),
    ]


class DocumentReferenceType(models.Model):
    _name = "document.reference.type"
    _description = "Document Reference Type"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("name_unique", "unique(name)", "Document type must be unique."),
    ]


class DocumentReferenceProperty(models.Model):
    _name = "document.reference.property"
    _description = "Document Reference Property"
    _order = "name"

    name = fields.Char(required=True)
    category = fields.Char()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("name_unique", "unique(name)", "Property name must be unique."),
    ]


class DocumentReferenceSequence(models.Model):
    _name = "document.reference.sequence"
    _description = "Document Reference Number Sequence"
    _order = "year desc, company_id, department_id"

    company_id = fields.Many2one(
        "document.reference.company",
        required=True,
        ondelete="cascade",
    )
    department_id = fields.Many2one(
        "document.reference.department",
        required=True,
        ondelete="cascade",
    )
    year = fields.Integer(required=True)
    next_number = fields.Integer(default=1, required=True)

    _sql_constraints = [
        (
            "unique_company_department_year",
            "unique(company_id, department_id, year)",
            "A sequence already exists for this company, department, and year.",
        )
    ]
