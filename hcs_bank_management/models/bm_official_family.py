# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

FAMILY_TYPE = [
    ('couple', 'Pareja'),
    ('child', 'Hijo/a')
]


class BM_OfficialFamily(models.Model):
    _name = 'bm.official.family'
    _description = 'Familia del funcionario'


    @api.depends('name')
    def _compute_display_name(self):
        for family in self:
            if not family.name:
                family.display_name = _('%(family_type)s') % {
                    'family_type': dict(FAMILY_TYPE)[family.family_type]
                }
            else:
                family.display_name = _('%(family_name)s') % {
                    'family_name': family.name
                }

    official_id = fields.Many2one('bm.official', 'Funcionario', ondelete='cascade', index=True)
    name = fields.Char()
    display_name = fields.Char(string='Nombre del familiar', compute='_compute_display_name')
    birthday = fields.Date('Fecha de nacimiento')
    family_type = fields.Selection(
        FAMILY_TYPE, string='Tipo', default='child', required=True)
    admission_date = fields.Date('Fecha de ingreso')
    school_situation = fields.Char('Situacion escolar')
    certificate_pdf = fields.Binary(string='Cert.de Capac.Exp.en Fecha')
    certificate_pdf_name = fields.Char()
