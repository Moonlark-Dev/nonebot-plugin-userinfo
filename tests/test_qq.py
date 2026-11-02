from datetime import datetime
from typing import Any, Optional

from nonebot.adapters.qq import (
    Bot,
    EventType,
    GroupAtMessageCreateEvent,
    MessageCreateEvent,
)
from nonebot.adapters.qq.config import BotInfo
from nonebot.adapters.qq.models import GroupMemberAuthor, Member, User
from nonebug import App

try:
    from nonebot.adapters.qq import GroupMessageCreateEvent
except ImportError:  # pragma: no cover - 旧版 adapter 没有该事件
    GroupMessageCreateEvent = None  # type: ignore[assignment,misc]

try:
    from nonebot.adapters.qq.models import GroupMemberInfo
except ImportError:  # pragma: no cover - 旧版 adapter 没有群成员接口模型
    GroupMemberInfo = None  # type: ignore[assignment,misc]


def _model_fields(model: Any) -> set[str]:
    fields = getattr(model, "model_fields", None)
    if fields is None:
        fields = getattr(model, "__fields__", {})
    return set(fields)


GROUP_MEMBER_AUTHOR_FIELDS = _model_fields(GroupMemberAuthor)
GROUP_AT_MESSAGE_EVENT_FIELDS = _model_fields(GroupAtMessageCreateEvent)
GROUP_MESSAGE_EVENT_FIELDS = (
    _model_fields(GroupMessageCreateEvent) if GroupMessageCreateEvent else set()
)
GROUP_MEMBER_INFO_FIELDS = _model_fields(GroupMemberInfo) if GroupMemberInfo else set()


def _fake_message_create_event(msg: str) -> MessageCreateEvent:
    return MessageCreateEvent(
        id="id",
        __type__=EventType.MESSAGE_CREATE,
        channel_id="6677",
        guild_id="5566",
        author=User(id="3344", username="MyUser", avatar="http://xxx.jpg"),
        content=msg,
    )


def _fake_group_member_author(
    member_openid: str,
    *,
    username: str = "GroupUser",
    member_role: str = "member",
) -> GroupMemberAuthor:
    kwargs: dict[str, Any] = {"id": "id", "member_openid": member_openid}
    if "bot" in GROUP_MEMBER_AUTHOR_FIELDS:
        kwargs["bot"] = False
    if "username" in GROUP_MEMBER_AUTHOR_FIELDS:
        kwargs["username"] = username
    if "member_role" in GROUP_MEMBER_AUTHOR_FIELDS:
        kwargs["member_role"] = member_role
    return GroupMemberAuthor(**kwargs)


def _fake_group_at_message_create_event(msg: str) -> GroupAtMessageCreateEvent:
    kwargs: dict[str, Any] = {
        "id": "id",
        "content": msg,
        "timestamp": "1234567890",
        "__type__": EventType.GROUP_AT_MESSAGE_CREATE,
        "author": _fake_group_member_author("3F21411B784D403E811E68BF3E2944D8"),
        "group_openid": "19303D3617EF432999F24342F99AEC65",
    }
    if "group_id" in GROUP_AT_MESSAGE_EVENT_FIELDS:
        kwargs["group_id"] = "group_id"
    return GroupAtMessageCreateEvent(**kwargs)


def _fake_group_message_create_event(msg: str) -> "GroupMessageCreateEvent":
    assert GroupMessageCreateEvent is not None
    kwargs: dict[str, Any] = {
        "id": "id",
        "content": msg,
        "timestamp": "1234567890",
        "__type__": EventType.GROUP_MESSAGE_CREATE,
        "author": _fake_group_member_author("3F21411B784D403E811E68BF3E2944D8"),
        "group_id": "group_id",
        "group_openid": "19303D3617EF432999F24342F99AEC65",
    }
    return GroupMessageCreateEvent(**kwargs)


def _fake_group_member_info(
    member_openid: str,
    *,
    username: str = "OtherUser",
    member_role: str = "admin",
) -> "GroupMemberInfo":
    assert GroupMemberInfo is not None
    kwargs: dict[str, Any] = {"member_openid": member_openid}
    if "bot" in GROUP_MEMBER_INFO_FIELDS:
        kwargs["bot"] = False
    if "username" in GROUP_MEMBER_INFO_FIELDS:
        kwargs["username"] = username
    if "member_role" in GROUP_MEMBER_INFO_FIELDS:
        kwargs["member_role"] = member_role
    return GroupMemberInfo(**kwargs)


def _expected_group_user_info(
    user_id: str,
    *,
    username: str,
    member_role: Optional[str],
    fields: set[str],
) -> Any:
    from nonebot_plugin_userinfo import UserInfo
    from nonebot_plugin_userinfo.image_source import QQAvatarOpenId

    return UserInfo(
        user_id=user_id,
        user_name=username if "username" in fields else "",
        user_displayname=None,
        user_remark=None,
        user_avatar=QQAvatarOpenId(appid="2233", user_openid=user_id),
        user_gender="unknown",
        user_role=member_role if "member_role" in fields else None,
    )


async def test_message_event(app: App):
    from nonebot_plugin_userinfo import UserInfo
    from nonebot_plugin_userinfo.image_source import ImageUrl

    async with app.test_matcher() as ctx:
        bot = ctx.create_bot(
            base=Bot, self_id="2233", bot_info=BotInfo(id="2233", token="", secret="")
        )

        user_info = UserInfo(
            user_id="3344",
            user_name="MyUser",
            user_displayname=None,
            user_remark=None,
            user_avatar=ImageUrl(url="http://xxx.jpg"),
            user_gender="unknown",
        )
        event = _fake_message_create_event("/user_info")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "", True, user_info=user_info)

        user_info = UserInfo(
            user_id="1234",
            user_name="member",
            user_displayname=None,
            user_remark=None,
            user_avatar=ImageUrl(url="http://xxx.jpg"),
            user_gender="unknown",
        )
        event = _fake_message_create_event("/user_info 1234")
        ctx.receive_event(bot, event)
        ctx.should_call_api(
            "get_member",
            {"guild_id": "5566", "user_id": "1234"},
            Member(
                user=User(id="1234", username="member", avatar="http://xxx.jpg"),
                joined_at=datetime.now(),
            ),
        )
        ctx.should_call_send(event, "", True, user_info=user_info)

        user_info = UserInfo(
            user_id="2233",
            user_name="Bot",
            user_displayname=None,
            user_remark=None,
            user_avatar=ImageUrl(url="http://xxx.jpg"),
            user_gender="unknown",
        )
        event = _fake_message_create_event("/bot_user_info")
        ctx.receive_event(bot, event)
        ctx.should_call_api(
            "me", {}, User(id="2233", username="Bot", avatar="http://xxx.jpg")
        )
        ctx.should_call_send(event, "", True, user_info=user_info)

        group_user_id = "3F21411B784D403E811E68BF3E2944D8"
        user_info = _expected_group_user_info(
            group_user_id,
            username="GroupUser",
            member_role="member",
            fields=GROUP_MEMBER_AUTHOR_FIELDS,
        )
        event = _fake_group_at_message_create_event("/user_info")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "", True, user_info=user_info)


async def test_group_message_event(app: App):
    if GroupMessageCreateEvent is None:
        return

    from nonebot_plugin_userinfo import UserInfo
    from nonebot_plugin_userinfo.image_source import QQAvatarOpenId

    async with app.test_matcher() as ctx:
        bot = ctx.create_bot(
            base=Bot, self_id="2233", bot_info=BotInfo(id="2233", token="", secret="")
        )

        group_user_id = "3F21411B784D403E811E68BF3E2944D8"
        user_info = _expected_group_user_info(
            group_user_id,
            username="GroupUser",
            member_role="member",
            fields=GROUP_MEMBER_AUTHOR_FIELDS,
        )
        event = _fake_group_message_create_event("/user_info")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "", True, user_info=user_info)

        # 查询群里的其他成员：新版 adapter 会通过 get_group_member 获取信息，
        # 旧版没有该接口时只能回退到 openid 头像。
        other_user_id = "1234"
        if (
            GroupMemberInfo is not None
            and hasattr(Bot, "get_group_member")
            and "group_openid" in GROUP_MESSAGE_EVENT_FIELDS
        ):
            member_info = _fake_group_member_info(
                other_user_id, username="OtherUser", member_role="admin"
            )
            ctx.should_call_api(
                "get_group_member",
                {
                    "group_openid": "19303D3617EF432999F24342F99AEC65",
                    "member_openid": other_user_id,
                },
                member_info,
            )
            user_info = _expected_group_user_info(
                other_user_id,
                username="OtherUser",
                member_role="admin",
                fields=GROUP_MEMBER_INFO_FIELDS,
            )
        else:
            user_info = UserInfo(
                user_id=other_user_id,
                user_name="",
                user_displayname=None,
                user_remark=None,
                user_avatar=QQAvatarOpenId(appid="2233", user_openid=other_user_id),
                user_gender="unknown",
                user_role=None,
            )

        event = _fake_group_message_create_event(f"/user_info {other_user_id}")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "", True, user_info=user_info)
