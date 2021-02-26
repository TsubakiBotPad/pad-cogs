from typing import Optional

from discord import Message
from discordmenu.embed.menu import EmbedMenu, EmbedControl
from discordmenu.emoji.emoji_cache import emoji_cache

from padinfo.menu.common import MenuPanes, emoji_buttons
from padinfo.view.id import IdView, IdViewState
from padinfo.view.transforminfo import TransformInfoView, TransformInfoViewState


class TransformInfoMenu:
    MENU_TYPE = 'TransformInfo'

    @staticmethod
    def menu():
        return EmbedMenu(TransformInfoMenuPanes.transitions(), TransformInfoMenu.tf_control)

    @staticmethod
    async def respond_with_base(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        ims['query'] = str(ims['b_resolved_monster_id'])
        ims['resolved_monster_id'] = None
        id_view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        id_control = TransformInfoMenu.id_control(id_view_state)
        return id_control

    @staticmethod
    async def respond_with_transform(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        ims['query'] = str(ims['t_resolved_monster_id'])
        ims['resolved_monster_id'] = None
        id_view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        id_control = TransformInfoMenu.id_control(id_view_state)
        return id_control

    @staticmethod
    async def respond_with_overview(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']
        tf_view_state = await TransformInfoViewState.deserialize(dgcog, user_config, ims)
        tf_control = TransformInfoMenu.tf_control(tf_view_state)
        return tf_control

    @staticmethod
    def tf_control(state: TransformInfoViewState):
        return EmbedControl(
            [TransformInfoView.embed(state)],
            [emoji_cache.get_by_name(e) for e in TransformInfoMenuPanes.emoji_names()]
        )

    @staticmethod
    def id_control(state: IdViewState):
        return EmbedControl(
            [IdView.embed(state)],
            [emoji_cache.get_by_name(e) for e in TransformInfoMenuPanes.emoji_names()]
        )


class TransformInfoEmoji:
    home = emoji_buttons['home']
    down = '\N{DOWN-POINTING RED TRIANGLE}'
    up = '\N{UP-POINTING RED TRIANGLE}'


class TransformInfoMenuPanes(MenuPanes):
    DATA = {
        TransformInfoEmoji.home: (TransformInfoMenu.respond_with_overview, TransformInfoView.VIEW_TYPE),
        TransformInfoEmoji.down: (TransformInfoMenu.respond_with_base, IdView.VIEW_TYPE),
        TransformInfoEmoji.up: (TransformInfoMenu.respond_with_transform, IdView.VIEW_TYPE),
    }
