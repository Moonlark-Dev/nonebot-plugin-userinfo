import asyncio
import re
import ssl

import httpx
from nonebot.log import logger

from .config import plugin_config
from .exception import NetworkError


def _tls12_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_2
    return context


async def download_url(url: str) -> bytes:
    kwargs = {}
    if plugin_config.userinfo_force_tls12:
        kwargs["verify"] = _tls12_context()
    async with httpx.AsyncClient(**kwargs) as client:
        for i in range(3):
            try:
                resp = await client.get(url, timeout=10)
                resp.raise_for_status()
                return resp.content
            except Exception as e:
                logger.warning(f"Error downloading {url}, retry {i}/3: {e}")
                await asyncio.sleep(3)
    raise NetworkError(f"{url} 下载失败！")


def check_qq_number(qq: str) -> bool:
    return bool(re.match(r"^\d{5,11}$", qq))
