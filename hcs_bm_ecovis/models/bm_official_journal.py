# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _
from dateutil.relativedelta import relativedelta
import calendar
import locale
# Change locale to display month in spanish
locale.setlocale(locale.LC_TIME, 'es_US.UTF-8')


PAYMENT_MODE = [
    ('1', 'Banco'), ('2', 'Cuenta Corriente'),
    ('3', 'Caja de Ahorro')
]
STATE = [
    ('draft', 'Borrador'), ('error', 'Revisar'),
    ('ready', 'Listo')
]


class BM_OfficialJournal(models.Model):
    _name = 'bm.official.journal'
    _description = 'Sueldos y Jornales del Funcionario'
    _rec_name = 'attendance_id'

    # region COMPUTE ONCHANGE
    @api.depends('journal_date')
    def _compute_journal_date_display(self):
        for rec in self:
            rec.journal_date_display = rec.journal_date.strftime(
                '%B/%Y').capitalize()

    @api.depends('official_gross_salary', 'attendance_worked_days')
    def _compute_attendance_amount(self):
        for rec in self:
            if rec.official_id:
                # Dias trabajados se fija a 30
                days_worked = 30
                # Calculo la asistencia del mes
                _amount = (rec.official_gross_salary / days_worked) * \
                    rec.attendance_worked_days
                rec.attendance_amount = round(_amount, 2) or 0

    @api.depends('overtime_fifty', 'overtime_hundred',
                 'attendance_worked_days', 'attendance_worked_hours',
                 'official_gross_salary')
    @api.onchange('overtime_fifty', 'overtime_hundred')
    def _compute_overtime(self):
        for rec in self:
            if rec.official_id:
                _amount = 0
                if rec.attendance_worked_hours > 0 and rec.attendance_worked_days > 0:
                    # Dias trabajados se fija a 30
                    days_worked = 30
                    # Salario al dia
                    _amount_per_day = rec.official_gross_salary / days_worked
                    # Salario por hora
                    _amount_per_hour = _amount_per_day / \
                        (rec.attendance_worked_hours / rec.attendance_worked_days)
                    # Salario al 50%
                    _amount_fifty = 0
                    if rec.overtime_fifty > 0:
                        _amount_fifty = (_amount_per_hour *
                                         1.5) * rec.overtime_fifty
                    # Salario al 100%
                    _amount_hundred = 0
                    if rec.overtime_hundred > 0:
                        _amount_hundred = (
                            _amount_per_hour * 2) * rec.overtime_hundred
                    # Salario Extra total
                    _amount = round(_amount_fifty + _amount_hundred, 2)
                rec.overtime_amount = _amount

    @api.depends('official_family_childs', 'official_gross_salary')
    def _compute_family_bonus_amount(self):
        for rec in self:
            if rec.official_id:
                # El bono corresponde al 5% del salario bruto
                bonus_amount = rec.official_gross_salary * 0.05
                # Por cada hijo, le corresponde un bonus
                rec.family_bonus_amount = round(
                    rec.official_family_childs * bonus_amount, 2)

    @api.depends('official_id')
    def _compute_vacation(self):
        for rec in self:
            _amount = 0
            for salary in rec.salary_ids:
                if salary.departure_id:
                    if salary.departure_id.departure_reason == 'vacation':
                        _amount += salary.departure_id.remuneration
            rec.vacation_amount = round(_amount, 2)

    @api.depends('salary_ids')
    def _compute_extra_salary_amount(self):
        current_month = fields.Date.today().replace(day=1)
        next_month = current_month + relativedelta(months=1)
        for rec in self:
            _amount = 0
            for sal in rec.salary_ids.search([
                    '&', '&',  '&',
                    ('journal_id', '=', rec.id),
                    ('charge_type', '=', '3'),  # Aguinaldo
                    ('payment_date', '>=', current_month),
                    ('payment_date', '<', next_month)]):
                _amount += sal.amount_to_pay
            rec.extra_salary_amount = round(_amount, 2)

    @api.depends('official_id')
    @api.onchange('attendance_amount', 'overtime_amount',
                  'vacation_amount', 'family_bonus_amount',
                  'extra_salary_amount', 'other_beneficts_amount')
    def _compute_total_general_amount(self):
        for rec in self:
            # Importe de asistencia
            _amount = rec.attendance_amount
            # Importe de Horas Extras
            _amount += rec.overtime_amount
            # Importe de Vacaciones
            _amount += rec.vacation_amount
            # Importe de Bonificacion Familiar
            _amount += rec.family_bonus_amount
            # Importe de Aguinaldo
            _amount += rec.extra_salary_amount
            # Importe de Otros Beneficios
            _amount += rec.other_beneficts_amount
            # Resultado
            rec.total_general_amount = round(_amount, 2)

    @api.depends('official_id')
    @api.onchange('total_general_amount')
    def _compute_ips_amount(self):
        for rec in self:
            # Si no es contrato, calculo el IPS
            if not rec.official_iscontract:
                # Obtengo el porcentaje de IPS
                _ips = rec.official_id.company_id.ips_worker_contribution / 100
                # Calculo el porcentaje de IPS del Total general
                _amount = rec.total_general_amount * _ips
                rec.ips_amount = round(_amount, 2)
            else:
                rec.ips_amount = 0

    @api.depends('salary_ids')
    def _compute_salary_advance_amount(self):
        current_month = fields.Date.today().replace(day=1)
        next_month = current_month + relativedelta(months=1)
        for rec in self:
            _amount = 0
            for sal in rec.salary_ids.search([
                    '&', '&',  '&',
                    ('journal_id', '=', rec.id),
                    ('charge_type', '=', '2'),  # Anticipo de sueldo
                    ('payment_date', '>=', current_month),
                    ('payment_date', '<', next_month)]):
                _amount += sal.amount_to_pay
            rec.salary_advance_amount = round(_amount, 2)

    @api.depends('salary_ids')
    def _compute_other_discounts_amount(self):
        current_month = fields.Date.today().replace(day=1)
        next_month = current_month + relativedelta(months=1)
        for rec in self:
            _amount = 0
            for sal in rec.salary_ids.search([
                    '&', '&',  '&',
                    ('journal_id', '=', rec.id),
                    ('charge_type', '=', '4'),  # Otros descuentos
                    ('payment_date', '>=', current_month),
                    ('payment_date', '<', next_month)]):
                _amount += sal.amount_to_pay
            rec.other_discounts_amount = round(_amount, 2)

    @api.depends('total_general_amount', 'ips_amount',
                 'salary_advance_amount', 'other_discounts_amount')
    @api.onchange('total_general_amount', 'ips_amount',
                  'salary_advance_amount', 'other_discounts_amount')
    def _compute_net_salary_amount(self):
        for rec in self:
            # Total general
            _amount = rec.total_general_amount
            # Descuentos
            _amount -= rec.ips_amount
            _amount -= rec.salary_advance_amount
            _amount -= rec.other_discounts_amount
            # NETO a percibir
            rec.net_salary_amount = round(_amount, 2)

    @api.onchange('official_id')
    def _onchange_official_id(self):
        self.attendance_id = self.attendance_id.search([
            '&', ('official_id', '=', self.official_id.id),
            ('attendance_date', '=', fields.Date.today().replace(day=1))
        ])

    # endregion

    # region FIELDS
    # region OFFICIAL
    official_id = fields.Many2one(
        'bm.official', 'Funcionario', ondelete='cascade', index=True)
    company_id = fields.Many2one(
        'res.company', 'Nombre de la empresa', related='official_id.company_id')
    official_working_hours = fields.Char(
        string='Horario de Trabajo', related='official_id.working_hours')
    official_payment_mode = fields.Selection(
        PAYMENT_MODE, string='Forma de pago', related='official_id.payment_mode')
    official_currency_id = fields.Many2one('res.currency',
                                           related='official_id.currency_id', string='Tipo de Moneda')  # , domain=_domain_currency
    official_gross_salary = fields.Float(
        'Salario Bruto', related='official_id.gross_salary')
    official_family_childs = fields.Integer(
        'Cantidad de Hijos', related='official_id.family_childs')
    official_iscontract = fields.Boolean(
        'Es contratado', related='official_id.iscontract')
    # endregion
    # region JOURNAL
    journal_date = fields.Datetime(
        default=fields.Datetime.today().replace(day=1))
    journal_date_display = fields.Char(
        'Fecha de asistencia', compute='_compute_journal_date_display')
    overtime_fifty = fields.Integer('Horas extras (50%)')
    overtime_hundred = fields.Integer('Horas extras (100%)')
    overtime_amount = fields.Integer(
        'Horas extras (Importe)', compute='_compute_overtime', default=0)
    other_beneficts_amount = fields.Float('Otros beneficios', default=0)
    family_bonus_amount = fields.Float(
        'Bonificacion Familiar', compute='_compute_family_bonus_amount', default=0)
    vacation_amount = fields.Float(
        'Vacaciones', compute='_compute_vacation', default=0)
    extra_salary_amount = fields.Float(
        'Aguinaldo', compute='_compute_extra_salary_amount', default=0)
    total_general_amount = fields.Float(
        'Total General', compute='_compute_total_general_amount', default=0)
    ips_amount = fields.Float(
        'I.P.S', compute='_compute_ips_amount', default=0)
    salary_advance_amount = fields.Float(
        'Anticipo de sueldo', compute='_compute_salary_advance_amount', default=0)
    other_discounts_amount = fields.Float(
        'Otros descuentos', compute='_compute_other_discounts_amount', default=0)
    net_salary_amount = fields.Float(
        'Neto a percibir', compute='_compute_net_salary_amount', default=0)
    state = fields.Selection(STATE, string='Estado', default='draft')
    # endregion
    # region ATTENDANCE
    attendance_id = fields.Many2one(
        'bm.official.attendance', 'Asistencia', ondelete='cascade', index=True)
    attendance_worked_days = fields.Integer(
        'Días Trabajados', related='attendance_id.worked_days')
    attendance_worked_hours = fields.Integer(
        'Horas de Trabajo', related='attendance_id.worked_hours')
    attendance_amount = fields.Float(
        'Importe de asistencia', compute='_compute_attendance_amount', default=0)
    # endregion
    # region SALARY_MOEVENT
    salary_ids = fields.One2many(
        'bm.official.journal.salary', 'journal_id', string='Movimientos de salario')
    # endregion
    # endregion

    # region FUNCTIONS
    def write(self, vals):
        # Aplico los cambios
        res = super(BM_OfficialJournal, self).write(vals)
        # Actualizo los movimientos de salarios
        self.update_salary_movements()
        return res

    @api.returns('self', lambda value: value.id)
    def copy(self):
        raise exceptions.UserError(
            _('No se pueden duplicar los Sueldos y Jornales.'))

    def update_salary_movements(self):
        for rec in self:
            # Solo aplica si esta en borrador
            if rec.state == 'draft':
                payment_date = fields.Datetime.today().replace(month=rec.journal_date.month)
                # Movmimientos de salario
                salarys = rec.salary_ids
                # Verifico los Pagos de licencia si corresponde
                for departure in rec.official_id.departure_id.search([('official_id', '=', rec.official_id.id)], order='id desc', limit=1):
                    # Si la licencia está dentro del mes del jornal
                    if departure.payment_date.month == rec.journal_date.month:
                        # Si no existe el movimiento, lo agrego
                        """ Lo deshabilito para que no aparezca el pago de licencia
                            como movimiento de salario
                        if not salarys.search([('departure_id', '=', departure.id)], limit=1):
                            salarys.create({
                                'journal_id': rec.id,
                                'charge_type': '5', # Pago de licencia
                                'departure_id': departure.id,
                                'amount_to_pay': departure.remuneration,
                                'payment_date': departure.payment_date,
                                'reference': ''
                            })
                        """
                        pass
                # region BENEFICIOS
                # Sueldo basico
                salarys = salarys.search(
                    ['&', ('journal_id', '=', rec.id), ('charge_type', '=', '1')], limit=1)
                if salarys:
                    # Actualizo el importe de la asistencia
                    salarys.write({
                        'amount_to_pay': rec.attendance_amount,
                        'reference': self._fields['attendance_amount'].string,
                        'payment_date': payment_date.replace(day=salarys.payment_date.day)
                    })
                else:
                    # Solo si el monto es mayor a 0
                    if rec.attendance_amount > 0:
                        salarys.create({
                            'journal_id': rec.id,
                            'charge_type': '1',  # Sueldo
                            'amount_to_pay': rec.attendance_amount,
                            'reference': self._fields['attendance_amount'].string,
                            'payment_date': payment_date
                        })
                # Horas extras
                salarys = salarys.search(
                    ['&', ('journal_id', '=', rec.id), ('charge_type', '=', '6')], limit=1)
                if salarys:
                    # Actualizo el importe de la asistencia
                    salarys.write({
                        'amount_to_pay': rec.overtime_amount,
                        'reference': self._fields['overtime_amount'].string,
                        'payment_date': payment_date.replace(day=salarys.payment_date.day)
                    })
                else:
                    # Solo si el monto es mayor a 0
                    if rec.overtime_amount > 0:
                        salarys.create({
                            'journal_id': rec.id,
                            'charge_type': '6',  # Pago de horas extras
                            'amount_to_pay': rec.overtime_amount,
                            'reference': self._fields['overtime_amount'].string,
                            'payment_date': payment_date
                        })
                # Vacaciones
                #salarys = salarys.search(['&', ('journal_id', '=', rec.id), ('charge_type', '=', '7')], limit=1)
                # if salarys:
                #    # Actualizo el importe de la asistencia
                #    salarys.write({
                #        'amount_to_pay': rec.vacation_amount,
                #        'reference': self._fields['vacation_amount'].string,
                #        'payment_date': payment_date.replace(day=salarys.payment_date.day)
                #    })
                # else:
                #    # Solo si el monto es mayor a 0
                #    if rec.vacation_amount > 0:
                #        salarys.create({
                #            'journal_id': rec.id,
                #            'charge_type': '7', # Pago de vacaciones
                #            'amount_to_pay': rec.vacation_amount,
                #            'reference': self._fields['vacation_amount'].string,
                #            'payment_date': payment_date
                #        })
                # Bonificacion Familiar
                salarys = salarys.search(
                    ['&', ('journal_id', '=', rec.id), ('charge_type', '=', '8')], limit=1)
                if salarys:
                    # Actualizo el importe de la asistencia
                    salarys.write({
                        'amount_to_pay': rec.family_bonus_amount,
                        'reference': self._fields['family_bonus_amount'].string,
                        'payment_date': payment_date.replace(day=salarys.payment_date.day)
                    })
                else:
                    # Solo si el monto es mayor a 0
                    if rec.family_bonus_amount > 0:
                        salarys.create({
                            'journal_id': rec.id,
                            'charge_type': '8',  # Pago de Bonificacion Familiar
                            'amount_to_pay': rec.family_bonus_amount,
                            'reference': self._fields['family_bonus_amount'].string,
                            'payment_date': payment_date
                        })
                # Aguinaldo
                salarys = salarys.search(
                    ['&', ('journal_id', '=', rec.id), ('charge_type', '=', '3')], limit=1)
                if salarys:
                    # Actualizo el importe de la asistencia
                    salarys.write({
                        'amount_to_pay': rec.extra_salary_amount,
                        'reference': self._fields['extra_salary_amount'].string,
                        'payment_date': payment_date.replace(day=salarys.payment_date.day)
                    })
                else:
                    # Solo si el monto es mayor a 0
                    if rec.extra_salary_amount > 0:
                        salarys.create({
                            'journal_id': rec.id,
                            'charge_type': '3',  # Pago de Aguinaldo
                            'amount_to_pay': rec.extra_salary_amount,
                            'reference': self._fields['extra_salary_amount'].string,
                            'payment_date': payment_date
                        })
                # endregion
                # region DESCUENTOS
                # I.P.S
                salarys = salarys.search(
                    ['&', ('journal_id', '=', rec.id), ('charge_type', '=', '10')], limit=1)
                if salarys:
                    # Actualizo el importe de la asistencia
                    salarys.write({
                        'amount_to_pay': rec.ips_amount,
                        'reference': self._fields['ips_amount'].string,
                        'payment_date': payment_date.replace(day=salarys.payment_date.day)
                    })
                else:
                    # Solo si el monto es mayor a 0
                    if rec.ips_amount > 0:
                        salarys.create({
                            'journal_id': rec.id,
                            'charge_type': '10',  # Descuento de IPS
                            'amount_to_pay': rec.ips_amount,
                            'reference': self._fields['ips_amount'].string,
                            'payment_date': payment_date
                        })
                # endregion
                pass

    def create_journal_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_journal_report?model=%(model)s&active_ids=%(ids)s&filename=%(filename)s' % ({
                'model': 'bm.official.journal',
                'ids': ','.join([str(id) for id in self.env.context.get('active_ids')]),
                'filename': 'Sueldos y jornales'
            }),
            'target': 'self',
        }

    def print_official_recipe_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_official_recipe?model=%(model)s&id=%(id)s&filename=%(filename)s' % ({
                'model': 'bm.official.journal',
                'id': self.id,
                'filename': 'Recibo'
            }),
            'target': 'self',
        }

    def open_journal_attendance(self):
        return {
            'name': 'Asistencias',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'res_model': 'bm.official.attendance',
            'view_id': False,
            'view_mode': 'form',
            'context': {
                'create': False
            }
        }

    def create_journal_txt(self):
        return {
            'name': _("Seleccione el formato a aplicar"),
            'context': self.env.context,
            'view_mode': 'form',
            'view_id': self.env.ref('hcs_bm_ecovis.bm_official_journal_wizard_form_view').id,
            'view_type': 'form',
            'res_model': 'bm.official.journal.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
    # endregion


class BM_OfficialJournalSalary(models.Model):
    _name = 'bm.official.journal.salary'
    _description = 'Movimientos de salario'

    PAYMENT_MODE = [
        ('1', 'Banco'), ('2', 'Cuenta Corriente'),
        ('3', 'Caja de Ahorro')
    ]
    CHARGE_TYPE = [
        ('1', 'Sueldo'),
        ('2', 'Anticipo de Sueldo'),
        ('3', 'Aguinaldo'),
        ('4', 'Otros descuentos'),
        ('5', 'Pago de Licencias'),
        ('6', 'Pago de Horas Extras'),
        ('7', 'Pago de Vacaciones'),
        ('8', 'Pago de Bonificacion Familiar'),
        ('9', 'Otros Beneficios'),
        ('10', 'Descuento de I.P.S')
    ]

    # region COMPUTE
    def _domain_departure_id(self):
        _domain = []
        journal = False
        # Obtengo el ID del journal
        params = self.env.context.get('params')
        if params:
            if params.get('id'):
                journal = params.get('id')
        if journal:
            journal = self.journal_id.browse(journal)

            # Obtengo las licencias del funcionario
            departure = self.departure_id.search([
                ('official_id', '=', journal.official_id.id)
            ])
            # Obtengo la fecha del jornal y retorno el domain
            current_month = journal.journal_date.replace(day=1)
            next_month = current_month + relativedelta(months=1)
            _domain = ['&', '&', '&',
                       ('id', 'in', departure.ids),
                       ('id', 'not in', journal.salary_ids.ids),
                       ('payment_date', '>=', current_month),
                       ('payment_date', '<', next_month)]
        return _domain
    # endregion

    # region FIELDS
    journal_id = fields.Many2one(
        'bm.official.journal', 'Sueldo', ondelete='cascade', index=True)
    official_id = fields.Many2one(
        'bm.official', string='Funcionario', related='journal_id.official_id', readonly=True)
    amount_to_pay = fields.Float(
        string='Salario a pagar', readonly=False, required=True)
    auxiliar_code = fields.Char(
        'Codigo Auxiliar')  # , compute='_compute_auxiliar_code', store=True
    charge_type = fields.Selection(
        CHARGE_TYPE, string='Tipo de Cobro', default='1', required=True)
    payment_date = fields.Date(
        string='Fecha de pago', default=lambda s: fields.Date.context_today(s), required=True)
    departure_id = fields.Many2one(
        'bm.official.departure', 'Licencia', ondelete='cascade', index=True, domain=_domain_departure_id)
    reference = fields.Char(string='Referencia')

    # endregion

    # region FUNCTIONS
    def print_salary_advance_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_salary_advance?model=%(model)s&id=%(id)s&filename=%(filename)s' % ({
                'model': 'bm.official.journal.salary',
                'id': self.id,
                'filename': 'Recibo de Anticipo'
            }),
            'target': 'self',
        }

    # endregion


class BM_OfficialJournalInherit(models.Model):
    _inherit = 'bm.official'

    # region FIELDS
    journal_ids = fields.One2many(
        'bm.official.journal', 'official_id', help='list of journals for the official')
    # endregion

    # region FUNCTIONS
    def _create_journals(self, args):
        """ # Crear nuevos sueldos y salarios para el mes dado """
        action_date = fields.Date.today().replace(day=1, month=args['month'])
        next_month = action_date + relativedelta(months=1)

        journal = False
        for off in args['official_ids']:
            journal = off.journal_ids.search(['&', '&', ('official_id', '=', off.id),
                                              ('journal_date', '>=', action_date),
                                              ('journal_date', '<', next_month)], order='journal_date desc', limit=1)
            # Si no existe el Sueldo y jornal, lo creo
            if not journal:
                journal = off.journal_ids.sudo().create({
                    'official_id': off.id,
                    'journal_date': action_date,
                })
                # Registro el cambio
                off._register_change('Se creó Sueldo y Jornales: %(reg)s' % ({
                    'reg': journal.journal_date_display
                }))

            attendance = off.attendance_ids.search(['&', '&', ('journal_id', '=', journal.id),
                                                    ('attendance_date',
                                                     '>=', action_date),
                                                    ('attendance_date', '<', next_month)], order='attendance_date desc', limit=1)

            # Si no existe la asistencia del journal, lo creo
            if not attendance:
                # Creo la asistencia del mes y la asocio
                # al jornal recien creado
                attendance = off.attendance_ids.sudo().create({
                    'journal_id': journal.id,
                    'attendance_date': action_date,
                })
                # Asocio la asistencia al journal
                journal.attendance_id = attendance.id
                # Computo las horas trabajadas
                attendance._compute_woked()
                # Registro el cambio
                off._register_change('Se creó la Asistencia: %(reg)s' % ({
                    'reg': attendance.attendance_date_display
                }))
        if 'return' in args:
            return journal
    # endregion
