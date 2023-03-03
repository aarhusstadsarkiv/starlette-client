import requests
import json
import typing

from .dynamic_settings import settings
from .logging import log
from .translate import translate


class FastAPIException(Exception):
    pass


class FastAPIClient:

    def __init__(self, **kwargs):
        self.url = kwargs.get('url', settings['fastapi_endpoint'])
        self.timeout = kwargs.get('timeout', 10)

    async def register(self, form_dict: dict) -> typing.Any:

        self.url += '/v1/auth/register'

        def request():
            return requests.post(self.url, json=form_dict, timeout=self.timeout)

        response = self._call(request)

        if response.status_code == 201:
            response_content = json.loads(response.content)
            return response_content
        else:

            if response.status_code == 400:
                raise FastAPIException(translate(
                    "User already exists. Try to login instead."), response.status_code, response.text)

            if response.status_code == 422:
                raise FastAPIException(translate(
                    "Email needs to be correct. Password needs to be at least 8 characters long."),
                    response.status_code, response.text)

    async def forgot_password(self, email: str) -> bytes:

        self.url += '/v1/auth/forgot-password'
        form_dict = {"email": email}

        def request():
            return requests.post(
                self.url,
                json=form_dict, timeout=self.timeout)

        response = self._call(request)
        if response.status_code == 202:
            # 'null' as string if correct
            return response.content
        else:
            raise FastAPIException(
                translate("System can not deliver an email about resetting password. Try again later."),
                response.status_code, response.text)

    def reset_password(self, token: str, password: str) -> bytes:

        self.url += '/v1/auth/reset-password'
        form_dict = {"token": token, "password": password}

        def request():
            return requests.post(
                self.url,
                json=form_dict, timeout=self.timeout)

        response = self._call(request)
        if response.status_code == 200:
            # 'null' as string if correct
            return response.content
        else:
            raise FastAPIException(translate("Reset of your password failed"),
                                   response.status_code, response.text)

    async def login_cookie(self, username: str, password: str) -> dict:

        self.url += '/v1/auth/login'
        session = requests.Session()

        def request():
            return session.post(
                self.url,
                data={"username": username, "password": password}, timeout=self.timeout)

        response = self._call(request)

        if response.status_code == 200:
            # 'null' as string if correct
            cookie = session.cookies.get_dict()['_auth']
            return {'_auth': cookie}
        else:
            raise FastAPIException(
                translate("Email or password is incorrect. Or your user has not been activated."),
                response.status_code, response.text)

    def logout_cookie(self, cookie: str) -> str:

        self.url += '/v1/auth/logout'
        session = requests.Session()
        session.cookies.set('_auth', cookie)

        def request():
            return session.post(
                self.url,
                json={}, timeout=self.timeout)

        response = self._call(request)

        if response.status_code == 200:
            # 'null' as string if correct
            return json.loads(response.content)
        else:
            raise FastAPIException(
                translate("Logout cookie failed"), response.status_code, response.text)

    async def login_jwt(self, username: str, password: str) -> str:

        self.url += '/v1/auth/jwt/login'

        def request() -> requests.Response:
            return requests.post(
                self.url,
                data={"username": username, "password": password}, timeout=self.timeout)

        response = self._call(request)

        if response.status_code == 200:
            return json.loads(response.content)
        else:
            raise FastAPIException(
                translate("Email or password is incorrect. Or your user has not been activated."),
                response.status_code, response.text)

    def logout_jwt(self, token: str, token_type: str = 'Bearer') -> dict:
        self.url += '/v1/auth/jwt/logout'

        headers = {'Authorization': f'{token_type} {token}'}

        def request() -> requests.Response:
            return requests.post(self.url, json={}, timeout=self.timeout, headers=headers)

        response = self._call(request)

        if response.status_code == 200:
            return json.loads(response.content)
        else:
            raise FastAPIException("Logout JWT failed",
                                   response.status_code, response.text)

    def me_jwt(self, access_token: str, token_type: str) -> dict:
        self.url += '/v1/users/me'

        headers = {
            'Authorization': f'{token_type} {access_token}'} if access_token else None

        def request() -> requests.Response:
            return requests.get(self.url, timeout=self.timeout, headers=headers)

        response = self._call(request)

        if response.status_code == 200:
            return json.loads(response.content)
        else:
            raise FastAPIException(
                translate("Me failed"), response.status_code, response.text)

    async def me_cookie(self, cookie: str) -> dict:
        self.url += '/v1/users/me'

        cookies = {'_auth': cookie} if cookie else None

        def request() -> requests.Response:
            return requests.get(self.url, timeout=self.timeout, cookies=cookies)

        response = self._call(request)

        if response.status_code == 200:
            return json.loads(response.content)
        else:
            raise FastAPIException(
                translate("Me failed"), response.status_code, response.text)

    def log_response(self, response: requests.Response) -> None:
        log.debug(self.url)
        log.debug(response.status_code)
        log.debug(response.text)

    def _call(self, func) -> requests.Response:
        try:
            return func()
        except Exception as e:
            log.error(e)
            raise FastAPIException("Network error", 408, "Request timeout")
