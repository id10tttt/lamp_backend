# -*- coding: utf-8 -*-
import logging
from odoo.tools import date_utils
import json
import datetime
from odoo import http
from odoo.http import Response, request, JsonRequest
from .response_code import ResponseCode
import dateutil.parser as parser
from ..tools.tools_common import get_redis_client
from odoo.exceptions import ValidationError
from odoo.addons.base.models.res_users import DEFAULT_CRYPT_CONTEXT

_logger = logging.getLogger(__name__)

ERROR_CODE = {
    -1: u'禁止访问',
}

SMS_EX = 60 * 2
DAILY_MOBILE_LIMIT_EX = 60 * 60 * 24
SMS_REDIS_PREFIX = 'user:login:sms:code'
SMS_CODE_DB = 1
SMS_SEND_LOG_DB = 4


def get_datetime_format():
    china_tz = datetime.timezone(datetime.timedelta(hours=8))
    req_time = datetime.datetime.now(china_tz).strftime('%Y%m%d')
    return req_time


class UserException(Exception):
    pass


class BaseController(object):

    def _crypt_context(self):
        """ Passlib CryptContext instance used to encrypt and verify
        passwords. Can be overridden if technical, legal or political matters
        require different kdfs than the provided default.

        Requires a CryptContext as deprecation and upgrade notices are used
        internally
        """
        return DEFAULT_CRYPT_CONTEXT.copy()

    def parse_product_date(self, product_date):
        """
        格式化日期
        :param product_date: 文件时间，格式未知
        :return: 格式化后时间
        """
        if not product_date:
            return False
        try:
            product_date = parser.parse(str(product_date))
        except Exception as e:
            raise ValidationError('日期无法格式化: {}, {}'.format(product_date, e))
        return product_date

    # @ormcache('product_code')
    def get_product_product_id(self, product_code):
        product_id = request.env['product.product'].sudo().search([('default_code', '=', product_code)])
        if not product_id:
            return False
        return product_id[0]

    def get_product_product_id_by_uuid(self, product_uuid):
        product_id = request.env['product.product'].sudo().search(
            [('product_tmpl_id.external_code', '=', product_uuid)])
        if not product_id:
            return False
        return product_id[0]

    def response_http_json_success(self, data=None, message='成功'):
        result = ResponseCode.CODE_200
        if data is not None:
            result['data'] = data
        else:
            result['data'] = []

        if message:
            result['message'] = message
        return result

    def get_ir_attachment_public_url(self, attachment_id):
        if not attachment_id.access_token:
            attachment_id.generate_access_token()
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return '{}/web/content/{}?access_token={}'.format(base_url, attachment_id.id,
                                                                        attachment_id.access_token)

    def response_http_json_error(self, code, data=None, message=None):
        custom_code = 'CODE_{}'.format(code)
        if hasattr(ResponseCode, custom_code):
            result = getattr(ResponseCode, custom_code)
        else:
            result = ResponseCode.CODE_403
        if message:
            result['message'] = message
        if data:
            result['data'] = data
        else:
            result['data'] = []
        return result

    def response_success_msg(self, data=None):

        result = ResponseCode.CODE_200
        if data is not None:
            result['data'] = data
        response = Response(result)
        return response

    def response_error_msg(self, code, data=None):
        custom_code = 'CODE_{}'.format(code)
        if hasattr(ResponseCode, custom_code):
            result = getattr(ResponseCode, custom_code)
        else:
            result = ResponseCode.CODE_403
        if data:
            result['data'] = data
        return request.make_response(json.dumps(result))

    def json_response(self, result=None, error=None):
        response = result
        mime = 'application/json'
        body = json.dumps(response, default=date_utils.json_default)
        return Response(
            body, status=error and error.pop('http_status', 200) or 200,
            headers=[('Content-Type', mime), ('Content-Length', len(body))]
        )

    def response_json_success(self, data=None, message='成功'):
        result = ResponseCode.CODE_200
        if data is not None:
            result['data'] = data
        else:
            result['data'] = []

        if message:
            result['message'] = message

        result = {
            'jsonrpc': '2.0',
            'result': result
        }
        # return result
        return request.make_response(
            headers={'Content-Type': 'json'},
            data=json.dumps(result)
        )

    def response_json_error(self, code, data=None, message=None):
        custom_code = 'CODE_{}'.format(code)
        if hasattr(ResponseCode, custom_code):
            result = getattr(ResponseCode, custom_code)
        else:
            result = ResponseCode.CODE_403
        if message:
            result['message'] = message
        if data:
            result['data'] = data
        else:
            result['data'] = []

        result = {
            'jsonrpc': '2.0',
            'result': result
        }
        return request.make_response(
            headers={'Content-Type': 'json'},
            data=json.dumps(result)
        )

    def parse_json_httpdata(self, http_data):
        try:
            return json.loads(http_data)
        except Exception as e:
            return http_data

    def save_api_request_log(self, http_request, payload_data):
        try:
            save_request_data = {
                'url': '{}'.format(http_request.path),
                'method': '{}'.format(http_request.method),
                'source_data': '{}'.format(self.parse_json_httpdata(http_request.data)),
                'return_msg': '{}'.format(payload_data)
            }
            res = request.env(user=request.user_id)['api.request.log'].sudo().with_delay().create(save_request_data)
            _logger.info('创建成功: {}'.format(res))
        except Exception as e:
            _logger.error('保存日志出错: {}'.format(e))

    # 保存 sms code
    def save_sms_code_to_redis(self, mobile, code):
        redis_client = get_redis_client(db=SMS_CODE_DB)
        redis_client.set('{}:{}'.format(SMS_REDIS_PREFIX, mobile), code, ex=SMS_EX)
        redis_client.close()

    def get_sms_code_from_redis(self, mobile):
        redis_client = get_redis_client(db=SMS_CODE_DB)
        code = redis_client.get('{}:{}'.format(SMS_REDIS_PREFIX, mobile))
        return code

    def save_mobile_sms_log_to_redis(self, mobile):
        today = get_datetime_format()
        increment_value = 1
        key_name = '{}:{}:log:{}'.format(SMS_REDIS_PREFIX, mobile, today)

        redis_client = get_redis_client(db=SMS_SEND_LOG_DB)
        redis_client.incrby(key_name, increment_value)
        redis_client.expire(key_name, DAILY_MOBILE_LIMIT_EX)
        redis_client.close()

    def get_mobile_sms_log_from_redis(self, mobile):
        today = get_datetime_format()
        key_name = '{}:{}:log:{}'.format(SMS_REDIS_PREFIX, mobile, today)
        redis_client = get_redis_client(db=SMS_SEND_LOG_DB)
        code = redis_client.get(key_name)
        redis_client.close()
        return code

    def get_or_create_res_partner(self, mobile):
        partner_id = request.env['res.partner'].sudo().search([
            ('mobile', '=', mobile)
        ])

        if partner_id and len(partner_id) == 1:
            return partner_id

        if not partner_id:
            partner_data = {
                'user_type': 'user',
                'odoo_create': False,
                'name': '手机号: {}'.format(mobile),
                'mobile': mobile
            }

            partner_id = request.env['res.partner'].sudo().create(partner_data)

            _logger.info('保存新用户: {}'.format(partner_id))

            return partner_id

        return False

    def get_or_create_res_partner_by_email(self, email, name=None):
        partner_id = request.env['res.partner'].sudo().search([
            ('email', '=', email)
        ])

        if partner_id and len(partner_id) == 1:
            return partner_id

        if not partner_id:
            partner_data = {
                'user_type': 'user',
                'odoo_create': False,
                'name': name or 'E-Mail: {}'.format(email),
                'email': email
            }

            partner_id = request.env['res.partner'].sudo().create(partner_data)

            _logger.info('保存新用户: {}'.format(partner_id))

            return partner_id

        return False

    def hashed_password(self, password):
        ctx = self._crypt_context()
        hash_password = ctx.hash if hasattr(ctx, 'hash') else ctx.encrypt
        hash_pwd = hash_password(password)

        return hash_pwd

    def create_res_partner_by_email(self, email, name, password):
        partner_id = request.env['res.partner'].sudo().search([
            ('email', '=', email)
        ])

        if partner_id and len(partner_id) == 1:
            return partner_id

        if not partner_id:
            partner_data = {
                'user_type': 'user',
                'odoo_create': False,
                'name': name or 'E-Mail: {}'.format(email),
                'email': email,
                'hash_password': self.hashed_password(password)
            }

            partner_id = request.env['res.partner'].sudo().create(partner_data)

            _logger.info('保存新用户: {}'.format(partner_id))

            return partner_id

        return False

    def check_password(self, password, hash_password):
        valid, replacement = self._crypt_context() \
            .verify_and_update(password, hash_password)

        if not valid:
            return False

        return True

    def _check_credentials(self, email, password):
        partner_id = request.env['res.partner'].sudo().search([
            ('email', '=', email)
        ])

        if len(partner_id) != 1:
            return False

        if not self.check_password(password, partner_id.hash_password):
            return False

        return partner_id

    def update_partner_password(self, partner_id, password, new_password):
        partner_id = request.env['res.partner'].sudo().search([
            ('id', '=', partner_id)
        ])

        if not partner_id:
            return False

        if not self.check_password(password, partner_id.hash_password):
            return False

        partner_id.write({
            'hash_password': self.hashed_password(new_password)
        })
        return partner_id
