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


def _get_field(paragraph):
    paragraph = paragraph.strip()
    newline = paragraph.find('\n')

    if newline >= 0:
        data = paragraph.split('\n')
        evo = paragraph[:newline]
        if evo.startswith('**'):
            information = paragraph[newline:]
            return EmbedField(evo, Box(information))

    # it didn't start with a bolded line, assume it's not an evo description
    return EmbedField('**Additional Information**', Box(paragraph))


def get_title(name, timestamp, success):
    if success:
        return Text('Which {} - Last Updated {}'.format(name, timestamp))
    else:
        return Text('Which {}'.format(name))


def get_fields(definition):
    paragraphs = definition.split('\n\n')
    return [_get_field(paragraph) for paragraph in paragraphs]


class WhichView:
    VIEW_TYPE = 'Which'

    @staticmethod
    def embed(state, props: WhichViewProps):
        name = props.name
        definition = props.definition
        timestamp = props.timestamp
        success = props.success

        fields = get_fields(definition) if success else []

        return EmbedView(
            EmbedMain(
                color=state.color,
                title=get_title(name, timestamp, success),
                description=definition if not success else ''
            ),
            embed_footer=embed_footer_with_state(state),
            embed_fields=fields
        )
