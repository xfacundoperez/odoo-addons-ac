# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

DEPARTURE_REASONS = [
    ('fired', 'Despido'),
    ('extra', 'Extra'),
    ('medical', 'Medica'),
    ('resigned', 'Renuncia'),
    ('retired', 'Retirado'),
    ('vacation', 'Vacaciones')
]
STATE = [
    ('active', 'Activo'),
    ('finish', 'Finalizado')
]


class BM_OfficialDeparture(models.Model):
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
        import locale
        # Change locale to display month in spanish
        locale.setlocale(locale.LC_TIME, 'es_US.UTF-8')
        for rec in self:
            rec.auxiliar_code = '%(month)s%(gross)s' % ({
                'month': fields.Datetime.now().strftime("%B"),
                'gross': int(rec.official_id.gross_salary) or ''
            })

    @api.depends('official_id', 'departure_reason', 'departure_end')
    def _compute_departured(self):
        for official_departure in self:
            official_departure.name = '#{}: {}'.format(official_departure.id, dict(
                DEPARTURE_REASONS)[official_departure.departure_reason])

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

    @api.depends('departure_start', 'departure_end', 'departure_reason')
    def _compute_remuneration(self):
        for rec in self:
            qty = 0
            if rec.departure_end and rec.departure_reason in ['vacation']:
                delta = rec.departure_end - rec.departure_start
                if delta.days > 0:
                    qty = delta.days * (rec.official_id.gross_salary / 30)
            rec.remuneration = float("{:.2f}".format(qty))

    @api.onchange('departure_end', 'official_id')
    def _onchange_departure_end(self):
        for rec in self:
            # Fix departure end
            if rec.departure_start and rec.departure_end:
                if rec.departure_end < rec.departure_start:
                    rec.departure_end = rec.departure_start
        self._compute_remuneration()

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
    name = fields.Char(compute='_compute_departured')
    official_id = fields.Many2one(
        'bm.official', 'Funcionario', ondelete='cascade', index=True, required=True, default=_default_official)
    official_identification_id = fields.Char(
        string='Nº identificación', related='official_id.identification_id', readonly=True)
    official_gross_salary = fields.Float(
        string='Salario Bruto', related='official_id.gross_salary', readonly=True)
    official_iscontract = fields.Boolean(
        related='official_id.iscontract', readonly=True)
    departure_reason = fields.Selection(
        DEPARTURE_REASONS, string='Motivo de salida', copy=False, tracking=True, required=True, default='medical')
    departure_description = fields.Text(
        string='Salida: Información adicional', copy=False, tracking=True)
    departure_start = fields.Date(
        string='Fecha de Salida', default=lambda self: fields.Date.today(), copy=False, required=True)
    payment_date = fields.Date(
        string='Fecha de Cobro', default=lambda self: fields.Date.today(), copy=False, required=True)
    departure_end = fields.Date(string='Fecha de Retorno', copy=False)
    auxiliar_code = fields.Char(
        'Codigo Auxiliar', compute='_compute_auxiliar_code', store=True)
    remuneration = fields.Float('Remuneracion', compute='_compute_remuneration', store=True, readonly=False)
    state = fields.Selection(STATE, string='Estado', default='active')
    # endregion

    # region FUNCTIONS
    @api.model
    def create(self, vals):
        rec = super(BM_OfficialDeparture, self)
        if 'active_id' in self._context:
            vals['official_id'] = self._context['active_id']
        # Obtengo el ultimo registro activo del funcionario
        if self.search(['&', ('official_id', '=', vals['official_id']),
                        ('state', '=', 'active')], limit=1):
            raise exceptions.UserError(
                _('Ya existe una licencia activa para este funcionario.'))
        # Chequeo que la licencia esté activa
        dep_end = datetime.strptime(
            vals['departure_end'], '%Y-%m-%d').date()
        if dep_end < fields.Date.today():
            vals['state'] = 'finish'
        # Registra el cambio
        official = self.official_id.browse(vals['official_id'])
        if vals['state'] == 'active':
            official.state = 'departured'
        official._register_change('Se creó una licencia de tipo %(reason)s' % ({
            'reason': dict(DEPARTURE_REASONS)[vals['departure_reason']]
        }))
        # Creo la licencia
        departure = rec.create(vals)
        # Checkeo las Asistencias, Sueldos y Jornales
        self.check_departure_journal_attendance(departure)
        # Finalizo la creación
        return departure

    def write(self, vals):
        res = super(BM_OfficialDeparture, self)
        for rec in self:
            if vals['state'] == 'finish':
                rec.official_id.state = 'ready'
                rec.official_id._register_change('Finalizó la licencia #%(id)s %(reason)s' % ({
                    'id': rec.id,
                    'reason': dict(DEPARTURE_REASONS)[rec.departure_reason]
                }))
        return res.write(vals)

    def unlink(self):
        res = super(BM_OfficialDeparture, self)
        for rec in self:
            data = ''
            if rec.departure_description:
                data += '%(field)s: %(value)s<br />'  % ({
                    'field': self._fields['departure_description'].string,
                    'value': rec.departure_description
                })
            data += '%(field)s: %(value)s<br />'  % ({
                'field': self._fields['departure_reason'].string,
                'value': dict(DEPARTURE_REASONS)[rec.departure_reason]
            })
            data += '%(field)s: %(value)s<br />'  % ({
                'field': self._fields['departure_start'].string,
                'value': rec.departure_start
            })
            if rec.departure_end:
                data += '%(field)s: %(value)s<br />'  % ({
                    'field': self._fields['departure_end'].string,
                    'value': rec.departure_end
                })
            data += '%(field)s: %(value)s<br />'  % ({
                'field': self._fields['remuneration'].string,
                'value': rec.remuneration
            })
            data += '%(field)s: %(value)s<br />'  % ({
                'field': self._fields['state'].string,
                'value': dict(STATE)[rec.state]
            })
            rec.official_id.state = 'ready'
            rec.official_id._register_change('%(user)s eliminó la licencia %(name)s:<br />%(data)s' % ({
                'user': self.env.user.name,
                'name': rec.name,
                'data': data
            }))
        return res.unlink()
        #raise exceptions.UserError(_('No se pueden eliminar las licencias.'))

    @api.returns('self', lambda value: value.id)
    def copy(self):
        raise exceptions.UserError(_('No se pueden duplicar las licencias.'))

    def check_departure_journal_attendance(self, departure):
        # Busco el jornal correspondiente a la fecha de la licencia
        dep_month = departure.departure_start.replace(day=1)
        journal = departure.official_id.journal_ids.search([
            '&', ('official_id', '=', departure.official_id.id),
            ('journal_date', '=', dep_month)])
        # Si no existe el journal, lo creo
        if not journal:
            journal = departure.official_id._create_journals({
                'official_ids': departure.official_id,
                'month': dep_month.month,
                'return': True
            })
        # Busco la licencia dentro de los registros de salario
        found_dep = False
        for salary in journal.salary_ids:
            if salary.departure_id == departure.id:
                found_dep = True
                break
        # Si no la encuentra el registro, la crea
        if not found_dep:
            journal.salary_ids.create({
                'journal_id': journal.id,
                'charge_type': '5', # Pago de licencia
                'departure_id': departure.id,
                'amount_to_pay': departure.remuneration,
                'payment_date': departure.payment_date
            })
        # Agrego las ausencias al registro de asistencia del mes
        delta = departure.departure_end - departure.departure_start        
        # Por cada día entre las fechas de licencia
        # verifico que existan dentro de los dias de la misma
        for d in range(delta.days + 1):
            found_date = False
            _day = departure.departure_start + timedelta(days=d)
            # Busco dentro de los dias ya cargados si existe
            for att_date in journal.attendance_id.days_ids:
                if _day == att_date.day_date:
                    found_date = True
                    break
            # Si no existe, lo agrego
            if not found_date:
                _missed_reason = 'A' # Ausente
                if departure.departure_reason == 'vacation':
                    _missed_reason = 'V' # Vacaciones
                if _day.weekday() == 6: # 6 = domingo
                    _missed_reason = 'D' # Domingo
                journal.attendance_id.days_ids.create({
                    'attendance_id': journal.attendance_id.id,
                    'day_date': _day,
                    'missed_reason': _missed_reason
                })

    def button_save(self):
        return self.env['bm.official.departure'].sudo().create({
            'official_id': self.env.context.get('active_id'),
            'departure_reason': self.departure_reason,
            'departure_description': self.departure_description,
            'remuneration': self.remuneration,
            'departure_start': self.departure_start,
            'departure_end': self.departure_end,
        })

    def check_departure_end(self):
        for rec in self.search([('state', '=', 'active')]):
            if rec.departure_reason in ['medical', 'extra', 'vacation']:
                # if departure_end is less from today, means is not departured
                if rec.departure_end < fields.Datetime.now().date():
                    rec.state = 'finish'

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

    # endregion
