# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _
from datetime import datetime, timedelta
import calendar
import locale
# Change locale to display month in spanish
locale.setlocale(locale.LC_TIME, 'es_US.UTF-8')

REASONS = [
    ('A', 'Ausente'),
    ('D', 'Domingo'),
    ('F', 'Feriado'),
    ('V', 'Vacaciones')
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

    @api.depends('attendance_date', 'days_ids')
    def _compute_woked(self):
        for rec in self:
            # Fecha de la asistencia cambiando el día a 1
            now = rec.attendance_date.replace(day=1)
            # Total de dias en el mes
            days_in_month = calendar.monthrange(now.year, now.month)[1]
            # Dias trabajados se fija a 30
            days_worked = 30
            # Total de horas trabajadas
            hours = 0
            #import wdb
            #wdb.set_trace()
            # Por cada dia, verifico que sea un dia laboral
            for dr in range(1, days_in_month + 1):
                daydate = now.replace(day=dr).date()
                # Verifico que no tenga ausencia
                missed = False
                for day in rec.days_ids.search(['&', ('attendance_id', '=', rec.id), ('day_date', '=', daydate)]):
                    if day.missed_reason not in ['D', 'F']:
                        days_worked -= 1
                        missed = True
                # Si el dia posee ausencia, continuo al siguiente
                if missed:
                    continue
                # Obtengo el dia de la semana
                weekday = now.replace(day=dr).weekday()
                # Calculo las horas trabajadas ese dia
                for osch in rec.journal_id.official_id.schedules_ids:
                    if int(osch.day_week) == weekday:
                        whf = datetime.strptime(osch.wh_first, "%H:%M")
                        whs = datetime.strptime(osch.wh_second, "%H:%M")
                        hours += ((whs - whf).seconds //
                                  3600 if osch.laboral else 0)

            # Dias trabajados
            rec.worked_days = days_worked
            # Horas totales trabajadas
            rec.worked_hours = hours

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
        'bm.official.attendance.days', 'attendance_id', string='Registro de ausencias')
    worked_days = fields.Integer('Días Trabajados', compute='_compute_woked')
    worked_hours = fields.Integer('Horas de Trabajo', readonly=True)
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
        for rec in res:
            # Fecha de la asistencia cambiando el día a 1
            now = rec.attendance_date.replace(day=1)
            # Obtengo el primer domingo del mes
            sunday = now + timedelta(days=(6 - now.weekday()))
            # Por cada domingo del mes actual,
            # busco dentro de los días si existe
            while sunday.month == now.month:
                if not rec.days_ids.search(['&', ('attendance_id', '=', rec.id), ('day_date', '=', sunday)]):
                    rec.days_ids.create({
                        'attendance_id': rec.id,
                        'day_date': sunday,
                        'missed_reason': 'D'
                    })
                sunday += timedelta(days=7)
        return res

    @api.returns('self', lambda value: value.id)
    def copy(self):
        raise exceptions.UserError(_('No se pueden duplicar las asistencias.'))

    # endregion


class BM_OfficialAttendanceDays(models.Model):
    _name = 'bm.official.attendance.days'
    _description = 'Asistencia del funcionario'

    # region ONCHANGE
    @api.onchange('day_date')
    def _onchange_day_date(self):
        if self.day_date and self.attendance_date:
            # Check selected day is in month
            if self.day_date.month != self.attendance_date.month:
                self.day_date = False
                raise exceptions.UserError(
                    _('No se puede elegir una fecha diferente al mes de la asistencia'))
            # Check selected day is sunday
            if self.day_date.weekday() == 6:  # Monday is 0 and Sunday is 6.
                self.missed_reason = 'D'
            else:
                self.missed_reason = 'A'
    # endregion

    # region FIELDS
    attendance_id = fields.Many2one(
        'bm.official.attendance', 'Asistencia', ondelete='cascade', index=True)
    attendance_date = fields.Datetime(
        related='attendance_id.attendance_date', readonly=True)
    day_date = fields.Date(
        'Día', required=True)
    missed_reason = fields.Selection(
        REASONS, string='Motivo de ausencia', default='A', required=True)
    # endregion

    _sql_constraints = [
        ('attendance_id_day_date_uniq', 'unique(attendance_id,day_date)',
         'No pueden haber 2 días repetidos en la misma asistencia'),
    ]


class BM_OfficialAttendanceInherit(models.Model):
    _inherit = 'bm.official'

    # region COMPUTE
    def _compute_hours_last_month(self):
        last_month = fields.Date.today().replace(day=1) - timedelta(days=-1)
        for off in self:
            att_hours = 0
            for att in off.attendance_ids:
                if att.attendance_date.month == last_month.month:
                    att_hours = att.worked_hours
                break

            off.hours_last_month = round(att_hours, 2)
            off.hours_last_month_display = '%g' % off.hours_last_month
    # endregion

    # region FIELDS
    attendance_ids = fields.One2many(
        'bm.official.attendance', 'id', help='list of attendances for the official')
    hours_last_month = fields.Float(compute='_compute_hours_last_month')
    hours_last_month_display = fields.Char(compute='_compute_hours_last_month')
    # endregion
