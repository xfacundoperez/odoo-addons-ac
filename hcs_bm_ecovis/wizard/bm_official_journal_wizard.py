# -*- coding: utf-8 -*-
from odoo import models, fields


class BM_OfficialSalary_Wizard(models.TransientModel):
    _name = "bm.official.journal.wizard"
    _description = "Sueldos y Jornales Wizard"

    format_id = fields.Many2one('res.bank.format', 'Formato')

    def apply_button(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_journal_txt?model=%(model)s&uid=%(uid)s&active_ids=%(ids)s&format_id=%(format_id)s' % ({
                'model': 'bm.official.journal',
                'ids': ','.join([str(id) for id in self.env.context.get('active_ids')]),
                'uid': self.env.context.get('uid'),
                'format_id': self.format_id.id
            }),
            'target': 'self',
        }
