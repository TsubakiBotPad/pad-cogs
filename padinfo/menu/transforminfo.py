from typing import Optional

from discord import Message
from discordmenu.embed.menu import EmbedMenu, EmbedControl
from tsutils import char_to_emoji

from tsutils.menu.panes import MenuPanes, emoji_buttons
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

        # base is always first
        ims['query'] = str(ims['resolved_monster_ids'][0])
        ims['resolved_monster_id'] = None
        id_view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        reaction_list = ims['reaction_list']
        id_control = TransformInfoMenu.id_control(id_view_state, reaction_list)
        return id_control

    @staticmethod
    async def respond_with_transform(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        # transform is always second
        ims['query'] = str(ims['resolved_monster_ids'][1])
        ims['resolved_monster_id'] = None
        id_view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        reaction_list = ims['reaction_list']
        id_control = TransformInfoMenu.id_control(id_view_state, reaction_list)
        return id_control

    @staticmethod
    async def respond_with_n(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']
        n = TransformInfoMenuPanes.get_n_from_reaction(data['reaction'])
        # does this work? is this check necessary? is reaction guaranteed to resolve?
        if n is None:
            return None

        ims['query'] = str(ims['resolved_monster_ids'][n])
        ims['resolved_monster_id'] = None
        id_view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        reaction_list = ims['reaction_list']
        id_control = TransformInfoMenu.id_control(id_view_state, reaction_list)
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
        reaction_list = state.reaction_list
        return EmbedControl(
            [TransformInfoView.embed(state)],
            reaction_list
        )

    @staticmethod
    def id_control(state: IdViewState, reaction_list):
        return EmbedControl(
            [IdView.embed(state)],
            reaction_list
        )


class TransformInfoEmoji:
    home = emoji_buttons['home']
    down = '\N{DOWN-POINTING RED TRIANGLE}'
    up = '\N{UP-POINTING RED TRIANGLE}'
    one = char_to_emoji('1')
    two = char_to_emoji('2')
    three = char_to_emoji('3')
    four = char_to_emoji('4')
    five = char_to_emoji('5')
    six = char_to_emoji('6')
    seven = char_to_emoji('7')
    eight = char_to_emoji('8')
    nine = char_to_emoji('9')
    ten = char_to_emoji('10')


class TransformInfoMenuPanes(MenuPanes):
    DATA = {
        TransformInfoEmoji.home: (TransformInfoMenu.respond_with_overview,
                                  TransformInfoView.VIEW_TYPE),
        TransformInfoEmoji.down: (TransformInfoMenu.respond_with_base, IdView.VIEW_TYPE),
        TransformInfoEmoji.up: (TransformInfoMenu.respond_with_transform, IdView.VIEW_TYPE),
        TransformInfoEmoji.one: (TransformInfoMenu.respond_with_n, IdView.VIEW_TYPE),
        TransformInfoEmoji.two: (TransformInfoMenu.respond_with_n, IdView.VIEW_TYPE),
        TransformInfoEmoji.three: (TransformInfoMenu.respond_with_n, IdView.VIEW_TYPE),
        TransformInfoEmoji.four: (TransformInfoMenu.respond_with_n, IdView.VIEW_TYPE),
        TransformInfoEmoji.five: (TransformInfoMenu.respond_with_n, IdView.VIEW_TYPE),
        TransformInfoEmoji.six: (TransformInfoMenu.respond_with_n, IdView.VIEW_TYPE),
        TransformInfoEmoji.seven: (TransformInfoMenu.respond_with_n, IdView.VIEW_TYPE),
        TransformInfoEmoji.eight: (TransformInfoMenu.respond_with_n, IdView.VIEW_TYPE),
        TransformInfoEmoji.nine: (TransformInfoMenu.respond_with_n, IdView.VIEW_TYPE),
        TransformInfoEmoji.ten: (TransformInfoMenu.respond_with_n, IdView.VIEW_TYPE),
    }

    @classmethod
    def get_reaction_list(cls, number_of_monsters: int):
        if number_of_monsters > 2:
            cls.HIDDEN_EMOJIS = TransformInfoEmoji.up
        else:
            cls.HIDDEN_EMOJIS = TransformInfoEmoji.one

        # add 1 for the home emoji
        return cls.emoji_names()[:number_of_monsters + 1]

    @classmethod
    def get_n_from_reaction(cls, reaction):
        # offset by 1 because of the home emoji
        return cls.emoji_names().index(reaction) - 1 if reaction in cls.emoji_names() else None
