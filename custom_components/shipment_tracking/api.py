import aiohttp
import asyncio
import async_timeout
import logging
import json
import time
import urllib.parse
import re
import html
import secrets

_LOGGER = logging.getLogger(__name__)

def normalize_phone(phone: str) -> str:
    """Return a 9-digit phone number as a string."""
    clean = re.sub(r'\D', '', str(phone))
    if len(clean) > 9 and clean.startswith('48'):
        clean = clean[2:]
    elif len(clean) > 9 and clean.startswith('0048'):
        clean = clean[4:]
    return clean

class InPostApi:
    BASE_URL = "https://api-inmobile-pl.easypack24.net"

    def __init__(self, session: aiohttp.ClientSession, device_uid: str = None):
        self._session = session
        self._token = None
        self._refresh_token = None
        self._device_uid = device_uid

    async def request(self, method, path, data=None, headers=None):
        """
        Perform a request against the InPost API with basic error handling and timeouts.

        A 30-second timeout is applied to avoid blocking the event loop.  Client errors
        (e.g. network issues) and timeouts are logged and re-raised as generic exceptions
        so that the coordinator can handle them uniformly.
        """
        if headers is None:
            headers = {}

        url = f"{self.BASE_URL}/{path.lstrip('/')}"
        default_headers = {
            "Content-Type": "application/json",
            "User-Agent": "InPost-Mobile",
            "Accept": "application/json",
        }

        if self._device_uid:
            default_headers["device-uid"] = self._device_uid
        if self._token:
            default_headers["Authorization"] = f"Bearer {self._token}"

        headers = {**default_headers, **headers}

        try:
            async with async_timeout.timeout(30):
                async with self._session.request(method, url, json=data, headers=headers) as resp:
                    text = await resp.text()
                    if resp.status >= 400:
                        if resp.status == 401:
                            _LOGGER.info("InPost error %s: %s", resp.status, text)
                        else:
                            _LOGGER.error("InPost error %s: %s", resp.status, text)
                        raise Exception(f"InPost API Error: {resp.status} - {text}")
                    try:
                        return json.loads(text)
                    except Exception:
                        # Return raw text if JSON decoding fails
                        return text
        except asyncio.TimeoutError:
            _LOGGER.error("InPost API request to %s timed out", url)
            raise Exception("InPost API request timed out")
        except aiohttp.ClientError as err:
            _LOGGER.error("InPost API client error: %s", err)
            raise Exception(f"InPost API client error: {err}")

    async def send_sms_code(self, phone_number):
        phone = normalize_phone(phone_number)
        payload = {
            "phoneNumber": {
                "value": str(phone),
                "prefix": "+48"
            }
        }
        return await self.request("POST", "/v1/account", payload)

    async def confirm_sms_code(self, phone_number, code):
        phone = normalize_phone(phone_number)
        payload = {
            "phoneNumber": {
                "value": str(phone),
                "prefix": "+48"
            },
            "smsCode": str(code),
            "devicePlatform": "Android"
        }
        data = await self.request("POST", "/v1/account/verification", payload)
        self._token = data.get("authToken")
        self._refresh_token = data.get("refreshToken")
        return data

    async def refresh_token(self):
        """Refresh the InPost token."""
        if not self._refresh_token:
            raise Exception("Missing InPost refresh token")
            
        payload = {
            "refreshToken": self._refresh_token,
            "phoneOS": "Android"
        }
        
        data = await self.request("POST", "v1/authenticate", payload)
        
        new_auth = data.get("authToken")
        if new_auth:
            self._token = new_auth
            if data.get("refreshToken"):
                self._refresh_token = data.get("refreshToken")
        
        return data

    async def get_parcels(self):
        return await self.request("GET", "v4/parcels/tracked")


class DpdApi:
    SSO_URL = "https://dpdsso.dpd.com.pl"
    API_URL = "https://mobapp.dpd.com.pl"
    CLIENT_ID = "DPDClientMDU"

    def __init__(self, session: aiohttp.ClientSession):
        self._session = session
        self._token = None
        self._refresh_token = None
        self._expires_at = 0

    async def request(self, method, url, data=None, headers=None, form_data=None):
        """
        Perform a DPD API call with token refresh, timeout and error handling.

        A 30-second timeout is applied.  Network errors and timeouts are logged and
        raised as generic exceptions.
        """
        if headers is None:
            headers = {}

        # Refresh access token if it is about to expire
        if self._token and self._refresh_token and time.time() > self._expires_at - 60:
            await self.refresh_access_token()

        default_headers = {
            "Accept": "application/json",
            "User-Agent": "DPD Mobile",
        }
        if self._token:
            default_headers["Authorization"] = f"Bearer {self._token}"
        headers = {**default_headers, **headers}

        kwargs = {"headers": headers}
        if data:
            kwargs["json"] = data
        if form_data:
            kwargs["data"] = form_data

        try:
            async with async_timeout.timeout(30):
                async with self._session.request(method, url, **kwargs) as resp:
                    text = await resp.text()
                    if resp.status >= 400:
                        if resp.status == 401:
                            _LOGGER.info("DPD error %s: %s", resp.status, text)
                        else:
                            _LOGGER.error("DPD error %s: %s", resp.status, text)
                        raise Exception(f"DPD API Error: {resp.status}")
                    try:
                        return json.loads(text)
                    except Exception:
                        return text
        except asyncio.TimeoutError:
            _LOGGER.error("DPD API request to %s timed out", url)
            raise Exception("DPD API request timed out")
        except aiohttp.ClientError as err:
            _LOGGER.error("DPD API client error: %s", err)
            raise Exception(f"DPD API client error: {err}")

    async def send_sms_code(self, phone_number):
        phone = normalize_phone(phone_number)
        url = f"{self.SSO_URL}/api/phone-verifications/{phone}"
        await self.request("PUT", url)
        return True

    async def register_with_code(self, phone_number, code):
        phone = normalize_phone(phone_number)
        url = f"{self.SSO_URL}/api/users"
        params = {
            "redirect_uri": "https://dpdsso.dpd.com.pl/landing-page?messageType=activeAccount",
            "client_id": self.CLIENT_ID
        }
        url_with_params = f"{url}?{urllib.parse.urlencode(params)}"
        
        payload = {
            "emailRegistration": None,
            "phoneRegistration": {"phone": phone, "code": code},
            "type": "PhoneBasedUserRegistrationModel"
        }
        
        resp = await self.request("POST", url_with_params, data=payload)
        auth_code = resp.get("code")
        
        token_url = f"{self.SSO_URL}/auth/realms/DPD/protocol/openid-connect/token"
        form_data = {
            "code": auth_code,
            "grant_type": "authorization_code",
            "client_id": self.CLIENT_ID
        }
        token_data = await self.request("POST", token_url, form_data=form_data)
        self._save_token_data(token_data)
        return token_data

    async def refresh_access_token(self):
        if not self._refresh_token: return
        
        url = f"{self.SSO_URL}/auth/realms/DPD/protocol/openid-connect/token"
        form_data = {
            "refresh_token": self._refresh_token,
            "grant_type": "refresh_token",
            "client_id": self.CLIENT_ID
        }
        try:
            async with self._session.post(url, data=form_data) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._save_token_data(data)
        except Exception as e:
             _LOGGER.error(f"DPD Token refresh failed: {e}")

    def _save_token_data(self, data):
        self._token = data.get("access_token")
        self._refresh_token = data.get("refresh_token")
        self._expires_at = time.time() + data.get("expires_in", 300)

    async def get_parcels(self):
        url = f"{self.API_URL}/mdupackageservices/api/v1/packages?userContext=RECEIVER"
        headers = {
            "X-Mobile-Platform": "android",
            "X-Mobile-Version": "2.10.2"
        }
        payload = {"alias": None, "sent": None}
        return await self.request("POST", url, data=payload, headers=headers)


class DhlApi:
    BASE_URL = "https://mojdhl.pl/api/dhl/public"

    def __init__(self, session: aiohttp.ClientSession, device_id: str = None):
        self._session = session
        self._token = None
        self._cookies = {}
        self._device_id = device_id

    async def request(self, method: str, path: str, data: dict | None = None):
        """
        Perform a request against the DHL API with error handling and a timeout.

        A 30-second timeout is applied to avoid blocking the event loop.  Client
        errors and timeouts are logged and re-raised as generic exceptions so
        callers can handle them uniformly.  The method will also capture any
        cookies returned by the API and include them on subsequent calls.

        :param method: HTTP method (GET/POST etc.)
        :param path: API path relative to the base URL
        :param data: Optional JSON payload for the request
        :return: Parsed JSON response or raw text
        :raises Exception: on HTTP errors, timeouts or client exceptions
        """
        url = f"{self.BASE_URL}/{path.lstrip('/')}"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "pl-PL",
            "Origin": "https://mojdhl.pl",
        }
        # Add authorization header if token is present
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        # Include any stored cookies in the request
        cookie_header = "; ".join([f"{k}={v}" for k, v in self._cookies.items()])
        if cookie_header:
            headers["Cookie"] = cookie_header

        try:
            async with async_timeout.timeout(30):
                async with self._session.request(method, url, json=data, headers=headers) as resp:
                    # Store any Set-Cookie headers for subsequent requests
                    if "Set-Cookie" in resp.headers:
                        for cookie in resp.headers.getall("Set-Cookie", []):
                            parts = cookie.split(';')[0].split('=', 1)
                            if len(parts) == 2:
                                self._cookies[parts[0]] = parts[1]

                    text = await resp.text()
                    if resp.status >= 400:
                        if resp.status == 401:
                            _LOGGER.info("DHL API error %s: %s", resp.status, text)
                        else:
                            _LOGGER.error("DHL API error %s: %s", resp.status, text)
                        raise Exception(f"DHL API Error: {resp.status} - {text}")
                    try:
                        return json.loads(text)
                    except Exception:
                        return text
        except asyncio.TimeoutError:
            _LOGGER.error("DHL API request to %s timed out", url)
            raise Exception("DHL API request timed out")
        except aiohttp.ClientError as err:
            _LOGGER.error("DHL API client error: %s", err)
            raise Exception(f"DHL API client error: {err}")

    async def validate_account(self, phone):
        return await self.request("POST", "auth/validate-account", {
            "phoneNumber": normalize_phone(phone), "prefix": "48", "captcha-payload": " "
        })

    async def generate_code(self, phone, captcha_payload=" "):
        return await self.request("POST", "auth/generate-code", {
            "phoneNumber": normalize_phone(phone), 
            "prefix": "48", 
            "isMobileDevice": False, 
            "captcha-payload": captcha_payload
        })

    async def validate_code(self, phone, code, device_id):
        data = await self.request("POST", "auth/validate-code", {
            "phoneNumber": normalize_phone(phone),
            "prefix": "48",
            "smsCode": code,
            "deviceId": device_id,
            "deviceName": "HomeAssistant",
            "rememberMe": True,
            "captcha-payload": " "
        })
        self._token = data.get("accessToken") or data.get("data", {}).get("accessToken")
        return data

    async def refresh_token(self):
        """Refresh the DHL token using the auth/recover endpoint."""
        if not self._device_id:
            raise Exception("Device ID required for DHL refresh")
        
        payload = {
            "deviceName": "HomeAssistant",
            "deviceId": self._device_id
        }
        
        if self._token:
            self._cookies["access-token"] = self._token

        data = await self.request("POST", "auth/recover", data=payload)
        
        new_token = data.get("accessToken") or data.get("data", {}).get("accessToken")
        if new_token:
            self._token = new_token
        return data

    async def get_parcels(self):
        return await self.request("POST", "user/shipment/v2.1/list/incoming/active/1", {
            "shipmentFilterTypes": [],
            "shipmentFilterStatuses": [],
            "page": 1
        })


class PocztexApi:
    API_BASE_URL = "https://aplikacja.pocztex.pl/api/customer"
    AUTH_BASE_URL = "https://idm.pocztex.pl"
    AUTH_REALM = "ppsa"
    CLIENT_ID = "mobile"
    REDIRECT_URI = "pocztex://auth/redirect"
    SCOPE = "offline_access"
    APP_VERSION = "1.0.12"
    LANGUAGE = "PL"
    LOGIN_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) "
        "Gecko/20100101 Firefox/147.0"
    )
    LOGIN_ACCEPT_LANGUAGE = "en-US,en;q=0.9"
    LOGIN_ORIGIN = "null"

    def __init__(self, session: aiohttp.ClientSession):
        self._session = session
        self._token = None
        self._refresh_token = None
        self._expires_at = 0
        self._refresh_expires_at = 0

    def _token_url(self):
        base = self.AUTH_BASE_URL.rstrip("/")
        realm = str(self.AUTH_REALM).strip("/")
        return f"{base}/realms/{realm}/protocol/openid-connect/token"

    def _authorize_url(self, state):
        base = self.AUTH_BASE_URL.rstrip("/")
        realm = str(self.AUTH_REALM).strip("/")
        auth_url = f"{base}/realms/{realm}/protocol/openid-connect/auth"
        params = {
            "client_id": self.CLIENT_ID,
            "response_type": "code",
            "redirect_uri": self.REDIRECT_URI,
        }
        if self.SCOPE:
            params["scope"] = self.SCOPE
        if state:
            params["state"] = state
        return f"{auth_url}?{urllib.parse.urlencode(params)}"

    async def _request_json(self, method, url, data=None, headers=None):
        """
        Internal helper to perform a request and parse JSON for the Pocztex API.

        A 30-second timeout is used.  Network errors and timeouts are logged
        and re-raised as generic exceptions.  The helper returns parsed JSON
        when possible, otherwise the raw text response.
        """
        if headers is None:
            headers = {}
        try:
            async with async_timeout.timeout(30):
                async with self._session.request(method, url, data=data, headers=headers, allow_redirects=False) as resp:
                    text = await resp.text()
                    if resp.status >= 400:
                        if resp.status == 401:
                            _LOGGER.info("Pocztex error %s: %s", resp.status, text)
                        else:
                            _LOGGER.error("Pocztex error %s: %s", resp.status, text)
                        raise Exception(f"Pocztex API Error: {resp.status} - {text}")
                    try:
                        return json.loads(text)
                    except Exception:
                        return text
        except asyncio.TimeoutError:
            _LOGGER.error("Pocztex API request to %s timed out", url)
            raise Exception("Pocztex API request timed out")
        except aiohttp.ClientError as err:
            _LOGGER.error("Pocztex API client error: %s", err)
            raise Exception(f"Pocztex API client error: {err}")

    def _parse_login_form(self, html_text):
        action = ""
        match = re.search(r'<form[^>]*action=["\\\']([^"\\\']+)["\\\']', html_text, re.IGNORECASE)
        if match:
            action = html.unescape(match.group(1))
        if not action:
            alt = re.search(r'/realms/[^"\\\']+/login-actions/authenticate[^"\\\']*', html_text, re.IGNORECASE)
            if alt:
                action = html.unescape(alt.group(0))
        hidden_inputs = {}
        for match in re.finditer(r'<input[^>]*type=["\\\']hidden["\\\'][^>]*>', html_text, re.IGNORECASE):
            tag = match.group(0)
            name_match = re.search(r'name=["\\\']([^"\\\']+)["\\\']', tag, re.IGNORECASE)
            value_match = re.search(r'value=["\\\']([^"\\\']*)["\\\']', tag, re.IGNORECASE)
            if name_match:
                hidden_inputs[name_match.group(1)] = html.unescape(value_match.group(1)) if value_match else ""
        return action, hidden_inputs

    async def _get_authorization_code(self, email, password):
        state = secrets.token_hex(16)
        auth_url = self._authorize_url(state)
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": self.LOGIN_ACCEPT_LANGUAGE,
            "User-Agent": self.LOGIN_USER_AGENT,
        }

        async with self._session.get(auth_url, headers=headers, allow_redirects=False) as resp:
            auth_html = await resp.text()
            if resp.status >= 400:
                raise Exception(f"Pocztex login page error: {resp.status}")
            action, hidden_inputs = self._parse_login_form(auth_html)
            if not action:
                raise Exception("Pocztex login form action not found")
            post_url = urllib.parse.urljoin(str(resp.url), action)

        form = {**hidden_inputs}
        form.setdefault("credentialId", "")
        form["username"] = email
        form["password"] = password
        form.setdefault("login", "Log in")

        post_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": self.LOGIN_ACCEPT_LANGUAGE,
            "Referer": auth_url,
            "Origin": self.LOGIN_ORIGIN,
            "User-Agent": self.LOGIN_USER_AGENT,
        }

        async with self._session.post(post_url, data=form, headers=post_headers, allow_redirects=False) as resp:
            location = resp.headers.get("Location")
            if location:
                resolved = urllib.parse.urljoin(str(resp.url), location)
                if resolved.startswith("pocztex://"):
                    return self._extract_code(resolved)

                async with self._session.get(resolved, headers=headers, allow_redirects=False) as next_resp:
                    next_location = next_resp.headers.get("Location")
                    if next_location:
                        next_resolved = urllib.parse.urljoin(str(next_resp.url), next_location)
                        if next_resolved.startswith("pocztex://"):
                            return self._extract_code(next_resolved)

            body = await resp.text()
            snippet = " ".join(body.split())[:500] if body else ""
            raise Exception(f"Pocztex login failed. Status {resp.status}. Body: {snippet}")

    def _extract_code(self, redirect_url):
        parsed = urllib.parse.urlparse(redirect_url)
        params = urllib.parse.parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        if not code:
            raise Exception("Pocztex authorization code not found")
        return code

    def _save_token_data(self, data):
        self._token = data.get("access_token")
        self._refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in")
        refresh_expires_in = data.get("refresh_expires_in")
        now = time.time()
        if expires_in:
            self._expires_at = now + int(expires_in) - 30
        if refresh_expires_in:
            self._refresh_expires_at = now + int(refresh_expires_in) - 30

    async def login(self, email, password):
        code = await self._get_authorization_code(email, password)
        token_data = await self._request_json(
            "POST",
            self._token_url(),
            data={
                "grant_type": "authorization_code",
                "client_id": self.CLIENT_ID,
                "code": code,
                "redirect_uri": self.REDIRECT_URI,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        self._save_token_data(token_data)
        return token_data

    async def refresh_token(self):
        if not self._refresh_token:
            raise Exception("Missing Pocztex refresh token")
        if self._refresh_expires_at and time.time() > self._refresh_expires_at:
            raise Exception("Pocztex refresh token expired")

        token_data = await self._request_json(
            "POST",
            self._token_url(),
            data={
                "grant_type": "refresh_token",
                "client_id": self.CLIENT_ID,
                "refresh_token": self._refresh_token,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        self._save_token_data(token_data)
        return token_data

    async def request(self, method, path, params=None):
        """
        Perform a generic request to the Pocztex API with token refresh and timeout.

        If the current token is close to expiration, it is refreshed first.  A
        timeout of 30 seconds is applied.  HTTP errors, client errors and
        timeouts are logged and re-raised as generic exceptions.  Responses are
        parsed as JSON when possible, otherwise returned as raw text.
        """
        # Refresh token if about to expire
        if self._token and self._expires_at and time.time() > self._expires_at - 60:
            await self.refresh_token()

        base = self.API_BASE_URL.rstrip("/")
        url = f"{base}/{path.lstrip('/')}"
        headers = {
            "Accept": "application/json",
            "X-App-Version": self.APP_VERSION,
            "Language": self.LANGUAGE,
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if params is None:
            params = {}
        if "language" not in params and self.LANGUAGE:
            params["language"] = self.LANGUAGE

        try:
            async with async_timeout.timeout(30):
                async with self._session.request(method, url, headers=headers, params=params) as resp:
                    text = await resp.text()
                    if resp.status >= 400:
                        _LOGGER.error("Pocztex API error %s: %s", resp.status, text)
                        raise Exception(f"Pocztex API Error: {resp.status} - {text}")
                    try:
                        return json.loads(text)
                    except Exception:
                        return text
        except asyncio.TimeoutError:
            _LOGGER.error("Pocztex API request to %s timed out", url)
            raise Exception("Pocztex API request timed out")
        except aiohttp.ClientError as err:
            _LOGGER.error("Pocztex API client error: %s", err)
            raise Exception(f"Pocztex API client error: {err}")

    async def get_parcels(self):
        return await self.request("GET", "/tracking")

    async def get_parcel_details(self, tracking_id):
        if tracking_id is None:
            raise Exception("Missing Pocztex tracking id")
        path = f"/tracking/{urllib.parse.quote(str(tracking_id))}/details"
        return await self.request("GET", path)
