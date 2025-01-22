# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.tools import config
import json
from .base import BaseController
import logging
from ..tools.rsa_utils import RSAUtils
from ..tools.tools_common import (
    get_random_login_code, get_access_token_from_redis, response_json_success, verify_auth_token_only,
    DEFAULT_TOKEN_EXPIRE, jwt_encode, LAMP_ISSUER, LAMP_AUDIENCE, verify_auth_token, save_access_token_to_redis)

_logger = logging.getLogger(__name__)

MAX_MOBILE_SMS_LIMIT = 20


# TODO
def send_sms_code(mobile, sms_code):
    return True


class LAMPUser(http.Controller, BaseController):
    @http.route('/api/v1/lamp/static/info', auth='public', methods=['POST'], csrf=False, cors="*", type='json')
    def lamp_info(self, lang='en_US'):
        try:
            with open(config.get('public_key_path'), 'rb') as pub_file:
                public_key = pub_file.read()

            resp_data = {
                'data': public_key.decode()
            }
        except Exception as e:
            _logger.error('获取公钥出错: {}'.format(e))
            return self.response_http_json_error(400, message='出现了错误!')

        return self.response_http_json_success(data=resp_data, message='成功')

    @http.route('/api/v1/lamp/user/login/code', auth='public', methods=['POST'], csrf=False, cors="*", type='http')
    def lamp_user_login_code(self, lang='en_US', **kwargs):

        try:
            request.env.context = dict(request.env.context, lang=lang)
            payload_data = json.loads(request.httprequest.data)
            _logger.info('payload_data: {}'.format(payload_data))
        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_json_error(400, message='出现错误!{}'.format(e))

        mobile = payload_data.get('mobile')
        auth_type = payload_data.get('auth_type')
        email = payload_data.get('email')

        if auth_type == 'mobile':
            if not mobile:
                return self.response_json_error(400, message='请输入手机号!')

            try:
                send_count = self.get_mobile_sms_log_from_redis(mobile)
                if not send_count:
                    send_count = 0
                else:
                    send_count = send_count.decode()
                    send_count = int(send_count)
                    _logger.info('{} 发送短信次数: {}'.format(mobile, send_count))
                cache_code = self.get_sms_code_from_redis(mobile)
            except Exception as e:
                _logger.error('出现错误: {}'.format(e))
                cache_code = None
                send_count = 0

            if cache_code:
                return self.response_json_error(400, message='请不要重复点击发送短信!')

            if send_count > MAX_MOBILE_SMS_LIMIT:
                return self.response_json_error(400, message='超出每日发送限制，请稍后重试!')

            sms_code = get_random_login_code()

            # send_state = AliCloudSMS().send_sms_code(phone_number=mobile, code=sms_code)
            send_state = send_sms_code(mobile, sms_code)

            # force_back = False
            if not send_state:
                return self.response_json_error(400, message='发送短信失败!')

            # 保存SMS CODE
            self.save_sms_code_to_redis(mobile, sms_code)
            self.save_mobile_sms_log_to_redis(mobile)

            # 测试环境，接口返回code
            prod_env = config.get('prod_env', False)
            # prod_env = True

            _logger.info('发送验证码: {}, {}'.format(mobile, sms_code))
            resp_data = {
                'code': sms_code
            }

            return self.response_json_success(message='发送成功!', data={} if prod_env else resp_data)

        elif auth_type == 'email':
            pass
        else:
            return self.response_json_error(400, message='暂不支持该类型的认证!')

    @http.route('/api/v1/lamp/user/login', auth='public', methods=['POST'], csrf=False, cors="*", type='http')
    def lamp_user_login(self, lang='en_US', **kwargs):

        try:
            request.env.context = dict(request.env.context, lang=lang)
            payload_data = json.loads(request.httprequest.data)
            _logger.info('payload_data: {}'.format(payload_data))
        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_json_error(400, message='出现错误!{}'.format(e))

        mobile = payload_data.get('mobile')
        code = payload_data.get('code')

        if not all([mobile, code]):
            return self.response_json_error(400, message='验证码错误!')

        redis_code = self.get_sms_code_from_redis(mobile)

        if not redis_code:
            return self.response_json_error(400, message='请先获取验证码!')

        partner_id = self.get_or_create_res_partner(mobile)

        if not partner_id:
            return self.response_json_error(400, message='数据异常，请检查数据!!')

        payload_data = {
            'mobile': mobile,
            'uid': partner_id.id,
            'aud': LAMP_AUDIENCE,
            'iss': LAMP_ISSUER
        }
        jwt_token = jwt_encode(payload_data, DEFAULT_TOKEN_EXPIRE)

        save_access_token_to_redis(mobile, jwt_token)

        token_data = {
            'access_token': jwt_token,
            'expire': DEFAULT_TOKEN_EXPIRE
        }

        return self.response_json_success(token_data, message='登陆成功')

    @http.route('/api/v1/lamp/token/check', auth='public', methods=['POST'], csrf=False, cors="*", type='http')
    @verify_auth_token_only()
    def check_user_login_token(self, lang='en_US'):
        return self.response_json_success({
            'message': 'success'
        })

    @http.route('/api/v1/lamp/user/profile', auth='public', methods=['get'], csrf=False, cors="*", type='http')
    @verify_auth_token_only()
    def user_profile(self, lang='en_US'):
        request.env.context = dict(request.env.context, lang=lang)
        partner_id = request.env['res.partner'].sudo().browse(request.partner_id)

        user_data = {
            'name': partner_id.name,
            'mobile': partner_id.mobile
        }
        return self.response_json_success(user_data)
