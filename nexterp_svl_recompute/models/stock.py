# Copyright (C) 2021 NextERP Romania SRL
# License OPL-1.0 or later
# (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#).


from odoo import api, fields, models
from odoo.tools import float_is_zero

import logging
_logger = logging.getLogger(__name__)


class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    new_unit_cost = fields.Monetary('New Unit Value', readonly=True)
    new_value = fields.Monetary('New Total Value', readonly=True)
    new_remaining_qty = fields.Float(digits=0, readonly=True)
    new_remaining_value = fields.Monetary('New Remaining Value', readonly=True)

    accounting_date = fields.Date(compute="_compute_accounting_date", store=True, string="Accounting Date")

    @api.depends('account_move_id', 'l10n_ro_invoice_id')
    def _compute_accounting_date(self):
        for svl in self:
            svl.accounting_date = (svl.account_move_id and svl.account_move_id.date) or (svl.l10n_ro_invoice_id and svl.l10n_ro_invoice_id.date) or svl.create_date

