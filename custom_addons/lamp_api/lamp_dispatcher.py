# Copyright 2022 ACSONE SA/NV
# License LGPL-3.0 or later (http://www.gnu.org/licenses/LGPL).

from .tools.tools_common import response_json_error
from odoo.http import HttpRequest


class LampApiDispatcher(HttpRequest):
    # 出现异常就返回!
    def _handle_exception(self, exception):
        return response_json_error(400, message='出现了错误! {}'.format(exception))
