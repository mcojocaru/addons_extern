# Copyright (C) 2023 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Stock Valuation Layer Fix Final Value",
    "version": "14.0.1.0.2",
    "category": "Localization",
    "summary": "Romania - Stock Valuation Layer Fix Final Value",
    "author": "NextERP Romania",
    "website": "https://nexterp.ro",
    "depends": ["l10n_ro_stock_account"],
    "license": "AGPL-3",
    "data": [
        "wizard/stock_valuation_layer_fix_final.xml",
        "security/ir.model.access.csv",        
    ],
    "installable": True,
    "maintainers": ["feketemihai"],
}
