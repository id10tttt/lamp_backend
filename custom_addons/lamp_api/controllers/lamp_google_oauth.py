# -*- coding: utf-8 -*-
from odoo import http
from .base import BaseController
from odoo.exceptions import AccessDenied
from ..tools.tools_common import jwt_encode, DEFAULT_TOKEN_EXPIRE, LAMP_AUDIENCE, LAMP_ISSUER
import logging
import google_auth_oauthlib.flow


_logger = logging.getLogger(__name__)


class AuthJWTAuth(http.Controller, BaseController):

    @http.route('/auth_oauth/google/signin', type='json', auth='public', methods=['GET'], csrf=False)
    def get_oauth_signin_url(self, *args, **kwargs):
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            'client_secret.json',
            scopes=[
                'https://www.googleapis.com/auth/drive.metadata.readonly',
                'https://www.googleapis.com/auth/calendar.readonly'])
        flow.redirect_uri = 'http://139.196.232.85:8069/auth_oauth/google/oauth2callback'
        authorization_url, state = flow.authorization_url(
            # Recommended, enable offline access so that you can refresh an access token without
            # re-prompting the user for permission. Recommended for web server apps.
            access_type='offline',
            # Optional, enable incremental authorization. Recommended as a best practice.
            include_granted_scopes='true',
            # Optional, set prompt to 'consent' will prompt the user for consent
            prompt='consent')

        return self.response_http_json_success(data={
            'authorization_url': authorization_url,
            'state': state
        }, message='成功')

    @http.route('/auth_oauth/google/oauth2callback', type='json', auth='public', methods=['POST'], csrf=False)
    def oauth_signin(self, *args, **kwargs):
        # 获取 OAuth2 登录信息
        provider = kwargs.get('provider')
        if provider != 'google':
            raise AccessDenied("Unsupported OAuth provider.")

        # 使用 Google OAuth 获取用户信息
        token = kwargs.get('token')
        user_info = self._get_google_user_info(token)

        user_email = user_info['email']
        # # 查找或创建用户
        # user = request.env['res.users'].sudo().search([('email', '=', user_info['email'])], limit=1)
        # if not user:
        #     user = request.env['res.users'].sudo().create({
        #         'name': user_info['name'],
        #         'login': user_info['email'],
        #         'email': user_info['email'],
        #     })

        # 查找或创建用户
        partner_id = self.get_or_create_res_partner(user_email)

        payload_data = {
            'mobile': user_email,
            'uid': partner_id.id,
            'aud': LAMP_AUDIENCE,
            'iss': LAMP_ISSUER
        }
        jwt_token = jwt_encode(payload_data, DEFAULT_TOKEN_EXPIRE)

        if not partner_id:
            return self.response_http_json_error(400, message='数据异常，请检查数据!!')

        token_data = {
            'access_token': jwt_token,
            'expire': DEFAULT_TOKEN_EXPIRE
        }

        _logger.info('google jwt token: {}'.format(token_data))

        return self.response_http_json_success(token_data, message='登陆成功')

    def _get_google_user_info(self, token):
        # 使用 Google API 获取用户信息（你可以使用 google-auth 库或直接调用 Google API）
        import google.auth.transport.requests
        import google.oauth2.id_token

        # 使用 Google OAuth 2.0 验证 ID token
        try:
            credentials, project_id = google.auth.load_credentials_from_file('path_to_your_credentials.json')
            request_session = google.auth.transport.requests.Request()
            id_info = google.oauth2.id_token.verify_oauth2_token(token, request_session, credentials.client_id)

            # 返回用户信息
            return {
                'email': id_info['email'],
                'name': id_info['name'],
            }
        except Exception as e:
            raise AccessDenied(f"Failed to verify Google token: {str(e)}")
