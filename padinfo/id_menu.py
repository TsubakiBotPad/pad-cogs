from typing import TYPE_CHECKING, Optional, List

from discord import Message
from discordmenu.embed.emoji import EmbedMenuEmojiConfig
from discordmenu.embed.menu import EmbedMenu, EmbedControl
from discordmenu.emoji.emoji_cache import emoji_cache
from discordmenu.reaction_filter import ValidEmojiReactionFilter, NotPosterEmojiReactionFilter, \
    MessageOwnerReactionFilter, FriendReactionFilter, BotAuthoredMessageReactionFilter
from tsutils import char_to_emoji

from padinfo.pane_names import IdMenuPaneNames
from padinfo.view.evos import EvosView
from padinfo.view.id import IdView
from padinfo.view.materials import MaterialsView
from padinfo.view.otherinfo import OtherInfoView
from padinfo.view.pantheon import PantheonView
from padinfo.view.pic import PicView
from padinfo.view_state.evos import EvosViewState
from padinfo.view_state.id import IdViewState
from padinfo.view_state.materials import MaterialsViewState
from padinfo.view_state.otherinfo import OtherInfoViewState
from padinfo.view_state.pantheon import PantheonViewState
from padinfo.view_state.pic import PicViewState

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel
    from dadguide.database_context import DbContext

menu_emoji_config = EmbedMenuEmojiConfig(delete_message='\N{CROSS MARK}')


class IdMenu:
    MENU_TYPE = 'IdMenu'

    @staticmethod
    def menu(original_author_id, friend_ids, bot_id, initial_control=None):
        if initial_control is None:
            initial_control = IdMenu.id_control

        valid_emoji_names = [e.name for e in emoji_cache.custom_emojis] + list(IdMenuPanes.emoji_names())
        reaction_filters = [
            ValidEmojiReactionFilter(valid_emoji_names),
            NotPosterEmojiReactionFilter(),
            BotAuthoredMessageReactionFilter(bot_id),
            MessageOwnerReactionFilter(original_author_id, FriendReactionFilter(original_author_id, friend_ids))
        ]
        embed = EmbedMenu(reaction_filters, IdMenuPanes.transitions(), initial_control, menu_emoji_config)
        return embed

    @staticmethod
    async def respond_with_left(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        db_context: "DbContext" = dgcog.database
        m = db_context.graph.get_monster(int(ims['resolved_monster_id']))

        use_evo_scroll = ims.get('use_evo_scroll') != 'False'
        new_monster_id = IdMenu.get_prev_monster_id(db_context, m, use_evo_scroll)
        if new_monster_id is None:
            ims['unsupported_transition'] = True
        ims['resolved_monster_id'] = str(new_monster_id) if new_monster_id else None
        pane_type = ims['pane_type']
        pane_type_to_func_map = IdMenuPanes.pane_types()
        response_func = pane_type_to_func_map[pane_type]
        return await response_func(message, ims, **data)

    @staticmethod
    def get_prev_monster_id(db_context: "DbContext", monster: "MonsterModel", use_evo_scroll):
        if use_evo_scroll:
            evos = sorted({*db_context.graph.get_alt_ids_by_id(monster.monster_id)})
            index = evos.index(monster.monster_id)
            new_id = evos[index - 1]
            return new_id
        else:
            prev_monster = db_context.graph.numeric_prev_monster(monster)
            return prev_monster.monster_id if prev_monster else None

    @staticmethod
    async def respond_with_right(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        db_context: "DbContext" = dgcog.database
        m = db_context.graph.get_monster(int(ims['resolved_monster_id']))

        use_evo_scroll = ims.get('use_evo_scroll') != 'False'
        new_monster_id = str(IdMenu.get_next_monster_id(db_context, m, use_evo_scroll))
        if new_monster_id is None:
            ims['unsupported_transition'] = True
        ims['resolved_monster_id'] = str(new_monster_id) if new_monster_id else None
        pane_type = ims.get('pane_type')
        pane_type_to_func_map = IdMenuPanes.pane_types()
        response_func = pane_type_to_func_map[pane_type]
        return await response_func(message, ims, **data)

    @staticmethod
    def get_next_monster_id(db_context: "DbContext", monster: "MonsterModel", use_evo_scroll):
        if use_evo_scroll:
            evos = sorted({*db_context.graph.get_alt_ids_by_id(monster.monster_id)})
            index = evos.index(monster.monster_id)
            if index == len(evos) - 1:
                # cycle back to the beginning of the evos list
                new_id = evos[0]
            else:
                new_id = evos[index + 1]
            return new_id
        else:
            next_monster = db_context.graph.numeric_next_monster(monster)
            return next_monster.monster_id if next_monster else None

    @staticmethod
    async def respond_with_current_id(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        control = IdMenu.id_control(view_state)
        return control

    @staticmethod
    async def respond_with_evos(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        view_state = await EvosViewState.deserialize(dgcog, user_config, ims)
        control = IdMenu.evos_control(view_state)
        return control

    @staticmethod
    async def respond_with_mats(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        view_state = await MaterialsViewState.deserialize(dgcog, user_config, ims)
        control = IdMenu.mats_control(view_state)
        return control

    @staticmethod
    async def respond_with_picture(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        view_state = await PicViewState.deserialize(dgcog, user_config, ims)
        control = IdMenu.pic_control(view_state)
        return control

    @staticmethod
    async def respond_with_pantheon(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        view_state = await PantheonViewState.deserialize(dgcog, user_config, ims)
        control = IdMenu.pantheon_control(view_state)
        return control

    @staticmethod
    async def respond_with_otherinfo(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        view_state = await OtherInfoViewState.deserialize(dgcog, user_config, ims)
        control = IdMenu.otherinfo_control(view_state)
        return control

    @staticmethod
    def id_control(state: IdViewState):
        if state is None:
            return None
        reaction_list = state.reaction_list
        return EmbedControl(
            [IdView.embed(state)],
            reaction_list or [emoji_cache.get_by_name(e) for e in IdMenuPanes.emoji_names()]
        )

    @staticmethod
    def evos_control(state: Optional[EvosViewState]):
        if state is None:
            return None
        reaction_list = state.reaction_list
        return EmbedControl(
            [EvosView.embed(state)],
            reaction_list or [emoji_cache.get_by_name(e) for e in IdMenuPanes.emoji_names()]
        )

    @staticmethod
    def mats_control(state: Optional[MaterialsViewState]):
        if state is None:
            return None
        reaction_list = state.reaction_list
        return EmbedControl(
            [MaterialsView.embed(state)],
            reaction_list or [emoji_cache.get_by_name(e) for e in IdMenuPanes.emoji_names()]
        )

    @staticmethod
    def pic_control(state: PicViewState):
        if state is None:
            return None
        reaction_list = state.reaction_list
        return EmbedControl(
            [PicView.embed(state)],
            reaction_list or [emoji_cache.get_by_name(e) for e in IdMenuPanes.emoji_names()]
        )

    @staticmethod
    def pantheon_control(state: Optional[PantheonViewState]):
        if state is None:
            return None
        reaction_list = state.reaction_list
        return EmbedControl(
            [PantheonView.embed(state)],
            reaction_list or [emoji_cache.get_by_name(e) for e in IdMenuPanes.emoji_names()]
        )

    @staticmethod
    def otherinfo_control(state: OtherInfoViewState):
        if state is None:
            return None
        reaction_list = state.reaction_list
        return EmbedControl(
            [OtherInfoView.embed(state)],
            reaction_list or [emoji_cache.get_by_name(e) for e in IdMenuPanes.emoji_names()]
        )


class IdMenuPanes:
    INITIAL_EMOJI = '\N{HOUSE BUILDING}'
    DATA = {
        IdMenu.respond_with_left: ('\N{BLACK LEFT-POINTING TRIANGLE}', None),
        IdMenu.respond_with_right: ('\N{BLACK RIGHT-POINTING TRIANGLE}', None),
        IdMenu.respond_with_current_id: ('\N{HOUSE BUILDING}', IdMenuPaneNames.id),
        IdMenu.respond_with_evos: (char_to_emoji('e'), IdMenuPaneNames.evos),
        IdMenu.respond_with_mats: ('\N{MEAT ON BONE}', IdMenuPaneNames.materials),
        IdMenu.respond_with_picture: ('\N{FRAME WITH PICTURE}', IdMenuPaneNames.pic),
        IdMenu.respond_with_pantheon: ('\N{CLASSICAL BUILDING}', IdMenuPaneNames.pantheon),
        IdMenu.respond_with_otherinfo: ('\N{SCROLL}', IdMenuPaneNames.otherinfo),
    }

    @classmethod
    def emoji_names(cls):
        return [v[0] for k, v in cls.DATA.items()]

    @classmethod
    def transitions(cls):
        return {v[0]: k for k, v in cls.DATA.items()}

    @classmethod
    def pane_types(cls):
        return {v[1]: k for k, v in cls.DATA.items() if v[1]}
