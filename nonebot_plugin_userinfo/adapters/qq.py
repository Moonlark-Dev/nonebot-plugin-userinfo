from typing import Any, Optional

from nonebot.exception import ActionFailed
from nonebot.log import logger

from ..getter import UserInfoGetter, register_user_info_getter
from ..image_source import ImageUrl, QQAvatarOpenId
from ..user_info import UserInfo

try:
    from nonebot.adapters import qq as qq_adapter

    Bot = qq_adapter.Bot
    Event = qq_adapter.Event
    C2CMessageCreateEvent = qq_adapter.C2CMessageCreateEvent
    GroupAtMessageCreateEvent = qq_adapter.GroupAtMessageCreateEvent
    GuildMessageEvent = qq_adapter.GuildMessageEvent

    # GroupMessageCreateEvent / InteractionCreateEvent 只在较新的 adapter
    # 中存在，旧版本没有这两个事件，不能因此让整个 QQ getter 注册失败。
    GroupMessageCreateEvent = getattr(qq_adapter, "GroupMessageCreateEvent", None)
    InteractionCreateEvent = getattr(qq_adapter, "InteractionCreateEvent", None)

    _message_events = tuple(
        event_type
        for event_type in (
            C2CMessageCreateEvent,
            GroupAtMessageCreateEvent,
            GroupMessageCreateEvent,
            InteractionCreateEvent,
        )
        if event_type is not None
    )
    _group_message_events = tuple(
        event_type
        for event_type in (GroupAtMessageCreateEvent, GroupMessageCreateEvent)
        if event_type is not None
    )

    def _get_attr(obj: Any, name: str) -> Any:
        """读取字段，兼容尚未提供该字段的旧版 QQ adapter。"""
        return getattr(obj, name, None)

    @register_user_info_getter(Bot, Event)
    class Getter(UserInfoGetter[Bot, Event]):
        async def _get_info(self, user_id: str) -> Optional[UserInfo]:
            user = None

            if self.bot.self_id == user_id:
                try:
                    user = await self.bot.me()
                except ActionFailed as e:
                    logger.warning(f"Error calling me: {e}")

            if not user and isinstance(self.event, GuildMessageEvent):
                if self.event.author.id == user_id:
                    user = self.event.author
                else:
                    guild_id = self.event.guild_id
                    try:
                        member = await self.bot.get_member(
                            guild_id=guild_id, user_id=user_id
                        )
                        if member:
                            user = member.user
                    except ActionFailed as e:
                        logger.warning(f"Error calling get_member: {e}")

            if user:
                return UserInfo(
                    user_id=user.id,
                    user_name=user.username or "",
                    user_avatar=ImageUrl(url=user.avatar) if user.avatar else None,
                )

            if isinstance(self.event, _message_events):
                user_name = ""
                user_role = None

                # GROUP_MESSAGE_CREATE 的 author 现在会携带 username、
                # member_role 等群成员字段，但它们只属于消息发送者。
                author = _get_attr(self.event, "author")
                if author is not None:
                    author_ids = {
                        _get_attr(author, "id"),
                        _get_attr(author, "member_openid"),
                        _get_attr(author, "user_openid"),
                    }
                    if user_id in author_ids:
                        user_name = _get_attr(author, "username") or ""
                        user_role = _get_attr(author, "member_role")
                    elif isinstance(self.event, _group_message_events):
                        # 查询群里的其他成员时，旧版 adapter 没有对应接口，
                        # 新版 adapter 可以通过 member_openid 拉取完整信息。
                        get_group_member = getattr(self.bot, "get_group_member", None)
                        group_openid = _get_attr(self.event, "group_openid")
                        if callable(get_group_member) and group_openid:
                            try:
                                member = await get_group_member(
                                    group_openid=group_openid,
                                    member_openid=user_id,
                                )
                            except ActionFailed as e:
                                logger.warning(f"Error calling get_group_member: {e}")
                            else:
                                if member:
                                    user_name = _get_attr(member, "username") or ""
                                    user_role = _get_attr(member, "member_role")

                return UserInfo(
                    user_id=user_id,
                    user_name=user_name,
                    user_avatar=QQAvatarOpenId(
                        appid=self.bot.bot_info.id, user_openid=user_id
                    ),
                    user_role=user_role,
                )

except ImportError:
    pass
