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
    @http.route('/api/v1/lamp/static/info', auth='public', methods=['POST'], csrf=False, cors="*", type='http')
    def lamp_info(self, lang='en_US'):
        try:
            with open(config.get('public_key_path'), 'rb') as pub_file:
                public_key = pub_file.read()

            resp_data = {
                'data': public_key.decode()
            }
        except Exception as e:
            _logger.error('获取公钥出错: {}'.format(e))
            return self.response_json_error(400, message='出现了错误!')

        return self.response_json_success(data=resp_data, message='成功')

    @http.route('/api/v1/lamp/user/login/code', auth='public', methods=['POST'], csrf=False, cors="*", type='json')
    def lamp_user_login_code(self, lang='en_US', **kwargs):

        try:
            request.env.context = dict(request.env.context, lang=lang)
            payload_data = json.loads(request.httprequest.data)
            _logger.info('payload_data: {}'.format(payload_data))
        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_http_json_error(400, message='出现错误!{}'.format(e))

        mobile = payload_data.get('mobile')
        auth_type = payload_data.get('auth_type')
        email = payload_data.get('email')

        redis_key = None
        if auth_type == 'mobile':
            if not mobile:
                return self.response_http_json_error(400, message='请输入手机号!')
            redis_key = mobile
        elif auth_type == 'email':
            if not email:
                return self.response_http_json_error(400, message='请输入邮箱!')
            redis_key = email
        else:
            return self.response_http_json_error(400, message='暂不支持该类型的认证!')

        if not redis_key:
            return self.response_http_json_error(400, message='认证数据类型异常!仅支持手机号/邮箱')

        try:
            send_count = self.get_mobile_sms_log_from_redis(redis_key)
            if not send_count:
                send_count = 0
            else:
                send_count = send_count.decode()
                send_count = int(send_count)
                _logger.info('{} 发送验证码次数: {}'.format(redis_key, send_count))
            cache_code = self.get_sms_code_from_redis(redis_key)
        except Exception as e:
            _logger.error('出现错误: {}'.format(e))
            cache_code = None
            send_count = 0

        if cache_code:
            return self.response_http_json_error(400, message='请不要重复点击发送验证码!')

        if send_count > MAX_MOBILE_SMS_LIMIT:
            return self.response_http_json_error(400, message='超出每日发送限制，请稍后重试!')

        sms_code = get_random_login_code()

        if auth_type == 'mobile':
            # send_state = AliCloudSMS().send_sms_code(phone_number=mobile, code=sms_code)
            send_state = send_sms_code(mobile, sms_code)

            # force_back = False
            if not send_state:
                return self.response_http_json_error(400, message='发送短信失败!')
        elif auth_type == 'email':
            server_id = request.env['ir.mail_server'].sudo().search([], limit=1)
            mail = request.env['mail.mail'].sudo().create({
                'subject': 'Register/Loin Code',
                'body_html': '<p>Dear Sir/Madam：</p><br/>Your code is :{}'.format(sms_code),
                'email_to': '{}'.format(email),
                'email_from': server_id.smtp_user if server_id else False,
            })
            mail.send()

        # 保存SMS CODE
        self.save_sms_code_to_redis(redis_key, sms_code)
        self.save_mobile_sms_log_to_redis(redis_key)

        # 测试环境，接口返回code
        prod_env = config.get('prod_env', False)
        # prod_env = True

        _logger.info('发送验证码: {}, {}'.format(redis_key, sms_code))
        resp_data = {
            'code': sms_code
        }

        return self.response_http_json_success(message='发送成功!', data={} if prod_env else resp_data)

    @http.route('/api/v1/lamp/user/register', auth='public', methods=['POST'], csrf=False, cors="*", type='json')
    def lamp_user_register(self, lang='en_US', **kwargs):

        try:
            request.env.context = dict(request.env.context, lang=lang)
            payload_data = json.loads(request.httprequest.data)
            warehouse_id = payload_data.get('warehouse_id')
            lang = payload_data.get('lang')
            if warehouse_id:
                warehouse_id = int(warehouse_id)

            if not lang:
                lang = 'en_US'
            _logger.info('payload_data: {}'.format(payload_data))
        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_http_json_error(400, message='出现错误!{}'.format(e))

        name = payload_data.get('name')
        email = payload_data.get('email')
        password = payload_data.get('password')
        code = payload_data.get('code')

        if not all([email, code]):
            return self.response_http_json_error(400, message='验证码错误!')

        redis_key = email

        redis_code = self.get_sms_code_from_redis(redis_key)

        if not redis_code:
            return self.response_http_json_error(400, message='请先获取验证码!')

        partner_data = {
            'name': name,
            'email': email,
            'password': password,
            'lang': lang,
            'warehouse_id': warehouse_id
        }
        partner_id = self.create_res_partner_by_email(partner_data)

        if not partner_id:
            return self.response_http_json_error(400, message='数据异常，请检查数据!!')

        payload_data = {
            'partner_id': partner_id.id,
            'email': email,
            'uid': partner_id.id,
            'aud': LAMP_AUDIENCE,
            'iss': LAMP_ISSUER
        }
        jwt_token = jwt_encode(payload_data, DEFAULT_TOKEN_EXPIRE)

        save_access_token_to_redis(redis_key, jwt_token)

        token_data = {
            'access_token': jwt_token,
            'expire': DEFAULT_TOKEN_EXPIRE
        }

        return self.response_http_json_success(token_data, message='登陆成功')

    @http.route('/api/v1/lamp/user/login', auth='public', methods=['POST'], csrf=False, cors="*", type='json')
    def lamp_user_login(self, lang='en_US', **kwargs):

        try:
            request.env.context = dict(request.env.context, lang=lang)
            payload_data = json.loads(request.httprequest.data)
            _logger.info('payload_data: {}'.format(payload_data))
        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_http_json_error(400, message='出现错误!{}'.format(e))

        email = payload_data.get('email')
        password = payload_data.get('password')

        if not all([email, password]):
            return self.response_http_json_error(400, message='验证码错误!')
        redis_key = email

        try:
            partner_id = self._check_credentials(email, password)
        except Exception as e:
            return self.response_http_json_error(400, message='出现了错误! {}'.format(e))

        if not partner_id:
            return self.response_http_json_error(400, message='登录失败!')

        payload_data = {
            'id': partner_id.id,
            'email': email,
            'uid': partner_id.id,
            'aud': LAMP_AUDIENCE,
            'iss': LAMP_ISSUER
        }
        jwt_token = jwt_encode(payload_data, DEFAULT_TOKEN_EXPIRE)

        save_access_token_to_redis(redis_key, jwt_token)

        token_data = {
            'access_token': jwt_token,
            'expire': DEFAULT_TOKEN_EXPIRE
        }

        return self.response_http_json_success(token_data, message='登陆成功')

    @http.route('/api/v1/lamp/user/reset-password', auth='public', methods=['POST'], csrf=False, cors="*", type='json')
    @verify_auth_token_only()
    def reset_user_password(self, lang='en_US'):
        try:
            request.env.context = dict(request.env.context, lang=lang)
            payload_data = json.loads(request.httprequest.data)
            _logger.info('payload_data: {}'.format(payload_data))
        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_http_json_error(400, message='出现错误!{}'.format(e))

        password = payload_data.get('password')
        new_password = payload_data.get('new_password')

        if not all([new_password, password]):
            return self.response_http_json_error(400, message='数据异常，不能为空!')

        if new_password == password:
            return self.response_http_json_error(400, message='重置的密码不能和当前的密码一致!')

        update_state = self.update_partner_password(request.partner_id, password, new_password)

        if not update_state:
            return self.response_http_json_error(400, message='更新密码出错!')

        return self.response_http_json_success({
            'message': 'success'
        })

    @http.route('/api/v1/lamp/user/forget/password/code', auth='public', methods=['POST'], csrf=False, cors="*",
                type='json')
    def send_forget_user_password_email_code(self, lang='en_US'):
        try:
            request.env.context = dict(request.env.context, lang=lang)
            payload_data = json.loads(request.httprequest.data)
            _logger.info('payload_data: {}'.format(payload_data))
        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_http_json_error(400, message='出现错误!{}'.format(e))

        email = payload_data.get('email')

        if not email:
            return self.response_http_json_error(400, message='数据异常，不能为空!')

        redis_key = email

        if self.get_cache_code_from_redis(redis_key):
            return self.response_http_json_error(400, message='1分钟内，请不要重复发送!')

        email_code = get_random_login_code()

        server_id = request.env['ir.mail_server'].sudo().search([], limit=1)
        mail = request.env['mail.mail'].sudo().create({
            'subject': 'Reset Password Code',
            'body_html': '<p>Dear Sir/Madam：</p><br/>Your code is :{}'.format(email_code),
            'email_to': '{}'.format(email),
            'email_from': server_id.smtp_user if server_id else False,
        })
        mail.send()

        self.save_cache_code_to_redis(redis_key, email_code)

        return self.response_http_json_success({
            'message': 'success'
        })

    @http.route('/api/v1/lamp/user/forget-password', auth='public', methods=['POST'], csrf=False, cors="*", type='json')
    def forget_user_password(self, lang='en_US'):
        try:
            request.env.context = dict(request.env.context, lang=lang)
            payload_data = json.loads(request.httprequest.data)
            _logger.info('payload_data: {}'.format(payload_data))
        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_http_json_error(400, message='出现错误!{}'.format(e))

        email = payload_data.get('email')
        password = payload_data.get('password')
        code = payload_data.get('code')

        if not all([code, password]):
            return self.response_http_json_error(400, message='数据异常，不能为空!')

        cache_code = self.get_cache_code_from_redis(email)

        if not cache_code:
            return self.response_http_json_error(400, message='请先获取验证码!')

        if cache_code.decode() != code:
            return self.response_http_json_error(400, message='验证码异常!')

        update_state = self.update_partner_password_forget_password(email, password)

        if not update_state:
            return self.response_http_json_error(400, message='更新密码出错!')

        return self.response_http_json_success({
            'message': 'success'
        })

    @http.route('/api/v1/lamp/token/check', auth='public', methods=['POST'], csrf=False, cors="*", type='json')
    @verify_auth_token_only()
    def check_user_login_token(self, lang='en_US'):
        return self.response_http_json_success({
            'message': 'success'
        })

    @http.route('/api/v1/lamp/user/profile', auth='public', methods=['get'], csrf=False, cors="*", type='http')
    @verify_auth_token_only()
    def user_profile(self, lang='en_US'):
        request.env.context = dict(request.env.context, lang=lang)
        partner_id = request.env['res.partner'].sudo().browse(request.partner_id)

        user_data = {
            'name': partner_id.name,
            'avatar': partner_id.get_pres_partner_attachment_url(partner_id),
            'mobile': partner_id.mobile,
            'email': partner_id.email,
            'remaining_points': partner_id.remaining_points,
            'warehouse_id': partner_id.warehouse_id.id if partner_id.warehouse_id else '',
            'warehouse_name': partner_id.warehouse_id.name if partner_id.warehouse_id else '',
            'customer_service': partner_id.warehouse_id.customer_service if partner_id.warehouse_id else '',
        }
        return self.response_json_success(user_data)

    @http.route('/api/v1/lamp/user/profile', auth='public', methods=['PATCH'], csrf=False, cors="*", type='json')
    @verify_auth_token_only()
    def update_my_profile(self, lang='en_US'):
        request.env.context = dict(request.env.context, lang=lang)
        partner_id = request.env['res.partner'].sudo().browse(request.partner_id)

        try:
            request.env.context = dict(request.env.context, lang=lang)
            payload_data = json.loads(request.httprequest.data)
            _logger.info('payload_data: {}'.format(payload_data))
            warehouse_id = payload_data.get('warehouse_id')
            if warehouse_id:
                warehouse_id = int(warehouse_id)
        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_http_json_error(400, message='出现错误!{}'.format(e))

        avatar = payload_data.get('avatar')

        lang = payload_data.get('lang')
        mobile = payload_data.get('mobile')
        name = payload_data.get('name')

        update_partner = {}
        if avatar:
            update_partner['image_1920'] = avatar

        if warehouse_id:
            update_partner['warehouse_id'] = warehouse_id

        if lang:
            update_partner['lang'] = lang

        if mobile:
            update_partner['mobile'] = mobile

        if name:
            update_partner['name'] = name

        if not update_partner:
            return self.response_http_json_error(code=400, message='没有可以更新的内容!')

        partner_id.write(update_partner)

        return self.response_http_json_success(200, message='更新成功')

    @http.route('/api/v1/lamp/user/points/history', auth='public', methods=['get'], csrf=False, cors="*", type='http')
    @verify_auth_token_only()
    def user_point_history(self, lang='en_US'):
        request.env.context = dict(request.env.context, lang=lang)
        partner_id = request.env['res.partner'].sudo().browse(request.partner_id)

        points_data = [{
            'order_no': earned_loyalty_id.order_no,
            'order_date': str(earned_loyalty_id.order_date),
            'points': earned_loyalty_id.points,
        } for earned_loyalty_id in partner_id.earned_loyalty_ids]
        return self.response_json_success(points_data)
