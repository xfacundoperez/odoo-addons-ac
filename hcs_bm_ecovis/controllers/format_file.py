from odoo import http
import base64
import tempfile
import io

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


def generate_companies_pdf(companies, images, filename):
    list_pdf = []
    report_qweb = http.request.env.ref(
        'hcs_bm_ecovis.bm_official_journal_report')

    # Por cada empresa, armo un PDF
    for company_id, data in companies.items():
        report_pdf = report_qweb.render_qweb_pdf(company_id, {
            'company': data['company'],
            'images': images,
            'periods': data['periods']
        })[0]
        report_title = '%(company_name)s - %(period)s.pdf' % ({
            'company_name': data['company'].name,
            'period': filename
        })
        # Guardo el PDF
        tmp_pdf = tempfile.TemporaryFile()
        tmp_pdf.write(report_pdf)
        tmp_pdf.seek(0)
        # agrego el PDF a la lista
        list_pdf.append({
            'title': report_title,
            'file': tmp_pdf.read()
        })
        # companies[idx][1]['pdf'] = {
        #    'name': pdf_title, 'file': tmp_pdf.read()
        # }
        tmp_pdf.close()

    return list_pdf


def generate_companies_xls(companies, images, filename):
    list_xls = []

    # Por cada empresa, armo un XLS
    for company_id, data in companies.items():
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        # Formato Blanco con letras negras bold
        header_format = workbook.add_format({
            'font_size': 10,
            'bold': True
        })
        header_format_center = workbook.add_format({
            'border': 1,
            'font_size': 10,
            'align': 'center',
            'text_wrap': True,
            'bold': True
        })
        header_format_right = workbook.add_format({
            'border': 1,
            'font_size': 10,
            'align': 'right',
            'bold': True
        })

        # Formato celda con letras negras, centrado y borde
        cell_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'text_wrap': True,
            'valign': 'vcenter',
        })

        # Create a format to use in the merged range.
        merge_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'text_wrap': True,
            'valign': 'vcenter',
        })

        for period, journals in data['periods']:
            worksheet = workbook.add_worksheet(period)

            # Add images to header
            gnpy_img = io.BytesIO(base64.b64decode(images['gnpy']))
            worksheet.insert_image(
                0, 1, "gnpy.png", {'image_data': gnpy_img, 'x_scale': 1.75, 'y_scale': 1.75})
            mtess_img = io.BytesIO(base64.b64decode(images['mtess']))
            worksheet.insert_image(0, 37, "mtess.png", {
                'image_data': mtess_img, 'x_scale': 1.75, 'y_scale': 1.75})

            # Primera linea
            _line = 5

            # Fila 1
            worksheet.write(_line, 1, 'REGISTRO PATRONAL M.J.T. Nº :',
                            header_format)
            worksheet.write(_line, 37, 'Razón Social:', header_format)
            _line += 1

            # Fila 2
            worksheet.write(_line, 1, 'REGISTRO PATRONAL I.P.S. Nº:',
                            header_format)
            worksheet.write(_line, 37, 'Explotación:', header_format)
            _line += 1

            # Fila 3
            worksheet.write(_line, 1, 'DEPARTAMENTO:', header_format)
            worksheet.write(_line, 37, 'DOMICILIO:', header_format)
            _line += 1

            # Fila 4
            worksheet.write(_line, 1, 'R.U.C N°:', header_format)
            worksheet.write(_line, 37, 'Ciudad:', header_format)
            _line += 1

            # Fila 5
            _line += 1

            # Fila 6
            _period_format = period.split('/')
            worksheet.write(_line, 2, 'Mes de', header_format_right)
            worksheet.write(
                _line, 3, _period_format[0], header_format_center)
            worksheet.write(_line, 39, 'Año', header_format_right)
            worksheet.write(
                _line, 40, _period_format[1], header_format_center)
            _line += 1

            # Fila 7
            worksheet.merge_range(
                _line, 4, _line, 34, '', merge_format)
            worksheet.merge_range(
                _line, 35, _line, 36, 'Salario', merge_format)
            worksheet.merge_range(
                _line, 37, _line, 38, 'Total', merge_format)
            worksheet.merge_range(_line, 39, _line, 41,
                                  'Horas Extras', merge_format)
            worksheet.merge_range(_line, 42, _line, 46,
                                  'Beneficios Sociales', merge_format)
            _line += 1

            # Fila 8
            worksheet.write(_line, 1, 'Nro. De Orden',
                            header_format_center)
            worksheet.write(_line, 2, 'Nombre y Apellido',
                            merge_format)
            # dias
            for d in range(1, 32):
                # d+2 = _col
                worksheet.write(_line, d+2, d, cell_format)
            # Official
            worksheet.write(_line, 34, 'Forma de Pago', cell_format)
            worksheet.write(_line, 35, 'Importe Unitario', cell_format)
            worksheet.write(_line, 36, 'Días Trabajados', cell_format)
            worksheet.write(_line, 37, 'Horas de Trabajo', cell_format)
            worksheet.write(_line, 38, 'Importe', merge_format)
            worksheet.write(_line, 39, '50%', cell_format)
            worksheet.write(_line, 40, '100%', cell_format)
            worksheet.write(_line, 41, 'Importe', cell_format)
            worksheet.write(_line, 42, 'Vacaciones', cell_format)
            worksheet.write(_line, 43, 'Bonif. Familiar', cell_format)
            worksheet.write(_line, 44, 'Aguinaldo', cell_format)
            worksheet.write(_line, 45, 'Otros Beneficios', cell_format)
            worksheet.write(_line, 46, 'Total General', merge_format)
            _line += 1

            _nro_orden = 1
            _attendance_worked_hours_total = 0
            _attendance_amount_total = 0
            _total_general_amount_total = 0

            for journal in journals:
                official = journal.official_id
                worksheet.write(_line, 1, _nro_orden, cell_format)
                worksheet.write(_line, 2, official.name, cell_format)
                _col = 3
                for d in range(1, 32):
                    worksheet.write(_line, _col, 8, cell_format)
                    _col += 1
                worksheet.write(
                    _line, 34, journal.official_payment_mode, cell_format)
                worksheet.write(
                    _line, 35, journal.official_gross_salary, cell_format)
                worksheet.write(
                    _line, 36, journal.attendance_worked_days, cell_format)
                worksheet.write(
                    _line, 37, journal.attendance_worked_hours, cell_format)
                _attendance_worked_hours_total += journal.attendance_worked_hours
                worksheet.write(
                    _line, 38, journal.attendance_amount, cell_format)
                _attendance_amount_total += journal.attendance_amount
                worksheet.write(
                    _line, 39, journal.overtime_fifty, cell_format)
                worksheet.write(
                    _line, 40, journal.overtime_hundred, cell_format)
                worksheet.write(
                    _line, 41, journal.overtime_amount, cell_format)
                worksheet.write(
                    _line, 42, journal.vacation_amount, cell_format)
                worksheet.write(
                    _line, 43, journal.family_bonus_amount, cell_format)
                worksheet.write(
                    _line, 44, journal.extra_salary_amount, cell_format)
                worksheet.write(
                    _line, 45, journal.other_beneficts_amount, cell_format)
                worksheet.write(
                    _line, 46, journal.total_general_amount, cell_format)
                _total_general_amount_total += journal.total_general_amount

                _nro_orden += 1
                _line += 1

            worksheet.conditional_format(11, 1, _line-1, 46, {'type': 'no_errors',
                                                              'format': cell_format})
            worksheet.write(_line, 2, 'TOTALES', cell_format)
            worksheet.write(
                _line, 37, _attendance_worked_hours_total, cell_format)
            worksheet.write(
                _line, 38, _attendance_amount_total, cell_format)
            worksheet.write(
                _line, 46, _total_general_amount_total, cell_format)
            _line += 2
            worksheet.write(_line, 24, 'Firma:_________________________')
            _line += 2
            worksheet.write(_line, 24, 'Aclaración:_________________________')

            # Fix column size
            worksheet.set_column('C:C', 20)
            worksheet.set_column('E:AH', 5)
            worksheet.set_column('AI:AU', 15)


        workbook.close()
        output.seek(0)
        report_title = '%(company_name)s - %(period)s.xlsx' % ({
            'company_name': data['company'].name,
            'period': filename
        })
        list_xls.append({
            'title': report_title,
            'file': output.read()
        })
        output.close()

    return list_xls
