# -*- coding: utf-8 -*-
from odoo import fields, models


class BMOfficialWizard(models.TransientModel):
    _name = "bm.official.wizard"
    _description = "BM Official Wizard"

    message = fields.Text(readonly=True, store=False)
