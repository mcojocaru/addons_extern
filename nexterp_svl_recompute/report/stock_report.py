# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

import pytz
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StorageSheet(models.TransientModel):
    _inherit = "l10n.ro.stock.storage.sheet"
    
    use_svl_new_values = fields.Boolean(
        default=False
    )

    def do_compute_product(self):
        if not self.use_svl_new_values:
            super().do_compute_product()
            return

        product_list, all_products = self.get_report_products()

        self.env["account.move.line"].check_access_rights("read")

        lines = self.env["l10n.ro.stock.storage.sheet.line"].search(
            [("report_id", "=", self.id)]
        )
        lines.unlink()

        datetime_from = fields.Datetime.to_datetime(self.date_from)
        datetime_from = fields.Datetime.context_timestamp(self, datetime_from)
        datetime_from = datetime_from.replace(hour=0)
        datetime_from = datetime_from.astimezone(pytz.utc)

        datetime_to = fields.Datetime.to_datetime(self.date_to)
        datetime_to = fields.Datetime.context_timestamp(self, datetime_to)
        datetime_to = datetime_to.replace(hour=23, minute=59, second=59)
        datetime_to = datetime_to.astimezone(pytz.utc)
        for location in self.with_context(active_test=False).location_ids.ids:
            params = {
                "report": self.id,
                "location": location,
                "product": tuple(product_list),
                "all_products": all_products,
                "company": self.company_id.id,
                "date_from": fields.Date.to_string(self.date_from),
                "date_to": fields.Date.to_string(self.date_to),
                "datetime_from": fields.Datetime.to_string(datetime_from),
                "datetime_to": fields.Datetime.to_string(datetime_to),
                "tz": self._context.get("tz") or self.env.user.tz or "UTC",
            }

            query_select_sold_init = """
            select * from(
                SELECT %(report)s as report_id, prod.id as product_id,
                    COALESCE(sum(svl.new_value), 0)  as amount_initial,
                    COALESCE(sum(svl.quantity), 0)  as quantity_initial,
                    COALESCE(svl.l10n_ro_account_id, Null) as account_id,
                    %(date_from)s || ' 00:00:00' as date_time,
                    %(date_from)s as date,
                    %(reference)s as reference,
                    %(reference)s as document,
                    %(location)s as location_id
                from product_product as prod
                left join stock_move as sm ON sm.product_id = prod.id AND sm.state = 'done' AND
                    sm.company_id = %(company)s AND
                     sm.date <  %(datetime_from)s AND
                    (sm.location_id = %(location)s OR sm.location_dest_id = %(location)s)
                left join stock_valuation_layer as svl on svl.stock_move_id = sm.id and
                        ((l10n_ro_valued_type !='internal_transfer' or
                            l10n_ro_valued_type is Null
                         ) or
                         (l10n_ro_valued_type ='internal_transfer' and quantity<0 and
                          sm.location_id = %(location)s) or
                         (l10n_ro_valued_type ='internal_transfer' and quantity>0 and
                          sm.location_dest_id = %(location)s))
                where prod.id in %(product)s
                GROUP BY prod.id, svl.l10n_ro_account_id)
            a --where a.amount_initial!=0 and a.quantity_initial!=0
            """

            params.update({"reference": "INITIAL"})
            self.env.cr.execute(query_select_sold_init, params=params)
            res = self.env.cr.dictfetchall()
            self.line_product_ids.create(res)

            query_select_sold_final = """
            select * from(
                SELECT %(report)s as report_id, sm.product_id as product_id,
                    COALESCE(sum(svl.new_value),0)  as amount_final,
                    COALESCE(sum(svl.quantity),0)  as quantity_final,
                    COALESCE(svl.l10n_ro_account_id, Null) as account_id,
                    %(date_to)s || ' 23:59:59' as date_time,
                    %(date_to)s as date,
                    %(reference)s as reference,
                    %(reference)s as document,
                    %(location)s as location_id
                from stock_move as sm
                inner join  stock_valuation_layer as svl on svl.stock_move_id = sm.id and
                        ((l10n_ro_valued_type !='internal_transfer' or
                          l10n_ro_valued_type is Null
                         ) or
                         (l10n_ro_valued_type ='internal_transfer' and quantity<0 and
                          sm.location_id = %(location)s) or
                         (l10n_ro_valued_type ='internal_transfer' and quantity>0 and
                          sm.location_dest_id = %(location)s))
                where sm.state = 'done' AND
                    sm.company_id = %(company)s AND
                    ( %(all_products)s  or sm.product_id in %(product)s ) AND
                    sm.date <=  %(datetime_to)s AND
                    (sm.location_id = %(location)s OR sm.location_dest_id = %(location)s)
                GROUP BY sm.product_id, svl.l10n_ro_account_id)
            a --where a.amount_final!=0 and a.quantity_final!=0
            """

            params.update({"reference": "FINAL"})
            self.env.cr.execute(query_select_sold_final, params=params)
            res = self.env.cr.dictfetchall()
            self.line_product_ids.create(res)

            query_in = """
            select * from(


            SELECT  %(report)s as report_id, sm.product_id as product_id,
                    COALESCE(sum(svl_in.new_value),0)   as amount_in,
                    COALESCE(sum(svl_in.quantity), 0)   as quantity_in,
                    CASE
                        WHEN abs(COALESCE(sum(svl_in.quantity), 0)) > 0.001
                            THEN round(COALESCE(sum(svl_in.new_value),0) / sum(svl_in.quantity), 2)
                        ELSE 0
                    END as unit_price_in,
                     svl_in.l10n_ro_account_id as account_id,
                     svl_in.l10n_ro_invoice_id as invoice_id,
                    sm.date as date_time,
                    date_trunc('day', sm.date at time zone 'utc' at time zone %(tz)s) as date,
                    sm.reference as reference,
                    %(location)s as location_id,
                    sp.partner_id,
                    COALESCE(am.name, sm.reference) as document
                from stock_move as sm
                    inner join stock_valuation_layer as svl_in
                            on svl_in.stock_move_id = sm.id and
                        ((sm.location_dest_id = %(location)s and
                        svl_in.quantity>=0 and
                        l10n_ro_valued_type not like '%%_return') or
                        (sm.location_id = %(location)s and
                        (svl_in.quantity<=0 and l10n_ro_valued_type like '%%_return')))
                    left join stock_picking as sp on sm.picking_id = sp.id
                    left join account_move am on svl_in.l10n_ro_invoice_id = am.id
                where
                    sm.state = 'done' AND
                    sm.company_id = %(company)s AND
                    ( %(all_products)s  or sm.product_id in %(product)s ) AND
                    sm.date >= %(datetime_from)s  AND  sm.date <= %(datetime_to)s  AND
                    (sm.location_dest_id = %(location)s or sm.location_id = %(location)s)
                GROUP BY sm.product_id, sm.date,
                 sm.reference, sp.partner_id, account_id, svl_in.l10n_ro_invoice_id, am.name)
            a --where a.amount_in!=0 and a.quantity_in!=0
                """

            self.env.cr.execute(query_in, params=params)
            res = self.env.cr.dictfetchall()
            self.line_product_ids.create(res)

            query_out = """
            select * from(

            SELECT  %(report)s as report_id, sm.product_id as product_id,
                    -1*COALESCE(sum(svl_out.new_value),0)   as amount_out,
                    -1*COALESCE(sum(svl_out.quantity),0)   as quantity_out,
                    CASE
                        WHEN abs(COALESCE(sum(svl_out.quantity), 0)) > 0.001
                            THEN round(COALESCE(sum(svl_out.new_value),0) / sum(svl_out.quantity), 2)
                        ELSE 0
                    END as unit_price_out,
                    svl_out.l10n_ro_account_id as account_id,
                    svl_out.l10n_ro_invoice_id as invoice_id,
                    sm.date as date_time,
                    date_trunc('day', sm.date at time zone 'utc' at time zone %(tz)s) as date,
                    sm.reference as reference,
                    %(location)s as location_id,
                    sp.partner_id,
                    COALESCE(am.name, sm.reference) as document
                from stock_move as sm

                    inner join stock_valuation_layer as svl_out
                            on svl_out.stock_move_id = sm.id and
                        ((sm.location_id = %(location)s and
                        svl_out.quantity<=0 and
                        l10n_ro_valued_type not like '%%_return') or
                        (sm.location_dest_id =  %(location)s and
                        (svl_out.quantity>=0 and l10n_ro_valued_type like '%%_return')))
                    left join stock_picking as sp on sm.picking_id = sp.id
                    left join account_move am on svl_out.l10n_ro_invoice_id = am.id
                where
                    sm.state = 'done' AND
                    sm.company_id = %(company)s AND
                    ( %(all_products)s  or sm.product_id in %(product)s ) AND
                    sm.date >= %(datetime_from)s  AND  sm.date <= %(datetime_to)s  AND
                    (sm.location_id = %(location)s or sm.location_dest_id = %(location)s)
                GROUP BY sm.product_id, sm.date,
                         sm.reference, sp.partner_id, account_id,
                         svl_out.l10n_ro_invoice_id, am.name)
            a --where a.amount_out!=0 and a.quantity_out!=0
                """
            self.env.cr.execute(query_out, params=params)
            res = self.env.cr.dictfetchall()
            self.line_product_ids.create(res)


