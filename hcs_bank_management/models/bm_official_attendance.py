# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _
from datetime import timedelta
import locale
# Change locale to display month in spanish
locale.setlocale(locale.LC_TIME, 'es_US.UTF-8')

REASONS_LIST = [
    ('A', 'Ausente'),
    ('LT', 'Llegada tarde'),
    ('HED', 'Hora extra diurna'),
    ('HEN', 'Hora extra nocturna'),
    ('HEF', 'Hora extra feriado')
]
MISSED_REASONS = [
    ('A', 'Ausencia'),
    ('LT', 'Ausencia parcial'),
    ('H', 'Hora extra'),
    ('L', 'Licencia'),
    ('U', 'Desvinculacion')
]


class BM_OfficialAttendance(models.Model):
    _name = 'bm.official.attendance'
    _description = 'Asistencia del funcionario'
    _order = 'attendance_date desc'

    # region COMPUTE
    @api.depends('attendance_date')
    def _compute_attendance_date_display(self):
        for rec in self:
            rec.attendance_date_display = rec.attendance_date.strftime(
                '%B/%Y').capitalize()

    @api.depends('worked_days', 'missed_hours', 'daytime_overtime', 'night_overtime',
                 'holiday_overtime', 'departure_hours', 'days_ids.time_date')
    def _compute_hours(self):
        """# Calculo de horas"""
        for rec in self:
            schedule_id = rec.official_id.schedules_ids
            worked_days = 30
            missed_hours = 0
            # Horas Extras
            daytime_overtime = 0
            night_overtime = 0
            holiday_overtime = 0
            # Licencias
            departure_hours = 0

            for day in rec.days_ids:
                # Fix para maximo de horas
                weekday = day.day_date.weekday()
                daily_worked_hours = schedule_id.calculate_daily_hours(weekday)
                if day.time_date < 0 or day.time_date > daily_worked_hours:
                    day.time_date = daily_worked_hours
                # Ausencias
                if day.missed_reason in ['A', 'LT']:
                    if day.missed_reason == 'A':
                        # Descuento 1 dia si se ausento el dia completo
                        worked_days -= 1
                    # Horas totales trabajadas
                    missed_hours += day.time_date
                # Horas extras
                elif day.missed_reason in ['H']:
                    if day.reason == 'HED':
                        daytime_overtime += day.time_date
                    if day.reason == 'HEN':
                        night_overtime += day.time_date
                    if day.reason == 'HEF':
                        holiday_overtime += day.time_date
                elif day.missed_reason in ['L', 'U']:
                    departure_hours += day.time_date
            rec.write({
                'worked_days': worked_days,
                'missed_hours': missed_hours,
                'daytime_overtime': daytime_overtime,
                'night_overtime': night_overtime,
                'holiday_overtime': holiday_overtime,
                'departure_hours': departure_hours
            })
    # endregion

    # region FIELDS
    journal_id = fields.Many2one(
        'bm.official.journal', string='Funcionario', ondelete='cascade', required=True, index=True)
    official_id = fields.Many2one(
        'bm.official', string='Funcionario', related='journal_id.official_id', readonly=True)
    official_working_hours = fields.Char(
        string='Horario de Trabajo', related='official_id.working_hours', readonly=True)
    official_iscontract = fields.Boolean(
        related='official_id.iscontract', readonly=True)
    attendance_date = fields.Datetime(
        default=fields.Datetime.today().replace(day=1))
    attendance_date_display = fields.Char(
        'Fecha de asistencia', compute='_compute_attendance_date_display')
    days_ids = fields.One2many(
        'bm.official.attendance.days', 'attendance_id', string='Registro de dias')
    worked_days = fields.Integer('Días Trabajados')
    missed_hours = fields.Float('Horas de ausencia', compute='_compute_hours')
    departure_hours = fields.Float(
        'Horas de licencias', compute='_compute_hours')
    daytime_overtime = fields.Float(
        'Horas extras (diurna)', compute='_compute_hours')
    night_overtime = fields.Float(
        'Horas extras (nocturna)', compute='_compute_hours')
    holiday_overtime = fields.Float(
        'Horas extras (feriado)', compute='_compute_hours')
    # endregion

    # region FUNCTIONS
    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, _('%(name)s (%(date)s)') % {
                'name': rec.official_id.name,
                'date': rec.attendance_date_display,
            }))
        return result

    @api.model
    def create(self, vals):
        res = super(BM_OfficialAttendance, self).create(vals)
        # Registro el cambio
        res.official_id._register_change('Se creó la Asistencia %(name)s' % ({
            'name': res.attendance_date_display
        }))
        return res

    def write(self, vals):
        res = super(BM_OfficialAttendance, self).write(vals)
        self.update_movements()
        return res

    @api.returns('self', lambda value: value.id)
    def copy(self):
        raise exceptions.UserError(_('No se pueden duplicar las asistencias.'))

    def update_movements(self):
        """Actualiza los movimientos de salarios, asistencias y licencias"""
        self.journal_id.update_movements()
    # endregion


class BM_OfficialAttendanceDays(models.Model):
    _name = 'bm.official.attendance.days'
    _description = 'Asistencia del funcionario'
    _order = "day_date" 

    @api.onchange('time_date')
    def _onchange_time_date(self):
        time_date = self.time_date
        daily_hours = self.attendance_id.official_id.\
            schedules_ids.calculate_daily_hours(self.day_date.weekday())
        if time_date < 0 or time_date > daily_hours:
            time_date = daily_hours
        if self.reason in ['LT'] and time_date == daily_hours:
            self.reason = 'A'
            self.missed_reason = 'A'
        self.time_date = time_date

    @api.onchange('reason')
    def _onchange_reason(self):
        missed_reason = self.missed_reason
        time_date = 0
        if not missed_reason in ['L', 'U']:
            missed_reason = self.reason
            if self.reason in ['HED', 'HEN', 'HEF']:
                missed_reason = 'H'
            elif self.reason in ['A']:
                daily_hours = self.attendance_id.official_id.\
                    schedules_ids.calculate_daily_hours(self.day_date.weekday())
                time_date = daily_hours
        self.time_date = time_date
        self.missed_reason = missed_reason

    @api.onchange('day_date')
    def _onchange_day_date(self):
        # day_date
        day_date = self.day_date
        attendance_date = self.attendance_date
        if day_date and attendance_date:
            if day_date.month != attendance_date.month:
                # Change month of the actual attendance
                day_date = fields.Datetime.today().replace(
                    day=day_date.day,
                    month=attendance_date.month,
                    year=attendance_date.year)
        self.day_date = day_date

    attendance_id = fields.Many2one(
        'bm.official.attendance', 'Asistencia', ondelete='cascade', index=True)
    attendance_date = fields.Datetime(
        related='attendance_id.attendance_date', readonly=True)
    day_date = fields.Date(
        'Día', required=True, default=fields.Datetime.today().replace(day=1))
    time_date = fields.Float('Horas')
    reason = fields.Selection(
        REASONS_LIST, string='Razon')
    missed_reason = fields.Selection(
        MISSED_REASONS, string='Referencia')
    laboral = fields.Boolean('Dia Laboral')

    #_sql_constraints = [
    #    ('attendance_id_day_date_uniq', 'unique(attendance_id,day_date)',
    #     'No pueden haber 2 días repetidos en la misma asistencia'),
    #]

    def update_departures(self):
        # Si hay licencia, actualizo
        journal_id = self.attendance_id.journal_id
        for salary_id in journal_id.salary_ids:
            departure_id = salary_id.departure_id
            if departure_id:
                departure_id.check_departure_journal_attendance()

    def create(self, vals):
        res = super(BM_OfficialAttendanceDays, self)
        for rec in vals:
            if 'reason' in rec:
                rec['missed_reason'] = rec['reason']
                if rec['reason'] in ['HED', 'HEN', 'HEF']:
                    rec['missed_reason'] = 'H'
        res.create(vals)

    def write(self, vals):
        res = super(BM_OfficialAttendanceDays, self)
        if 'reason' in vals:
            vals['missed_reason'] = vals['reason']
            if vals['reason'] in ['HED', 'HEN', 'HEF']:
                vals['missed_reason'] = 'H'
        res.write(vals)

    """def unlink(self):
        res = super(BM_OfficialAttendanceDays, self)
        for rec in self:
            if rec.missed_reason == 'L':
                raise exceptions.UserError(
                    _('No se puede eliminar un registro de licencia, debe editarla para esto.'))
        res.unlink()"""


class BM_OfficialAttendanceInherit(models.Model):
    _inherit = 'bm.official'

    def _compute_hours_last_month(self):
        last_month = fields.Date.today().replace(day=1) - timedelta(days=-1)
        for off in self:
            att_hours = 0
            # for att in off.attendance_ids:
            #    if att.attendance_date.month == last_month.month:
            #        att_hours = att.worked_hours
            #    break

            off.hours_last_month = round(att_hours, 2)
            off.hours_last_month_display = '%g' % off.hours_last_month

    # region FIELDS
    attendance_ids = fields.One2many(
        'bm.official.attendance', 'id', help='list of attendances for the official')
    hours_last_month = fields.Float(compute='_compute_hours_last_month')
    hours_last_month_display = fields.Char(compute='_compute_hours_last_month')
    # endregion
