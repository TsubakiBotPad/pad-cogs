from abc import abstractmethod
from typing import Optional

from discord import Message
from tsutils.menu.panes import MenuPanes

from padinfo.view.components.evo_scroll_mixin import EvoScrollViewState


class EvoScrollMenu:
    VIEW_STATE_TYPE: EvoScrollViewState

    @staticmethod
    @abstractmethod
    def get_panes_type() -> MenuPanes:
        ...

    @classmethod
    async def respond_with_left(cls, message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        user_config = data['user_config']
        # Figure out the new monster before doing all of the queries necessary for
        # The specific pane type. For now just deserialize as the base Id ViewState.
        view_state = await cls.VIEW_STATE_TYPE.deserialize(dbcog, user_config, ims)
        view_state.decrement_monster(dbcog, ims)

        response_func = cls._get_response_func(ims)
        return await response_func(message, ims, **data)

    @classmethod
    async def respond_with_right(cls, message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        user_config = data['user_config']
        view_state = await cls.VIEW_STATE_TYPE.deserialize(dbcog, user_config, ims)
        view_state.increment_monster(dbcog, ims)

        response_func = cls._get_response_func(ims)
        return await response_func(message, ims, **data)

    @classmethod
    def _get_response_func(cls, ims):
        panes = cls.get_panes_type()

        pane_type = ims.get('pane_type')
        if pane_type is not None:
            pane_type_to_func_map = panes.pane_types()
            return pane_type_to_func_map[pane_type]

        home = panes.INITIAL_EMOJI
        return panes.transitions()[home]
