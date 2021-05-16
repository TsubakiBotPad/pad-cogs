from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.text import Text
from discordmenu.embed.view import EmbedView
from tsutils import embed_footer_with_state


class WhichViewProps:
    def __init__(self, name: str, definition: str, timestamp: str, success: bool):
        self.name = name
        self.definition = definition
        self.timestamp = timestamp
        self.success = success


def get_title(name, timestamp, success):
    if success:
        return Text('Which {} - Last Updated {}'.format(name, timestamp))
    else:
        return Text('Which {}'.format(name))


class WhichView:
    VIEW_TYPE = 'Which'

    @staticmethod
    def embed(state, props: WhichViewProps):
        name = props.name
        definition = props.definition
        timestamp = props.timestamp
        success = props.success

        fields = [

        ]

        return EmbedView(
            EmbedMain(
                color=state.color,
                title=get_title(name, timestamp, success)
            ),
            embed_footer=embed_footer_with_state(state),
            embed_fields=fields
        )
