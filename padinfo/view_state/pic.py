from padinfo.pane_names import IdMenuPaneNames
from padinfo.view_state.base_id import ViewStateBaseId


class PicViewState(ViewStateBaseId):

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': IdMenuPaneNames.pic,
        })
        return ret
