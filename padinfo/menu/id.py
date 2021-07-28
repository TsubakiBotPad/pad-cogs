from typing import Optional

from discord import Message
from discordmenu.embed.menu import EmbedMenu, EmbedControl
from tsutils import char_to_emoji
from tsutils.enums import ChildMenuType
from tsutils.menu.panes import MenuPanes

from padinfo.menu.simple_text import SimpleTextMenu
from padinfo.view.components.view_state_base_id import ViewStateBaseId
from padinfo.view.evos import EvosView, EvosViewState
from padinfo.view.id import IdView, IdViewState
from padinfo.view.materials import MaterialsView, MaterialsViewState
from padinfo.view.otherinfo import OtherInfoView, OtherInfoViewState
from padinfo.view.pantheon import PantheonView, PantheonViewState
from padinfo.view.pic import PicView, PicViewState


class IdMenu:
    MENU_TYPE = ChildMenuType.IdMenu.name

    @staticmethod
    def menu(initial_control=None):
        if initial_control is None:
            initial_control = IdMenu.id_control

        embed = EmbedMenu(IdMenuPanes.transitions(), initial_control,
                          delete_func=IdMenu.respond_with_delete)
        return embed

    @staticmethod
    async def respond_with_left(message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        user_config = data['user_config']
        # Figure out the new monster before doing all of the queries necessary for
        # The specific pane type. For now just deserialize as the base Id ViewState.
        view_state = await ViewStateBaseId.deserialize(dbcog, user_config, ims)
        view_state.decrement_monster(dbcog, ims)

        pane_type = ims['pane_type']
        pane_type_to_func_map = IdMenuPanes.pane_types()
        response_func = pane_type_to_func_map[pane_type]
        return await response_func(message, ims, **data)

    @staticmethod
    async def respond_with_right(message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        user_config = data['user_config']
        view_state = await ViewStateBaseId.deserialize(dbcog, user_config, ims)
        view_state.increment_monster(dbcog, ims)

        pane_type = ims.get('pane_type')
        pane_type_to_func_map = IdMenuPanes.pane_types()
        response_func = pane_type_to_func_map[pane_type]
        return await response_func(message, ims, **data)

    @staticmethod
    async def respond_with_refresh(message: Optional[Message], ims, **data):
        # This is used by disambig screen & other multi-message embeds, where we need to deserialize & then
        # re-serialize the ims, with the same information in place
        pane_type = ims.get('pane_type') or IdView.VIEW_TYPE
        pane_type_to_func_map = IdMenuPanes.pane_types()
        response_func = pane_type_to_func_map[pane_type]
        return await response_func(message, ims, **data)

    @staticmethod
    async def respond_with_delete(message: Optional[Message], ims, **data):
        if not ims.get('is_child'):
            return await message.delete()
        if ims.get('idle_message'):
            ims['menu_type'] = SimpleTextMenu.MENU_TYPE
            ims['message'] = ims['idle_message']
            return await SimpleTextMenu.respond_with_message(message, ims, **data)
        return await message.edit(embed=None)

    @staticmethod
    async def respond_with_current_id(message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        user_config = data['user_config']

        view_state = await IdViewState.deserialize(dbcog, user_config, ims)
        control = IdMenu.id_control(view_state)
        return control

    @staticmethod
    async def respond_with_evos(message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        user_config = data['user_config']

        view_state = await EvosViewState.deserialize(dbcog, user_config, ims)
        control = IdMenu.evos_control(view_state)
        return control

    @staticmethod
    async def respond_with_mats(message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        user_config = data['user_config']

        view_state = await MaterialsViewState.deserialize(dbcog, user_config, ims)
        control = IdMenu.mats_control(view_state)
        return control

    @staticmethod
    async def respond_with_picture(message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        user_config = data['user_config']

        view_state = await PicViewState.deserialize(dbcog, user_config, ims)
        control = IdMenu.pic_control(view_state)
        return control

    @staticmethod
    async def respond_with_pantheon(message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        user_config = data['user_config']

        view_state = await PantheonViewState.deserialize(dbcog, user_config, ims)
        control = IdMenu.pantheon_control(view_state)
        return control

    @staticmethod
    async def respond_with_otherinfo(message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        user_config = data['user_config']

        view_state = await OtherInfoViewState.deserialize(dbcog, user_config, ims)
        control = IdMenu.otherinfo_control(view_state)
        return control

    @staticmethod
    def id_control(state: IdViewState):
        if state is None:
            return None
        return EmbedControl(
            [IdView.embed(state)],
            state.reaction_list or IdMenuPanes.emoji_names()
        )

    @staticmethod
    def evos_control(state: Optional[EvosViewState]):
        if state is None:
            return None
        return EmbedControl(
            [EvosView.embed(state)],
            state.reaction_list or IdMenuPanes.emoji_names()
        )

    @staticmethod
    def mats_control(state: Optional[MaterialsViewState]):
        if state is None:
            return None
        return EmbedControl(
            [MaterialsView.embed(state)],
            state.reaction_list or IdMenuPanes.emoji_names()
        )

    @staticmethod
    def pic_control(state: PicViewState):
        if state is None:
            return None
        return EmbedControl(
            [PicView.embed(state)],
            state.reaction_list or IdMenuPanes.emoji_names()
        )

    @staticmethod
    def pantheon_control(state: Optional[PantheonViewState]):
        if state is None:
            return None
        return EmbedControl(
            [PantheonView.embed(state)],
            state.reaction_list or IdMenuPanes.emoji_names()
        )

    @staticmethod
    def otherinfo_control(state: OtherInfoViewState):
        if state is None:
            return None
        return EmbedControl(
            [OtherInfoView.embed(state)],
            state.reaction_list or IdMenuPanes.emoji_names()
        )


class IdMenuEmoji:
    left = '\N{BLACK LEFT-POINTING TRIANGLE}'
    right = '\N{BLACK RIGHT-POINTING TRIANGLE}'
    home = '\N{HOUSE BUILDING}'
    evos = char_to_emoji('E')
    mats = '\N{MEAT ON BONE}'
    pic = '\N{FRAME WITH PICTURE}'
    pantheon = '\N{CLASSICAL BUILDING}'
    otherinfo = '\N{SCROLL}'
    refresh = "\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}"
    delete = '\N{CROSS MARK}'


class IdMenuPanes(MenuPanes):
    DATA = {
        IdMenuEmoji.left: (IdMenu.respond_with_left, None),
        IdMenuEmoji.right: (IdMenu.respond_with_right, None),
        IdMenuEmoji.home: (IdMenu.respond_with_current_id, IdView.VIEW_TYPE),
        IdMenuEmoji.evos: (IdMenu.respond_with_evos, EvosView.VIEW_TYPE),
        IdMenuEmoji.mats: (IdMenu.respond_with_mats, MaterialsView.VIEW_TYPE),
        IdMenuEmoji.pic: (IdMenu.respond_with_picture, PicView.VIEW_TYPE),
        IdMenuEmoji.pantheon: (IdMenu.respond_with_pantheon, PantheonView.VIEW_TYPE),
        IdMenuEmoji.otherinfo: (IdMenu.respond_with_otherinfo, OtherInfoView.VIEW_TYPE),
        IdMenuEmoji.refresh: (IdMenu.respond_with_refresh, None),
        IdMenuEmoji.delete: (IdMenu.respond_with_delete, None),
    }
    HIDDEN_EMOJIS = [
        IdMenuEmoji.refresh,
        IdMenuEmoji.delete,
    ]
