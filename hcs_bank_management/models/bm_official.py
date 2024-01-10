# -*- coding: utf-8 -*-
import base64
import re
from odoo import fields, models, exceptions, api, _
from odoo.modules.module import get_module_resource
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta

# region TYPES
IDENTIFICATION_TYPES = [
    ('1', 'CEDULA DE IDENTIDAD'), ('2', 'CREDENCIAL CIVICA'),
    ('3', 'R.U.C.'), ('4', 'PASAPORTE'),
    ('5', 'DNI-DOC.NAC.IDENTID.'), ('6', 'REGISTRO DE COMERCIO'),
    ('7', 'LIB.DE ENROLAMIENTO'), ('10', 'GARANTIA'),
    ('15', 'Entidades Públicas'), ('16', 'CARNET-INMIGRACIONES'),
    ('98', 'No Registra'), ('99', 'Inst. Financieras'),
    ('20', 'REPRES.DIPLOMATICAS')
]
GENDER = [
    ('M', 'Masculino'), ('F', 'Femenino')
]
MARITAL = [
    ('S', 'Soltero(a)'), ('C', 'Casado(a)'),
    ('D', 'Divorciado(a)'), ('V', 'Viudo(a)')
]
LEGAL_SITUATION = [
    ('C', 'Contratado'), ('F', 'Funcionario'),
]
CONTRACT_TYPE = [
    ('I', 'Contrato Por Tiempo Indefinido'), ('D', 'Contrato Por Tiempo Definido')
]
LIST_DAYWEEK = [
    ('0', 'Lunes'), ('1', 'Martes'),
    ('2', 'Miercoles'), ('3', 'Jueves'),
    ('4', 'Viernes'), ('5', 'Sabado'),
    ('6', 'Domingo')
]
LIST_HOUR = []
for t in range(0, 24):
    t = t if t > 9 else f"0{t}"
    LIST_HOUR.append((f"{t}:00", f"{t}:00"))
    LIST_HOUR.append((f"{t}:30", f"{t}:30"))

PAYMENT_MODE = [
    ('1', 'Banco'), ('2', 'Cuenta Corriente'),
    ('3', 'Caja de Ahorro')
]

ACCOUNT_STATUS = [
    ('1', 'Cuenta Activa'),
    ('2', 'Cuenta Inactiva'),
    ('3', 'Cuenta Cancelada'),
]

STATE = [
    ('draft', 'Borrador'), ('error', 'Revisar'),
    ('pending', 'Pendiente'), ('departured', 'Licencia'),
    ('ready', 'Listo')
]
# endregion


class BM_Official(models.Model):
    _name = 'bm.official'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Funcionarios'

    # region _DEFAULT_
    @api.model
    def _default_image(self):
        image_path = get_module_resource(
            'hcs_bank_management', 'static/src/img', 'default_image.png')
        return base64.b64encode(open(image_path, 'rb').read())

    @api.model
    def _default_country(self):
        return self.env['res.country'].search([('code_number', '=', '586')], limit=1).id
    # endregion

    # region COMPUTE
    @api.depends('department_id')
    def _compute_parent_id(self):
        for official in self.filtered('department_id.manager_id'):
            official.parent_id = official.department_id.manager_id

    @api.depends('departure_id', 'departure_id.state', 'departure_id.departure_reason')
    def _compute_departured(self):
        for rec in self:
            # Buscar el registro de salida más reciente con estado 'active' o 'archived'
            departured_reg = rec.departure_id.search([
                '&',
                ('official_id', '=', rec.id),
                ('state', 'in', ['active', 'archived'])
            ], order='id desc', limit=1)

            state = 'departured' if departured_reg else 'ready'
            departure_medical = False

            if departured_reg and departured_reg.departure_reason == 'medical':
                departure_medical = True

            values = {
                'departure_id': departured_reg.id if departured_reg else False,
                'departure_medical': departure_medical,
                'state': state
            }

            rec.write(values)

    @api.depends('job_id')
    def _compute_job_title(self):
        for official in self.filtered('job_id'):
            official.job_title = official.job_id.name

    @api.depends('name')
    @api.onchange('name_first', 'surname_first')
    def _compute_official(self):
        for official in self:
            # Nombre del funcionario
            _nombre = official.name_first or ''
            _apellido = official.surname_first or ''
            official.name = '{} {}'.format(_nombre.upper(), _apellido.upper())

    @api.depends('address_name')
    def _compute_address_name(self):
        for official in self:
            _address = []
            if official.state_id:
                _address.append(official.state_id.name)
            if official.location_id:
                _address.append(official.location_id.name)
            # Domicilio: Departamento + Localidad + Dirección.
            _dir = '%(street)s' % ({
                'street': official.street or ''
            })
            if (official.street2):
                _dir = '%(street)s %(street2)s' % ({
                    'street': official.street,
                    'street2': official.street2
                })
            if (official.house_no):
                _dir = '%(dir)s N°%(num)s' % ({
                    'dir': _dir,
                    'num': official.house_no
                })
            if _dir:
                _address.append(_dir)
            # Full direction
            official.address_name = ' + '.join(_address)
            # Compute Days
            self._compute_day_week()

    @api.depends('parent_id')
    def _compute_coach(self):
        for official in self:
            manager = official.parent_id
            previous_manager = official._origin.parent_id
            if manager and (official.coach_id == previous_manager or not official.coach_id):
                official.coach_id = manager
            elif not official.coach_id:
                official.coach_id = False

    @api.depends('family_ids')
    def _compute_family_childs(self):
        for official in self:
            official.family_childs = official.family_ids.search_count(
                ['&', ('official_id', '=', official.id), ('family_type', '=', 'child')])

    @api.depends('schedules_ids')
    def _compute_working_hours(self):
        for rec in self:
            working_hours = rec.schedules_ids.calculate_weekly_hours()
            rec.working_hours = '%(wh)s Horas semanales' % (
                {'wh': round(working_hours)})
            #hours = 0
            # for osch in official.schedules_ids:
            #    whf = datetime.strptime(osch.checkin, "%H:%M")
            #    whs = datetime.strptime(osch.checkout, "%H:%M")
            #    hours += ((whs - whf).seconds//3600 if osch.laboral else 0)

    @api.depends('vacation_right_date', 'admission_date', 'departure_id')
    def _compute_vacation_days(self):
        today = datetime.now().date()
        for rec in self:
            vacation_days = rec.vacation_days
            # if rec.state != 'departured':
            # Calcular la cantidad de años completos de antigüedad
            seniority_years = rec.get_official_seniority(today)

            # Calcular los días de vacaciones basados en la antigüedad
            if seniority_years < 5:
                vacation_days = 12
            elif seniority_years < 10:
                vacation_days = 18
            else:
                vacation_days = 30

            # Verifico los días de vacaciones disponibles del año actual
            departures = rec.departure_id.search([('departure_reason', '=', 'vacation')]).filtered(
                lambda d: d.departure_start.year == today.year)

            # Calculo los dias
            for dep in departures:
                dep_days = (dep.departure_end - dep.departure_start).days + 1
                vacation_days -= dep_days

            rec.vacation_days = vacation_days

    @api.depends('vacation_right_date')
    def _compute_vacation_right_date(self):
        for rec in self:
            rec.vacation_right_date = rec.admission_date + \
                relativedelta(years=1)
    # endregion

    # region DOMAINS
    @api.model
    def _domain_currency(self):
        ids = []
        if 'params' in self.env.context:
            if 'id' in self.env.context['params']:
                ids = self.browse(
                    self.env.context['params']['id']).company_id.currency_ids.ids
        return [('id', 'in', ids)]
    # endregion

    # region ONCHANGE
    @api.onchange('job_id')
    def _on_change_job_id(self):
        for official in self:
            official.profession_id = None
    # endregion

    # region CONSTRAINS
    @api.constrains('work_phone', 'particular_phone', 'mobile_phone')
    def constrains_phone(self):
        phoneRegex = '^[0-9]*$'
        phoneRegexExpl = [
            'Solo numeros del 0 al 9',
        ]
        # Constrains Phone
        message = None
        for rec in self:
            if (rec.work_phone):
                if not re.match(phoneRegex, rec.work_phone):
                    message = 'El campo \'{}\' no tiene un formato valido.\n{}'.format(
                        rec._fields['work_phone'].string, '\n - '.join(phoneRegexExpl))
                    break
            if (rec.particular_phone):
                if not re.match(phoneRegex, rec.particular_phone):
                    message = 'El campo \'{}\' no tiene un formato valido.\n{}'.format(
                        rec._fields['particular_phone'].string, '\n - '.join(phoneRegexExpl))
                    break
            if (rec.mobile_phone):
                if not re.match(phoneRegex, rec.mobile_phone):
                    message = 'El campo \'{}\' no tiene un formato valido.\n{}'.format(
                        rec._fields['mobile_phone'].string, '\n - '.join(phoneRegexExpl))
                    break
        if message:
            raise exceptions.Warning(message)

    @api.constrains('gross_salary')
    def constrains_gross_salary(self):
        for record in self:
            # Contrains campo salario bruto
            if (not record.gross_salary):
                raise exceptions.Warning(
                    'El campo Salario bruto debe ser mayor a 0')

    @api.constrains('employer_number')
    def constrains_employer_number(self):
        for record in self:
            if record.employer_number:
                if not record.employer_number.isdigit():
                    raise exceptions.Warning(
                        'El campo Numero Patronal debe ser solo números')

    # endregion

    # region FIELDS
    # region Basico
    name = fields.Char(string='Nombre Completo', compute='_compute_official')
    name_first = fields.Char('Nombre', size=20, required=True)
    surname_first = fields.Char('Apellido', size=20, required=True)
    gender = fields.Selection(GENDER, 'Sexo', default='M')
    marital = fields.Selection(MARITAL, string='Estado Civil', default='S')
    birthday = fields.Date('Fecha de nacimiento')
    country_birth_id = fields.Many2one('res.country', 'País de Nacimiento')
    state_birth_id = fields.Many2one(
        'res.country.state', 'Lugar de nacimiento', domain="[('country_id', '=?', country_birth_id)]")
    identification_id = fields.Char('Cédula de identidad')
    identification_type = fields.Selection(
        IDENTIFICATION_TYPES, string='Tipo de Cédula', default='1')
    identification_expiry = fields.Date('Vencimiento de Cédula')
    idenfitication_image_front = fields.Binary(
        string='Cédula de Identidad (Frente)', max_width=100, max_height=100)
    idenfitication_image_back = fields.Binary(
        string='Cédula de Identidad (Dorso)', max_width=100, max_height=100)
    # endregion
    # region Familia
    family_ids = fields.One2many(
        'bm.official.family', 'official_id', string='Familia del funcionario')
    family_childs = fields.Integer('Hijos', compute='_compute_family_childs')
    # endregion
    # region Contacto
    country_id = fields.Many2one(
        'res.country', 'Nacionalidad (País)', default=_default_country)
    state_id = fields.Many2one(
        'res.country.state', 'Departamento', domain="[('country_id', '=', country_id)]")
    location_id = fields.Many2one(
        'res.country.location', 'Localidad', domain="[('state_id', '=', state_id)]")
    neighborhood_id = fields.Many2one(
        'res.country.neighborhood', 'Barrio', domain="[('location_id', '=', location_id)]")
    zip = fields.Char('C. P.')
    house_no = fields.Char('Nro. Casa')
    street = fields.Char('Dirección')
    street2 = fields.Char('Dirección 2')
    address_name = fields.Char('Domicilio', compute="_compute_address_name")
    reference = fields.Char('Referencia')
    email = fields.Char('E-mail')
    work_phone = fields.Char('Teléfono Laboral')
    particular_phone = fields.Char('Teléfono particular')
    mobile_phone = fields.Char('Teléfono celular')
    # endregion
    # region Laboral
    legal_situation = fields.Selection(
        LEGAL_SITUATION, string='Situación Legal')
    employer_number = fields.Char('Numero Patronal')
    iscontract = fields.Boolean(string='Es Contratado', default=False)
    contract_type = fields.Selection(
        CONTRACT_TYPE, string='Tipo de Contrato', default='D')
    # , domain=_domain_currency
    currency_id = fields.Many2one('res.currency', string='Tipo de Moneda')

    schedules_ids = fields.One2many(
        'bm.official.schedules', 'official_id', string='Horarios de la empresa')
    working_hours = fields.Char(
        string='Horario de Trabajo', compute='_compute_working_hours')
    gross_salary = fields.Float('Salario Bruto')
    payment_mode = fields.Selection(
        PAYMENT_MODE, string='Forma de pago', default='1')
    admission_date = fields.Date('Fecha de ingreso')
    contract_end_date = fields.Date('Fecha de fin de contrato')
    department_id = fields.Many2one('bm.department', 'Departamento de la empresa',
                                    domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    job_id = fields.Many2one('bm.job', 'Cargo',
                             domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    profession_id = fields.Many2one('bm.job.profession', 'Profesión del funcionario',
                                    domain="[('job_id', '=', job_id)]")
    parent_id = fields.Many2one('bm.official', 'Gerente', compute="_compute_parent_id", store=True,
                                readonly=False, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    coach_id = fields.Many2one('bm.official', 'Supervisor', compute='_compute_coach', store=True, readonly=False,
                               domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                               help='Seleccione el \'funcionario\' que es el supervisor de este funcionario.\n'
                               'El \'Supervisor\' no tiene derechos o responsabilidades específicos por defecto.')
    unlinked = fields.Boolean('Desvinculado', default=False)
    departure_id = fields.Many2one(
        'bm.official.departure', 'Licencia', compute='_compute_departured')
    departure_medical = fields.Boolean(string='Licencia Medica', default=False)
    vacation_days = fields.Integer(
        string='Días de Vacaciones', compute='_compute_vacation_days', store=True)
    vacation_right_date = fields.Date(
        'Vacaciones a partir desde', compute='_compute_vacation_right_date')
    # endregion
    # region Cuenta
    account_registration = fields.Date(string="Fecha de Alta de cuenta")
    account_number = fields.Char(string="Número de la Cuenta", digits=(9))
    account_name = fields.Char(string="Descripción de la Cuenta", digits=(30))
    account_status = fields.Selection(
        ACCOUNT_STATUS, string="Estado de la Cuenta")
    # endregion
    # region Empresa
    company_id = fields.Many2one(
        'res.company', 'Nombre de la empresa', default=lambda self: self.env.company)
    official_sub_ids = fields.One2many(
        'bm.official', 'parent_id', string='Funcionarios a cargo')
    # endregion
    # region Extra
    image_1920 = fields.Image(default=_default_image)
    notes = fields.Text('Notas')
    color = fields.Integer(string='Color Index', default=0)
    active = fields.Boolean(string='Active', default=True)
    state = fields.Selection(STATE, string='Estado', default='draft')
    # endregion
    # endregion

    # region FUNCTIONS
    def show_message(self, title, message, *args):
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'res_model': 'bm.official.wizard',
            'view_mode': 'form',
            'context': {'default_message': message},
            'target': 'new'
        }

    def _compute_day_week(self):
        for rec in self:
            # Si no existiera el dia lo creo
            for day in LIST_DAYWEEK:
                found = False
                # Copio los dias tal cual esté en la empresa
                for osch in rec.schedules_ids.search([('official_id', '=', rec.id)]):
                    if osch.day_week == day[0]:
                        found = True
                if not found:
                    cday = rec.company_id.schedules_ids.search(
                        ['&', ('company_id', '=', rec.company_id.id), ('day_week', '=', day[0])])
                    rec.schedules_ids.create({
                        'official_id': rec.id,
                        'day_week': cday.day_week,
                        'checkin': cday.checkin,
                        'checkout': cday.checkout,
                        'laboral': cday.laboral,
                    })

    def _register_change(self, title, vals=[]):
        data = ''
        for rec in vals:
            if rec['value']:
                data += '%(field)s: %(value)s<br />' % ({
                    'field': rec['value'],
                    'value': rec['value']
                })
        body = title + "<br/>" + data
        self.message_post(body=body)

    def js_action_def(self, *args):
        official = self.env['bm.official'].sudo()
        for arg in args:
            arg['official_ids'] = official.search(
                [('company_id', 'in', arg['cids'])])
            official._create_journals(arg)

    def create_journal_wizard(self):
        """Open wizard create journal"""
        return {
            'name': _("Crear Sueldos y Jornales"),
            'context': self.env.context,
            'view_mode': 'form',
            'view_id': self.env.ref('hcs_bank_management.create_journal_wizard_form_view').id,
            'view_type': 'form',
            'res_model': 'bm.official.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def create_journal(self, selected_date):
        """ # Crear nuevos sueldos y salarios para el mes dado """
        journal_date = selected_date.replace(day=1)
        next_month = (selected_date + relativedelta(months=1)).replace(day=1)
        for rec in self:
            # Jornal del mes a crear
            journal = rec.journal_ids.search(['&',  ('journal_date', '>=', journal_date), (
                'journal_date', '<', next_month)], order='journal_date desc', limit=1)
            # Si no existe lo creo
            if not journal:
                journal = rec.journal_ids.sudo().create({
                    'official_id': rec.id,
                    'journal_date': journal_date,
                    'payment_date': selected_date,
                })

            # attendance = rec.attendance_ids.search(['&', '&', ('journal_id', '=', journal.id),
            #                                        ('attendance_date', '>=', journal_date),
            #                                        ('attendance_date', '<', next_month)], order='attendance_date desc', limit=1)

            # Si no existe la asistencia del journal, lo creo
            if not journal.attendance_id:
                # Creo la asistencia del mes y la asocio  al jornal recien creado
                journal.attendance_id = rec.attendance_ids.sudo().create({
                    'journal_id': journal.id,
                    'attendance_date': journal_date,
                })
                # Asocio la asistencia al journal
                #journal.attendance_id = attendance.id
                # Computo las horas trabajadas
                #journal.attendance_id._compute_worked_hours()

    def get_official_seniority(self, date=None):
        if not date:
            return 0
        # Calcula la antigüedad en años
        seniority_months = (date - self.admission_date).days // 30
        seniority_years = seniority_months // 12
        return seniority_years

    # endregion


class BM_ResCompanySchedules(models.Model):
    _name = 'bm.official.schedules'
    _description = 'Horarios del funcionario'

    official_id = fields.Many2one(
        'bm.official', 'Nombre del funcionario', ondelete='cascade', index=True)
    day_week = fields.Selection(
        LIST_DAYWEEK, 'Día', required=True)
    checkin = fields.Selection(
        LIST_HOUR, 'Hora inicio', default='07:30', required=True)
    checkout = fields.Selection(
        LIST_HOUR, 'Hora fin', default='17:30', required=True)
    laboral = fields.Boolean('Dia Laboral', default=True, required=True)

    def calculate_daily_hours(self, weekday=-1):
        if weekday < 0:
            return 0

        daily_hours = 0
        for rec in self:
            if int(rec.day_week) == weekday:
                checkin_hour, checkin_minute = map(int, rec.checkin.split(":"))
                checkout_hour, checkout_minute = map(
                    int, rec.checkout.split(":"))
                daily_hours = (checkout_hour - checkin_hour) + \
                    (checkout_minute - checkin_minute) / 60 if rec.laboral else 0
                break
        return daily_hours

    def calculate_weekly_hours(self):
        weekly_hours = 0
        for rec in self:
            if rec.laboral:
                checkin_hour, checkin_minute = map(int, rec.checkin.split(":"))
                checkout_hour, checkout_minute = map(
                    int, rec.checkout.split(":"))
                daily_hours = (checkout_hour - checkin_hour) + \
                    (checkout_minute - checkin_minute) / 60
                weekly_hours += daily_hours
        return round(weekly_hours)

    def calculate_worked_hours(self):
        weekly_hours = self.calculate_weekly_hours()
        return int((weekly_hours / 6) * 30)
