# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BM_Department(models.Model):
    _name = 'bm.department'
    _description = 'Departmento de la empresa'
    _inherit = ['mail.thread']
    _order = 'name'
    _rec_name = 'complete_name'

    name = fields.Char('Nombre', required=True)
    complete_name = fields.Char(
        'Nombre completo', compute='_compute_complete_name', store=True)
    company_id = fields.Many2one(
        'res.company', string='Empresa', index=True, default=lambda self: self.env.company)
    parent_id = fields.Many2one('bm.department', string='departamento superior', index=True,
                                domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('parent_id', '!=', parent_id)]")
    child_ids = fields.One2many(
        'bm.department', 'parent_id', string='Departmentos')
    manager_id = fields.Many2one('bm.official', string='Responsable', tracking=True,
                                 domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    member_ids = fields.One2many(
        'bm.official', 'department_id', string='Miembros', readonly=True)
    jobs_ids = fields.One2many(
        'bm.job', 'department_id', string='Puestos de trabajo')
    note = fields.Text('Notas')
    color = fields.Integer('Color')
    active = fields.Boolean('Activo', default=True)

    def name_get(self):
        if not self.env.context.get('hierarchical_naming', True):
            return [(record.id, record.name) for record in self]
        return super(BM_Department, self).name_get()

    @api.model
    def name_create(self, name):
        return self.create({'name': name}).name_get()[0]

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for department in self:
            if department.parent_id:
                department.complete_name = '%s / %s' % (
                    department.parent_id.complete_name, department.name)
            else:
                department.complete_name = department.name

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(
                _('No puede crear departamentos recursivos.'))

    @api.model
    def create(self, vals):
        # TDE note: auto-subscription of manager done by hand, because currently
        # the tracking allows to track+subscribe fields linked to a res.user record
        # An update of the limited behavior should come, but not currently done.
        department = super(BM_Department, self.with_context(
            mail_create_nosubscribe=True)).create(vals)
        manager = self.env['bm.official'].browse(vals.get('manager_id'))
        return department

    def write(self, vals):
        """
        Si se actualiza al gerente de un departamento, debemos actualizar a todos los empleados
        de la jerarquía del departamento y suscribir al nuevo gerente.
        """
        # TDE note: auto-subscription of manager done by hand, because currently
        # the tracking allows to track+subscribe fields linked to a res.user record
        # An update of the limited behavior should come, but not currently done.
        if 'manager_id' in vals:
            manager_id = vals.get('manager_id')
            if manager_id:
                manager = self.env['bm.official'].browse(manager_id)
            # set the officials's parent to the new manager
            self._update_employee_manager(manager_id)
        return super(BM_Department, self).write(vals)

    def _update_employee_manager(self, manager_id):
        officials = self.env['bm.official']
        for department in self:
            officials = officials | self.env['bm.official'].search([
                ('id', '!=', manager_id),
                ('department_id', '=', department.id),
                ('parent_id', '=', department.manager_id.id)
            ])
        officials.write({'parent_id': manager_id})
