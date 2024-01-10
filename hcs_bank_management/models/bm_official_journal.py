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
    ('ready', 'Listo'), ('liquidated', 'Liquidado')
]


class BM_OfficialJournal(models.Model):
    _name = 'bm.official.journal'
    _description = 'Sueldos y Jornales del Funcionario'
    _rec_name = 'attendance_id'

    # region COMPUTE
    @api.depends('journal_date')
    def _compute_journal_date_display(self):
        for rec in self:
            rec.journal_date_display = rec.journal_date.strftime(
                '%B/%Y').capitalize()

    @api.depends('attendance_amount')
    def _compute_attendance_amount(self):
        """# Calculo de asistencia"""
        for rec in self:
            daily_amount = rec.official_gross_salary / 30
            attendance_amount = daily_amount * rec.attendance_worked_days
            rec.attendance_amount = attendance_amount

    @api.depends('missed_amount')
    def _compute_missed_amount(self):
        """# Calculo de asistencia"""
        for rec in self:
            schedule_id = rec.official_id.schedules_ids
            laboral_days = sum(schedule.laboral for schedule in schedule_id if schedule.laboral)

            if laboral_days:
                worked_hours_per_day = schedule_id.calculate_weekly_hours() / laboral_days
                daily_amount = rec.official_gross_salary / 30
                missed_amount = (daily_amount / worked_hours_per_day) * rec.attendance_missed_hours
            else:
                missed_amount = 0.0

            rec.missed_amount = missed_amount
    #endregion

    # region ONCHANGE
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
    journal_date = fields.Date(
        default=fields.Date.today().replace(day=1))
    journal_date_display = fields.Char(
        'Fecha de asistencia', compute='_compute_journal_date_display')
    payment_date = fields.Date(
        string='Fecha de pago', required=True)
    state = fields.Selection(STATE, string='Estado', default='draft')
    # endregion
    # region ATTENDANCE
    attendance_id = fields.Many2one(
        'bm.official.attendance', 'Asistencia', ondelete='cascade', index=True)
    attendance_worked_days = fields.Integer(
        'Días Trabajados', related='attendance_id.worked_days')
    attendance_missed_hours = fields.Float(related='attendance_id.missed_hours')
    attendance_departure_hours = fields.Float(related='attendance_id.departure_hours')
    attendance_daytime_overtime = fields.Float(related='attendance_id.daytime_overtime')
    attendance_night_overtime = fields.Float(related='attendance_id.night_overtime')
    attendance_holiday_overtime = fields.Float(related='attendance_id.holiday_overtime')
    # endregion
    # region JOURNAL_AMOUNTS
    attendance_amount = fields.Float('Importe de asistencia', compute='_compute_attendance_amount')
    family_bonus_amount = fields.Float('Bonificacion Familiar', default=0)
    vacation_amount = fields.Float('Vacaciones', default=0)
    extra_salary_amount = fields.Float('Aguinaldo', default=0)
    other_beneficts_amount = fields.Float('Otros beneficios', default=0)
    total_general_amount = fields.Float('Total General', default=0)
    ips_amount = fields.Float('Descuento de I.P.S', default=0)
    missed_amount = fields.Float('Importe de ausencias', compute='_compute_missed_amount')
    salary_advance_amount = fields.Float('Anticipo de sueldo', default=0)
    other_discounts_amount = fields.Float('Otros descuentos', default=0)
    net_salary_amount = fields.Float('Neto a percibir', default=0)
    # endregion
    # region SALARY_MOEVENT
    salary_ids = fields.One2many(
        'bm.official.journal.salary', 'journal_id', string='Movimientos de salario')
    # endregion
    # endregion

    # region FUNCTIONS
    @api.model
    def create(self, vals):
        res = super(BM_OfficialJournal, self).create(vals)
        # Registro el cambio
        res.official_id._register_change('Se creo el Sueldo y Jornal: %(name)s' % ({
            'name': res.journal_date_display
        }))
        return res

    """def write(self, vals):
        res = super(BM_OfficialJournal, self).write(vals)
        return res"""

    @api.returns('self', lambda value: value.id)
    def copy(self):
        raise exceptions.UserError(
            _('No se pueden duplicar los Sueldos y Jornales.'))

    def update_movements(self):
        pass

    """def update_movements(self):
        # Actualiza los movimientos de salarios
        #Los siguientes, se agregan manualmente en cada registro de salario
        #- 09: 'Otros Beneficios'
        #- 07: 'Pago de Vacaciones'
        #- 04: 'Otros descuentos'
        for rec in self:
            # Solo aplica si esta en borrador
            if not rec.state == 'draft':
                continue
            payment_date = fields.Datetime.today().replace(month=rec.journal_date.month)
            salarys = rec.salary_ids
            # region SUELDO
            sid = False
            for salary in salarys:
                if salary.charge_type == '1':
                    sid = salary
                    break
            data = {
                'amount_to_pay': rec.attendance_amount,
                'reference': self._fields['attendance_amount'].string,
                'payment_date': payment_date
            }
            if rec.attendance_amount > 0:
                if sid:
                    data['payment_date'] = payment_date.replace(
                        day=sid.payment_date.day)
                    sid.write(data)
                else:
                    data['journal_id'] = rec.id
                    data['charge_type'] = '1'  # Sueldo
                    salarys.create(data)
            # endregion
            # region AUSENCIAS
            sid = False
            for salary in salarys:
                if salary.charge_type == '1':
                    sid = salary
                    break
            data = {
                'amount_to_pay': rec.attendance_amount,
                'reference': self._fields['attendance_amount'].string,
                'payment_date': payment_date
            }
            if rec.attendance_amount > 0:
                if sid:
                    data['payment_date'] = payment_date.replace(
                        day=sid.payment_date.day)
                    sid.write(data)
                else:
                    data['journal_id'] = rec.id
                    data['charge_type'] = '1'  # Sueldo
                    salarys.create(data)
            # endregion


            # region LICENCIAS
            last_day = calendar.monthrange(
                rec.journal_date.year, rec.journal_date.month)[1]
            first_dt = rec.journal_date.replace(day=1)
            last_dt = rec.journal_date.replace(day=last_day)
            # Licencias del mes
            departures = rec.official_id.departure_id.search(['&', '&',
                                                              ('official_id', '=',
                                                               rec.official_id.id),
                                                              ('departure_start',
                                                               '>=', first_dt),
                                                              ('departure_start', '<=', last_dt)])
            # Obtengo las licencias del mes
            for dep in departures:
                # Checkeo las Asistencias, Sueldos y Jornales
                dep.check_departure_journal_attendance()
            # update
            salarys = rec.salary_ids
            # Verifico si existe la licencia
            resigned = False
            for salary in salarys:
                if salary.departure_id:
                    if salary.departure_id.id in departures.ids:
                        if salary.departure_id.departure_reason in ['fired', 'retired', 'resigned']:
                            resigned = True
                            break
                    else:
                        # Si la licencia no pertenece al jornal, la remuevo
                        salary.unlink()
                        # update
                        salarys = rec.salary_ids
                        break

            # endregion
            # region AGUINALDO
            # Antes de calcular aguinaldo, debo verificar si hay licencia de resecion
            sid = False
            for salary in salarys:
                if salary.charge_type == '3':
                    sid = salary
                    break
            # Lista de meses con pago
            extra_salary_payments = self.get_extra_salary_payments(
                rec, resigned)
            count_payments = len(extra_salary_payments)
            data = {
                'reference': "%(ref)s %(len)s %(mstr)s" % {
                    'ref': self._fields['extra_salary_amount'].string,
                    'len': count_payments,
                    'mstr': 'meses' if count_payments > 1 else 'mes'
                },
                'payment_date': payment_date
            }
            if count_payments > 0:
                extra_salary_amount = 0
                for pay in extra_salary_payments:
                    extra_salary_amount += pay[1]  # Sumo solo la cantidad
                # Divido el total, por 12 meses
                extra_salary_amount = float("{:.2f}".format(extra_salary_amount / 12))
                data['amount_to_pay'] = extra_salary_amount
                # Si resigno, agrego que es proporcional
                if resigned:
                    data['reference'] = data['reference'] + " (Proporcional)"
                if sid:
                    data['payment_date'] = payment_date.replace(
                        day=sid.payment_date.day)
                    sid.write(data)
                else:
                    data['journal_id'] = rec.id
                    data['charge_type'] = '3'  # Aguinaldo
                    salarys.create(data)
            else:
                if sid:
                    sid.unlink()
                    # update
                    salarys = rec.salary_ids

            # endregion
            # region HORAS_EXTRAS
            # Lo dejo para poner las horas extras como un item de salario
            sid = False
            for salary in salarys:
                if salary.charge_type == '6':
                    sid = salary
                    break
            data = {
                'amount_to_pay': rec.overtime_amount,
                'reference': self._fields['overtime_amount'].string,
                'payment_date': payment_date
            }
            if rec.overtime_amount > 0:
                if sid:
                    data['payment_date'] = payment_date.replace(
                        day=sid.payment_date.day)
                    sid.write(data)
                else:
                    data['journal_id'] = rec.id
                    data['charge_type'] = '6'  # Pago de horas extras
                    salarys.create(data)
            else:
                if sid:
                    sid.unlink()
                    # update
                    salarys = rec.salary_ids
            # endregion
            # region BONIFICACION_FAMILIAR
            sid = False
            for salary in salarys:
                if salary.charge_type == '8':
                    sid = salary
                    break
            data = {
                'amount_to_pay': rec.family_bonus_amount,
                'reference': self._fields['family_bonus_amount'].string,
                'payment_date': payment_date
            }
            if rec.family_bonus_amount > 0:
                if sid:
                    data['payment_date'] = payment_date.replace(
                        day=sid.payment_date.day)
                    sid.write(data)
                else:
                    data['journal_id'] = rec.id
                    data['charge_type'] = '8'  # Bonificacion Familiar
                    salarys.create(data)
            else:
                if sid:
                    sid.unlink()
                    # update
                    salarys = rec.salary_ids
            # endregion
            # region I.P.S
            sid = False
            for salary in salarys:
                if salary.charge_type == '10':
                    sid = salary
                    break
            data = {
                'amount_to_pay': rec.ips_amount,
                'reference': self._fields['ips_amount'].string,
                'payment_date': payment_date
            }
            if rec.ips_amount > 0:
                if sid:
                    data['payment_date'] = payment_date.replace(
                        day=sid.payment_date.day)
                    sid.write(data)
                else:
                    data['journal_id'] = rec.id
                    data['charge_type'] = '10'  # Descuento de IPS
                    salarys.create(data)
            else:
                if sid:
                    sid.unlink()
                    # update
                    salarys = rec.salary_ids
            # endregion"""

    def _compute_amounts(self):
        for rec in self:
            attendance_amount = 0
            other_beneficts_amount = 0
            family_bonus_amount = 0
            vacation_amount = 0
            extra_salary_amount = 0
            total_general_amount = 0
            ips_amount = 0
            salary_advance_amount = 0
            other_discounts_amount = 0
            net_salary_amount = 0
            if rec.state not in ['ready', 'liquidated']:
                attendance_amount = 1
                other_beneficts_amount = 1
                family_bonus_amount = 1
                vacation_amount = 1
                extra_salary_amount = 1
                total_general_amount = 1
                ips_amount = 1
                salary_advance_amount = 1
                other_discounts_amount = 1
                net_salary_amount = 1
            rec.write({
                'attendance_amount': attendance_amount,
                'other_beneficts_amount': other_beneficts_amount,
                'family_bonus_amount': family_bonus_amount,
                'vacation_amount': vacation_amount,
                'extra_salary_amount': extra_salary_amount,
                'total_general_amount': total_general_amount,
                'ips_amount': ips_amount,
                'salary_advance_amount': salary_advance_amount,
                'other_discounts_amount': other_discounts_amount,
                'net_salary_amount': net_salary_amount
            })

    def get_extra_salary_payments(self, rec, resigned=False):
        # Funcionario
        offid = rec.official_id
        is_december = rec.journal_date.month == 12  # Diciembre
        # Lista de meses
        list = []
        if is_december or resigned:
            #journals = journal.search(['&', ('official_id', '=', offid.id), ('state', '=', 'liquidated')])
            journals = rec.search([('official_id', '=', offid.id)])
            # Busco los jornales liquidados de todo el año del jornal
            for journal in journals:
                month = journal.journal_date.month
                # Si es proporcional, solo hasta el mes del jornal
                if resigned:
                    if month > rec.journal_date.month:
                        continue
                # Por cada jornal, obtengo Neto a percibir
                list.append((month, journal.net_salary_amount))
        return list

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
            'view_id': self.env.ref('hcs_bank_management.bm_official_journal_wizard_form_view').id,
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
    BENEFITS_CHARGES = [
        ('B1', 'Salario'),
        ('B2', 'Aguinaldo (SAC)'),
        #('B3', 'Horas nocturnas (30%)'),
        #('B4', 'Horas extras diurnas (50%)'),
        #('B5', 'Horas extras nocturnas (100%)'),
        #('B6', 'Domingos & feriados (100%)'),
        #('B7', 'Horas extras nocturnas domingos & feriados (200%)'),
        ('B8', 'Vacaciones'),
        ('B9', 'Bonificación Familiar'),
        ('B99', 'Otros ingresos'),
    ]
    DISCOUNT_CHARGES = [
        ('D1', 'Aporte al I.P.S'),
        ('D2', 'Anticipo'),
        #('D3', 'Asociaciones, cooperativas'),
        #('D4', 'Prestamos'),
        #('D5', 'Judiciales'),
        #('D6', 'Suspensiones'),
        ('D7', 'Ausencias Injustificadas'),
        ('D8', 'Llegadas tardias'),
        ('D99', 'Otros descuentos'),
    ]
    CHARGE_TYPES = BENEFITS_CHARGES + DISCOUNT_CHARGES
    """CHARGE_TYPES = [
        ('1', 'Sueldo'),
        ('2', 'Anticipo de Sueldo'),
        ('3', 'Aguinaldo'),
        ('4', 'Otros descuentos'),
        ('5', 'Pago de Licencias'),
        ('6', 'Pago de Horas Extras'),
        # ('7', 'Pago de Vacaciones'),  | Se usa Pago de Licencias
        ('8', 'Pago de Bonificacion Familiar'),
        ('9', 'Otros Beneficios'),
        ('10', 'Descuento de I.P.S')
    ]"""

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
        string='Salario a cobrar', readonly=False, required=True)
    auxiliar_code = fields.Char(
        'Codigo Auxiliar')  # , compute='_compute_auxiliar_code', store=True
    charge_type = fields.Selection(
        CHARGE_TYPES, string='Tipo de Cobro', default='1', required=True)
    payment_date = fields.Date(
        string='Fecha de cobro', default=lambda s: fields.Date.context_today(s), required=True)
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
        action_date = fields.Date.today().replace(
            day=1, month=args['month'], year=args['year'])
        next_month = action_date + relativedelta(months=1)

        journal = False
        for official_id in args['official_ids']:
            journal = official_id.journal_ids.search(['&', '&', ('official_id', '=', official_id.id),
                                                      ('journal_date',
                                                       '>=', action_date),
                                                      ('journal_date', '<', next_month)], order='journal_date desc', limit=1)
            # Si no existe el Sueldo y jornal, lo creo
            if not journal:
                journal = official_id.journal_ids.sudo().create({
                    'official_id': official_id.id,
                    'journal_date': action_date,
                    'payment_date': action_date,
                })

            attendance = official_id.attendance_ids.search(['&', '&', ('journal_id', '=', journal.id),
                                                            ('attendance_date',
                                                             '>=', action_date),
                                                            ('attendance_date', '<', next_month)], order='attendance_date desc', limit=1)

            # Si no existe la asistencia del journal, lo creo
            if not attendance:
                # Creo la asistencia del mes y la asocio
                # al jornal recien creado
                attendance = official_id.attendance_ids.sudo().create({
                    'journal_id': journal.id,
                    'attendance_date': action_date,
                })
                # Asocio la asistencia al journal
                journal.attendance_id = attendance.id
                # Computo las horas trabajadas
                attendance._compute_woked()
        if 'return' in args:
            return journal
    # endregion
