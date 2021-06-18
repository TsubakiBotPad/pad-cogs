from discordmenu.embed.components import EmbedField, EmbedMain
from discordmenu.embed.text import Text
from discordmenu.embed.view import EmbedView
from tsutils import embed_footer_with_state

class ButtonInfoViewProps:
    def __init__(self, result):
        self.result = result


class ButtonInfoView:
    VIEW_TYPE = 'ButtonInfo'

    @staticmethod
    def embed(state, props: ButtonInfoViewProps):
        info_str = props.result

        fields = [
            EmbedField('Info', Text(info_str))
        ]

        return EmbedView(
            EmbedMain(
                color=state.color,
                title='Button Info'
            ),
            embed_footer=embed_footer_with_state(state),
            embed_fields=fields
        )
