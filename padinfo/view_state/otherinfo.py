from padinfo.pane_names import IdMenuPaneNames
from padinfo.view_state.base_id import ViewStateBaseId


class OtherInfoViewState(ViewStateBaseId):
    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': IdMenuPaneNames.otherinfo,
        })
        return ret
