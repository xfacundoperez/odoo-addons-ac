from odoo import http
from odoo.addons.web.controllers.main import serialize_exception, content_disposition
from odoo.modules.module import get_module_resource
from . import format_bank, format_file
import base64
import locale
import logging
import tempfile
import zipfile
import io

# Change locale to display month in spanish 
locale.setlocale(locale.LC_TIME, 'es_US.UTF-8')

_logger = logging.getLogger(__name__)

IMAGES = [
    ('gnpy', base64.b64encode(open(get_module_resource(
        'hcs_bm_ecovis', 'static/src/img', 'gnpy.png'), 'rb').read())),
    ('mtess', base64.b64encode(open(get_module_resource(
        'hcs_bm_ecovis', 'static/src/img', 'mtess.png'), 'rb').read()))
]


class BM_ControllerMain(http.Controller):

    @http.route('/web/binary/download_journal_report', type='http', auth="user")
    @serialize_exception
    def download_journal_report(self, model, active_ids, filename=None, **kw):
        """Download link for files stored as binary fields.
        :param str model: name of the model to fetch the binary from
        :param list active_ids: list of IDs of the records from which to fetch the binary
        :param str filename: field holding the file's name, if any
        :returns: :class:`werkzeug.wrappers.Response`
        """
        journals = http.request.env[model].search(
            [('id', 'in', active_ids.split(','))])

        # Group records by company and period
        companies = {}
        for journal in journals:
            company = journal['company_id']
            company_id = company['id']
            period = journal['journal_date_display']
            # dias trabajados
            #days_worked = [d for d in range(1, 31)]
            # Obtengo el recibo en PDF del funcionario
            #official_pdf = self.download_official_recipe(
            #    model, journal['id'], 'Recibo', returnpdf=True)
            official_pdf = None
            # Agrego la empresa a la lista
            if company_id not in companies:
                companies[company_id] = {
                    'company': company,
                    'periods':  [(period, [journal])],
                    'recipes': []
                }
                if official_pdf:
                    companies[company_id]['recipes'].append(official_pdf)
            else:
                # Busco que el periodo dentro de 'periods'
                pidx = self.array_index(
                    companies[company_id]['periods'], period)
                if not pidx >= 0:
                    companies[company_id]['periods'].append(
                        (period, [journal]))
                else:
                    companies[company_id]['periods'][pidx][1].append(journal)
                # Agrego el recibo en PDF del funcionario a la lista
                if official_pdf:
                    companies[company_id]['recipes'].append(official_pdf)

        # Ordeno los periodos por Año y Mes
        for idx, company in companies.items():
            companies[idx]['periods'] = sorted(company['periods'], key=lambda p: self.sort_period(p))

        # Genero los pdfs por cada compania
        #companies_pdf = format_file.generate_companies_pdf(companies, dict(IMAGES), filename)
        companies_pdf = []

        # Genero los excels por cada compania
        companies_xls = format_file.generate_companies_xls(companies, dict(IMAGES), filename)

        # Create ZIP file
        zip_filename = "%(fn)s.zip" % ({
            'fn': filename
        })
        bitIO = io.BytesIO()

        with zipfile.ZipFile(bitIO, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            for cid, data in companies.items():
                company = data['company']
                # Write PDFs for each company
                for pdf in companies_pdf:
                    pdf_name = f'{company["name"]}/{pdf["title"]}'
                    zf.writestr(pdf_name, pdf['file'])
                # Write XLSs for each company
                for xls in companies_xls:
                    xls_name = f'{company["name"]}/{xls["title"]}'
                    zf.writestr(xls_name, xls['file'])
                # Write official PDFs for each official
                for pdf in data['recipes']:
                    pdf_name = f'{company["name"]}/recibos/{pdf["title"]}'
                    zf.writestr(pdf_name, pdf['file'])

        # Return ZIP file
        headers = [('Content-Type', 'application/x-zip-compressed'),
                   ('Content-Disposition', f'attachment; filename="{zip_filename}"')]
        return http.request.make_response(bitIO.getvalue(), headers=headers)

    def sort_period(self, period):
        month_str, year_str = period[0].split('/')
        month = {
            'enero': 1,
            'febrero': 2,
            'marzo': 3,
            'abril': 4,
            'mayo': 5,
            'junio': 6,
            'julio': 7,
            'agosto': 8,
            'septiembre': 9,
            'octubre': 10,
            'noviembre': 11,
            'diciembre': 12
        }[month_str.lower()]
        return int(year_str), month

    @http.route('/web/binary/download_journal_txt', type='http', auth="user")
    @serialize_exception
    def download_journal_txt(self, model, uid, active_ids, format_id, **kw):
        """ Download link for files stored as binary fields.
        :param str model: name of the model to fetch the binary from
        :param str uid: id of the user who action
        :param str active_ids: ids of the record from which to fetch the binary
        :param str filename: field holding the file's name, if any
        :param str format_id: id of the format to use
        :returns: :class:`werkzeug.wrappers.Response`
        """
        ids = [int(id) for id in active_ids.split(',')]

        companies = []
        # Ordeno los Sueldos y Jornales por empresa
        for journal in http.request.env[model].search([('id', 'in', ids)]):
            cid = journal.company_id.id
            # Busco la empresa
            cidx = self.array_index(companies, cid)
            # Periodo
            period = journal.journal_date_display
            # Journal ID
            jid = journal.id
            if not cidx >= 0:
                companies.append((cid, {
                    'periods': [{
                        period: [jid],
                        'txt': False
                    }],
                }))
            else:
                # Busco que el periodo exista
                period_idx = self.array_index(
                    companies[cidx][1]['periods'], period)
                # Si el periodo no existe, lo agrego
                if not period_idx >= 0:
                    companies[cidx][1]['periods'].append({
                        period: [jid],
                        'txt': False
                    })
                else:
                    companies[cidx][1]['periods'][period_idx][period].append(
                        jid)

        # Formato a aplicar
        format_txt = http.request.env['res.bank.format'].browse(int(format_id))

        # Por cada empresa, armo un TXT
        for idx, company in enumerate(dict(companies).items()):
            cid = company[0]
            data = company[1]
            company_model = http.request.env['res.company'].browse(cid)
            # Guardo el PDF
            try:
                format_func = getattr(
                    format_bank.BM_FormatBank(), format_txt.function_name)
                for period in data['periods']:
                    pkey = list(period.keys())[0]
                    journals = http.request.env['bm.official.journal'].browse(
                        period[pkey])
                    file = format_func(journals)
                    if file:
                        file_title = '%(cname)s/%(period)s/%(title)s.txt' % ({
                            'cname': company_model.name,
                            'period': pkey.replace('/', ' '),
                            'title': file['title'] if file['title'] else format_txt.title
                        })
                        period_idx = self.array_index(
                            companies[idx][1]['periods'], pkey)
                        companies[idx][1]['periods'][period_idx]['txt'] = {
                            'name': file_title, 'data': file['data']
                        }
            except:
                format_func = None

        if format_func:
            zip_filename = "%(filename)s.zip" % ({
                'filename': 'Archivos TXT'
            })
            bitIO = BytesIO()
            with zipfile.ZipFile(bitIO, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
                for company in dict(companies).items():
                    for period in company[1]['periods']:
                        file = period['txt']
                        if file:
                            zf.writestr(file['name'], file['data'])
            return http.request.make_response(bitIO.getvalue(),
                                              headers=[('Content-Type', 'application/x-zip-compressed'),
                                                       ('Content-Disposition', content_disposition(zip_filename))])

    @http.route('/web/binary/download_salary_advance', type='http', auth="user")
    @serialize_exception
    def download_salary_advance(self, model, id, filename=None, **kw):
        """ Download link for files stored as binary fields.
        :param str model: name of the model to fetch the binary from
        :param str active_ids: ids of the record from which to fetch the binary
        :param str filename: field holding the file's name, if any
        :returns: :class:`werkzeug.wrappers.Response`
        """
        model = http.request.env[model].browse(int(id))

        report = http.request.env.ref(
            'hcs_bm_ecovis.bm_official_journal_salary_advance_report')
        pdf_report = report.sudo().render_qweb_pdf(model.id, {
            'images': dict(IMAGES),
            'mes': model.payment_date.strftime('%B').capitalize(),
            'anio': model.payment_date.strftime('%Y')
        })[0]
        pdf_title = '%(cname)s - %(filename)s.pdf' % ({
            'cname': model.official_id.company_id.name,
            'filename': filename
        })

        # Genero el PDF
        tmp_pdf = tempfile.TemporaryFile()
        tmp_pdf.write(pdf_report)
        tmp_pdf.seek(0)
        pdf_file = tmp_pdf.read()
        tmp_pdf.close()
        # Si se requiere, retorno el PDF
        return http.request.make_response(pdf_file, headers=[
            ('Content-Type', 'application/pdf'), ('Content-Length', len(pdf_file)),
            ('Content-Disposition', 'attachment; filename="%(title)s"' %
                ({'title': pdf_title}))
        ])

    @http.route('/web/binary/download_vacation_report', type='http', auth="user")
    @serialize_exception
    def download_vacation_report(self, model, id, filename=None, **kw):
        """ Download link for files stored as binary fields.
        :param str model: name of the model to fetch the binary from
        :param str active_ids: ids of the record from which to fetch the binary
        :param str filename: field holding the file's name, if any
        :returns: :class:`werkzeug.wrappers.Response`
        """
        model = http.request.env[model].browse(int(id))

        report = http.request.env.ref(
            'hcs_bm_ecovis.bm_official_departure_vacation_report')
        pdf_report = report.sudo().render_qweb_pdf(model.id)[0]
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
        return http.request.make_response(pdf_file, headers=[
            ('Content-Type', 'application/pdf'), ('Content-Length', len(pdf_file)),
            ('Content-Disposition', 'attachment; filename="%(title)s"' %
                ({'title': pdf_title}))
        ])

    @http.route('/web/binary/download_official_recipe', type='http', auth="user")
    @serialize_exception
    def download_official_recipe(self, model, id, filename=None, returnpdf=False, **kw):
        """ Download link for files stored as binary fields.
        :param str model: name of the model to fetch the binary from
        :param str active_ids: ids of the record from which to fetch the binary
        :param str filename: field holding the file's name, if any
        :returns: :class:`werkzeug.wrappers.Response`
        """
        model = http.request.env[model].browse(int(id))

        if not model.state == 'ready':
            return None

        report = http.request.env.ref(
            'hcs_bm_ecovis.bm_official_journal_recipe_report')
        pdf_report = report.sudo().render_qweb_pdf(model.id)[0]
        pdf_title = '%(cname)s - %(period)s - %(filename)s.pdf' % ({
            'cname': model.official_id.name,
            'period': model.journal_date_display.capitalize().replace('/', ' '),
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

    def array_index(self, array, search):
        for i, tupple in enumerate(array):
            for value in tupple:
                if value == search:
                    return i
        return -1
