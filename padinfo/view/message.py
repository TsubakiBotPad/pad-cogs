from discordmenu.embed.components import EmbedMain
from discordmenu.embed.view import EmbedView

from padinfo.view.components.base import pad_info_footer_with_state
from padinfo.view_state.message import MessageViewState


class MessageView:
    @staticmethod
    def embed(state: MessageViewState):
        return EmbedView(
            EmbedMain(
                color=state.color,
                description=state.message
            ),
            embed_footer=pad_info_footer_with_state(state),
        )
