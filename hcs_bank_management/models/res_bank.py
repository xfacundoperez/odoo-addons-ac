from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval

FIELD_TYPE_EXCLUDED = ['binary', 'html', 'many2many', 'many2one',
                       'many2one_reference', 'monetary', 'one2many', 'reference', 'selection']
# retrieve field types defined by the framework only (not extensions)
FIELD_TYPES = [(key, _(key.capitalize()))for key in sorted(
    fields.Field.by_type) if key not in FIELD_TYPE_EXCLUDED]
AVAILABLE_MODELS = ['bm.official', 'bm.official.attendance',
                    'bm.official.family', 'bm.official.journal',
                    'bm.official.journal.salary', 'res.company']


class BM_ResBank(models.Model):
    _inherit = 'res.bank'

    format_txt = fields.Text('Formato del archivo TXT')
    format_id = fields.Many2one(
        'res.bank.format', string='Formato del archivo TXT', required=True, ondelete='cascade', index=True)


class BM_ResBankFormat(models.Model):
    _name = 'res.bank.format'
    _description = 'Formato del archivo TXT'

    bank_id = fields.Many2one(
        'res.bank', 'Banco', ondelete='cascade', index=True)
    title = fields.Char('Titulo del archivo', required=True)
    field_ids = fields.One2many(
        'res.bank.format.fields', 'format_id', string='Campos')
    format_code = fields.Text('Código Python')
    result = fields.Text(string='Resultado')
    function_name = fields.Char('Nombre de la funcion')

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, '#%s %s' % (rec.id, rec.bank_id.name)))
        return result

    def action_execute(self):
        try:
            if self.model_id:
                model = self.env[self.model_id.model]
            else:
                model = self
            if self.code:
                self.result = safe_eval(self.format_code.strip(), {
                                        'self': model}, mode='eval')
        except Exception as e:
            self.result = str(e)


class BM_ResBankFormatFields(models.Model):
    _name = 'res.bank.format.fields'
    _description = 'Campos del formato del archivo TXT'
    _rec_name = 'name'

    def _domain_field_id(self):
        return [('model', 'in', AVAILABLE_MODELS)]

    format_id = fields.Many2one(
        'res.bank.format', 'Formato', ondelete='cascade', index=True)
    field_id = fields.Many2one('ir.model.fields', string='Campo relacionado',
                               help='Campo desde donde obtiene el dato a mostrar',
                               domain=_domain_field_id, ondelete='cascade', index=True)
    name = fields.Char('Nombre', required=True)
    ttype = fields.Selection(selection=FIELD_TYPES,
                             string='Tipo', required=True)
    size = fields.Integer('Tamaño', default=0)
    decimal_size = fields.Integer('Decimales', default=0)
    format = fields.Char('Formato')
    isreq = fields.Boolean('Requerido', default=False)
    desc = fields.Text('Descripción')
    selection_ids = fields.One2many('res.bank.format.fields.selection',
                                    'format_field_id', string='Valores',
                                    domain="[('format_field_id', '=?', format_id)]")


class BM_ResBankFormatFieldsSelection(models.Model):
    _name = 'res.bank.format.fields.selection'
    _description = 'Seleccion del campo del formato del archivo TXT'

    def _domain_field_id(self):
        return [('model', 'in', AVAILABLE_MODELS)]

    format_field_id = fields.Many2one('res.bank.format.fields',
                                      'Campo del formato', ondelete='cascade', index=True)
    field_id = fields.Many2one('ir.model.fields', string="Campo relacionado", related='format_field_id.field_id',
                               help='Campo desde donde obtiene el dato a mostrar')
    key = fields.Char('Clave')
    name = fields.Char('Nombre')
    domain_rule = fields.Text('Definicion de regla', help='Se debe definir cuando se aplica la regla', default="field_id='VALOR'")
    desc = fields.Text('Descripción')

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, '%s, %s' % (rec.key, rec.name)))
        return result
