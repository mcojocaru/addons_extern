# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Stock Valuation Layer Recomputation",
    "version": "14.0.1.0.3",
    "category": "Localization",
    "summary": "Romania - Stock Valuation Layer Recomputation",
    "author": "NextERP Romania," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": ["l10n_ro_stock_account", "l10n_ro_stock_report"],
    "license": "AGPL-3",
    "data": [
        "wizard/stock_valuation_layer_recompute_views.xml",
        "report/stock_report_view.xml",
        "views/stock_valuation_layer_views.xml",
        "security/ir.model.access.csv",        
    ],
    "installable": True,
    "maintainers": ["feketemihai"],
}
