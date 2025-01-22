# Copyright 2022 ACSONE SA/NV
# License LGPL-3.0 or later (http://www.gnu.org/licenses/LGPL).

from .tools.tools_common import response_http_json_error, response_json_error
from odoo.http import HttpRequest, JsonRequest
import logging

_logger = logging.getLogger(__name__)


class LampApiDispatcher(HttpRequest):
    # 出现异常就返回!
    def _handle_exception(self, exception):
        _logger.info('error: {}'.format(exception), exc_info=True)
        return response_json_error(400, message='出现了错误! {}'.format(exception))


class LampApiJsonDispatcher(JsonRequest):
    # 出现异常就返回!
    def _handle_exception(self, exception):
        _logger.info('error: {}'.format(exception), exc_info=True)
        return response_http_json_error(400, message='出现了错误! {}'.format(exception))
