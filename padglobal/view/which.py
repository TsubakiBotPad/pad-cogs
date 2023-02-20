from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.text import Text
from discordmenu.embed.view import EmbedView
from discordmenu.emoji.emoji_cache import emoji_cache
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.view.closable_embed import ClosableEmbedViewState

STAR = '* '
BULLET_EMOJIS = ['db', 'dp', 'dg']
UNKNOWN_EDIT_TIMESTAMP = '1970-01-01'


class WhichViewProps:
    def __init__(self, name: str, definition: str, timestamp: str, success: bool):
        self.name = name
        self.definition = definition
        self.timestamp = timestamp
        self.success = success


def _get_field(paragraph, color):
    lines = paragraph.strip().splitlines()
    lines = [_replace_bullets(line.strip(), color) for line in lines]

    if len(lines) > 1:
        evo = lines[0]
        information = '\n'.join(lines[1:])
        if evo.startswith('**'):
            return EmbedField(evo, Box(information))

    # it wasn't multiple lines that started with a bolded line, assume it's not an evo description
    return EmbedField('**Additional Information**', Box(paragraph))


def _replace_bullets(line, color_index):
    if line.startswith(STAR):
        bullet = emoji_cache.get_emoji(BULLET_EMOJIS[color_index])
        return '{} {}'.format(bullet, line[len(STAR):])
    else:
        return line


def get_description(definition, timestamp, success):
    if success:
        if timestamp == UNKNOWN_EDIT_TIMESTAMP:
            return Text('No last-updated date recorded')
        else:
            return Text('Last Updated {}'.format(timestamp))
    else:
        return definition


def get_fields(definition):
    paragraphs = definition.split('\n\n')
    color = 0
    fields = []

    for paragraph in paragraphs:
        fields.append(_get_field(paragraph, color))
        color = ((color + 1) % len(BULLET_EMOJIS))

    return fields


class WhichView:
    VIEW_TYPE = 'Which'

    @staticmethod
    def embed(state: ClosableEmbedViewState, props: WhichViewProps):
        name = props.name
        definition = props.definition
        timestamp = props.timestamp
        success = props.success

        fields = get_fields(definition) if success else []

        return EmbedView(
            EmbedMain(
                color=state.qs.embedcolor,
                title='Which {}'.format(name),
                description=get_description(definition, timestamp, success)
            ),
            embed_footer=embed_footer_with_state(state, qs=state.qs),
            embed_fields=fields
        )
