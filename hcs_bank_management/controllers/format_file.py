from odoo import http
from datetime import date
import base64
import tempfile
import io
import calendar

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter

MARITAL = [
    ('S', 'Soltero(a)'), ('C', 'Casado(a)'),
    ('D', 'Divorciado(a)'), ('V', 'Viudo(a)')
]
DEPARTURE_REASONS = [
    ('fired', 'Despido'),
    ('extra', 'Extra'),
    ('medical', 'Medica'),
    ('resigned', 'Renuncia'),
    ('retired', 'Retirado'),
    ('vacation', 'Vacaciones')
]

def company_journal_xls(cids, images, filename):
    list_xls = []

    # Imagenes como lista
    image_list = [{
        'name': 'gnpy.png',
        'image': io.BytesIO(base64.b64decode(images['gnpy']))
    }, {
        'name': 'mtess.png',
        'image': io.BytesIO(base64.b64decode(images['mtess']))
    }]

    # Por cada empresa, armo un XLS
    for cid, data in cids.items():
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Por cada Periodo, armo una pagina
        for periodo, jornales in data['periods']:
            # Info del periodo
            _periodo = {
                'title': periodo.replace('/', ' '),
                'month': periodo.split('/')[0],
                'year': periodo.split('/')[1]
            }
            # Obtengo el mes teniendo en cuenta el primer jornal
            jd = jornales[0].journal_date
            # Obtengo el ultimo dia del mes de ese jornal
            ultimo_dia = calendar.monthrange(jd.year, jd.month)[1] + 1

            # Agrego las paginas
            # Obreros y Empleados
            xls_page_officials(workbook, data['company'], jornales, image_list)
            # Vacaiones
            xls_page_vacation(workbook, data['company'], _periodo, jornales, image_list)
            # Jornales por periodos
            xls_page_journal(workbook, data['company'], _periodo, jornales, image_list, ultimo_dia)

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

def xls_page_officials(workbook, company, journals, images):
    worksheet = workbook.add_worksheet('Empleados y Obreros')

    # region FORMATS
    # size16, center, vcenter, wrap, bold
    format_title_top = workbook.add_format({
        'align': 'center',
        'bold': True,
        'font_size': 14,
        'text_wrap': True,
        'valign': 'vcenter'
    })
    # bold, right, fs12
    format_title_right = format_cell(workbook, {
        'align': 'right',
        'bold': True,
        'font_size': 12
    })
    # bold, border, center, vcenter, wrap.
    format_header = workbook.add_format({
        'bold': 1,
        'border': 1,
        'align': 'center',
        'text_wrap': True,
        'valign': 'vcenter',
    })
    # center, vcenter, wrap
    format_table_cell = workbook.add_format({
        'border': 1,
        'align': 'center',
        'text_wrap': True,
        'valign': 'vcenter',
    })
    # left
    format_left = format_cell(workbook, {
        'align': 'left'
    })

    # endregion

    # Tamaño de las columnas
    worksheet.set_column('B:B', 8)
    worksheet.set_column('C:D', 20)
    worksheet.set_column('E:H', 15)
    worksheet.set_column('I:I', 8)
    worksheet.set_column('J:S', 15)

    # region ENCABEZADO
    # Agrego la primera imagen
    worksheet.insert_image(0, 2, images[0]['name'], {
                           'image_data': images[0]['image'], 'x_scale': 1.75, 'y_scale': 1.75})

    # Agrego la segunda imagen
    worksheet.insert_image(0, 15, images[1]['name'], {
                           'image_data': images[1]['image'], 'x_scale': 1.75, 'y_scale': 1.75})

    # Primera linea con datos
    linea = 2

    # Titulo
    worksheet.merge_range(
        linea, 5, linea, 12, 'REGISTRO DE EMPLEADOS Y OBREROS', format_title_top)
    linea += 1
    worksheet.merge_range(
        linea, 5, linea, 12, '1º SEMESTRE - AÑO 2019', format_title_top)
    linea += 4

    worksheet.write(linea, 2, 'EMPLEADOR:', format_title_right)
    worksheet.write(linea, 3, company.name, format_left)
    worksheet.write(linea, 15, 'REGISTRO PATRONAL M.J.T. Nº :',
                    format_title_right)
    worksheet.write(linea, 16, '', format_left)
    linea += 1

    worksheet.write(linea, 2, 'RAZON SOCIAL:', format_title_right)
    worksheet.write(linea, 3, company.company_registry or company.name, format_left)
    worksheet.write(linea, 15, 'REGISTRO PATRONAL I.P.S. Nº:',
                    format_title_right)
    worksheet.write(linea, 16, company.employer_registration_number or '', format_left)
    linea += 1

    worksheet.write(linea, 2, 'ACTIVIDAD:', format_title_right)
    worksheet.write(linea, 3, company.exploitation or '', format_left)
    worksheet.write(linea, 15, 'R.U.C. Nº:', format_title_right)
    worksheet.write(linea, 16, '', format_left)
    linea += 1

    worksheet.write(linea, 2, 'DIRECCIÓN:', format_title_right)
    worksheet.write(linea, 3, company.address_name or '', format_left)
    worksheet.write(linea, 15, 'TELÉFONO:', format_title_right)
    worksheet.write(linea, 16, company.phone or '', format_left)
    linea += 1

    worksheet.write(linea, 2, 'DEPARTAMENTO:', format_title_right)
    worksheet.write(linea, 3, company.state_id.name or '', format_left)
    worksheet.write(linea, 15, 'CORREO ELECTRONICO:', format_title_right)
    worksheet.write(linea, 16, company.email or '', format_left)
    linea += 1

    worksheet.write(linea, 2, 'LOCALIDAD:', format_title_right)
    worksheet.write(linea, 3, company.location_id.name or '', format_left)
    worksheet.write(linea, 15, 'PAGINA WEB:', format_title_right)
    worksheet.write(linea, 16, company.website or '', format_left)
    linea += 2
    # endregion

    # region HEADER_TABLA
    linea += 1
    worksheet.merge_range(linea - 1, 1, linea, 1,
                          'Nro. De Orden', format_header)
    worksheet.merge_range(linea - 1, 2, linea, 2,
                          'Apellidos, Nombres (Orden Alfabetico)', format_header)
    worksheet.merge_range(linea - 1, 3, linea, 3, 'Domicilio', format_header)
    worksheet.merge_range(linea - 1, 4, linea, 4,
                          'Cedula de identidad', format_header)
    worksheet.merge_range(linea - 1, 5, linea, 5,
                          'Nacionalidad', format_header)
    worksheet.merge_range(linea - 1, 6, linea, 6, 'Edad', format_header)
    worksheet.merge_range(linea - 1, 7, linea, 7,
                          'Estado Civil', format_header)
    worksheet.merge_range(linea - 1, 8, linea - 1, 11,
                          'Menores', format_header)
    worksheet.write(linea, 8, 'Nº.de Hijos', format_header)
    worksheet.write(linea, 9, 'Fecha de Nacimiento', format_header)
    worksheet.write(linea, 10, 'Situación Escolar', format_header)
    worksheet.write(linea, 11, 'Cert.de Capac.Exp.en Fecha', format_header)
    worksheet.merge_range(linea - 1, 12, linea, 12,
                          'Horario de Trabajo', format_header)
    worksheet.merge_range(linea - 1, 13, linea, 13, 'Profesión', format_header)
    worksheet.merge_range(linea - 1, 14, linea, 14,
                          'Cargo Desempeñado', format_header)
    worksheet.merge_range(linea - 1, 15, linea, 15,
                          'Fecha de Entrada', format_header)
    worksheet.merge_range(linea - 1, 16, linea, 16,
                          'Fecha de Salida', format_header)
    worksheet.merge_range(linea - 1, 17, linea, 17,
                          'Motivo de Salida', format_header)
    worksheet.merge_range(linea - 1, 18, linea, 18, 'Obs.', format_header)
    # endregion

    # region FILAS_TABLA
    linea += 1
    orden = 1

    # Por cada jornal, agrego una fila
    for journal in journals:
        # Escribo desde la primera columna
        columna = 1

        # Funcionario del jornal
        official = journal.official_id

        # Nro. Orden
        worksheet.write(linea, columna, orden, format_table_cell)
        columna += 1
        # Nombre y Apellido
        worksheet.write(linea, columna, official.name, format_table_cell)
        columna += 1
        # Domicilio
        worksheet.write(linea, columna, official.address_name,
                        format_table_cell)
        columna += 1
        # Cedula de identidad
        worksheet.write(
            linea, columna, official.identification_id, format_table_cell)
        columna += 1
        # Nacionalidad
        worksheet.write(
            linea, columna, official.country_id.name, format_table_cell)
        columna += 1
        # Edad
        worksheet.write(linea, columna, calculate_age(
            official.birthday), format_table_cell)
        columna += 1
        # Obtengo el Estado civil
        official_marital = MARITAL[next(
            (i for i, v in enumerate(MARITAL) if v[0] == official.marital), 0)][1]
        # Estado civil
        worksheet.write(linea, columna, official_marital, format_table_cell)
        columna += 1

        # Menores
        # Nro. Hijos
        worksheet.write(linea, columna, official.family_childs,
                        format_table_cell)
        columna += 1
        # Fecha de Nacimiento
        child_birthday = ''
        # Situacion escolar
        child_escolar = ''
        # Cert.de Capac.Exp.en Fecha
        child_exp_date = ''
        for child in official.family_ids:
            if child.birthday:
                child_birthday += child.birthday.strftime('%Y-%m-%d') + '\n'
                # quito el ultimo \n
                child_birthday = child_birthday[:-1]
            if child.school_situation:
                child_escolar += child.school_situation + '\n'
                # quito el ultimo \n
                child_escolar = child_escolar[:-1]
            # child_exp_date += child.certificate_pdf_name + '\n' | Es un PDF
        worksheet.write(linea, columna, child_birthday, format_table_cell)
        columna += 1
        worksheet.write(linea, columna, child_escolar, format_table_cell)
        columna += 1
        worksheet.write(linea, columna, child_exp_date, format_table_cell)
        columna += 1

        # Horario de Trabajo
        worksheet.write(linea, columna, official.working_hours,
                        format_table_cell)
        columna += 1
        # Profesion
        worksheet.write(
            linea, columna, official.profession_id.name or '', format_table_cell)
        columna += 1
        # Cargo Desempeñado
        worksheet.write(
            linea, columna, official.job_id.name or '', format_table_cell)
        columna += 1
        # Fecha de Entrada
        off_adm_date = '' if not official.admission_date else official.admission_date.strftime(
            '%Y-%m-%d')
        worksheet.write(linea, columna, off_adm_date, format_table_cell)
        columna += 1
        # Fecha de Salida
        off_adm_date = '' if not official.contract_end_date else official.contract_end_date.strftime(
            '%Y-%m-%d')
        worksheet.write(linea, columna, off_adm_date, format_table_cell)
        columna += 1
        # Obtengo el Motivo de Salida
        official_departure_reason = DEPARTURE_REASONS[next(
            (i for i, v in enumerate(DEPARTURE_REASONS) if v[0] == official.departure_id.departure_reason), 0)][1]
        # Motivo de Salida
        worksheet.write(
            linea, columna, official_departure_reason, format_table_cell)
        columna += 1
        # Obs.
        worksheet.write(
            linea, columna, official.departure_id.departure_description or '', format_table_cell)
        columna += 1

        # Proxima Linea
        orden += 1
        linea += 1
    # endregion

    # Border para toda la tabla
    # worksheet.conditional_format(
    #    14, 1, linea-1, 18, {'type': 'no_errors', 'format': cell_format})

def xls_page_vacation(workbook, company, period, journals, images):
    worksheet = workbook.add_worksheet('Vacaciones')

    # region FORMATS
    # bold, size, fs12
    format_title = format_cell(workbook, {
        'bold': True,
        'font_size': 12
    })
    # bold, right, fs12
    format_title_right = format_cell(workbook, {
        'align': 'right',
        'bold': True,
        'font_size': 12
    })
    # bold, border, center, vcenter, wrap.
    format_header = workbook.add_format({
        'bold': 1,
        'border': 1,
        'align': 'center',
        'text_wrap': True,
        'valign': 'vcenter',
    })
    # center, vcenter, wrap
    format_table_cell = workbook.add_format({
        'border': 1,
        'align': 'center',
        'text_wrap': True,
        'valign': 'vcenter',
    })
    # left
    format_left = format_cell(workbook, {
        'align': 'left'
    })

    # endregion

    # region ENCABEZADO
    # Agrego la primera imagen
    worksheet.insert_image(0, 2, images[0]['name'], {
                           'image_data': images[0]['image'], 'x_scale': 1.75, 'y_scale': 1.75})

    # Agrego la segunda imagen
    worksheet.insert_image(0, 7, images[1]['name'], {
                           'image_data': images[1]['image'], 'x_scale': 1.75, 'y_scale': 1.75})

    # Primera linea con datos
    linea = 6

    # Titulo
    worksheet.write(linea, 2, 'REGISTRO PATRONAL M.J.T. Nº:',
                    format_title_right)
    worksheet.write(linea, 3, '', format_left)
    worksheet.write(linea, 7, 'RAZON SOCIAL:', format_title_right)
    worksheet.write(linea, 8, company.company_registry or company.name, format_left)
    linea += 1

    worksheet.write(linea, 2, 'REGISTRO PATRONAL I.P.S. N°:',
                    format_title_right)
    worksheet.write(linea, 3, company.employer_registration_number or '', format_left)
    worksheet.write(linea, 7, 'EXPLOTACION:', format_title_right)
    worksheet.write(linea, 8, company.exploitation or '', format_left)
    linea += 1

    worksheet.write(linea, 2, 'DEPARTAMENTO:', format_title_right)
    worksheet.write(linea, 3, company.state_id.name or '', format_left)
    worksheet.write(linea, 7, 'DOMICILIO:', format_title_right)
    worksheet.write(linea, 8, company.address_name or '', format_left)
    linea += 1

    worksheet.write(linea, 2, 'R.U.C. Nº:', format_title_right)
    worksheet.write(linea, 3, '', format_left)
    worksheet.write(linea, 7, 'CIUDAD:', format_title_right)
    worksheet.write(linea, 8, company.location_id.name or '', format_left)
    linea += 2

    worksheet.write(linea, 7, 'AÑO', format_title_right)
    worksheet.write(linea, 8, period['year'], format_title)
    linea += 2
    # endregion

    # region HEADER_TABLA
    worksheet.merge_range(linea - 1, 1, linea, 1,
                          'Nro. De Orden', format_header)
    worksheet.merge_range(linea - 1, 2, linea, 2,
                          'Nombre y Apellido', format_header)
    worksheet.merge_range(linea - 1, 3, linea, 3,
                          'Fecha de Nacimiento', format_header)
    worksheet.merge_range(linea - 1, 4, linea, 4,
                          'Fecha de Entrada', format_header)
    worksheet.merge_range(linea - 1, 5, linea - 1, 7,
                          'Duración de las vacaciones', format_header)
    worksheet.write(linea, 5, 'Días', format_header)
    worksheet.write(linea, 6, 'Desde', format_header)
    worksheet.write(linea, 7, 'Hasta', format_header)
    worksheet.merge_range(linea - 1, 8, linea, 8,
                          'Remuneracion', format_header)
    worksheet.merge_range(linea - 1, 9, linea, 9,
                          'Observaciones', format_header)

    # Tamaño de las columnas
    worksheet.set_column('B:B', 8)
    worksheet.set_column('C:C', 35)
    worksheet.set_column('D:E', 12)
    worksheet.set_column('F:F', 8)
    worksheet.set_column('G:I', 15)
    worksheet.set_column('J:J', 35)
    # endregion

    # region FILAS_TABLA
    linea += 1
    orden = 1

    # Por cada jornal, agrego una fila
    for journal in journals:
        # Escribo desde la primera columna
        columna = 1

        # Funcionario del jornal
        official = journal.official_id

        # Licencias del funcionario
        # del mes del jornal
        for vacation in official.departure_id.search(['&', '&',
                                                      ('official_id',
                                                       '=', official.id),
                                                      ('departure_start', '>',
                                                       journal.journal_date.date()),
                                                      ('departure_reason', '=', 'vacation')]):
            # Desde
            vac_dep_start = '' if not vacation.departure_start else vacation.departure_start.strftime(
                '%Y-%m-%d')
            # Hasta
            vac_dep_end = '' if not vacation.departure_end else vacation.departure_end.strftime(
                '%Y-%m-%d')

            # Calcula dias de vacaciones
            departure_delta = (vacation.departure_end -
                               vacation.departure_start)

            # Nro. Orden
            worksheet.write(linea, columna, orden, format_table_cell)
            columna += 1
            # Nombre y Apellido
            worksheet.write(
                linea, columna, vacation.official_id.name, format_table_cell)
            columna += 1
            # Fecha de Nacimiento
            worksheet.write(
                linea, columna, vacation.official_id.birthday or '', format_table_cell)
            columna += 1
            # Fecha de Entrada
            worksheet.write(
                linea, columna, vacation.official_id.admission_date or '', format_table_cell)
            columna += 1
            # Días
            worksheet.write(
                linea, columna, departure_delta.days, format_table_cell)
            columna += 1
            # Desde
            worksheet.write(linea, columna, vac_dep_start, format_table_cell)
            columna += 1
            # Hasta
            worksheet.write(linea, columna, vac_dep_end, format_table_cell)
            columna += 1
            # Remuneracion | vacation.remuneration
            worksheet.write(
                linea, columna, 0, format_table_cell)
            columna += 1
            # Observaciones
            worksheet.write(
                linea, columna, vacation.departure_description or '-', format_table_cell)
            columna += 1

            # Proxima Linea
            orden += 1
            linea += 1
    # endregion

def xls_page_journal(workbook, company, period, journals, images, month_last_day):
    worksheet = workbook.add_worksheet(period['title'])

    # region FORMATS
    # bold, right, fs12
    format_title_right = format_cell(workbook, {
        'align': 'right',
        'bold': True,
        'font_size': 12
    })
    # bold, right, fs16
    format_title_2_right = format_cell(workbook, {
        'align': 'right',
        'bold': True,
        'border': 1,
        'font_size': 16
    })
    # bold, right, fs16
    format_title_2_center = format_cell(workbook, {
        'align': 'center',
        'bold': True,
        'border': 1,
        'font_size': 16
    })
    # bold, border, center, vcenter, wrap.
    format_header = workbook.add_format({
        'bold': 1,
        'border': 1,
        'align': 'center',
        'text_wrap': True,
        'valign': 'vcenter',
    })
    # center, vcenter, wrap
    format_table_cell = workbook.add_format({
        'border': 1,
        'align': 'center',
        'text_wrap': True,
        'valign': 'vcenter',
    })
    # center, vcenter, wrap
    format_table_cell_b = workbook.add_format({
        'bold': True,
        'border': 1,
        'align': 'center',
        'text_wrap': True,
        'valign': 'vcenter',
    })
    # left
    format_left = format_cell(workbook, {
        'align': 'left'
    })
    # right
    format_right = format_cell(workbook, {
        'align': 'right'
    })
    # border
    format_border = format_cell(workbook, {
        'border': 1
    })
    # endregion

    # region ENCABEZADO
    # Agrego la primera imagen
    worksheet.insert_image(0, 2, images[0]['name'], {
        'image_data': images[0]['image'], 'x_scale': 1.75, 'y_scale': 1.75})

    # Primera linea con datos
    linea = 6

    # Datos de la empresa
    worksheet.write(linea, 2, 'REGISTRO PATRONAL M.J.T. Nº :', format_title_right)
    worksheet.merge_range(linea, 3, linea, 10, '', format_left)
    linea += 1
    worksheet.write(linea, 2, 'REGISTRO PATRONAL I.P.S. Nº:', format_title_right)
    worksheet.merge_range(linea, 3, linea, 10, company.employer_registration_number or '', format_left)
    linea += 1
    worksheet.write(linea, 2, 'DEPARTAMENTO:', format_title_right)
    worksheet.merge_range(linea, 3, linea, 10, company.state_id.name or '', format_left)
    linea += 1
    worksheet.write(linea, 2, 'R.U.C N°:', format_title_right)
    worksheet.merge_range(linea, 3, linea, 10, '', format_left)
    linea += 2

    worksheet.write(linea, 2, 'Mes de', format_title_2_right)
    worksheet.merge_range(linea, 3, linea, 10,
                          period['month'], format_title_2_center)
    worksheet.write(linea, 39, 'Año', format_title_2_right)
    worksheet.merge_range(linea, 40, linea, 41,
                          period['year'], format_title_2_center)
    linea += 2
    # endregion

    # region HEADER_TABLA
    # Escribo desde la primera columna
    columna = 1
    worksheet.write(linea, columna, 'Nro. De Orden', format_header)
    columna += 1
    worksheet.write(linea, columna, 'Nombre y Apellido', format_header)
    # Ancho de columna
    worksheet.set_column(columna, columna, 20)
    columna += 1
    # Columnas con los días del mes
    for dia in range(1, month_last_day):
        worksheet.write(linea, columna, dia, format_header)
        worksheet.set_column(columna, columna, 3)
        columna += 1
    worksheet.write(linea, columna, 'Forma de Pago', format_header)
    # Ancho de columna
    worksheet.set_column(columna, columna, 8)
    columna += 1

    # Salario
    worksheet.merge_range(linea - 1, columna, linea - 1,
                          columna + 1, 'Salario', format_header)
    # Datos del salario
    worksheet.write(linea, columna, 'Importe Unitario', format_header)
    worksheet.set_column(columna, columna, 12)
    columna += 1
    worksheet.write(linea, columna, 'Días Trabajados', format_header)
    worksheet.set_column(columna, columna, 10)
    columna += 1

    # Total
    worksheet.merge_range(linea - 1, columna, linea - 1,
                          columna + 1, 'Total', format_header)
    # Datos de Total
    worksheet.write(linea, columna, 'Horas de Trabajo', format_header)
    worksheet.set_column(columna, columna, 10)
    _attwh_column = columna
    columna += 1
    worksheet.write(linea, columna, 'Importe', format_header)
    worksheet.set_column(columna, columna, 12)
    _attat_column = columna
    columna += 1

    # Horas Extras
    worksheet.merge_range(linea - 1, columna, linea - 1,
                          columna + 3, 'Horas Extras', format_header)
    # Datos de Horas Extras
    worksheet.write(linea, columna, '50%', format_header)
    worksheet.set_column(columna, columna, 6)
    columna += 1
    worksheet.write(linea, columna, '100%', format_header)
    worksheet.set_column(columna, columna, 6)
    columna += 1
    worksheet.write(linea, columna, 'Importe', format_header)
    worksheet.set_column(columna, columna, 12)
    columna += 1
    worksheet.write(linea, columna, 'Vacaciones', format_header)
    worksheet.set_column(columna, columna, 12)
    columna += 1

    # Beneficios Sociales
    worksheet.merge_range(linea - 1, columna, linea - 1,
                          columna + 3, 'Beneficios Sociales', format_header)
    # Datos de Beneficios Sociales
    worksheet.write(linea, columna, 'Bonif. Familiar', format_header)
    worksheet.set_column(columna, columna, 12)
    columna += 1
    worksheet.write(linea, columna, 'Aguinaldo', format_header)
    worksheet.set_column(columna, columna, 12)
    columna += 1
    worksheet.write(linea, columna, 'Otros Beneficios', format_header)
    worksheet.set_column(columna, columna, 12)
    columna += 1
    worksheet.write(linea, columna, 'Total General', format_header)
    worksheet.set_column(columna, columna, 12)
    # endregion

    # region ENCABEZADO
    # Fix para segunda imagen e info
    columna -= 4

    # Agrego la segunda imagen
    worksheet.insert_image(0, columna, images[1]['name'], {
        'image_data': images[1]['image'], 'x_scale': 1.75, 'y_scale': 1.75})

    # Agrego info extra
    worksheet.write(6, columna, 'Razon Social:', format_title_right)
    worksheet.merge_range(6, columna + 1, 6, columna + 2, company.company_registry or company.name, format_left)
    worksheet.write(7, columna, 'Explotación:', format_title_right)
    worksheet.merge_range(7, columna + 1, 7, columna + 2, company.exploitation or '', format_left)
    worksheet.write(8, columna, 'DOMICILIO:', format_title_right)
    worksheet.merge_range(8, columna + 1, 8, columna + 2, company.address_name or '', format_left)
    worksheet.write(9, columna, 'Ciudad:', format_title_right)
    worksheet.merge_range(9, columna + 1, 9, columna + 2, company.location_id.name or '', format_left)
    linea += 1
    # endregion

    # region FILTAS_TABLA
    orden = 1
    att_worked_hours_total = 0
    att_amount_total = 0
    general_amount_total = 0

    # Por cada jornal, agrego una fila
    for journal in journals:
        # Escribo desde la primera columna
        columna = 1

        # Funcionario del jornal
        official = journal.official_id

        # Nro. Orden
        worksheet.write(linea, columna, orden, format_table_cell)
        columna += 1

        # Nombre y Apellido
        worksheet.write(linea, columna, official.name, format_table_cell)
        columna += 1

        # Columnas con los días del mes
        for dia in range(1, month_last_day):
            # Horas por default
            strhoras = '8'
            # Obtengo la rason de la ausencia
            for att_days_id in journal.attendance_id.days_ids:
                # Verifico si tiene ausencia el dia
                # del mes y cambio strhoras por
                # el motivo de ausencia
                if att_days_id.day_date.day == dia:
                    strhoras = att_days_id.missed_reason
            worksheet.write(linea, columna, strhoras, format_table_cell)
            columna += 1

        # Forma de Pago
        worksheet.write(
            linea, columna, journal.official_payment_mode, format_table_cell)
        columna += 1

        # Salario
        # Importe Unitario
        worksheet.write(
            linea, columna, journal.official_gross_salary, format_table_cell)
        columna += 1
        # Días Trabajados
        worksheet.write(
            linea, columna, journal.attendance_worked_days, format_table_cell)
        columna += 1

        # Total
        # Horas de Trabajo
        worksheet.write(
            linea, columna, journal.attendance_worked_hours, format_table_cell)
        columna += 1
        # Importe
        worksheet.write(
            linea, columna, journal.attendance_amount, format_table_cell)
        columna += 1
        # Suma de Horas de Trabajo e Importe
        #att_worked_hours_total += journal.attendance_worked_hours
        att_amount_total += journal.attendance_amount

        # Horas Extras
        # 50%
        worksheet.write(linea, columna, journal.overtime_fifty,
                        format_table_cell)
        columna += 1
        # 100%
        worksheet.write(
            linea, columna, journal.overtime_hundred, format_table_cell)
        columna += 1
        # Importe
        worksheet.write(linea, columna, journal.overtime_amount,
                        format_table_cell)
        columna += 1
        # Vacaciones
        worksheet.write(linea, columna, journal.vacation_amount,
                        format_table_cell)
        columna += 1

        # Beneficios Sociales
        # Bonif. Familiar
        worksheet.write(
            linea, columna, journal.family_bonus_amount, format_table_cell)
        columna += 1
        # Aguinaldo
        worksheet.write(
            linea, columna, journal.extra_salary_amount, format_table_cell)
        columna += 1
        # Otros Beneficios
        worksheet.write(
            linea, columna, journal.other_beneficts_amount, format_table_cell)
        columna += 1
        # Total General
        worksheet.write(
            linea, columna, journal.total_general_amount, format_table_cell)
        # Suma de Total General
        general_amount_total += journal.total_general_amount

        # Proxima Linea
        orden += 1
        linea += 1
    # endregion

    # Border para toda la tabla
    worksheet.conditional_format(
        12, 1, linea-1, columna, {'type': 'no_errors', 'format': format_border})

    # region PIE_TABLA
    # Fila de totales
    worksheet.write(linea, 2, 'TOTALES', format_table_cell_b)
    worksheet.write(linea, _attwh_column,
                    att_worked_hours_total, format_table_cell_b)
    worksheet.write(linea, _attat_column,
                    att_amount_total, format_table_cell_b)
    worksheet.write(linea, columna, general_amount_total, format_table_cell_b)

    # Firma
    linea += 2
    worksheet.write(linea, 24, 'Firma:', format_right)
    worksheet.write(linea, 25, '____________________________')
    # Aclaracion
    linea += 2
    worksheet.write(linea, 24, 'Aclaración:', format_right)
    worksheet.write(linea, 25, '____________________________')
    # endregion

def format_cell(workbook, *args):
    args = next(iter(args or {}), {})
    return workbook.add_format({
        'align': args.get('align') or 'left',
        'font_size': args.get('font_size') or 10,
        'border': args.get('border') or 0,
        'text_wrap': args.get('text_wrap') or False,
        'bold': args.get('bold') or 1,
        'valign': args.get('valign') or 'vcenter'
    })

def calculate_age(first_date, second_date=date.today()):
    if not first_date:
        return ''
    return second_date.year - first_date.year - ((second_date.month, second_date.day) < (first_date.month, first_date.day))

# No se usa mas en PDF
def generate_companies_pdf(companies, images, filename):
    list_pdf = []
    report_qweb = http.request.env.ref(
        'hcs_bank_management.bm_official_journal_report')

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
