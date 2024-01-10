# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
import locale
# Change locale to display month in spanish
locale.setlocale(locale.LC_TIME, 'es_US.UTF-8')

STATE = [('draft', 'Borrador'),
         ('pending', 'Pendiente'),
         ('active', 'Activo'),
         ('finish', 'Finalizado'),
         ('archived', 'Archivado')]
LICENCES = [('extra', 'Extra'),
            ('medical', 'Medica'),
            ('vacation', 'Vacaciones')]
UNLINKED = [('fired', 'Despido'),
            ('resigned', 'Renuncia'),
            ('retired', 'Retirado')]
JUSTIFIED_CAUSES = [
    ('a', 'El engaño por parte del trabajador mediante certificados o referencias personales falsas sobre la capacidad, conducta moral o actitudes profesionales del trabajador.'),
    ('b', 'Hurto, robo u otro de delito contra el patrimonio de las personas, cometido por el trabajador en el lugar del trabajo, cualesquiera que sean las circunstancias de su comisión.'),
    ('c', 'Los actos de violencia, amenazas, injurias o malos tratamientos del trabajador para con el empleador, sus representantes, familiares o jefes de la empresa, oficina o taller, cometidos durante las labores.'),
    ('d', 'La comisión de alguno de los mismos actos contra los compañeros de labor, si con ellos se alterase el orden en el lugar del trabajo.'),
    ('e', 'La perpetración fuera del servicio, contra el empleador, sus representantes, o familiares, de algunos de los actos enunciados en el inciso c), si fuesen de tal gravedad que hicieran imposible el cumplimiento del contrato.'),
    ('f', 'Los perjuicios materiales que ocasione el trabajador intencionalmente, por negligencia, imprudencia o falta grave, en los edificios, obras, maquinarias, herramientas, materias primas, productos y demás objetos relacionados con el trabajo.'),
    ('g', 'La comisión por el trabajador de actos inmorales, en el lugar del trabajo.'),
    ('h', 'La revelación por el trabajador de secretos industriales o de fábricas o asuntos de carácter reservado que conociese en razón de sus funciones en perjuicio de la empresa.'),
    ('i', 'El hecho de comprometer el trabajador con su imprudencia o descuido inexcusables la seguridad de la empresa, fábrica, taller u oficina, así como la de las personas que allí se encontrasen.'),
    ('j', 'La concurrencia del trabajador a sus tareas en estado de embriaguez, o bajo influencia de alguna droga o narcótico, o portando armas peligrosas, salvo aquéllas que, por naturaleza de su trabajo, le estuviesen permitidas.'),
    ('k', 'La condena del trabajador a una pena privativa de libertad de cumplimiento efectivo.'),
    ('l', 'La negativa manifiesta del trabajador para adoptar las medidas preventivas o someterse a los procedimientos indicados por las Leyes, los reglamentos, las autoridades competentes o el empleador, que tiendan a evitar accidentes de trabajo y enfermedades profesionales.'),
    ('m', 'La falta de acatamiento del trabajador, en forma manifiesta y reiterada y con perjuicio del empleador, de las normas que éste o sus delegados le indiquen claramente para la mayor eficacia y rendimiento en las labores.'),
    ('n', 'El trabajo a desgano o disminución intencional en el rendimiento del trabajo y la incitación a otros trabajadores para el mismo fin.'),
    ('o', 'La pérdida de la confianza del empleador en el trabajador que ejerza un puesto de dirección, fiscalización o vigilancia. Si dicho trabajador hubiese sido promovido de un empleo de escalafón, podrá volver a éste, salvo que medie otra causa justificada de despido.'),
    ('p', 'La negociación del trabajador por cuenta propia o ajena, sin permiso expreso del empleador, cuando constituya un acto de competencia a la empresa donde trabaja.'),
    ('q', 'Participar en una huelga declarada ilegal por autoridad competente.'),
    ('r', 'La inasistencia del trabajador a las tareas contratadas durante tres días consecutivos o cuatro veces en el mes, siempre que se produjera sin permiso o sin causa justificada.'),
    ('s', 'El abandono del trabajo de parte del trabajador.'),
    ('t', 'La falta reiterada de puntualidad del trabajador en el cumplimiento del horario de trabajo, después de haber sido apercibido por el empleador o sus delegados.'),
    ('u', 'La interrupción de las tareas por el trabajador, sin causa justificada aunque permanezca en su puesto. En caso de huelga, deberá abandonar el lugar de trabajo'),
    ('v', 'La desobediencia del trabajador al empleador o sus representantes, siempre que se trate del servicio contratado.'),
    ('w', 'Comprobación en el trabajador de enfermedad infecto contagiosas o mental o de otras dolencias o perturbaciones orgánicas, siempre que le incapaciten permanentemente para el cumplimiento de las tareas contratadas o constituyan un peligro para terceros; y,'),
    ('x', 'Las violaciones graves por el trabajador de las cláusulas del contrato de trabajo o disposiciones del reglamento interno de taller, aprobado por la autoridad competente.'),
    ('y', 'Los actos de acoso sexual consistentes en amenaza, presión, hostigamiento, chantaje o manoseo con propósitos sexuales hacia un trabajador de uno u otro sexo por parte de los representantes del empleador, jefes de la empresa, oficina o taller o cualquier otro superior jerárquico.')
]
DEPARTURE_REASONS = LICENCES + UNLINKED


class BMOfficialDepartureModel(models.Model):
    _name = 'bm.official.departure'
    _description = 'Licencia del funcionario'

    # region _DEFAULT_
    @api.model
    def _default_official(self):
        if 'active_id' in self._context:
            return self.official_id.browse(self._context['active_id'])
        return None
    # endregion

    # region COMPUTE
    @api.depends('official_id')
    def _compute_auxiliar_code(self):
        for rec in self:
            rec.average_monthly_salary = rec.official_gross_salary
            rec.auxiliar_code = '%(id)s%(month)s%(gross)s' % ({
                'id': rec.id or '',
                'month': fields.Datetime.now().strftime("%B").upper(),
                'gross': int(rec.official_id.gross_salary) or ''
            })

    @api.depends('official_id', 'departure_reason', 'departure_end')
    def _compute_departured_name(self):
        for rec in self:
            name = "#%(id)s: %(reason)s" % {
                'id': rec.id,
                'reason': dict(DEPARTURE_REASONS)[rec.departure_reason]
            }
            if rec.name != name:
                rec.name = name

    @api.depends('official_id', 'departure_start')
    def _compute_notification_days_apply(self):
        for rec in self:
            notification_days = 0
            if rec.official_admission_date and rec.departure_start:
                diff = relativedelta(rec.departure_start,
                                     rec.official_admission_date)
                years = diff.years
                if years < 1:
                    notification_days = 30
                elif years <= 4:
                    notification_days = 45
                elif years < 10:
                    notification_days = 60
                else:
                    notification_days = 90
            rec.notification_days_apply = notification_days

    @api.depends('official_id', 'departure_start')
    def _compute_vacation_caused_apply(self):
        for rec in self:
            vacation_caused = 0
            if rec.official_admission_date and rec.departure_start:
                diff = relativedelta(rec.departure_start,
                                     rec.official_admission_date)
                years = diff.years
                if years < 1:
                    vacation_caused = 0
                elif years <= 4:
                    vacation_caused = 12
                elif years < 10:
                    vacation_caused = 18
                else:
                    vacation_caused = 30
            rec.vacation_caused_apply = vacation_caused
            rec.vacation_caused = vacation_caused

    @api.depends('official_id', 'departure_start')
    def _compute_vacation_proportional_apply(self):
        for rec in self:
            vacation_proportional = 0
            if rec.official_admission_date and rec.departure_start:
                diff = relativedelta(rec.departure_start,
                                     rec.official_admission_date)
                years = diff.years
                months = diff.months
                if years < 0:
                    vacation_proportional = 0
                elif years <= 4:
                    vacation_proportional = 12
                elif years < 10:
                    vacation_proportional = 18
                else:
                    vacation_proportional = 30
                vacation_proportional = ((months / 12) * vacation_proportional)
                vacation_proportional = round(vacation_proportional, 1)
            rec.vacation_proportional_apply = vacation_proportional
            rec.vacation_proportional = vacation_proportional

    @api.depends('official_id', 'average_monthly_salary')
    def _compute_average_daily_salary(self):
        for rec in self:
            rec.average_daily_salary = rec.average_monthly_salary / 30

    @api.depends('official_admission_date', 'departure_start')
    def _compute_seniority(self):
        for rec in self:
            seniority = []
            if rec.official_admission_date and rec.departure_start:
                diff = relativedelta(rec.departure_start,
                                     rec.official_admission_date)

                years = diff.years
                months = diff.months
                days = diff.days

                if years > 0:
                    seniority.append(f'{years} año(s)')
                if months > 0:
                    seniority.append(f'{months} mes(es)')
                if days > 0:
                    seniority.append(f'{days} día(s)')
            rec.seniority = ', '.join(seniority) if seniority else 'N/A'

    @api.depends('official_id', 'fired_justified', 'notification_days_apply', 'unpaid_days', 'notification_days', 'average_daily_salary', 'vacation_caused', 'vacation_proportional', 'vacation_delayed')
    def _compute_amounts(self):
        for rec in self:
            # Calcular la antigüedad en años y meses
            seniority_years, seniority_months = self._calculate_seniority(rec)

            # Calcular el monto de días no pagados
            rec.unpaid_days_amount = self._calculate_unpaid_days_amount(rec)

            # Calcular el monto de preaviso
            rec.notification_amount = self._calculate_notification_amount(rec)

            # Calcular el monto de compensación
            rec.compensation_amount = self._calculate_compensation_amount(
                rec, seniority_years, seniority_months)

            # Calcular el monto de vacaciones causadas
            rec.vacation_caused_amount = self._calculate_vacation_caused_amount(
                rec, seniority_months)

            # Calcular el monto de vacaciones proporcionales
            rec.vacation_proportional_amount = self._calculate_vacation_proportional_amount(
                rec)

            # Calcular el monto de vacaciones aplazadas
            rec.vacation_delayed_amount = self._calculate_vacation_delayed_amount(
                rec, seniority_months)

            # Calcular el monto del bono salarial
            rec.salary_bonus_amount = self._calculate_salary_bonus_amount(
                rec, seniority_years)

            # Calcular el subtotal final
            rec.subtotal_amount = sum([
                rec.unpaid_days_amount, rec.vacation_caused_amount,
                rec.vacation_proportional_amount, rec.vacation_delayed_amount
            ])

            # Si es despido, sumo la notificación
            notification_discount = 0
            if rec.reason_unlinked == 'fired':
                rec.subtotal_amount += rec.notification_amount
                # Si no es causa justificada, sumo la indemnización
                if not rec.fired_justified:
                    rec.subtotal_amount += rec.compensation_amount
            elif rec.reason_unlinked == 'resigned' and rec.fired_justified:
                notification_discount = rec.notification_amount

            # Calcular el monto de IPS
            rec.ips_amount = self._calculate_ips_amount(rec)

            # Calcular el monto total, con el aguinaldo y el descuento
            rec.total_amount = rec.subtotal_amount + rec.salary_bonus_amount - rec.ips_amount - notification_discount

    # endregion

    # region ONCHANGE
    @api.onchange('reason_licences', 'reason_unlinked')
    def on_change_reason(self):
        reason = self.reason_licences or self.reason_unlinked
        self.fired_justified = False
        self.fired_causes = False
        self.notification_days = 0
        if self.departure_reason != reason:
            self.departure_reason = reason

    @api.onchange('departure_reason')
    def on_change_departure_reason(self):
        if self.departure_reason == 'medical':
            self.departure_end = self._origin.departure_end
        else:
            self.departure_end = None

    @api.onchange('departure_start')
    def on_change_departure_start(self):
        for rec in self:
            # Fix departure end
            if rec.departure_start and rec.departure_end:
                if rec.departure_start > rec.departure_end:
                    rec.departure_start = rec.departure_end

    @api.onchange('departure_end', 'official_id')
    def _onchange_departure_end(self):
        for rec in self:
            # Fix departure end
            if rec.departure_start and rec.departure_end:
                if rec.departure_end < rec.departure_start:
                    rec.departure_end = rec.departure_start
    # endregion

    # region CONSTRAINS
    @api.constrains('departure_start', 'departure_end')
    def constrains_departure(self):
        for rec in self:
            exeption = None
            if rec.departure_start and rec.departure_end:
                if rec.departure_start > rec.departure_end:
                    exeption = 'El campo \'Fecha de Salida\' no puede ser mayor a \'Fecha de Retorno\''
                if rec.departure_end < rec.departure_start:
                    exeption = 'El campo \'Fecha de Retorno\' no puede ser menor a \'Fecha de Salida\''
                delta = rec.departure_start - rec.departure_end
                if delta.days >= 35:
                    exeption = 'La Licencia no puede tener 35 días o más entre \'Fecha de Retorno\' y \'Fecha de Salida\''
            if exeption:
                raise exceptions.UserError(_(exeption))

    # endregion

    # region FIELDS
    name = fields.Char(compute='_compute_departured_name')
    auxiliar_code = fields.Char(
        'Codigo Auxiliar', compute='_compute_auxiliar_code', store=True)
    departure_description = fields.Text(
        'Salida: Información adicional', copy=False, tracking=True)
    departure_end = fields.Date('Fecha de retorno', copy=False)
    departure_start = fields.Date(
        'Fecha de salida', default=lambda self: fields.Date.today(), copy=False, required=True)
    departure_reason = fields.Selection(
        DEPARTURE_REASONS, string='Motivo de salida')
    fired_justified = fields.Boolean('Despido justificado', default=False)
    fired_causes = fields.Selection(
        JUSTIFIED_CAUSES, string='Causa justificada', default='a', help='\n'.join([') '.join(j) for j in JUSTIFIED_CAUSES]))
    reason_unlinked = fields.Selection(
        UNLINKED, string='Motivo de desvinculacion')
    reason_licences = fields.Selection(
        LICENCES, string='Motivo de licencia')
    seniority = fields.Char(string='Antigüedad', compute='_compute_seniority')
    state = fields.Selection(STATE, string='Estado', default='draft')
    # region OFFICIAL
    official_id = fields.Many2one('bm.official', 'Funcionario', ondelete='cascade',
                                  index=True, required=True, default=_default_official)
    official_admission_date = fields.Date(
        related='official_id.admission_date', readonly=True)
    official_identification_id = fields.Char(
        related='official_id.identification_id', readonly=True)
    official_iscontract = fields.Boolean(
        related='official_id.iscontract', readonly=True)
    official_gross_salary = fields.Float(
        related='official_id.gross_salary', readonly=True)
    official_vacation_days = fields.Integer(
        related='official_id.vacation_days', readonly=True)
    official_ips = fields.Integer(
        related='official_id.company_id.ips_worker_contribution', readonly=True)
    # endregion
    # region SALARY
    average_monthly_salary = fields.Float('Promedio mensual')
    average_daily_salary = fields.Float(
        'Promedio diario', compute='_compute_average_daily_salary')
    unpaid_days = fields.Integer('Dias no abonados',
                                 help="Insertar solamente los días del mes trabajados que aún no fueron pagados")
    # endregion
    # region NOTIFY
    notification_days_apply = fields.Integer(
        'Dias que le corresponden', compute='_compute_notification_days_apply',
        help="""Según el artículo 87 del Código Laboral, el preaviso conforme a la antigüedad seria:
        a) Cumplido el período de prueba hasta un año de servicio, 30 días de preaviso.
        b) De más de un año y hasta cinco años de antigüedad, 45 días de preaviso.
        c) De más de cinco y hasta diez años de antigüedad, 60 días de preaviso.
        d) De más de diez años de antigüedad en adelante, 90 días de preaviso.
        """)
    notification_days = fields.Integer(
        'Dias recibidos', help="Indicar si recibió días de preaviso. <br>Si recibió menos de lo estipulado en el Código Laboral, indicar los días otorgados")
    # endregion
    # region VACATION
    vacation_caused_apply = fields.Integer(
        'Dias que le corresponden', compute='_compute_vacation_caused_apply')
    vacation_caused = fields.Integer('Dias gozados')
    vacation_proportional_apply = fields.Integer(
        'Dias que le corresponden', compute='_compute_vacation_proportional_apply')
    vacation_proportional = fields.Integer('Dias gozados')
    vacation_delayed = fields.Integer(
        'Dias gozados',
        help="""Artículo 224: Las vacaciones no son acumulables.
        Sin embargo, a petición del trabajador podrán acumularse por dos años, siempre que no perjudique los intereses de la empresa""")
    # endregion
    # region SALARY BONUS
    salary_bonus = fields.Char('Aguinaldo proporcional')
    salary_bonus_amount = fields.Float(
        'Aguinaldo proporcional', compute='_compute_amounts')
    # endregion
    # region DISCOUNTS
    ips_amount = fields.Float('Descuento de I.P.S',
                              compute='_compute_amounts', store=True)
    # endregion
    # region SETTLEMENTS
    unpaid_days_amount = fields.Float(
        'Salario por dias trabajados', compute='_compute_amounts', store=True)
    notification_amount = fields.Float(
        'Preaviso', compute='_compute_amounts', store=True)
    compensation_amount = fields.Float(
        'Indemnizacion', compute='_compute_amounts', store=True)
    vacation_caused_amount = fields.Float(
        'Vacaciones causadas', compute='_compute_amounts', store=True)
    vacation_proportional_amount = fields.Float(
        'Vacaciones proporcionales', compute='_compute_amounts', store=True)
    vacation_delayed_amount = fields.Float(
        'Vacaciones acumuladas', compute='_compute_amounts', store=True)
    subtotal_amount = fields.Float('Sub Total', compute='_compute_amounts')
    total_amount = fields.Float('Total', compute='_compute_amounts')
    # endregion

    # endregion

    # region OVERRIDE
    @api.model
    def create(self, vals):
        res = super(BMOfficialDepartureModel, self)
        vals = self.check_departure(vals)
        res = res.create(vals)
        res.official_id._register_change('%(user)s creó la licencia %(name)s' % ({
            'user': self.env.user.name,
            'name': res.name
        }))
        return res

    def unlink(self):
        res = super(BMOfficialDepartureModel, self)
        for rec in self:
            data = [{
                'field': self._fields['departure_reason'].string,
                'value': dict(DEPARTURE_REASONS)[rec.departure_reason]
            }, {
                'field': self._fields['departure_start'].string,
                'value': rec.departure_start
            }, {
                'field': self._fields['state'].string,
                'value': dict(STATE)[rec.state]
            }]
            if rec.departure_description:
                data.append({
                    'field': self._fields['departure_description'].string,
                    'value': rec.departure_description
                })
            if rec.reason_licences:
                data.append({
                    'field': self._fields['reason_licences'].string,
                    'value': rec.reason_licences
                })
            if rec.reason_unlinked:
                data.append({
                    'field': self._fields['reason_unlinked'].string,
                    'value': dict(UNLINKED)[rec.reason_unlinked]
                })
            if rec.departure_end:
                data.append({
                    'field': self._fields['departure_end'].string,
                    'value': rec.departure_end
                })

            rec.official_id._register_change('%(user)s eliminó la licencia %(name)s' % ({
                'user': self.env.user.name,
                'name': rec.name
            }), data)
            # Activo el funcionario
            rec.official_id.state = 'ready'
        return res.unlink()

    @api.returns('self', lambda value: value.id)
    def copy(self):
        raise exceptions.UserError(_('No se pueden duplicar las licencias.'))
    # endregion

    # region FUNCTIONS
    def check_departure_journal_attendance(self):
        """# Check Departure Journal
        - Busco el jornal de la licencia
        - Busco el registro de salario en el jornal:
            - Vacaciones 
            - Despido
            - Renuncia
            - Retiro
        """
        for rec in self:
            # Solo si es de estos tipos
            if rec.departure_reason not in ['vacation', 'fired', 'resigned', 'retired']:
                continue

            official_id = rec.official_id
            departure_start = rec.departure_start

            # Busco el jornal correspondiente
            # fecha de la licencia
            journal = official_id.journal_ids.search([
                '&', ('official_id', '=', official_id.id),
                ('journal_date', '=', departure_start.replace(day=1))])
            if not journal:
                journal = official_id._create_journals({
                    'official_ids': official_id,
                    'month': departure_start.month,
                    'year': departure_start.year,
                    'return': True
                })

            # Movimiento de salario
            salary_vals = {
                'charge_type': 'B8',  # Vacaciones
                'amount_to_pay': rec.total_amount
            }
            # Busco la licencia dentro de los registros de salario
            salary_found = False
            for salary_id in journal.salary_ids:
                if salary_id.departure_id == rec:
                    salary_found = True
                    break
            if salary_found:
                journal.salary_ids.browse(salary_id.id).write(salary_vals)
            else:
                salary_vals['journal_id'] = journal.id
                salary_vals['departure_id'] = rec.id
                #salary_vals['payment_date'] = departure.payment_date
                journal.salary_ids.create(salary_vals)

            departure_end = rec.departure_end
            # Si resigno, no tiene fecha de retorno
            # Cambio la fecha de retorno al ultimo dia del mes
            # para agregar licencias hasta fin de mes
            if not departure_end:
                last_day = calendar.monthrange(
                    departure_start.year, departure_start.month)[1]
                departure_end = departure_start.replace(day=last_day)
            licenced_days = (departure_end - departure_start).days

            attendance_id = journal.attendance_id
            schedule_id = official_id.schedules_ids
            # Agrego las ausencias al registro de asistencia del mes
            for day in range(licenced_days + 1):
                # convierto el dia a Fecha
                day = departure_start + timedelta(days=day)
                days_found = False
                for days_id in attendance_id.days_ids:
                    if day == days_id.day_date:
                        days_found = True
                        break
                if not days_found:
                    weekday = day.weekday()
                    time_date = schedule_id.calculate_daily_hours(
                        weekday)  # Total de horas trabajadas ese dia
                    reason = 'A'  # Licencia
                    missed_reason = 'L'  # Licencia
                    # Agrego el registro
                    journal.attendance_id.days_ids.create({
                        'attendance_id': journal.attendance_id.id,
                        'day_date': day,
                        'time_date': time_date,
                        'reason': reason,
                        'missed_reason': missed_reason
                    })

    def check_departure(self, vals):
        departure_start = vals.get('departure_start')
        departure_end = vals.get('departure_end')
        departure_reason = vals.get('departure_reason')
        official_id = vals.get('official_id')
        #if write:
        #    departure_start = self.departure_start.strftime('%Y-%m-%d')
        #    departure_reason = self.departure_reason
        #    official_id = self.official_id.id
        #if not write:

        # Verificar si hay una licencia de tipo 'UNLINKED' que se superpone
        unlinked_departures = self.search([
            ('official_id', '=', official_id),
            ('departure_reason', 'in', [u[0] for u in UNLINKED])
        ])
        if unlinked_departures:
            raise exceptions.UserError(
                _('Este funcionario ya posee una desvinculación.'))

        # Verificar si hay otras licencias que se superponen
        overlapping_departures = self.search([
            ('official_id', '=', official_id),
            ('departure_start', '<=', departure_end),
            ('departure_end', '>=', departure_start),
            ('id', '!=', self.id),  # Excluir la propia licencia
        ])
        if overlapping_departures:
            raise exceptions.UserError(
                _('Existe una licencia que se superpone en fechas.'))

        # Vacaciones
        if departure_start and departure_end and official_id:
            official_id = self.official_id.browse(official_id)
            if departure_reason == 'vacation':
                if official_id.vacation_days == 0:
                    raise exceptions.UserError(
                        _('El funcionario no posee dias de vacaciones disponibles.'))
                departure_start_date = datetime.strptime(
                    departure_start, '%Y-%m-%d').date()
                departure_end_date = datetime.strptime(
                    departure_end, '%Y-%m-%d').date()
                departure_days = (departure_end_date -
                                  departure_start_date).days + 1
                if departure_days > official_id.vacation_days:
                    raise exceptions.UserError(
                        _('No se puede superar el número de vacaciones disponibles.'))

        # Chequeo si finalizo
        self.check_departure_end()

        return vals

    def check_departure_end(self):
        """ Termino la licencia si se cumplió la fecha de retorno """
        today = fields.Date.today()
        for rec in self:
            resigned = rec.departure_reason in [u[0] for u in UNLINKED]
            departure_end = rec.departure_end or today
            state = 'pending'
            
            if resigned and rec.departure_start <= today:
                state = 'archived'
            elif not resigned:
                if rec.departure_start <= today < departure_end:
                    state = 'active'
                else:
                    state = 'finish'

                if state == 'active':
                    rec.official_id.write({'state': 'departured'})
                elif state in ['finish', 'archived']:
                    rec.official_id._register_change('Finalizó la licencia %s' % rec.name)
            rec.state = state
    # endregion

    # region CALCULATE
    def _calculate_seniority(self, rec):
        # Lógica para calcular la antigüedad en años y meses
        diff = relativedelta(rec.departure_start, rec.official_admission_date)
        seniority_years = diff.years
        seniority_months = diff.months
        return seniority_years, seniority_months

    def _calculate_unpaid_days_amount(self, rec):
        # Lógica para calcular el monto de días no pagados
        unpaid_days_amount = rec.average_daily_salary * rec.unpaid_days
        return round(unpaid_days_amount, 2)

    def _calculate_notification_amount(self, rec):
        # Lógica para calcular el monto de preaviso
        notification_amount = 0
        if rec.fired_justified:
            notification_amount = (
                rec.notification_days_apply - rec.notification_days) * rec.average_daily_salary
            if rec.reason_unlinked == 'resigned':
                notification_amount = notification_amount / 2
        return round(notification_amount, 2)

    def _calculate_compensation_amount(self, rec, seniority_years, seniority_months):
        # Lógica para calcular el monto de compensación
        compensation_amount = 0
        if not rec.fired_justified:
            compensation_rules = {
                10: 15,  # 0 a 10 años de antigüedad = 15 días
                11: 30   # más de 10 años de antigüedad = 90 días
            }
            compensation_days = 0
            fix_seniority_years = seniority_years + \
                1 if (seniority_months >= 6) else seniority_years
            for rule_years, days in compensation_rules.items():
                if fix_seniority_years <= rule_years:
                    compensation_days = days
                    break
            compensation_amount = compensation_days * rec.average_daily_salary
            if seniority_years > 0:
                compensation_amount = (
                    compensation_days * seniority_years) * rec.average_daily_salary
        return round(compensation_amount, 2)

    def _calculate_vacation_caused_amount(self, rec, seniority_months):
        # Lógica para calcular el monto de vacaciones causadas
        vacation_caused_amount = (
            rec.vacation_caused_apply - rec.vacation_caused) * rec.average_daily_salary
        if seniority_months >= 6:
            vacation_caused_amount *= 2
        return round(vacation_caused_amount, 2)

    def _calculate_vacation_proportional_amount(self, rec):
        # Lógica para calcular el monto de vacaciones proporcionales
        vacation_proportional_amount = (
            rec.vacation_proportional_apply - rec.vacation_proportional) * rec.average_daily_salary
        return round(vacation_proportional_amount, 2)

    def _calculate_vacation_delayed_amount(self, rec, seniority_months):
        # Lógica para calcular el monto de vacaciones aplazadas
        vacation_delayed_amount = rec.vacation_delayed * rec.average_daily_salary
        if seniority_months >= 6:
            vacation_delayed_amount *= 2
        return round(vacation_delayed_amount, 2)

    def _calculate_salary_bonus_amount(self, rec, seniority_years):
        # Lógica para calcular el monto del bono salarial
        salary_bonus_amount = 0
        if rec.official_admission_date and rec.departure_start:
            antAnho = rec.departure_start.year
            antmonth = rec.departure_start.month
            antday = rec.departure_start.day
            incAnho = rec.official_admission_date.year
            incmonth = rec.official_admission_date.month
            incday = rec.official_admission_date.day
            if seniority_years >= 1 or antAnho != incAnho:
                salary_bonus_amount = (
                    ((antmonth-1) * 30 + (antday-1)) / 12) * rec.average_daily_salary
            else:
                resmonth = antmonth - incmonth
                resday = antday - incday
                salary_bonus_amount = (
                    ((resmonth * 30) + resday) / 12) * rec.average_daily_salary
        return round(salary_bonus_amount, 2)

    def _calculate_ips_amount(self, rec):
        # Lógica para calcular el monto de IPS
        ips_amount = (rec.official_ips / 100) * rec.subtotal_amount
        return round(ips_amount, 2)

    def calculate_salary_bonus_amount(self):
        """# Aguinaldo
        Para calcular el aguinaldo se deben sumar todos los salarios
        recibidos en el año hasta el momento del despido y dividir esa suma por 12."""
        year = datetime.now().year
        journals = self.official_id.journal_ids.filtered(
            lambda j: j.journal_date.year == year)
        total_net_salary = sum(
            journal.net_salary_amount for journal in journals)
        salary_bonus_amount = round(total_net_salary / 12, 2)
        return salary_bonus_amount

    def calculate_compensation_amount(self):
        """# La Indemnización
        Se paga solamente en el caso del despido injustificado. Al trabajador le corresponden
        15 jornales diarios por cada año de servicio. Para calcular la suma del jornal diario
        se calcula el promedio del salario de los últimos seis months de trabajo y se divide
        por 30 días. Este jornal promedio se multiplica por 15. El resultado es lo que le
        corresponden al Trabajador por cada año de trabajo.
        Entonces se multiplica el monto por año por la cantidad de años que trabajó.
        Ejemplo:
        - un trabajador tiene una antigüedad de 5 años.
        - Le corresponden 15 jornales diarios por cada año de servicio, es decir 5 años x 15 días = 75 días.
        - Su sueldo durante los últimos 6 months fue constante de Gs. 2.500.000.-
        - El jornal diario es entonces 2.500.000 / 30 = 83.333.-
        - Su indemnización va ser: 75 días x 83.333 = 6.249.975.-
        """
        compensation_amount = 0
        if not self.fired_justified:
            total_salary = 0
            # Se toma 7 months, ya que el mes actual no se cuenta
            six_months_back = self.departure_start - relativedelta(months=7)
            six_month_salaries = self.official_id.journal_ids.filtered(
                lambda j: six_months_back.month >= j.journal_date.month and j.journal_date.month < self.departure_start.month)
            # Calcula la suma de los salarios de los últimos seis months
            total_salary = sum(six_month_salaries.mapped('net_salary_amount'))
            # Calcula el salario promedio diario
            average_salary_last_six_months = total_salary / 30  # 6 months / 30 días
            # Obtiene la antigüedad del trabajador
            seniority_years = self.official_id.get_official_seniority(
                self.departure_start)
            # Calcula la indemnización
            compensation_amount = seniority_years * 15 * average_salary_last_six_months
        return compensation_amount

    def calculate_compensation_notice_amount(self):
        """# El Preaviso
        Normalmente se le debe avisar al trabajador con anticipación que la relación
        laboral será terminada por voluntad del empleador, según los siguientes plazos:
        - de 0 a 1 año antigüedad = 30 días
        - de 1 a 5 años antigüedad = 45 días
        - de 5 a 10 años antigüedad = 60 días
        - más de 10 años antigüedad = 90 días

        Si el empleador decide no dar este preaviso, sino terminar la relación laboral inmediatamente,
        está obligado a pagarle al trabajador esos días que le corresponderían de preaviso.

        Nuevamente debe calcular el jornal diario, pero tomando el sueldo actual y no el sueldo promedio
        de los últimos 6 months como en la indemnización.
        Ese jornal se multiplica por los días que le corresponden al trabajador.
        Ejemplo:
            El trabajador tiene 8 años de antigüedad y su sueldo actual es del 3.000.000.-
            Su jornal diario es de 3.000.000 / 30 = 100.000.-
            Le corresponden 60 días de preaviso por su antigüedad.
            Va cobrar: 60 días x 100.000 = 6.000.000.-
        """
        notification_amount = 0
        if not self.fired_justified:
            # Obtiene la antigüedad del trabajador
            seniority_years = self.official_id.get_official_seniority(
                self.departure_start)

            # Define las reglas de preaviso según la antigüedad
            compensation_rules = {
                1: 30,  # de 0 a 1 año de antigüedad = 30 días
                5: 45,  # de 1 a 5 años de antigüedad = 45 días
                10: 60,  # de 5 a 10 años de antigüedad = 60 días
                11: 90  # más de 10 años de antigüedad = 90 días
            }
            # Calcula los días de preaviso según la antigüedad
            compensation_days = 0
            for rule_years, days in compensation_rules.items():
                if seniority_years <= rule_years:
                    compensation_days = days
                    break
            # Calcula el jornal diario
            daily_salary = self.official_id.gross_salary / 30
            # Calcula el monto del preaviso
            notification_amount = compensation_days * daily_salary
        return notification_amount

    # endregion

    # region REPORTS
    def print_vacation_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_vacation_report?model=%(model)s&id=%(id)s&filename=%(filename)s' % ({
                'model': 'bm.official.departure',
                'id': self.id,
                'filename': 'Comunicacion de vacaciones'
            }),
            'target': 'self',
        }

    def _print_resignaion_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_departure_resignation_report?model=%(model)s&id=%(id)s' % ({
                'model': 'bm.official.departure',
                'id': self.id
            }),
            'target': 'self',
        }

    # endregion
