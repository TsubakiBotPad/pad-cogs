from padinfo.common.config import UserConfig
from padinfo.pane_names import IdMenuPaneNames
from padinfo.view_state.base_id import ViewStateBaseId
from padinfo.view_state.common import get_reaction_list_from_ims, get_monster_from_ims


class OtherInfoViewState(ViewStateBaseId):
    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': IdMenuPaneNames.otherinfo,
        })
        return ret
