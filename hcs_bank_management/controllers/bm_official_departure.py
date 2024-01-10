from odoo import http
from odoo.addons.web.controllers.main import serialize_exception
import locale
import logging
import tempfile


# Change locale to display month in spanish
locale.setlocale(locale.LC_TIME, 'es_US.UTF-8')

_logger = logging.getLogger(__name__)


class BMOfficialDepartureController(http.Controller):

    @http.route('/web/binary/download_departure_resignation_report', type='http', auth="user")
    @serialize_exception
    def download_departure_resignation_report(self, model, id, returnpdf=False, **kw):
        """ Download link for files stored as binary fields.
        :param str model: name of the model to fetch the binary from
        :param str active_ids: ids of the record from which to fetch the binary
        :param str filename: field holding the file's name, if any
        :returns: :class:`werkzeug.wrappers.Response`
        """
        report = http.request.env.ref(
            'hcs_bank_management.bm_official_departure_resignation_report')
        pdf_report = report.sudo().render_qweb_pdf(id)[0]
        pdf_title = '%(cname)s - %(filename)s.pdf' % ({
            'cname': model.official_id.name,
            'filename': 'Comunicacion de rescision'
        })

        # Genero el PDF
        tmp_pdf = tempfile.TemporaryFile()
        tmp_pdf.write(pdf_report)
        tmp_pdf.seek(0)
        pdf_file = tmp_pdf.read()
        tmp_pdf.close()
        if returnpdf:
            return {
                'title': pdf_title,
                'file': pdf_file
            }
        else:
            return http.request.make_response(pdf_file, headers=[
                ('Content-Type', 'application/pdf'), ('Content-Length', len(pdf_file)),
                ('Content-Disposition', 'attachment; filename="%(title)s"' %
                 ({'title': pdf_title}))
            ])




    """def download_departure_resignation_report(self, model, id, filename=None, returnpdf=False, **kw):
        "" Download link for files stored as binary fields.
        :param str model: name of the model to fetch the binary from
        :param str active_ids: ids of the record from which to fetch the binary
        :param str filename: field holding the file's name, if any
        :returns: :class:`werkzeug.wrappers.Response`
        ""
        model = http.request.env[model].browse(int(id))

        # Al momento de generar el despido
        # se debe generar o actualizar el ultimo
        # Jornal del funcionario para obtener
        # Los dias trabajados de ese mes
        # Luego se calcula los ultimos 6
        # o menos meses de aguinaldo
        #
        # Tambien se deberia calcular las
        # vacaiones proporcionales pero se deberia
        # obtener las vacaciones pendientes
        # de algun lado para esto.
        # Busco los jornales del funcionario
        journal_model = http.request.env['bm.official.journal']
        journal_model = journal_model.search(['&',
                                              ('official_id', '=',
                                               model.official_id.id),
                                              ('journal_date', '=', model.departure_start.replace(day=1))], limit=1)

        # Dias trabajados se fija a 30
        days_worked = 30
        # Salario del funcionario, dividido 30 dias
        gross_salary_per_day = model.official_gross_salary / days_worked
        # Calculo la asistencia del mes
        worked_days_amount = round(
            journal_model.attendance_worked_days * gross_salary_per_day, 2)
        # Aguinaldo
        extra_salary = model.salary_bonus_amount
        extra_salary_ref = model.salary_bonus or "Aguinaldo"
        # Vacaciones
        vacation_amount = model.total_amount
        # Descuento del I.P.S.
        ips = model.official_id.company_id.ips_worker_contribution
        ips_amount = journal_model.ips_amount
        # Total
        total_payment = worked_days_amount + extra_salary + vacation_amount
        total_to_pay = round(total_payment - ips_amount, 2)
        total_to_pay_letter = journal_model.numero_a_letras(total_to_pay)

        data = {
            'antique': self.calculate_age(model.official_id.admission_date, model.departure_start),
            'gross_salary_per_day': round(gross_salary_per_day, 2),
            'worked_days': journal_model.attendance_worked_days,
            'worked_days_amount': round(worked_days_amount, 2),
            'extra_salary': round(extra_salary, 2),
            'extra_salary_ref': extra_salary_ref,
            'vacation_amount': round(vacation_amount, 2),
            'ips': ips,
            'ips_amount': round(ips_amount, 2),
            'total_payment': round(total_payment, 2),
            'total_to_pay': round(total_to_pay, 2),
            'total_to_pay_letter': total_to_pay_letter
        }

        report = http.request.env.ref(
            'hcs_bank_management.bm_official_departure_resignation_report')
        pdf_report = report.sudo().render_qweb_pdf(model.id, data=data)[0]
        pdf_title = '%(cname)s - %(filename)s.pdf' % ({
            'cname': model.official_id.name,
            'filename': filename
        })

        # Genero el PDF
        tmp_pdf = tempfile.TemporaryFile()
        tmp_pdf.write(pdf_report)
        tmp_pdf.seek(0)
        pdf_file = tmp_pdf.read()
        tmp_pdf.close()
        if returnpdf:
            return {
                'title': pdf_title,
                'file': pdf_file
            }
        else:
            return http.request.make_response(pdf_file, headers=[
                ('Content-Type', 'application/pdf'), ('Content-Length', len(pdf_file)),
                ('Content-Disposition', 'attachment; filename="%(title)s"' %
                 ({'title': pdf_title}))
            ])
            """

    def calculate_age(self, first_date, second_date):
        if not first_date:
            return ''
        year = second_date.year - first_date.year - \
            ((second_date.month, second_date.day)
             < (first_date.month, first_date.day))
        return '%(a)s %(b)s' % {
            'a': year,
            'b': 'Año' if year == 1 else 'Años'
        }

    def array_index(self, array, search):
        for i, tupple in enumerate(array):
            for value in tupple:
                if value == search:
                    return i
        return -1
