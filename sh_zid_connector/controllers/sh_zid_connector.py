# -*- coding: utf-8 -*-
# Part of insightful-erp Technologies.

from odoo.http import route, request, Controller


class Zid(Controller):

    # @route('/zid/auth', type='http', auth='user')
    # def auth_redirect(self, code, **kw):
    #     zid_conf = request.env['zid.config'].sudo().search(
    #         [('auth_active', '=', True)], limit=1)
    #     if zid_conf and code:
    #         zid_conf.make_auth_request(code)
    #     return request.redirect('/web')
    @route('/zid/auth', type='http', auth='user')
    def auth_redirect(self, code, **kw):
        try:
            zid_conf = request.env['zid.config'].sudo().search(
                [('auth_active', '=', True)], limit=1)
            # if zid_conf and code:
            if zid_conf:
                # zid_conf.make_auth_request(code, kw)
                zid_conf.make_auth_request(code)
                return request.redirect('/web')
            else:
                return f"Something want wrong, Zid config not found ! code: {code}, kw: {kw}"
        except Exception as e:
            return f"Exception: {e}, code: {code}, kw: {kw}"
