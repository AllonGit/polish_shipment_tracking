import aiohttp
import asyncio
import async_timeout
import json
import logging
import re


_LOGGER = logging.getLogger(__name__)


async def request_json(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    *,
    json_data=None,
    data=None,
    headers=None,
    params=None,
    allow_redirects: bool = True,
    timeout: int = 30,
    label: str = "API",
    log_401_as_info: bool = False,
    error_with_text: bool = True,
    on_response=None,
):
    """
    Perform a request, parse JSON when possible, and apply consistent error handling.

    Returns parsed JSON when available, otherwise the raw response text.
    """
    if headers is None:
        headers = {}
    api_label = f"{label} API"
    error_label = f"{api_label} Error"

    try:
        async with async_timeout.timeout(timeout):
            kwargs = {
                "headers": headers,
                "params": params,
                "allow_redirects": allow_redirects,
            }
            if json_data is not None:
                kwargs["json"] = json_data
            if data is not None:
                kwargs["data"] = data

            async with session.request(method, url, **kwargs) as resp:
                if on_response:
                    on_response(resp)

                text = await resp.text()
                if resp.status >= 400:
                    if resp.status == 401 and log_401_as_info:
                        _LOGGER.info("%s error %s: %s", label, resp.status, text)
                    else:
                        _LOGGER.error("%s error %s: %s", label, resp.status, text)
                    if error_with_text:
                        raise Exception(f"{error_label}: {resp.status} - {text}")
                    raise Exception(f"{error_label}: {resp.status}")
                try:
                    return json.loads(text)
                except Exception:
                    return text
    except asyncio.TimeoutError:
        _LOGGER.error("%s request to %s timed out", api_label, url)
        raise Exception(f"{api_label} request timed out")
    except aiohttp.ClientError as err:
        _LOGGER.error("%s client error: %s", api_label, err)
        raise Exception(f"{api_label} client error: {err}")


def normalize_phone(phone: str) -> str:
    """Return a 9-digit phone number as a string."""
    clean = re.sub(r"\D", "", str(phone))
    if len(clean) > 9 and clean.startswith("48"):
        clean = clean[2:]
    elif len(clean) > 9 and clean.startswith("0048"):
        clean = clean[4:]
    return clean
