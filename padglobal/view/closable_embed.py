from discordmenu.embed.view_state import ViewState


class ClosableEmbedViewState(ViewState):
    def __init__(self, original_author_id, menu_type, raw_query, color, view_type, props):
        super().__init__(original_author_id, menu_type, raw_query)
        self.color = color
        self.view_type = view_type
        self.props = props

    def serialize(self):
        return super().serialize()
