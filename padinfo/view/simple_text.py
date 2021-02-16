from discordmenu.embed.components import EmbedMain
from discordmenu.embed.view import EmbedView

from padinfo.view.components.base import pad_info_footer_with_state
from padinfo.view_state.simple_text import SimpleTextViewState


class SimpleTextView:
    @staticmethod
    def embed(state: SimpleTextViewState):
        return EmbedView(
            EmbedMain(
                color=state.color,
                description=state.message
            ),
            embed_footer=pad_info_footer_with_state(state),
        )
