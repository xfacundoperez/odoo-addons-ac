from odoo import models, fields, api, exceptions, _

LIST_YEARS = [(str(y), str(y))
              for y in range(1900, (fields.Datetime.now().year + 30)+1)]

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


class BM_ResCompany(models.Model):
    _inherit = 'res.company'

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
                'street': official.street or None
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
            # Compute days
            self._compute_day_week()

    exploitation = fields.Char(
        string='Explotación', required=True)
    years = fields.Selection(
        LIST_YEARS, string='Año', default=str(fields.Datetime.now().year))
    ips_worker_contribution = fields.Integer('Aporte Obrero IPS (%)')
    employer_registration_number = fields.Integer('Nro. Registro Patronal:')
    currency_ids = fields.Many2many('res.currency', 'company_allowed_currency_rel', 'id',
                                    string='Monedas permitidas', store=True)
    # region ACCOUNT
    company_code = fields.Char(
        'Código de la Empresa')
    debit_account = fields.Char('Cuenta Debito')
    credit_account = fields.Char('Cuenta Crédito')
    # endregion
    # region ADDRESS
    address_name = fields.Char('Domicilio', compute="_compute_address_name")
    state_id = fields.Many2one(
        'res.country.state', 'Departamento', domain="[('country_id', '=', country_id)]")
    location_id = fields.Many2one(
        'res.country.location', 'Localidad', domain="[('state_id', '=', state_id)]")
    neighborhood_id = fields.Many2one(
        'res.country.neighborhood', 'Barrio', domain="[('location_id', '=', location_id)]")
    house_no = fields.Char('Nro. Casa')
    street = fields.Char('Dirección')
    street2 = fields.Char('Dirección 2')
    reference = fields.Char('Referencia')
    # endregion
    # region SCHEDULES
    schedules_ids = fields.One2many(
        'bm.res.company.schedules', 'company_id', string='Horarios de la empresa')
    # endregion

    _sql_constraints = []

    # region FUNCTION
    def _compute_day_week(self):
        for day in LIST_DAYWEEK:
            found = False
            laboral = True
            if int(day[0]) > 4:
                laboral = False
            for rec in self.schedules_ids.search([('company_id', '=', self.id)]):
                if rec.day_week == day[0]:
                    found = True
            if not found:
                rec  = self.schedules_ids.create({
                    'company_id': self.id,
                    'day_week': day[0],
                    'laboral': laboral
                })
   # endregion

class BM_ResCompanySchedules(models.Model):
    _name = 'bm.res.company.schedules'
    _description = 'Horarios de la empresa'

    company_id = fields.Many2one(
        'res.company', 'Nombre de la Empresa', ondelete='cascade', index=True)
    day_week = fields.Selection(
        LIST_DAYWEEK, 'Día', required=True)
    wh_first = fields.Selection(
        LIST_HOUR, 'Hora inicio', default='07:30', required=True)
    wh_second = fields.Selection(
        LIST_HOUR, 'Hora fin', default='17:30', required=True)
    laboral = fields.Boolean('Dia Laboral', default=True, required=True)
