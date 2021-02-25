from typing import Union

from discordmenu.embed.components import EmbedFooter
from discordmenu.intra_message_state import IntraMessageState

from padinfo.view.components.view_state_base import ViewStateBase
from padinfo.view.components.view_state_base_id import ViewStateBaseId

TSUBAKI_FLOWER_ICON_URL = 'https://d1kpnpud0qoyxf.cloudfront.net/tsubaki/tsubakiflower.png'


def pad_info_footer():
    return EmbedFooter('Requester may click the reactions below to switch tabs')


def pad_info_footer_with_state(state: Union[ViewStateBase, ViewStateBaseId]):
    url = IntraMessageState.serialize(TSUBAKI_FLOWER_ICON_URL, state.serialize())
    return EmbedFooter(
        'Requester may click the reactions below to switch tabs',
        icon_url=url)
