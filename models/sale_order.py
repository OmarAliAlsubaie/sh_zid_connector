# -*- coding: utf-8 -*-
# Part of insightful-erp Technologies.

from odoo import fields, models


MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'out_receipt': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
    'in_receipt': 'supplier',
}


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    zid_id = fields.Char(string="zid id")
    workflow_id = fields.Many2one(
        'sh.auto.sale.workflow', string="Sale Workflow")
    is_boolean = fields.Boolean(related="company_id.group_auto_sale_workflow")
    sh_zid_payment_journal = fields.Many2one(
        'account.journal', string="Zid Payment Journal")
    zid_so_date = fields.Datetime(string="Zid SO Date")

    # AUTO SALE ORDER WORK FLOW FROM ORDER CONFIRM TO PAYEMENT BASED ON CONFIGURATION

    def action_confirm(self):
        super(SaleOrder, self).action_confirm()
        if not self.workflow_id:
            return
        if self.workflow_id.validate_order and self.picking_ids:
            if self.workflow_id.force_transfer:
                for picking in self.picking_ids:
                    for stock_move in picking.move_ids_without_package:
                        self.env.cr.execute(
                            """ UPDATE stock_move set date=%s where id=%s""",
                            [str(self.zid_so_date), stock_move.id],
                        )
                        self.env.cr.commit()
                        if stock_move.move_line_ids:
                            stock_move.move_line_ids.update({
                                'quantity': stock_move.product_uom_qty,
                            })
                        else:
                            self.env['stock.move.line'].sudo().create({
                                'picking_id': picking.id,
                                'move_id': stock_move.id,
                                'date': stock_move.date,
                                'reference': stock_move.reference,
                                'origin': stock_move.origin,
                                'quantity': stock_move.product_uom_qty,
                                'product_id': stock_move.product_id.id,
                                'product_uom_id': stock_move.product_uom.id,
                                'location_id': stock_move.location_id.id,
                                'location_dest_id': stock_move.location_dest_id.id
                            })
                    picking.button_validate()
                    if picking.state != 'done':
                        sms = self.env['confirm.stock.sms'].sudo().create({
                            'pick_ids': [(4, picking.id)],
                        })
                        sms.send_sms()
                        picking.button_validate()

                    if self.zid_id and self.zid_so_date:
                        self.env.cr.execute(""" UPDATE stock_picking set scheduled_date=%s,date_done=%s where id=%s""",
                            [str(self.zid_so_date), str(self.zid_so_date), picking.id])
                        self.env.cr.commit()
                        picking.write({
                            "date_done": self.zid_so_date,
                        })

            else:
                for picking in self.picking_ids:
                    picking.button_validate()
                    wiz = self.env['stock.immediate.transfer'].sudo().create({
                        'pick_ids': [(4, picking.id)],
                        'immediate_transfer_line_ids': [(0, 0, {
                            'picking_id': picking.id,
                            'to_immediate': True,
                        })]
                    })
                    wiz.with_context(
                        button_validate_picking_ids=picking.ids).process()

                    if picking.state != 'done':
                        sms = self.env['confirm.stock.sms'].create({
                            'pick_ids': [(4, picking.id)],
                        })
                        sms.send_sms()
                        ret = picking.button_validate()
                        if 'res_model' in ret and ret['res_model'] == 'stock.backorder.confirmation':
                            backorder_wizard = self.env['stock.backorder.confirmation'].sudo().create({
                                'pick_ids': [(4, picking.id)],
                                'backorder_confirmation_line_ids': [(0, 0, {
                                    'picking_id': picking.id,
                                    'to_backorder': True,

                                })]
                            })
                            backorder_wizard.with_context(
                                button_validate_picking_ids=picking.ids).process()
        if self.workflow_id.create_invoice:
            invoice = self._create_invoices()
            if self.workflow_id.sale_journal or self.sh_zid_payment_journal:
                invoice.write({
                    'journal_id': self.workflow_id.sale_journal.id,
                    "invoice_date": self.zid_so_date,
                    "invoice_date_due": self.zid_so_date,
                })
                invoice.line_ids.write({
                    "date": self.zid_so_date,
                })

            if self.workflow_id.validate_invoice:
                invoice.action_post()

                if self.workflow_id.send_invoice_by_email:
                    template_id = self.env.ref(
                        'account.email_template_edi_invoice')
                    template_id.with_context(model_description='').sudo().send_mail(
                        invoice.id, force_send=True, notif_layout="mail.mail_notification_paynow")
                if self.workflow_id.register_payment:
                    payment = self.env['account.payment'].sudo().create({
                        'currency_id': invoice.currency_id.id,
                        'amount': invoice.amount_total,
                        'payment_type': 'inbound',
                        'partner_id': invoice.commercial_partner_id.id,
                        'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[invoice.move_type],
                        'ref': invoice.payment_reference or invoice.name,
                        'payment_method_id': self.workflow_id.payment_method.id,
                        'journal_id': self.workflow_id.payment_journal.id,
                    })
                    payment.action_post()
                    line_id = payment.line_id.filtered(lambda l: l.credit)
                    invoice.js_assign_outstanding_line(line_id.id)
