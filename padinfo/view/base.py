from padinfo.view.components.view_state_base_id import ViewStateBaseId

class BaseIdView:
    VIEW_TYPE = 'Base'
    TSUBAKI = 2141

    @classmethod
    def embed(cls, state: ViewStateBaseId):
        raise NotImplementedError()
