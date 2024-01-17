# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from collections import defaultdict
from datetime import datetime, time


class SVLFixFinalProduct(models.TransientModel):
    _name = 'svl.fix.final.product'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    product_id = fields.Many2one(
        'product.product', string='Product',
    )    
    location_id = fields.Many2one(
        'stock.location', string='Location',
    )        
    wizard_id = fields.Many2one(
        'svl.fix.final', string='Field Label',
    )
    last_svl_id = fields.Many2one(
        'stock.valuation.layer', compute_sudo=True, 
        store=True, compute='_compute_final_values'
    )
    final_value = fields.Float(readonly=True)
    fix_final_date= fields.Date(
        compute='_compute_final_values', store=True, compute_sudo=True,
        readonly=False
    )
    svl_last_date = fields.Datetime(
        string="Last SVL Date", related='last_svl_id.create_date'
    )

    @api.depends('product_id', 'location_id')
    def _compute_final_values(self):
        for rec in self:
            rec.last_svl_id = self.env['stock.valuation.layer']
            rec.svl_last_date = rec.wizard_id.je_post_date            
            svl = self.env['stock.valuation.layer'].search(
                [
                    ('product_id', '=', rec.product_id.id), 
                    ('l10n_ro_location_id', '=', rec.location_id.id),
                    ('company_id', '=', rec.wizard_id.company_id.id),
                ], 
                order='create_date desc', limit=1
            )
            if svl:
                rec.last_svl_id = svl.id
                rec.svl_last_date = svl.create_date
                # svl_date = datetime.combine(svl.create_date, time.min)
                svl_date = fields.Date.to_date(svl.create_date)
                if rec.wizard_id.je_post_date and rec.wizard_id.je_post_date >= svl_date:
                    rec.fix_final_date = rec.wizard_id.je_post_date
                else:
                    rec.fix_final_date = svl_date

    @api.onchange('fix_final_date')
    def onchange_fix_final_date(self):
        svl_date = fields.Date.to_date(self.create_date)
        svl_last_date = fields.Date.to_date(self.svl_last_date)
        if self.fix_final_date < svl_last_date:
            raise UserError(
                _('Date must be greater than or equal to {}').format(
                    self.svl_last_date
                )
            )


class StockValuationLayerFixFinalValue(models.TransientModel):
    _name = 'svl.fix.final'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    je_post_date = fields.Date(
        'Journal Entries Date', 
        default=fields.Date.today, 
        required=True
    )
    product_ids = fields.One2many(
        'svl.fix.final.product',
        'wizard_id',
        string='Products',
    )
    create_journal_entries = fields.Boolean(
        string='Create Journal Entries', default=False
    )

    @api.model
    def default_get(self, _fields):
        res = super().default_get(_fields)
        company = self.env.company
        res['company_id'] = company.id
        res['je_post_date'] = fields.Date.today()
        domain_locations = [
            ('usage', '=', 'internal'), 
            ('scrap_location', '=', False),
            ('company_id', '=', self.env.company.id)
        ]
        locations = self.env['stock.location'].search(domain_locations, order="id")
        products = self.env['product.product'].with_context(active_test=False)
        products = products.search([('type', '=', 'product')], order="id")
        products = products.filtered(lambda p: p.valuation == 'real_time')

        product_lines = []
        today = fields.Date.today()         
        prec_digits = company.currency_id.decimal_places
        idx = 10        
        for location_id in locations:
            domain = [
                '|',
                    ("l10n_ro_location_dest_id", "=", location_id.id),
                    ("l10n_ro_location_id", "=", location_id.id),
                ("product_id", "in", products.ids),
                ("company_id", "=", company.id),
            ]            
            groups = self.env["stock.valuation.layer"].read_group(
                domain,
                [
                    "value:sum",
                    "quantity:sum",
                ],
                ["product_id"],
            )
            products = self.browse()
            for group in groups:
                prod = self.env['product.product'].browse(group["product_id"][0])
                value_svl = self.env.company.currency_id.round(group["value"])
                quantity_svl = group["quantity"]
                # if qty == 0:
                #     print(f"prod: {prod.id} - qty: {qty} - val: {val} - name: {prod.name} - location: {location_id.name}")
                if (
                    float_is_zero(quantity_svl, precision_rounding=prod.uom_id.rounding)                    
                    and not float_is_zero(value_svl, precision_rounding=prec_digits)
                ):
                    line_fields = [f for f in self.env['svl.fix.final.product']._fields.keys()]
                    line_data_tmpl = self.env['svl.fix.final.product'].default_get(line_fields)
                    line_data = dict(line_data_tmpl)
                    line_data.update({
                        'sequence': idx, 
                        'product_id': prod.id,
                        'location_id': location_id.id,
                        'final_value': value_svl,
                        'wizard_id': self.id,
                    })
                    product_lines.append((0, 0, line_data))
                    idx += 10

        res['product_ids'] = product_lines
        return res

    @api.onchange('je_post_date')
    def onchange_fix_final_date(self):
        for line in self.product_ids:
            line.fix_final_date = self.je_post_date

    def buttton_do_correction(self):
        for line in self.product_ids:
            svl = self.env['stock.valuation.layer'].create([{
                'product_id': line.product_id.id,
                'description': "0 QTY Fix final value",
                'company_id': line.wizard_id.company_id.id,
                'value': -line.final_value,
                'quantity': 0,
                'l10n_ro_location_id': line.location_id.id,
                'l10n_ro_location_dest_id': line.location_id.id,
                'stock_move_id': line.last_svl_id.stock_move_id.id,
                'l10n_ro_valued_type': line.last_svl_id.l10n_ro_valued_type,
            }])
            svl.update({'create_date': line.fix_final_date})
            if self.create_journal_entries:
                sm = svl.stock_move_id
                sm.with_context(force_period_date=svl.create_date)._account_entry_move(
                    svl.quantity, svl.description, svl.id, svl.value
                )