from nonebot import get_plugin_config
from pydantic import BaseModel


class Config(BaseModel):
    """Plugin Config Here"""

    userinfo_force_tls12: bool = False
    """强制 download_url 使用 TLSv1.2"""


plugin_config = get_plugin_config(Config)
