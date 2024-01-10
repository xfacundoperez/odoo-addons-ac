# -*- coding: utf-8 -*-
{
    'name': "Ecovis: Bank Management TEST",
    'version': '1.0',
    'category': 'Human Resources/Employees',
    'summary': 'Ecovis: Centraliza la información de funcionarios por compañias asociadas',
    'description': """
        Ecovis: Centraliza la información de funcionarios por compañias asociadas

        Organizá la plantilla de funcionarios y salarios por compañía asociada a la empresa
    """,
    'author': "HC Sinergia",
    'website': "http://www.hcsinergia.com",
    # any module necessary for this one to work correctly
    'depends': ['base', 'web', 'contacts', 'report_xlsx'],
    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/bm_official_journal_wizard.xml',
        'wizard/bm_official_wizard.xml',
        'reports/bm_official_default_report.xml',
        'reports/bm_official_departure_vacation_report.xml',
        'reports/bm_official_journal_recipe_report.xml',
        'reports/bm_official_journal_report.xml',
        'reports/bm_official_journal_salary_advance_report.xml',
        'views/assets.xml',
        'views/bm_menu.xml',
        'views/bm_official.xml',
        'views/bm_department.xml',
        'views/bm_job.xml',
        'views/bm_official_attendance.xml',
        'views/bm_official_departure.xml',
        'views/bm_official_family.xml',
        'views/bm_official_journal.xml',
        'views/res_bank.xml',
        'views/res_company.xml',
        'views/res_country.xml',
        'data/bm_data_mail_channel.xml',
        'data/bm_data_res_country.xml',
        'data/bm_data_ir_con.xml'
    ],
    'qweb': [
        'static/src/xml/action_call.xml'
    ],
    'installable': True,
    'application': True
}
