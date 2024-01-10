# -*- coding: utf-8 -*-
from odoo import http
from datetime import datetime
import tempfile


class BM_FormatBank(http.Controller):

    def format_itau(self, journals):
        # Solo si hay Jornales
        if not len(journals):
            return False

        # Fecha Actual
        _now = datetime.now()

        # [:N] = Obtengo los N caracteres
        # rjust(N, C) = Rellena con N caracteres C a la izquierda (numericos)
        # ljust(N, C) = Rellena con N caracteres C a la derecha (alfanumericos)

        # region EMPRESA
        # Código
        company_code = http.request.env.user.company_id.employer_registration_number or ''
        # Código empresa (asignado por el Banco)
        ICDSRV = company_code[:3].rjust(3, '0')
        # Cuenta debito
        company_debit = http.request.env.user.company_id.debit_account or ''
        # Nro. de cuenta para débito/Cuenta empresa
        ICTDEB = company_debit[:10].rjust(10, '0')
        # Cuenta debito
        company_credit = http.request.env.user.company_id.credit_account or ''
        # Nro. de cuenta para crédito (N:10)
        ICTCRE = company_credit[:10].rjust(10, '0')

        # endregion

        file_content_detail = ''
        _amount_total = {
            'IMTOTR': 0,
            'IMTOT2': 0
        }
        for journal in journals:
            # Nro. de documento (C:12) | cédula de identidad, RUC, Pasaporte, otros. Del beneficiario, proveedor, cliente
            INRODO = journal.official_id.identification_id
            INRODO = INRODO[:12].ljust(12, ' ')

            for salary in journal.salary_ids:
                # Tipo Transferencia (C:2)
                ITITRA = '01'
                # ['01',  # Pago de Salarios
                #  '02',  # Pago a Proveedores
                #  '03',  # Cobro de Factura/Cuota
                #  '09']  # Débitos comandados

                # Cheque a la orden de/Cliente/Facturado/Beneficiario/Pagador (C:50)
                IORDEN = '' # De donde obtener el dato (?)
                IORDEN = IORDEN[:50].ljust(50, ' ')

                # Tipo débito/crédito (C:1)
                ITCRDB = 'D'
                # ['D',  # Débito
                #  'C',  # Crédito
                #  'H',  # Cheque
                #  'F']  # Cobro de Factura/Cuota

                # Si pago en cheque (ITCRDB='H') relleno con ceros
                if ITCRDB == 'H':
                    ICTCRE = '0'[:10].rjust(10, '0')


                # Moneda del funcionario (N:1)
                IMONED = '0'  # Guaranies
                if journal.official_id.currency_id.name == 'USD':
                    IMONED = '1'  # USD

                # Monto Transferencia/Factura/Cuota (N:15.2) | últimos dos dígitos corresponde a decimales.
                IMTOTR = "%.2f" % salary.amount_to_pay
                IMTOTR = str(IMTOTR).replace('.', '')[:15].rjust(15, '0')
                # Salario total a pagar
                _amount_total['IMTOTR'] += salary.amount_to_pay

                # Monto Transferencia (segundo vencimiento) (N:15.2)
                IMTOT2 = "%.2f" % 0
                IMTOT2 = str(IMTOT2).replace('.', '')[:15].rjust(15, '0')
                # Monto del segundo vencimiento
                _amount_total['IMTOT2'] += 0

                # Tipo Factura (N:1) | Solo para Pago a Proveedores. Demas 0
                ITIFAC = '0'
                # [0,   # Default
                #  1,   # Factura Contado
                #  2]   # Factura Crédito

                # Nro. de Factura (C:20) | Para pago a proveedores. Demás blancos
                INRFAC = ''
                INRFAC = INRFAC[:20].ljust(20, ' ')

                # Nro. de Cuota pagada/a cobrar. (N:3) | Solo para ITCRDB='F' Cobro de Factura/Cuota
                INRCUO = '0'
                INRCUO = INRCUO[:3].rjust(3, '0')

                # Fecha para realizar el crédito/Fecha vencimiento (N:8) | Formato: Aaaammdd
                IFCHCR = _now.strftime("%Y%m%d")
                # Fecha segundo vencimiento. (N:8) | Solo para 'F' Cobro de Factura/Cuota | Formato: 'Aaaammdd'
                IFCHC2 = _now.strftime("%Y%m%d")
                
                # Comentario de concepto cobrado/pagado (C:50)
                ICEPTO = ''
                ICEPTO = ICEPTO[:50].ljust(50, ' ')

                # Referencia operación empresa (C:15)
                INRREF = ''
                INRREF = INRREF[:15].ljust(15, ' ')
                # Fecha de carga de transacción (N:8) | Formato: Aaaammdd
                IFECCA = _now.strftime("%Y%m%d")
                # Hora de carga de transacción (N:8) | Formato: Hhmmss
                IHORCA = _now.strftime("%H%M%S")
                # Nombre del usuario que cargó (C:10)
                IUSUCA = http.request.env.user.name
                IUSUCA = IUSUCA[:12].ljust(12, ' ')

                file_content_detail += "%(1)s%(2)s%(3)s%(4)s%(5)s%(6)s%(7)s" % ({
                    # ITIREG: Tipo de registro enviado (C:1)
                    '1': 'D',
                    # ITITRA: Tipo Transferencia (C:2)
                    '2': ITITRA,
                    # ICDSRV: Código empresa (asignado por el Banco) (C:3)
                    '3': ICDSRV,
                    # ICTDEB: Nro. de cuenta para débito/Cuenta empresa (N:10)
                    '4': ICTDEB,
                    # IBCOCR: Nro. de Banco para crédito (N:3) | Siempre 017
                    '5': '017',
                    # ICTCRE: Nro. de cuenta para crédito (N:10)
                    '6': ICTCRE,
                    # ITCRDB: Tipo débito/crédito (C:1)
                    '7': ITCRDB,
                })
                file_content_detail += "%(1)s%(2)s%(3)s%(4)s%(5)s%(6)s%(7)s" % ({
                    # Cheque a la orden de/Cliente Facturado/Beneficiario/Pagador (C:50)
                    '1': IORDEN,
                    # Moneda correspondiente al monto (N:1)
                    '2': IMONED,
                    # Monto Transferencia/Factura/Cuota (N:15)
                    '3': IMTOTR,
                    # Monto Transferencia (segundo vencimiento) (N:15)
                    '4': IMTOT2,
                    # Nro. de documento (C:12)
                    '5': INRODO,
                    # Tipo Factura (N:1)
                    '6': ITIFAC,
                    # Nro. de Factura (C:20)
                    '7': INRFAC,
                })
                file_content_detail += "%(1)s%(2)s%(3)s%(4)s%(5)s%(6)s%(7)s%(8)s" % ({
                    # Nro. de Cuota pagada/a cobrar. (N:3)
                    '1': INRCUO,
                    # Fecha para realizar el crédito/Fecha vencimiento (N:8)
                    '2': IFCHCR,
                    # Fecha segundo vencimiento (N:8)
                    '3': IFCHC2,
                    # Comentario de concepto cobrado/pagado (C:50)
                    '4': ICEPTO,
                    # Referencia operación empresa (C:15)
                    '5': INRREF,
                    # Fecha de carga de transacción (N:8)
                    '6': IFECCA,
                    # Hora de carga de transacción (N:6)
                    '7': IHORCA,
                    # Nombre del usuario que cargo (C:10)
                    '8': IUSUCA,
                })
                file_content_detail += '\n'

        file_content_detail += "%(1)s%(2)s%(3)s%(4)s%(5)s%(6)s%(7)s" % ({
            # ITIREG: Tipo de registro enviado (C:1)
            '1': 'C',
            # ITITRA: Tipo Transferencia (C:2)
            '2': ''.rjust(2, '0'),
            # ICDSRV: Código empresa (asignado por el Banco) (C:3)
            '3': ''.rjust(3, '0'),
            # ICTDEB: Nro. de cuenta para débito/Cuenta empresa (N:10)
            '4': ''.rjust(10, '0'),
            # IBCOCR: Nro. de Banco para crédito (N:3)
            '5': ''.rjust(3, '0'),
            # ICTCRE: Nro. de cuenta para crédito (N:10)
            '6': ''.rjust(10, '0'),
            # ITCRDB: Tipo débito/crédito (C:1)
            '7': ' ',
        })
        file_content_detail += "%(1)s%(2)s%(3)s%(4)s%(5)s%(6)s%(7)s" % ({
            # Cheque a la orden de/Cliente Facturado/Beneficiario/Pagador (C:50)
            '1': ''.ljust(50, ' '),
            # Moneda correspondiente al monto (N:1)
            '2': '0',
            # Monto Transferencia/Factura/Cuota (N:15)
            '3': str(_amount_total['IMTOTR']).replace('.', '')[:15].rjust(15, '0'),
            # Monto Transferencia (segundo vencimiento) (N:15)
            '4': str(_amount_total['IMTOT2']).replace('.', '')[:15].rjust(15, '0'),
            # Nro. de documento (C:12)
            '5': ''.rjust(12, '0'),
            # Tipo Factura (N:1)
            '6': '0',
            # Nro. de Factura (C:20)
            '7': ''.ljust(20, ' '),
        })
        file_content_detail += "%(1)s%(2)s%(3)s%(4)s%(5)s%(6)s%(7)s%(8)s" % ({
            # Nro. de Cuota pagada/a cobrar. (N:3)
            '1': ''.rjust(3, '0'),
            # Fecha para realizar el crédito/Fecha vencimiento (N:8)
            '2': ''.rjust(8, '0'),
            # Fecha segundo vencimiento (N:8)
            '3': ''.rjust(8, '0'),
            # Comentario de concepto cobrado/pagado (C:50)
            '4': ''.ljust(50, ' '),
            # Referencia operación empresa (C:15)
            '5': ''.ljust(15, ' '),
            # Fecha de carga de transacción (N:8)
            '6': ''.rjust(8, '0'),
            # Hora de carga de transacción (N:6)
            '7': ''.rjust(6, '0'),
            # Nombre del usuario que cargo (C:10)
            '8': ''.ljust(12, ' '),
        })


        # No es necesario formatear el titulo
        txt_title = False

        # Create temporary file, write info and download
        txt_temp = tempfile.TemporaryFile()
        # Write data into your file respectively with your logic
        txt_temp.write(str.encode(file_content_detail))
        txt_temp.seek(0)
        txt_file = txt_temp.read()
        txt_temp.close()

        return {
            'data': txt_file,
            'title': txt_title
        }

    def format_sudameris(self, journals):
        # Solo si hay Jornales
        if not len(journals):
            return False

        # Empresa
        company_id = http.request.env.user.company_id
        # Código
        company_code = company_id.employer_registration_number or ''
        # Cuenta debito
        company_debit = company_id.debit_account or ''
        # Moneda
        company_currency = '6900'  # Guaranies
        if company_id.currency_id.name == 'USD':
            company_currency = '1'  # USD
        # Mail
        company_email = http.request.env.user.company_id.email or ''

        # Contenido del TXT
        file_content_detail = ''
        _amount_to_pay_sum = 0
        for journal in journals:
            # Nombre del funcionario
            official_name = journal.official_id.name_first.split(' ')
            # Apellido del funcionario
            official_surname = journal.official_id.surname_first.split(' ')
            # Fecha de pago del jornal
            _fecha_pago = journal.payment_date.strftime("%d/%m/%Y")
            # Concepto
            _concepto = 'Pago_de_Salario'
            # Referencia: AÑO|MES|DIA|HORA|MIN|SEG|CODEMPRESA
            _referencia = "%(time)s%(code)s" % ({
                'time': _fecha_pago.strftime("%Y%m%d%H%M%S"),
                'code': company_code
            })

            file_content_detail += "{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{}\n".format(
                # Identificador del detalle(C:1)
                'D',
                # Concepto(C:30)
                _concepto,
                # Primer Apellido(C:15)
                official_surname[0],
                # Segundo Apellido(C:15)
                official_surname[1] if len(official_surname) > 1 else '',
                # Primer Nombre(C:15)
                official_name[0],
                # Segundo Nombre(C:15)
                official_name[1] if len(official_name) > 1 else '',
                # País(I:3)
                journal.official_id.country_id.code_number,
                # Tipo de Documento(I:2)
                journal.official_id.identification_type,
                # Número de Documento(C:15)
                journal.official_id.identification_id,
                # Moneda(I:4)
                '6900',
                # Importe(N:15.2)
                "%.2f" % journal.net_salary_amount,
                # Fecha de Pago(D:8)
                journal.journal_date.strftime("%d/%m/%Y") or '',
                # Modalidad de Pago(I:3)
                journal.official_payment_mode or '',
                # Número de Cuenta(I:9)
                '',
                # Sucursal Empleado(I:3)
                '',
                # Moneda Empleado(I:4)
                '6900',
                # Operación Empleado(I:9): En estos campos va siempre el numero 0
                '0',
                # Tipo de Operación Empleado(I:3): En estos campos va siempre el numero 0
                '0',
                # Suboperación Empleado(I:3): En estos campos va siempre el numero 0
                '0',
                # Referencia(C:18): Dicho campo debe ser exactamente igual que el campo REFERENCIA en la CABECERA
                _referencia,
                # Tipo de Contrato(I:3): Este campo se coloca siempre el numero 1
                '1',
                # Sueldo Bruto(N:15.2)
                "%.2f" % journal.official_id.gross_salary or '0.00',
                # Fecha Fin de Contrato(D:8)
                journal.official_id.contract_end_date or '//',
            )

        file_content_header = "{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{}\n".format(
            'H',                            # Identificador de cabecera(C:1)
            company_code,                   # Código de contrato(I:9)
            company_email,                  # E-mail asociado al Servicio(C:50)
            company_currency,               # Moneda(I:4)
            "%.2f" % _amount_to_pay_sum,    # Importe(N:15.2)
            len(journals),                  # Cantidad de Documentos(I:5)
            _fecha_pago,                    # Fecha de Pago(D:8)
            _referencia,                    # Referencia(C:18)
            '0',                            # Tipo de Cobro(I:3)
            '1',                            # Debito Crédito(I:1)
            company_debit,                  # Cuenta Débito(I:9)
            '10',                           # Sucursal Débito(I:3)
            '20',                           # Módulo Débito(I:3)
            company_currency,               # Moneda Débito(I:4)
            '0',                            # Operación Débito(I:9)
            '0',                            # Sub Operación Débito(I:3)
            '0'                             # Tipo Operación Débito(I:3)
        )

        # Creo el archivo TXT
        # Tipo de dato: I: Entero, C: Caracter o Alfanumérico, D: Fecha, N: Numérico decimal con dos valores decimales
        # Composición del nombre: ENTIDAD_SERVICIO_FECHA+HORA.TXT
        txt_title = '{}_{}.txt'.format(_concepto, _referencia)
        txt_content = str.encode(file_content_header + file_content_detail)
        # Create temporary file, write info and download
        txt_temp = tempfile.TemporaryFile()
        # Write data into your file respectively with your logic
        txt_temp.write(txt_content)
        txt_temp.seek(0)
        txt_file = txt_temp.read()
        txt_temp.close()

        return {
            'data': txt_file,
            'title': txt_title
        }
