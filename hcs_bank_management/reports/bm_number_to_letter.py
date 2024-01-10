# -*- coding: utf-8 -*-
from odoo import models

SINGULAR_CURRENCY = 'guaraní'
PLURAL_CURRENCY = 'guaraníes'

SINGULAR_CENTS = 'centimo'
PLURAL_CENTS = 'cents'

MAX_NUM = 999999999999

UNITS = (
    'cero',
    'uno',
    'dos',
    'tres',
    'cuatro',
    'cinco',
    'seis',
    'siete',
    'ocho',
    'nueve'
)

DOZENS = (
    'diez',
    'once',
    'doce',
    'trece',
    'catorce',
    'quince',
    'dieciseis',
    'diecisiete',
    'dieciocho',
    'diecinueve'
)

TEN_TENS = (
    'cero',
    'diez',
    'veinte',
    'treinta',
    'cuarenta',
    'cincuenta',
    'sesenta',
    'setenta',
    'ochenta',
    'noventa'
)

HOUNDREDS = (
    '_',
    'ciento',
    'doscientos',
    'trescientos',
    'cuatroscientos',
    'quinientos',
    'seiscientos',
    'setecientos',
    'ochocientos',
    'novecientos'
)

class BMOfficialNTL(models.Model):
    _inherit = "bm.official"

    def nubmer_to_letter(self, number):
        number = float(number)
        integer_number = int(number)
        if integer_number > MAX_NUM:
            return 'Número demasiado alto'
        if integer_number < 0:
            return 'menos %s' % self.nubmer_to_letter(abs(number))
        letter_to_decimal = ''
        decimal_part = int(round((abs(number) - abs(integer_number)) * 100))
        if decimal_part > 9:
            letter_to_decimal = 'punto %s' % self.nubmer_to_letter(decimal_part)
        elif decimal_part > 0:
            letter_to_decimal = 'punto cero %s' % self.nubmer_to_letter(decimal_part)
        if (integer_number <= 99):
            result = self.read_tens(integer_number)
        elif (integer_number <= 999):
            result = self.read_hundreds(integer_number)
        elif (integer_number <= 999999):
            result = self.read_miles(integer_number)
        elif (integer_number <= 999999999):
            result = self.read_millions(integer_number)
        else:
            result = self.read_billion(integer_number)
        result = result.replace('uno mil', 'un mil')
        result = result.strip()
        result = result.replace(' _ ', ' ')
        result = result.replace('  ', ' ')
        if decimal_part > 0:
            result = '%s %s' % (result, letter_to_decimal)
        return result

    def number_to_currency(self, number):
        number = float(number)
        integer_number = int(number)
        decimal_part = int(round((abs(number) - abs(integer_number)) * 100))
        cents = ''
        if decimal_part == 1:
            cents = SINGULAR_CENTS
        else:
            cents = PLURAL_CENTS
        moneda = ''
        if integer_number == 1:
            moneda = SINGULAR_CURRENCY
        else:
            moneda = PLURAL_CURRENCY
        letras = self.nubmer_to_letter(integer_number)
        letras = letras.replace('uno', 'un')
        letter_to_decimal = 'con %s %s' % (self.nubmer_to_letter(decimal_part).replace('uno', 'un'), cents)
        letras = '%s de %s %s' % (letras, moneda, letter_to_decimal)
        return letras

    def read_tens(self, number):
        if number < 10:
            return UNITS[number]
        decena, unidad = divmod(number, 10)
        if number <= 19:
            result = DOZENS[unidad]
        elif number <= 29:
            result = 'veinti%s' % UNITS[unidad]
        else:
            result = TEN_TENS[decena]
            if unidad > 0:
                result = '%s y %s' % (result, UNITS[unidad])
        return result

    def read_hundreds(self, number):
        centena, decena = divmod(number, 100)
        if number == 0:
            result = 'cien'
        else:
            result = HOUNDREDS[centena]
            if decena > 0:
                result = '%s %s' % (result, self.read_tens(decena))
        return result

    def read_miles(self, number):
        millar, centena = divmod(number, 1000)
        result = ''
        if (millar == 1):
            result = ''
        if (millar >= 2) and (millar <= 9):
            result = UNITS[millar]
        elif (millar >= 10) and (millar <= 99):
            result = self.read_tens(millar)
        elif (millar >= 100) and (millar <= 999):
            result = self.read_hundreds(millar)
        result = '%s mil' % result
        if centena > 0:
            result = '%s %s' % (result, self.read_hundreds(centena))
        return result

    def read_millions(self, number):
        million, millar = divmod(number, 1000000)
        result = ''
        if (million == 1):
            result = ' un million '
        if (million >= 2) and (million <= 9):
            result = UNITS[million]
        elif (million >= 10) and (million <= 99):
            result = self.read_tens(million)
        elif (million >= 100) and (million <= 999):
            result = self.read_hundreds(million)
        if million > 1:
            result = '%s millones' % result
        if (millar > 0) and (millar <= 999):
            result = '%s %s' % (result, self.read_hundreds(millar))
        elif (millar >= 1000) and (millar <= 999999):
            result = '%s %s' % (result, self.read_miles(millar))
        return result

    def read_billion(self, number):
        billion, million = divmod(number, 1000000)
        return '%s millones %s' % (self.read_miles(billion), self.read_millions(million))