# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from collections import defaultdict
import logging
_logger = logging.getLogger(__name__)

"""
#
#prods = ['AA.GN4801.00','AE.MO.14DBRS0K00','AE.MO.TB4BRS0K00','AI.MO.89103','AL.SKN.21007','AL.SKN.21010','AL.SKN.21012','AL.SKN.21013','AL.SKN.21050','AL.SKN.21090','AL.SKN.21148','AL.SKN.21149','AL.SKN.21165','AL.SKN.21166','AL.SKN.21167','AL.SKN.21391','AL.SKN.21401','AL.SKN.21403','AL.SKN.21539','BB.HZ.9045436','BB.MO4112.80','BB.MO4113.00','BC.HZ.9486420','BF.FO.21205','BF.FO.21636','BF.FO.22303','BF.VI.2140T','BF.VI.2140V','BH.NKI.4830','DA.TS.428048.11','DH.GN6010.91','EA.EVL.2154015','EA.EVL.2154045','FA.SN.18000200002','FA.SN.18000200004','FA.SN.18000200008','FC.FO.60902','FE.CP.9610','FH.FO.60711','FH.SN.340102','FH.SN.340105','GB.BC.921403','GB.CP2225.1003','GB.FO.51405','GB.FO.51517','GB.SD.003080','GB.SD.023080','GB.SD.033080','GB.SN.18000300004','GB.SN.18000300005','GB.SN.18000300007','GF.CP2631.5111','GF.CP4621.0202','GF.CP4621.0203','GG.CP4615.9302','GL.CP2536.01','GL.CP2634.02','GL.CP2634.03','GL.CP2637.01','GL.CP2686.00','GL.CP2836.01','GL.CP2846.01','GL.CP3616.01','GL.CP8559.01','GL.CP8559.02','GL.CP8559.03','GL.CP8559.06','GL.CP8559.07','GL.CP8559.22','GL.CP8566.01','GL.CP8566.02','GL.CP8566.03','GL.CP8566.99','GL.CP8576.01','GL.CP8576.03','GL.CP8586.00','GL.CP8599.01','GL.SN.180001000','GL.SN.180002000','GL.SN.180004000','GL.SN.180006000','GO.SN.18000100021','GO.SN.18000101059','HB.CP3649.0002','HB.CP7550.30','HB.CP9520.18','HC.CP9540.12','PF.SN.8103223']
prods = self.env['product.product'].browse(718)
for prod in prods:
    print(f"PRODUCT={prod}")
    fields = self.env['svl.recompute']._fields
    fields = list(fields.keys())
    defaults = self.env['svl.recompute'].default_get(fields)
    defaults.update(
        company_id=2, 
        debug=True, 
        recompute_type='fifo_average', 
        date_from='2022-01-01', 
        run_svl_recompute=True, 
        fix_remaining_qty=True,         
        update_svl_values=True, 
        compute_locations=True,        
        update_account_moves=False
    )
    wiz = self.env['svl.recompute'].create(defaults)
    wiz.product_ids = [(6, 0, prod.ids)]
    print(f"{wiz.product_ids}")
    wiz.buttton_do_correction()
self._cr.commit()


"""
class SVLRecomputeLocation(models.TransientModel):
    _name = 'svl.recompute.location'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
    )
    svl_recompute_id = fields.Many2one(
        'svl.recompute',
        string='Field Label',
    )


class StockValuationLayerRecompute(models.TransientModel):
    _name = 'svl.recompute'
    _check_company_auto = True

    recompute_type = fields.Selection(
        selection=[('fifo_average', 'FIFO/Average'), 
        ('manufacturing', 'Manufacturing Orders')], string="Type", default="fifo_average")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    product_ids = fields.Many2many('product.product', string="Related products", check_company=True)
    lot_id = fields.Many2one('stock.production.lot')
    date_from = fields.Date("Recompute Start Date")
    account_move_date = fields.Date("Account Move Date >=")

    location_ids = fields.One2many(
        'svl.recompute.location',
        'svl_recompute_id',
        string='Locations',
        readonly=False,
        store=True,
    )
    run_svl_recompute = fields.Boolean(
        default=True
    )
    fix_remaining_qty = fields.Boolean('Fix Remaining Qty/Val',
        default=True
    )
    update_svl_values = fields.Boolean(
        default=False
    )
    update_account_moves = fields.Boolean(
        default=False
    )    
    debug = fields.Boolean(default=False)
    compute_locations = fields.Boolean(default=False) 


    @api.onchange('update_account_moves')
    def onchange_upd_account_moves(self):
        if self.update_account_moves is True:
            self.update_svl_values = True

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        locs = self.env['stock.location'].search([
            ('usage', '=', 'internal'), ('scrap_location', '=', False)
        ], order="id")

        location_ids = []
        idx = 10
        for loc in locs:
            location_ids.append((0, 0, {
                'sequence': idx, 'location_id': loc.id
            }))
            idx += 10
        res['location_ids'] = location_ids
        return res

    @api.onchange('lot_id')
    def onchange_lot(self):
        self.product_ids = [(6, 0, self.lot_id.product_id.ids)]

    @api.onchange('product_ids')
    def onchange_product(self):
        if self.product_ids:
            svls = self.env['stock.valuation.layer'].search([
                ('product_id', 'in', self.product_ids.ids),
                ('company_id', '=', self.company_id.id)
            ])
            locs = set(svls.mapped('l10n_ro_location_id') + svls.mapped('l10n_ro_location_dest_id'))
            locs = list(filter(lambda l: l._should_be_valued(), locs))
            wiz_locs = list(filter(lambda l: l.location_id in locs, self.location_ids))
            self.location_ids = [(6, 0, [l.id for l in wiz_locs])]

    def buttton_do_correction(self):
        archived_locs = self.env['stock.location'].search([('active', '=', False)])
        archived_locs.write({'active': True})

        self._prepare_svls()
        if self.run_svl_recompute:
            self.action_start_recompute()
        if self.fix_remaining_qty:
            self._fix_remaining_qty_value()                
        self._finalize_svls()        

        archived_locs.write({'active': False})

    def _prepare_svls(self):
        #backup unit_cost and value
        if self.product_ids:
            products = self.product_ids
        else:
            products = self.env['product.product'].search([])

        locations = self.location_ids.mapped('location_id')
        domain = [
                    ('company_id', '=', self.company_id.id),
                    ('product_id', 'in', products.ids),
                    '|',
                        ('l10n_ro_location_dest_id', 'in', locations.ids),
                        ('l10n_ro_location_id', "in", locations.ids),
                ]
        svls = self.env['stock.valuation.layer'].search(domain)
        for svl in svls:
            svl.new_unit_cost = svl.unit_cost
            svl.new_value = svl.value
            svl.new_remaining_value = svl.remaining_value
            svl.new_remaining_qty = svl.remaining_qty

    def _compute_lot_locations(self, product, lot):
        if self.debug:
            _logger.info(f"_compute_lot_locations for {product.name_get()[0][1]}, LOT={lot and lot.name}")
        locs = []
        walked_moves = []

        def walk(mvl):  
            if self.debug:
                _logger.info(f"walk mvl {mvl.location_id.name_get()}, {mvl.location_dest_id.name_get()}")
            loc = mvl.location_dest_id
            if loc._should_be_valued() and loc not in locs:
                if lot:
                    if lot == mvl.lot_id:
                        if self.debug: _logger.info(f"added loc {loc.name_get()}")
                        locs.append(loc)
                    else:
                        if self.debug: _logger.info(f"NOT added loc {loc.name_get()}")  
                else:
                    if product == mvl.product_id:
                        if self.debug: _logger.info(f"added loc {loc.name_get()}")
                        locs.append(loc)
                    else:
                        if self.debug: _logger.info(f"NOT added loc {loc.name_get()}")  

            else:
                if self.debug:
                    if loc._should_be_valued():
                        _logger.info(f" not valued {mvl.location_dest_id.name_get()}")
                    else:
                        _logger.info(f" already in locs {mvl.location_dest_id.name_get()}")


            if not mvl.move_id._is_out():
                domain = [
                    ('state', '=', 'done'),
                    ('company_id', '=', mvl.company_id.id),
                    ('product_id', '=', mvl.product_id.id),
                    ('location_id', '=', mvl.location_dest_id.id),
                    ('product_id', '=', product.id)
                ]
                if lot:
                    domain += [('lot_id', '=', lot.id)]

                next_moves = self.env['stock.move.line'].search()
                for m in next_moves:
                    if m not in walked_moves:
                        walked_moves.append(m)
                        walk(m)
  
        domain = [
            ('company_id', '=', self.company_id.id),
            ('product_id', '=', product.id),
            ('location_id.usage', 'in', ('supplier', 'inventory'))
        ]
        if lot:
            domain += [('lot_ids', 'in', lot.ids)]
        svls = self.env['stock.valuation.layer'].search(domain)
        for svl in svls:
            walked_movs = []
            walk(svl.stock_move_line_id)

        domain_all = [
            ('company_id', '=', self.company_id.id),
            ('product_id', '=', product.id),
        ]
        if lot:
            domain_all += [('lot_ids', 'in', lot.ids)]

        svls_all = self.env['stock.valuation.layer'].search(domain_all)
        svls_out = svls_all.filtered(lambda s: s.stock_move_id._is_out())
        for so in svls_out:
            if so.location_id not in locs:
                locs.append(so.location_id)

        return locs

    def action_start_recompute(self):
        if self.product_ids:
            products = self.product_ids
        else:
            products = self.env['product.product'].search([])

        locations = self.location_ids.sorted(lambda l: l.sequence)

        locs = [l.location_id for l in locations]
        if self.recompute_type == 'fifo_average':
            for product in products:
                if product.cost_method == "fifo":

                    lot_ids = self.env['stock.production.lot']
                    if self.lot_id:
                        lot_ids = self.lot_id
                    else:
                        lot_ids = self.env['stock.production.lot'].search([
                            ('product_id', '=', product.id)
                        ])
                    

                    if self.compute_locations and lot_ids:
                        for lot in lot_ids:
                            computed_locs = self._compute_lot_locations(product, lot)
                            if self.debug:
                                _logger.info(f"COMPUTED LOCATIONS={[l.name_get()[0][1] for l in computed_locs]}")

                            for loc in computed_locs:
                                self._run_fifo(product, loc, lot_id=lot)
                    else:    
                        if self.compute_locations:
                            locs = self._compute_lot_locations(product, None)
                        for loc in locs:
                            if lot_ids:
                                for lot in lot_ids:
                                    self._run_fifo(product, loc, lot_id=lot)
                            else:
                                self._run_fifo(product, loc)

                if product.cost_method == "average":
                    self._run_average(product, locations.ids)
        else:
            self.recompute_manufacturing_orders(products)

        return True


    def action_check_products(self):
        if self.product_ids:
            products = self.product_ids
        else:
            products = self.env['product.product'].search([])
        locations = self.location_ids.mapped('location_id')

        result = []
        if self.recompute_type == 'fifo_average':
            for product in products:
                if product.cost_method == "average":
                    is_diff, _date, diff = self._check_average(product, locations.ids)
                    if is_diff:
                        result.append((product.default_code, _date, diff))

        msg = "\n".join([f"{prod[0]} - {prod[1]} - {prod[2]}" for prod in result])
        raise UserError(msg)

    def _delete_out_lcs(self, svl_loc_out):
        #delete landed costs for svls out
        svl_loc_out_lc = self.env['stock.valuation.layer'].search(
            [('stock_valuation_layer_id', 'in', svl_loc_out.ids),
            ('l10n_ro_valued_type', 'in', ('consumption', 'delivery', 'internal_transfer'))]
        )
        if svl_loc_out_lc:
            svl_loc_out_lc.mapped('account_move_id').button_draft()
            svl_loc_out_lc.mapped('account_move_id').button_cancel()
            self._cr.execute('delete from stock_valuation_layer where id in %s', (tuple(svl_loc_out_lc.ids),))        

    def _check_average(self, product, locations):
        self = self.sudo()

        def _check_diff(new_value, svl):
            if (svl.stock_landed_cost_id or 
                (svl.stock_valuation_layer_id and svl.l10n_ro_valued_type in ('delivery', 'consumption', 'reception_return'))):
                return False
                
            svl_val = svl.value + sum([s.value for s in svl.stock_valuation_layer_ids])
            diff = abs(round(abs(new_value) - abs(svl_val), 2))
            if diff > 0.4:
                return diff
            return False

        date_from = fields.Datetime.to_datetime(self.date_from)
        avg = [0, 0]
        product = product.with_context(to_date=self.date_from)
        last_svl_before_date = None

        if product.quantity_svl > 0.01:
            quantity_svl = round(product.quantity_svl, 2)
            value_svl = max(0, round(product.value_svl, 2))
            avg = [round(value_svl / quantity_svl, 2), quantity_svl]
        else:
            dom = ['&',
                '&',
                    ('product_id', '=', product.id),
                    ('create_date', '<', date_from),
                '|',
                        ('l10n_ro_location_dest_id', 'in', locations),
                        ('l10n_ro_location_id', "in", locations),
                ]

            value_svl = product.value_svl
            last_svl_before_date = self.env['stock.valuation.layer'].search(
                    dom, limit=1, order='create_date desc')            
            if round(value_svl, 6):
                if last_svl_before_date:
                    svl = self.env['stock.valuation.layer'].create({
                     'company_id': self.company_id.id,
                     'product_id': product.id,
                     'create_date': last_svl_before_date.create_date,
                     'stock_move_id': last_svl_before_date.stock_move_id.id,
                     'quantity': 0,
                     'value': -value_svl,
                     'new_value': -value_svl,
                     'description': "fix 0 qty value for BEFORE RECOMPUTE DATE",
                     'l10n_ro_location_id': last_svl_before_date.l10n_ro_location_id.id,
                     'l10n_ro_location_dest_id': last_svl_before_date.l10n_ro_location_dest_id.id,
                     'l10n_ro_account_id': last_svl_before_date.l10n_ro_account_id.id
                    })
                    self._cr.execute("update stock_valuation_layer set create_date = '%s' where id = %s" % (
                        last_svl_before_date.create_date, svl.id))
                    #svl.stock_move_id.with_context(force_period_date=svl.create_date)._account_entry_move(
                    #    svl.quantity, svl.description, svl.id, svl.value)    


        domain = ['&',
                    '&',
                        ('product_id', '=', product.id),
                        ('create_date', '>=', date_from),
                    '|',
                        '&',
                            ('description', 'like', 'Product value manually modified'),
                            ('l10n_ro_valued_type', '=', False),
                        '|',
                            '&',
                                ('l10n_ro_location_dest_id', 'in', locations),
                                ('quantity', '>', 0.001),
                            '&',
                                ('l10n_ro_location_id', "in", locations),
                                ('quantity', '<', 0.001),
                ]

        svls = self.env['stock.valuation.layer'].search(domain).sorted(lambda svl: svl.create_date)

        #delete landed costs for svls out
        svl_loc_out = svls.filtered(lambda svl: svl.quantity < 0)

        svls = list(svls)
        while svls:
            svl = svls[0]

            if not svl.l10n_ro_valued_type and svl.quantity == 0 and avg[1] > 0:
                #Product value manually modified
                old_value = avg[0] * avg[1]
                new_avg = (old_value + svl.value) / (avg[1])
                avg = [new_avg, avg[1]]

            else:
                if svl.l10n_ro_valued_type and 'return' in svl.l10n_ro_valued_type:
                    orig_mv = svl.stock_move_id.move_orig_ids
                    if orig_mv:
                        svl_orig = orig_mv.stock_valuation_layer_ids
                        val = abs(sum([s.value for s in svl_orig]))
                        qty = sum([s.quantity for s in svl_orig])
                        if abs(qty) > 0.001 :
                            new_value = round(svl.quantity * abs(val / qty), 2)
                            if _check_diff(new_value, svl):
                                return True, svl.create_date, _check_diff(new_value, svl)

                if (
                        svl.stock_move_id and
                        (
                            svl.stock_move_id._is_in() or
                            (
                                svl.stock_move_id._is_internal_transfer()
                                and
                                (
                                    svl.stock_move_id.location_id.company_id !=
                                    svl.stock_move_id.location_dest_id.company_id
                                )
                                and
                                (
                                    svl.company_id == svl.l10n_ro_location_dest_id.company_id
                                )
                            )
                        ) or
                        (
                            svl.stock_move_id._is_internal_transfer() and
                            svl.l10n_ro_location_id.scrap_location and
                            svl.quantity > 0
                        )
                    ):
                    #update average cost
                    if  svl.quantity > 0:
                        old_value = avg[0] * avg[1]
                        #include landed costs and price diffs
                        svl_val = sum([s.value for s in (svl + svl.stock_valuation_layer_ids)])

                        if (avg[1] + svl.quantity) > 0:
                            new_avg = (old_value + svl_val) / (avg[1] + svl.quantity)
                        else:
                            new_avg = 0

                        avg = [new_avg, avg[1] + svl.quantity]

                elif (
                        svl.stock_move_id._is_out() or 
                        (
                            svl.stock_move_id._is_internal_transfer() and 
                            svl.l10n_ro_location_dest_id.scrap_location and
                            svl.quantity < 0
                        )
                    ):
                    svl_qty = abs(svl.quantity)
                    if  0 >= avg[1] or avg[1] < svl_qty:
                        #move svl later, after a reception
                        #return True, svl.create_date
                        pass

                    else:
                        if 'return' not in svl.l10n_ro_valued_type:
                            new_value = round(avg[0] * svl.quantity, 2)
                            if _check_diff(new_value, svl):
                                return True, svl.create_date, _check_diff(new_value, svl)
                        else:
                            if (avg[1] - abs(svl.quantity)) > 0:
                                avg[0] = (avg[0] * avg[1] - abs(svl.value)) / (avg[1] - abs(svl.quantity))
                            else:
                                avg[0] = 0
                        avg[1] = max(0, avg[1] - abs(svl.quantity))

                elif svl.stock_move_id._is_internal_transfer() and svl.quantity < 0:
                    new_value = round(avg[0] * svl.quantity, 2)                      
                    if _check_diff(new_value, svl):
                        return True, svl.create_date, _check_diff(new_value, svl)
                    
                    if svl.company_id != svl.l10n_ro_location_dest_id.company_id:
                        svl_qty = abs(svl.quantity)
                        if avg[1] <= 0 or avg[1] < svl_qty:
                            should_break = shift_svl0_later(svls)
                            if should_break:
                                return True, svl.create_date, False

                        else:
                            if (avg[1] - abs(svl.quantity)) > 0:
                                avg[0] = (avg[0] * avg[1] - abs(svl.value)) / (avg[1] - abs(svl.quantity))
                            else:
                                avg[0] = 0
                            avg[1] = max(0, avg[1] - abs(svl.quantity))


            svls = svls[1:]

        return False, False, False


    def _run_average(self, product, locations):
        self = self.sudo()

        def shift_svl0_later(svls):
            should_break = False
            svl_qty = abs(svl.quantity)
            #move svl later, after a reception

            idx = -1
            for i in range(len(svls)):
                if svls[i].quantity > 0:
                    if svls[i].quantity >= svl_qty:
                        idx = i
                        break
                    else:
                        svl_qty -= svls[i].quantity
            if idx != -1:
                svls.insert(idx + 1, svl)
            else:
                print(f"NEGATIVE SVL: {svl.id} {svl.description}")
                print(svls)
                should_break = True
            return should_break

        date_from = fields.Datetime.to_datetime(self.date_from)
        avg = [0, 0]
        product = product.with_context(to_date=self.date_from)
        last_svl_before_date = None
 
        if product.quantity_svl > 0.01:
            quantity_svl = round(product.quantity_svl, 2)
            value_svl = max(0, round(product.value_svl, 2))
            avg = [round(value_svl / quantity_svl, 2), quantity_svl]
        else:
            dom = ['&',
                '&',
                    ('product_id', '=', product.id),
                    ('create_date', '<', date_from),
                '|',
                        ('l10n_ro_location_dest_id', 'in', locations),
                        ('l10n_ro_location_id', "in", locations),
                ]

            value_svl = product.value_svl
            last_svl_before_date = self.env['stock.valuation.layer'].search(
                    dom, limit=1, order='create_date desc')            
            if round(value_svl, 6):
                if last_svl_before_date:
                    svl = self.env['stock.valuation.layer'].create({
                     'company_id': self.company_id.id,
                     'product_id': product.id,
                     'create_date': last_svl_before_date.create_date,
                     'stock_move_id': last_svl_before_date.stock_move_id.id,
                     'quantity': 0,
                     'value': -value_svl,
                     'new_value': -value_svl,
                     'description': "fix 0 qty value for BEFORE RECOMPUTE DATE",
                     'l10n_ro_location_id': last_svl_before_date.l10n_ro_location_id.id,
                     'l10n_ro_location_dest_id': last_svl_before_date.l10n_ro_location_dest_id.id,
                     'l10n_ro_account_id': last_svl_before_date.l10n_ro_account_id.id
                    })
                    self._cr.execute("update stock_valuation_layer set create_date = '%s' where id = %s" % (
                        last_svl_before_date.create_date, svl.id))
                    #svl.stock_move_id.with_context(force_period_date=svl.create_date)._account_entry_move(
                    #    svl.quantity, svl.description, svl.id, svl.value)    


        domain = ['&',
                        ('company_id', '=', self.company_id.id),    
                        '&',
                            '&',
                                ('product_id', '=', product.id),
                                ('create_date', '>=', date_from),
                            '|',
                                '&',
                                    ('description', 'like', 'Product value manually modified'),
                                    ('l10n_ro_valued_type', '=', False),
                                '|',
                                    '&',
                                        ('l10n_ro_location_dest_id', 'in', locations),
                                        ('quantity', '>', 0.001),
                                    '&',
                                        ('l10n_ro_location_id', "in", locations),
                                        ('quantity', '<', 0.001),
                ]

        svls = self.env['stock.valuation.layer'].search(domain).sorted(lambda svl: svl.create_date)

        #delete landed costs for svls out
        svl_loc_out = svls.filtered(lambda svl: svl.quantity < 0)
        #self._delete_out_lcs(svl_loc_out)

        svls = list(svls)
        last_avg = avg[0]
        while svls:
            svl = svls[0]
            if not svl.l10n_ro_valued_type and svl.quantity == 0 and avg[1] > 0:
                #Product value manually modified
                old_value = avg[0] * avg[1]
                new_avg = (old_value + svl.value) / (avg[1])
                avg = [new_avg, avg[1]]

            else:
                if svl.l10n_ro_valued_type and 'return' in svl.l10n_ro_valued_type:
                    orig_mv = svl.stock_move_id.move_orig_ids
                    if orig_mv:
                        svl_orig = orig_mv.stock_valuation_layer_ids
                        val = abs(sum([s.value for s in svl_orig]))
                        qty = sum([s.quantity for s in svl_orig])
                        if abs(qty) > 0.001 :
                            svl.value = round(svl.quantity * abs(val / qty), 2)
                            svl.unit_cost = round(abs(val / qty), 2)
                        else:
                            svl.value = 0
                            svl.unit_cost = 0

                if (
                        svl.stock_move_id and
                        (
                            svl.stock_move_id._is_in() or
                            (
                                svl.stock_move_id._is_internal_transfer()
                                and
                                (
                                    svl.stock_move_id.location_id.company_id !=
                                    svl.stock_move_id.location_dest_id.company_id
                                )
                                and
                                (
                                    svl.company_id == svl.l10n_ro_location_dest_id.company_id
                                )
                            )
                        ) or
                        (
                            svl.stock_move_id._is_internal_transfer() and
                            svl.l10n_ro_location_id.scrap_location and
                            svl.quantity > 0
                        )
                    ):
                    #update average cost
                    if  svl.quantity > 0:
                        old_value = avg[0] * avg[1]
                        #include landed costs and price diffs
                        svl_val = sum([s.value for s in (svl + svl.stock_valuation_layer_ids)])

                        if (avg[1] + svl.quantity) > 0:
                            new_avg = (old_value + svl_val) / (avg[1] + svl.quantity)
                        else:
                            new_avg = 0

                        avg = [new_avg, avg[1] + svl.quantity]

                elif (
                        svl.stock_move_id._is_out() or 
                        (
                            svl.stock_move_id._is_internal_transfer() and 
                            svl.l10n_ro_location_dest_id.scrap_location and
                            svl.quantity < 0
                        )
                    ):
                    svl_qty = abs(svl.quantity)
                    if  0 >= avg[1] or avg[1] < svl_qty:
                        #move svl later, after a reception
                        should_break = shift_svl0_later(svls)
                        if should_break:
                            break
                    else:
                        if 'return' not in svl.l10n_ro_valued_type:
                            svl.unit_cost = round(avg[0], 2)
                            svl.value = round(avg[0] * svl.quantity, 2)
                        else:
                            if (avg[1] - abs(svl.quantity)) > 0:
                                avg[0] = (avg[0] * avg[1] - abs(svl.value)) / (avg[1] - abs(svl.quantity))
                            else:
                                avg[0] = 0
                        avg[1] = max(0, avg[1] - abs(svl.quantity))

                elif svl.stock_move_id._is_internal_transfer() and svl.quantity < 0:
                    svl.unit_cost = round(avg[0], 2)
                    svl.value = round(avg[0] * svl.quantity, 2)                      

                    svl_plus = svl.stock_move_id.sudo().stock_valuation_layer_ids.filtered(lambda s: s.quantity > 0)
                    if svl.company_id != svl.l10n_ro_location_dest_id.company_id:
                        mv_dest = svl.stock_move_id.with_company(svl.l10n_ro_location_dest_id.company_id).move_dest_ids
                        svl_plus |= mv_dest.sudo().stock_valuation_layer_ids#.filtered(lambda s: s.quantity > 0)

                    for svlp in svl_plus:
                        svlp.sudo().unit_cost = round(avg[0], 2)
                        svlp.sudo().value = round(svlp.quantity * avg[0], 2)               
                    
                    if svl.company_id != svl.l10n_ro_location_dest_id.company_id:
                        svl_qty = abs(svl.quantity)
                        if avg[1] <= 0 or avg[1] < svl_qty:
                            should_break = shift_svl0_later(svls)
                            if should_break:
                                break
                        else:
                            if (avg[1] - abs(svl.quantity)) > 0:
                                avg[0] = (avg[0] * avg[1] - abs(svl.value)) / (avg[1] - abs(svl.quantity))
                            else:
                                avg[0] = 0
                            avg[1] = max(0, avg[1] - abs(svl.quantity))


            svls = svls[1:]
            last_avg = round(avg[0], 3) or last_avg

        if not round(last_avg, 3) and last_svl_before_date:
            last_avg = last_svl_before_date.unit_cost
        product.sudo().with_company(self.env.company).with_context(disable_auto_svl=True).standard_price = last_avg

    def _run_fifo(self, product, loc):
        if self.debug:
            _logger.info(f"PRODUCT={product}, LOCATION={loc.name_get()[0][1]}, LOT={lot_id and lot_id.name or ''}")
        date_from = fields.Datetime.to_datetime(self.date_from)
        
        date_domain = [('create_date', '>=', date_from)]
        domain_company = [('company_id', '=', self.company_id.id)]
        domain_in = (
            domain_company + date_domain + 
            [
                ('product_id', '=', product.id), 
                ("l10n_ro_location_dest_id", "=", loc.id), 
                ('l10n_ro_quantity', '>', 0.001)
            ]
        )

        if lot_id:
            domain_in += [('lot_ids', 'in', lot_id.ids)]
        svl_loc_in = self.env['stock.valuation.layer'].search(domain_in)

        domain_out = (
            domain_company + date_domain + 
            [
                ('product_id', '=', product.id), 
                ("l10n_ro_location_id", "=", loc.id), 
                ('quantity', '<', 0)
            ]
        )
        if lot_id:
            domain_out += [('lot_ids', 'in', lot_id.ids)]

        svl_loc_out = self.env['stock.valuation.layer'].search(domain_out)

        svl_loc_in = svl_loc_in.sorted(lambda svl: svl.create_date)
        svl_loc_out = svl_loc_out.sorted(lambda svl: svl.create_date)

        #delete landed costs for svls out
        #self._delete_out_lcs(svl_loc_out)

        should_restart_fifo = True
        restart_counter = 0
        while should_restart_fifo:
            should_restart_fifo = False

            quantity = abs(sum(svl_loc_out.mapped('quantity')))
            # build fifo list, [qty, unit_cost] pairs
            fifo_lst = []
            t_qty = quantity
            for svl_in in svl_loc_in:
                value = sum([s.value for s in (svl_in + svl_in.stock_valuation_layer_ids)])
                unit_cost = value / svl_in.quantity
                if t_qty > svl_in.quantity:
                    fifo_lst.append([svl_in.quantity, unit_cost, value, svl_in.stock_move_id, svl_in])
                    t_qty -= svl_in.quantity
                else:
                    fifo_lst.append([t_qty, unit_cost, value, svl_in.stock_move_id, svl_in])
                    break
            # assign unit cost to delivery svls based on fifo_lst
            if self.debug:
                _logger.info(f"FIFO LST={fifo_lst}")                
                _logger.info(f"SVL OUT LST={svl_loc_out}")

            if fifo_lst:
                last_price = fifo_lst[0][1]

                #handle reception returns separately
                svl_loc_out_rr = svl_loc_out.filtered(self.is_reception_return)
                for svl_out in svl_loc_out_rr:
                    if self.debug:
                        _logger.info(f"FIFO LST={fifo_lst}")                                   

                    if self.is_reception_return(svl_out):
                        for i in range(len(fifo_lst)):
                            fifo_entry = fifo_lst[i]
                            if fifo_entry[3] in svl_out.stock_move_id.move_orig_ids:
                                fifo_entry[0] -= abs(svl_out.quantity)
                                if svl_out.unit_cost != fifo_entry[1]:
                                    # fix reception_return unit_cost and value
                                    svl_out.unit_cost = fifo_entry[1]
                                    svl_out.value = fifo_entry[1] * svl_out.quantity
                                if fifo_entry[0] == 0:
                                    del fifo_lst[i]
                                break

                svl_loc_out = svl_loc_out.filtered(lambda svl: not self.is_reception_return(svl))    

                for svl_out in svl_loc_out:
                    if self.debug:
                        _logger.info(f"FIFO LST={fifo_lst}")                                   

                    svl_qty = abs(svl_out.quantity)
                    if not fifo_lst:
                        svl_out.unit_cost = last_price
                        svl_out.value = svl_out.quantity * last_price
                    else:
                        fifo_qty = fifo_lst[0][0]
                        if svl_qty <= fifo_qty:
                            last_price = fifo_lst[0][1]
                            svl_out.unit_cost = last_price

                            link_value = sum([s.value for s in svl_out.stock_valuation_layer_ids])
                            if link_value < 0:
                                svl_out.value = (-1) * (svl_qty * last_price - abs(link_value))
                            else:
                                svl_out.value = (-1) * (svl_qty * last_price + link_value)
                            
                            if self.debug:
                                _logger.info(f"SET SVL OUT id={svl_out.id} qty={svl_out.quantity} val={svl_out.value} uc={svl_out.unit_cost}")

                            fifo_lst[0][0] = fifo_qty - svl_qty
                            if fifo_lst[0][0] == 0:
                                fifo_lst.pop(0)
                        else:
                            value = 0
                            while svl_qty > 0:
                                if fifo_lst:
                                    [fifo_qty, unit_cost, val, mv, svl_id] = fifo_lst[0]
                                    last_price = unit_cost
                                    if fifo_qty <= svl_qty:
                                        value += fifo_qty * unit_cost
                                        svl_qty -= fifo_qty
                                        fifo_lst.pop(0)
                                    else:
                                        value += svl_qty * unit_cost
                                        fifo_lst[0][0] = fifo_qty - svl_qty
                                        break
                                else:
                                    break

                            link_value = sum([s.value for s in svl_out.stock_valuation_layer_ids])
                            if link_value < 0:
                                value -= abs(link_value)
                            else:
                                value += link_value

                            svl_out.value = (-1) * value
                            svl_out.unit_cost = (-1) * value / svl_out.quantity

                            if self.debug:
                                _logger.info(f"SET SVL OUT id={svl_out.id} qty={svl_out.quantity} val={svl_out.value} uc={svl_out.unit_cost}")


                    # check for delivery_return in fifo_lst to have the correct value and unit_price
                    if svl_out.stock_move_id.move_dest_ids and svl_out.stock_move_id.move_dest_ids[0].state == 'done':
                        should_restart_fifo = True
                        for i in range(len(fifo_lst)):
                            fifo_entry = fifo_lst[i]
                            if fifo_entry[3] in svl_out.stock_move_id.move_dest_ids:
                                # fix new unit_price in fifo

                                svl_out_val = svl_out.value
                                svl_qty = svl_out.quantity
                                link_value = sum([s.value for s in svl_out.stock_valuation_layer_ids])
                                if link_value < 0:
                                    svl_out_val = (-1) * (svl_qty * last_price - abs(link_value))
                                else:
                                    svl_out_val = (-1) * (svl_qty * last_price + link_value)
                                svl_out_uc = abs(svl_out_val / svl_out.quantity)

                                if svl_out_uc != fifo_entry[1]:
                                    # fix reception_return unit_cost and value
                                    fifo_entry[1] = fifo_entry[4].unit_cost = svl_out_uc
                                    fifo_entry[4].value = svl_out_uc * fifo_entry[4].quantity
                                break

                    # Fix internal transfer price
                    if svl_out.l10n_ro_valued_type == "internal_transfer":
                        plus_svl = svl_out.stock_move_id.stock_valuation_layer_ids.filtered(
                            lambda svl: (
                                svl.id != svl_out.id 
                                and svl.quantity > 0 
                                and svl.stock_move_line_id == svl_out.stock_move_line_id
                            )
                        )
                        if plus_svl:
                            uc = (svl_out.quantity != 0 and svl_out.value / svl_out.quantity) or 0
                            plus_svl.unit_cost = uc
                            for o_svl in plus_svl:
                                o_svl.value = o_svl.quantity * uc

                    if should_restart_fifo:
                        if restart_counter > 5:
                            should_restart_fifo = False
                        else:
                            restart_counter += 1

                        svl_ret = (svl_loc_in + svl_loc_out).filtered(lambda svl: svl.stock_move_id in svl_out.stock_move_id.move_dest_ids)
                        if svl_ret:
                            svl_ret = svl_ret[0]

                            svl_out_val = svl_out.value
                            uc_svl_ret = (svl_out.quantity != 0 and svl_out_val / svl_out.quantity) or 0                                    
                            svl_ret.unit_cost = uc_svl_ret
                            svl_ret.value = uc_svl_ret * svl_ret.quantity                                

                            if self.debug:
                                _logger.info(f"SET SVL RET id={svl_ret.id} qty={svl_ret.quantity} val={svl_ret.value} uc={svl_ret.unit_cost}")

                            if round(abs(svl_ret.value) - abs(svl_out_val), 3) == 0:
                                should_restart_fifo = False
                        else:
                            should_restart_fifo = False

    def recompute_manufacturing_orders(self, products):
        # Redo productions with computed cost
        date_from = fields.Datetime.to_datetime(self.date_from)
        domain = [
                    ('product_id', 'in', products.ids),
                    ('date', '>=', date_from), 
                    ('production_id', '!=', False),
                    ('state', '=', 'done')
                ]

        production_moves = self.env['stock.move'].search(domain)
        orders = production_moves.mapped('production_id')
        for order in orders:
            move = order.move_finished_ids
            val_layers = move.mapped('stock_valuation_layer_ids')
            old_cost = sum(move.mapped('stock_valuation_layer_ids.unit_cost'))
            old_value = sum(move.mapped('stock_valuation_layer_ids.value'))
            print(old_cost)
            print(old_value)
            qty_done = sum([mv.product_uom._compute_quantity(mv.quantity_done, mv.product_id.uom_id) for mv in move])
            new_cost = 0
            for m in order.move_raw_ids.filtered(lambda x: x.state == 'done').sudo():
                new_cost += -1 * sum(m.stock_valuation_layer_ids.mapped("value"))
            new_cost = new_cost / qty_done
            print(new_cost)
            for mv in move:
                mv.price_unit = new_cost
            for layer in val_layers:
                layer.write({
                    "unit_cost": new_cost,
                    "value": layer.quantity * new_cost,
                    "remaining_value": layer.remaining_qty * new_cost
                })


    def _fix_remaining_qty_value(self):
        if self.product_ids:
            products = self.product_ids
        else:
            products = self.env['product.product'].search([])

        locations = self.location_ids.mapped('location_id')
        if self.update_svl_values:
            if len(products) == 1:
                self._cr.execute("""
                    UPDATE stock_valuation_layer 
                    SET remaining_qty = 0, remaining_value = 0 
                    WHERE 
                        product_id = %s and 
                        company_id = %s
                    """, (products.id, self.company_id.id)
                )
            elif products:
                self._cr.execute("""
                    UPDATE stock_valuation_layer 
                    set remaining_qty = 0, remaining_value = 0 
                    WHERE 
                        product_id in %s and 
                        company_id = %s
                    """, (tuple(products.ids), self.company_id.id)
                )
            self.env.cr.commit()
        else:
            svls = self.env['stock.valuation.layer'].search([
                ('product_id', 'in', products.ids), 
                ('company_id', '=', self.company_id.id)]
            )
            svls.write({'remaining_qty': 0, 'remaining_value': 0})

        # Fix remaining qty
        for location in locations.filtered(lambda l: l._should_be_valued()):
            if len(products) == 1:
                self._cr.execute("""
                    SELECT product_id, location_id, lot_id, sum(quantity) as quantity 
                    FROM stock_quant 
                    WHERE 
                        location_id = %s and 
                        product_id = %s and 
                        company_id = %s
                    GROUP BY product_id, location_id, lot_id;
                    """ % (location.id, products.id, self.company_id.id)
                )                        
            else:
                self._cr.execute("""
                    SELECT product_id, location_id, lot_id, sum(quantity) as quantity 
                    FROM stock_quant 
                    WHERE 
                        location_id = %s and 
                        product_id in %s and 
                        company_id = %s
                    GROUP BY product_id, location_id, lot_id;
                    """ % (location.id, tuple(products.ids), self.company_id.id)
                )      

            plds = self._cr.dictfetchall()

            for pld in plds:
                product = self.env['product.product'].browse(pld['product_id'])  
                lot_id = self.env['stock.production.lot'].browse(pld['lot_id'])
                qty = pld['quantity']
                sign = 1
                if qty >= 0:
                    domain_svls = [
                        ('company_id', '=', self.company_id.id), 
                        ("product_id", "=", product.id), 
                        ("l10n_ro_location_dest_id", "=", location.id), 
                        ("quantity", ">", 0)
                    ]
                else:
                    sign = -1
                    domain_svls = [
                        ('company_id', '=', self.company_id.id),
                        ("product_id", "=", product.id), 
                        ("l10n_ro_location_id", "=", location.id), 
                        ("quantity", "<", 0)
                    ]

                if self.lot_id and self.lot_id != lot_id:
                    continue

                if lot_id:
                    domain_svls.append(("lot_ids", "in", lot_id.ids))

                svls = self.env['stock.valuation.layer'].search(domain_svls)
                svls = svls.sorted(lambda svl: svl.create_date)

                #check if it is a delivery return, fix value
                for svl in svls.filtered(lambda s: s.stock_move_id._is_delivery_return()):
                    svl_origin = svl.stock_move_id.origin_returned_move_id.stock_valuation_layer_ids
                    if svl_origin:
                        origin_value = sum([s.value for s in svl_origin])
                        origin_qty = sum([s.quantity for s in svl_origin])
                        if origin_qty:
                            unit_cost = origin_value / origin_qty
                            svl.value = svl.quantity * unit_cost
                            svl.unit_cost = unit_cost


                for svl in svls.sorted("create_date", reverse=True):
                    added_cost = sum([s.value for s in svl.stock_valuation_layer_ids])
                    svl_value = svl.value + added_cost

                    unit_cost = svl_value / svl.quantity if svl.quantity else 0                    
                    unit_cost = unit_cost or product.with_company(self.company_id).standard_price                        
                    if qty * sign > 0:
                        if abs(svl.quantity) <= qty * sign:
                            svl.remaining_qty = svl.quantity
                            svl.remaining_value = svl.quantity * unit_cost
                            qty = (abs(qty) - abs(svl.quantity)) * sign
                        else:
                            svl.remaining_qty = abs(qty) * sign
                            svl.remaining_value = sign * abs(qty) * unit_cost
                            qty = 0
        
                    if not svl.unit_cost:
                        svl.unit_cost = unit_cost


    def _finalize_svls(self):
        if self.product_ids:
            products = self.product_ids
        else:
            products = self.env['product.product'].search([])

        locations = self.location_ids.mapped('location_id')
        account_move_date = fields.Datetime.to_datetime(self.account_move_date)
        domain = ['&',
                    '&',
                        ('product_id', 'in', products.ids),
                        ('create_date', '>=', account_move_date),
                    '|',
                        '&',
                            ('l10n_ro_location_dest_id', 'in', locations.ids),
                            ('quantity', '>', 0.001),
                        '&',
                            ('l10n_ro_location_id', "in", locations.ids),
                            ('quantity', '<', 0.001),
                ]

        svls = self.env['stock.valuation.layer'].search(domain)
        for svl in svls:
            if not self.update_svl_values:
                #switch new_unit_cost vs unit_cost
                # and new_value vs value
                new = svl.unit_cost
                svl.unit_cost = svl.new_unit_cost
                svl.new_unit_cost = new

                new = svl.value
                svl.value = svl.new_value
                svl.new_value = new

                new = svl.remaining_value
                svl.remaining_value = svl.new_remaining_value
                svl.new_remaining_value = new

                new = svl.remaining_qty
                svl.remaining_qty = svl.new_remaining_qty
                svl.new_remaining_qty = new

            if self.update_account_moves:
                if (svl.quantity < 0 or svl.stock_move_id.move_orig_ids):
                    svl = svl.sudo()
                    if svl.account_move_id and svl.account_move_id.amount_total != 0.0:
                        if round(abs(svl.value) - abs(svl.account_move_id.amount_total), 5) != 0:
                            svl.account_move_id._check_fiscalyear_lock_date()
                            svl.account_move_id.button_draft()

                            line_debit = svl.account_move_id.line_ids.filtered(lambda l: l.balance > 0)
                            line_debit.with_context(check_move_validity=False).debit = abs(svl.value)
                            line_debit.with_context(check_move_validity=False).credit = 0
                            line_debit.with_context(check_move_validity=False).amount_currency = abs(svl.value)                            
                            
                            line_credit = svl.account_move_id.line_ids.filtered(lambda l: l.balance < 0)
                            line_credit.with_context(check_move_validity=False).credit = abs(svl.value)
                            line_credit.with_context(check_move_validity=False).debit = 0
                            line_credit.with_context(check_move_validity=False).amount_currency = -abs(svl.value)                              

                            svl.account_move_id.with_context(force_period_date=svl.create_date).action_post()
                    else:
                        if svl.account_move_id and svl.account_move_id.amount_total == 0:
                            svl.account_move_id.button_draft()
                            svl.account_move_id.button_cancel()

                        if svl.value != 0:
                            svl.stock_move_id.with_context(force_period_date=svl.create_date)._account_entry_move(
                                svl.quantity, svl.description, svl.id, svl.value
                            )
                            #if svl.account_move_id:
                            #    self._cr.execute(f"update account_move set date = '{svl.create_date.date()}' where id = {svl.account_move_id.id}")  
                            #    self._cr.execute(f"update account_move_line set date = '{svl.create_date.date()}' where id = {svl.account_move_id.id}")  
