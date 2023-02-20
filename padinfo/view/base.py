from abc import ABCMeta, abstractmethod

from discordmenu.embed.view import EmbedView

from padinfo.view.components.view_state_base_id import ViewStateBaseId


class BaseIdView(metaclass=ABCMeta):
    VIEW_TYPE: str
    TSUBAKI = 2141
