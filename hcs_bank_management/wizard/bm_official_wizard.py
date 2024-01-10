# -*- coding: utf-8 -*-
from odoo import fields, models


class BMOfficialWizard(models.TransientModel):
    _name = "bm.official.wizard"
    _description = "BM Official Wizard"

    message = fields.Text(readonly=True, store=False)
    date = fields.Date(default=fields.Date.today())

    def create_journal(self):
        model = self._context['active_model']
        ids = self.env.context['active_ids']
        for rec in self.env[model].browse(ids):
            rec.create_journal(self.date)
