from tsutils.menu.view.closable_embed import ClosableEmbedViewState
from tsutils.menu.components.footers import embed_footer_with_state
from discordmenu.embed.view import EmbedView
from discordmenu.embed.components import EmbedMain
from discord import Color


class PADleMonsterConfirmationViewProps:
    def __init__(self, title: str):
        self.title = title


class PADleMonsterConfirmationView:
    VIEW_TYPE = 'PADleConfirmation'

    @classmethod
    def embed(cls, state: ClosableEmbedViewState, props: PADleMonsterConfirmationViewProps):
        return EmbedView(
            EmbedMain(
                color=Color.red(),
                title=props.title,
            ),
            embed_footer=embed_footer_with_state(state, text="Click the X to close.")
        )
