# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class BM_Job(models.Model):
    _name = 'bm.job'
    _description = 'Puesto de trabajo'
    _inherit = ['mail.thread']

    name = fields.Char(string='Nombre del puesto',
                       required=True, index=True, translate=True)
    no_of_officials = fields.Integer(compute='_compute_officials', string='Número actual de funcionarios',
                                     store=True, help='Número de funcionarios que ocupan actualmente este puesto de trabajo.')
    official_ids = fields.One2many(
        'bm.official', 'job_id', string='Funcionarios')
    description = fields.Text('Description del puesto')
    requirements = fields.Text('Requerimientos')
    department_id = fields.Many2one('bm.department', string='Departamento',
                                    domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)
    profession_ids = fields.One2many(
        'bm.job.profession', 'job_id', string='Profesiones del funcionario')
    #profession_id = fields.Many2one('bm.job.profession', string='Profesión del puesto', required=True)
    #profession = fields.Char(string='Profesión del puesto', required=True)

    _sql_constraints = [('name_company_uniq', 'unique(name, company_id, department_id)',
                         'El nombre del puesto de trabajo debe ser único por departamento en la empresa.!')]

    @api.depends('official_ids.job_id', 'official_ids.active')
    def _compute_officials(self):
        official_data = self.env['bm.official'].read_group(
            [('job_id', 'in', self.ids)], ['job_id'], ['job_id'])
        result = dict((data['job_id'][0], data['job_id_count'])
                      for data in official_data)
        for job in self:
            job.no_of_officials = result.get(job.id, 0)

    @api.model
    def create(self, values):
        """ No queremos que el usuario actual sea seguidor de todos los trabajos creados """
        return super(BM_Job, self.with_context(mail_create_nosubscribe=True)).create(values)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        if 'name' not in default:
            default['name'] = _('%s (copy)') % (self.name)
        return super(BM_Job, self).copy(default=default)

class BM_JobProfession(models.Model):
    _name = 'bm.job.profession'
    _description = 'Profesion del puesto'
    
    name = fields.Char(string='Nombre de la profesion',
                       required=True, index=True, translate=True)
    job_id = fields.Many2one('bm.job', 'Puesto de trabajo', ondelete='cascade', index=True)
    description = fields.Text('Description del puesto')
    requirements = fields.Text('Requerimientos')
