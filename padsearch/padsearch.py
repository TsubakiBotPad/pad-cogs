import logging
import re
from fnmatch import fnmatch
from io import BytesIO

from ply import lex
from redbot.core import commands
from redbot.core.utils.chat_formatting import box, pagify
from tsutils import timeout_after

logger = logging.getLogger('red.padbot-cogs.padsearch')

HELP_MSG = """
{0.prefix}search <specification string>

To get more than 10 results, include the word 'all' in your search.

Colors can be any of:
  fire water wood light dark null
Additionally, orb colors can be any of:
  heart jammer poison mortal and bomb

Options which take multiple colors should be comma-separated.

Single instance filters
* hp(n)       : Max HP >= n
* atk(n)      : Max ATK >= n
* rcv(n)      : Max RCV >= n
* weighted(n) : Weighted stat >= n
* cd(n)       : Min cd <= n
* farmable    : Obtainable outside REM
* haste(n)    : Skill cds reduced by n
* inheritable : Can be inherited
* shuffle     : Board shuffle (aka refresh)
* unlock      : Orb unlock
* delay(n)    : Delay enemies by n
* attabsorb   : Attribute Absorb shield null
* absorbnull  : Damage Abasorb shield null
* combo(n)    : Increase combo count by n
* shield(n)   uce damage taken by n%
* resolve     : Leader skill where you survive when HP reduced to 0

Multiple instance filters
* active(str)     : Active skill name/description
* board(colors,)  : Board change to a comma-sep list of colors
* color(color)    : Primary monster color
* column(color)   : Creates a column of a color
* hascolor(color) : Primary or secondary monster color
* leader(str)     : Leader skill description
* name(str)       : Monster name
* row(color)      : Creates a row of a color
* type(str)       : Monster type
* convert(c1, c2) : Convert from color 1 to color 2, accepts any as entry as well
"""


@timeout_after(1)
def filt_timeout(filts, ms):
    for f in filts:
        ms = [m for m in ms if f(m)]
    return ms


COLORS = [
    'fire',
    'water',
    'wood',
    'light',
    'dark',
    'nil',
]

TYPES = [
    "attacker",
    "awoken",
    "balanced",
    "devil",
    "dragon",
    "enhance",
    "evolve",
    "god",
    "healer",
    "machine",
    "physical",
    "protected",
    "vendor",
]

ORB_TYPES = [
    'any',
    'fire',
    'water',
    'wood',
    'light',
    'dark',
    'heal',
    'jammer',
    'poison',
    'mortal',
]


def assert_color(value):
    value = replace_named_color(value)
    if value not in COLORS:
        raise commands.UserFeedbackCheckFailure(
            'Unexpected color {}, expected one of {}'.format(value, COLORS))
    return value


def assert_orbcolor(value):
    value = replace_named_color(value)
    if value not in ORB_TYPES:
        raise commands.UserFeedbackCheckFailure(
            'Unexpected orb {}, expected one of {}'.format(value, ORB_TYPES))
    return value


def assert_orbcolors(values):
    return [assert_orbcolor(c) for c in values]


def split_csv_orbcolors(value):
    parts = [p.strip() for p in value.split(',')]
    return assert_orbcolors(parts)


COLOR_REPLACEMENTS = {
    'red': 'fire',
    'r': 'fire',
    'blue': 'water',
    'b': 'water',
    'green': 'wood',
    'g': 'wood',
    'l': 'light',
    'd': 'dark',
    'x': 'nil',
    'null': 'nil',
    'heart': 'heal',
    'h': 'heal',
    'p': 'poison',
    'mortal': 'mortalpoison',
    'j': 'jammer',
    'o': 'bomb',
}


def replace_named_color(color: str):
    color = color.lower().strip()
    return COLOR_REPLACEMENTS.get(color, color)


def replace_colors_in_text(text: str):
    text = text.replace('red', 'fire')
    text = text.replace('blue', 'water')
    text = text.replace('green', 'wood')
    text = text.replace('heart', 'heal')
    return text


def clean_name(txt, name):
    return txt.replace(name, '').strip('() ')


def re_clean_name(txt, name):
    return clean_name(txt, name)[2:-1]


def board_filter(colors):
    def fn(m, colors=colors):
        # Copy for safety
        colors = list(colors)
        m_colors = list(m.search.board_change)

        if len(m_colors) != len(colors):
            return False

        any_values = 0
        for c in colors:
            if c == 'any':
                any_values += 1
            else:
                if c in m_colors:
                    m_colors.remove(c)
                else:
                    return False

        # Check remaining anys
        return any_values == len(m_colors)

    return fn


class PadSearchLexer(object):
    tokens = [
        'ACTIVE',
        'ALL',
        'BOARD',
        'CD',
        'COLOR',
        'COLUMN',
        'FARMABLE',
        'HASCOLOR',
        'HASTE',
        'INHERITABLE',
        'LEADER',
        'NAME',
        'ROW',
        'TYPE',
        'SHUFFLE',
        'UNLOCK',
        'RESOLVE',
        'DELAY',
        'REMOVE',
        'CONVERT',
        'COMBO',
        'ABSORBNULL',
        'ATTABSORB',
        'SHIELD',
        'HP',
        'ATK',
        'RCV',
        'WEIGHTED',
        'REACTIVE',
        'RELEADER',
    ]

    def t_ACTIVE(self, t):
        r'\bactive\(.+?\)'
        t.value = clean_name(t.value, 'active')
        t.value = replace_colors_in_text(t.value)
        return t

    def t_REACTIVE(self, t):
        r"reactive\(r'.+?'\)"
        t.value = re_clean_name(t.value, 'reactive')
        t.value = replace_colors_in_text(t.value)
        return t

    def t_ALL(self, t):
        r'all(\(\))?'
        return t

    def t_BOARD(self, t):
        r'board\([a-zA-z, ]+\)'
        t.value = clean_name(t.value, 'board')
        t.value = replace_colors_in_text(t.value)
        return t

    def t_CD(self, t):
        r'cd\(\d+\)'
        t.value = clean_name(t.value, 'cd')
        t.value = int(t.value)
        return t

    def t_COLOR(self, t):
        r'color\([a-zA-z]+\)'
        t.value = clean_name(t.value, 'color')
        t.value = replace_colors_in_text(t.value)
        return t

    def t_COLUMN(self, t):
        r'column\([a-zA-z]+\)'
        t.value = clean_name(t.value, 'column')
        t.value = replace_colors_in_text(t.value)
        return t

    def t_FARMABLE(self, t):
        r'farmable(\(\))?'
        return t

    def t_HASCOLOR(self, t):
        r'hascolor\([a-zA-z]+\)'
        t.value = clean_name(t.value, 'hascolor')
        t.value = replace_colors_in_text(t.value)
        return t

    def t_HASTE(self, t):
        r'haste\(\d+\)'
        t.value = clean_name(t.value, 'haste')
        t.value = int(t.value)
        return t

    def t_INHERITABLE(self, t):
        r'inheritable(\(\))?'
        return t

    def t_LEADER(self, t):
        r'\bleader\(.+?\)'
        t.value = clean_name(t.value, 'leader')
        t.value = replace_colors_in_text(t.value)
        return t

    def t_RELEADER(self, t):
        r"releader\(r'.+?'\)"
        t.value = re_clean_name(t.value, 'releader')
        t.value = replace_colors_in_text(t.value)
        return t

    def t_NAME(self, t):
        r'name\([a-zA-Z0-9 ]+\)'
        t.value = clean_name(t.value, 'name')
        return t

    def t_ROW(self, t):
        r'row\([a-zA-Z]+\)'
        t.value = clean_name(t.value, 'row')
        t.value = replace_colors_in_text(t.value)
        return t

    def t_SHUFFLE(self, t):
        r'shuffle(\(\))?'
        return t

    def t_TYPE(self, t):
        r'type\([a-zA-z]+\)'
        t.value = clean_name(t.value, 'type')
        return t

    def t_UNLOCK(self, t):
        r'unlock(\(\))?'
        return t

    def t_RESOLVE(self, t):
        r'resolve(\(\))?'
        return t

    def t_DELAY(self, t):
        r'delay\(\d+\)'
        t.value = clean_name(t.value, 'delay')
        t.value = int(t.value)
        return t

    def t_REMOVE(self, t):
        r'remove\([a-zA-Z0-9 ]+\)'
        t.value = t.value.replace('remove', '').strip('()')
        return t

    def t_CONVERT(self, t):
        r'convert\([a-zA-z, ]+\)'
        t.value = clean_name(t.value, 'convert')
        i = t.value.split(',')
        i[0] = replace_named_color(i[0]).lower()
        i[1] = replace_named_color(i[1]).lower()
        t.value = i
        return t

    def t_COMBO(self, t):
        r'combo\(\d+\)'
        t.value = clean_name(t.value, 'combo')
        t.value = int(t.value)
        return t

    def t_ABSORBNULL(self, t):
        r'absorbnull(\(\))?'
        return t

    def t_ATTABSORB(self, t):
        r'attabsorb(\(\))?'
        return t

    def t_SHIELD(self, t):
        r'shield\(\d+[\d%]\)'
        t.value = clean_name(t.value, 'shield')
        t.value = t.value.strip('%')
        t.value = int(t.value)
        return t

    def t_ATK(self, t):
        r'atk\(\d+\)'
        t.value = clean_name(t.value, 'atk')
        t.value = int(t.value)
        return t

    def t_HP(self, t):
        r'hp\(\d+\)'
        t.value = clean_name(t.value, 'hp')
        t.value = int(t.value)
        return t

    def t_RCV(self, t):
        r'rcv\(\d+\)'
        t.value = clean_name(t.value, 'rcv')
        t.value = int(t.value)
        return t

    def t_WEIGHTED(self, t):
        r'weighted\(\d+\)'
        t.value = clean_name(t.value, 'weighted')
        t.value = int(t.value)
        return t

    t_ignore = ' \t\n'

    def t_error(self, t):
        raise commands.UserFeedbackCheckFailure("Unknown text '%s'" % (t.value,))

    def build(self, **kwargs):
        # pass debug=1 to enable verbose output
        self.lexer = lex.lex(module=self)
        return self.lexer


class SearchConfig(object):

    def __init__(self, lexer, db_context: "DbContext"):
        self.all = False
        self.cd = None
        self.farmable = None
        self.haste = None
        self.inheritable = None
        self.shuffle = None
        self.unlock = None
        self.resolve = None
        self.delay = None
        self.combo = None
        self.absorbnull = None
        self.attabsorb = None
        self.shield = None
        self.hp = None
        self.atk = None
        self.rcv = None
        self.weighted = None

        self.active = []
        self.reactive = []
        self.board = []
        self.column = []
        self.color = []
        self.hascolor = []
        self.leader = []
        self.releader = []
        self.name = []
        self.row = []
        self.types = []
        self.remove = []
        self.convert = []
        for tok in iter(lexer.token, None):
            type = tok.type
            value = tok.value
            self.all |= type == 'ALL'
            self.cd = self.setIfType('CD', type, self.cd, value)
            self.farmable = self.setIfType('FARMABLE', type, self.farmable, value)
            self.haste = self.setIfType('HASTE', type, self.haste, value)
            self.inheritable = self.setIfType('INHERITABLE', type, self.inheritable, value)
            self.shuffle = self.setIfType('SHUFFLE', type, self.shuffle, value)
            self.unlock = self.setIfType('UNLOCK', type, self.unlock, value)
            self.resolve = self.setIfType('RESOLVE', type, self.resolve, value)
            self.delay = self.setIfType('DELAY', type, self.delay, value)
            self.combo = self.setIfType('COMBO', type, self.combo, value)
            self.absorbnull = self.setIfType('ABSORBNULL', type, self.absorbnull, value)
            self.attabsorb = self.setIfType('ATTABSORB', type, self.attabsorb, value)
            self.shield = self.setIfType('SHIELD', type, self.shield, value)
            self.atk = self.setIfType('ATK', type, self.atk, value)
            self.hp = self.setIfType('HP', type, self.hp, value)
            self.rcv = self.setIfType('RCV', type, self.rcv, value)
            self.weighted = self.setIfType('WEIGHTED', type, self.weighted, value)

            if type == 'ACTIVE':
                self.active.append(value)
            if type == 'REACTIVE':
                self.reactive.append(value)
            if type == 'BOARD':
                self.board.append(split_csv_orbcolors(value))
            if type == 'COLOR':
                self.color.append(assert_color(value))
            if type == 'COLUMN':
                self.column.append(assert_orbcolor(value))
            if type == 'HASCOLOR':
                self.hascolor.append(assert_color(value))
            if type == 'LEADER':
                self.leader.append(value)
            if type == 'RELEADER':
                self.releader.append(value)
            if type == 'NAME':
                self.name.append(value)
            if type == 'ROW':
                self.row.append(assert_orbcolor(value))
            if type == 'TYPE':
                if value not in TYPES:
                    raise commands.UserFeedbackCheckFailure(
                        'Unexpected type {}, expected one of {}'.format(value, TYPES))
                self.types.append(value)
            if type == 'REMOVE':
                self.remove.append(value)
            if type == 'CONVERT':
                self.convert.append(value)

        self.filters = list()
        self.re_filters = list()
        self.gl_filters = list()
        self.regeces = list()
        self.globs = list()

        # Single
        if self.cd:
            self.filters.append(lambda m: m.search.active_min and m.search.active_min <= self.cd)

        if self.farmable:
            self.filters.append(lambda m: db_context.graph.monster_is_farmable_evo(m))

        if self.haste:
            text = "charge allies' skill by {}".format(self.haste)
            self.filters.append(lambda m, t=text: t in m.search.active_desc)

        if self.inheritable:
            self.filters.append(lambda m: m.is_inheritable)

        if self.shuffle:
            text = 'replace all'
            self.filters.append(lambda m, t=text: t in m.search.active_desc)

        if self.unlock:
            text = 'unlock all orbs'
            self.filters.append(lambda m, t=text: t in m.search.active_desc)

        if self.resolve:
            text = 'may survive when'
            self.filters.append(lambda m, t=text: t in m.search.leader)

        if self.delay:
            text = 'delay enemies for {}'.format(self.delay)
            self.filters.append(lambda m, t=text: t in m.search.active_desc)

        if self.combo:
            text = 'increase combo count by {}'.format(self.combo)
            self.filters.append(lambda m, t=text: t in m.search.active_desc)

        if self.convert:
            text_from = self.convert[0][0]
            text_to = self.convert[0][1]
            self.filters.append(lambda m,
                                       tt=text_to,
                                       tf=text_from:
                                [tt] in m.search.orb_convert.values() if text_from == 'any' else
                                (tf in m.search.orb_convert.keys() if text_to == 'any' else
                                 (tf in m.search.orb_convert.keys() and
                                  tt in m.search.orb_convert[tf])))

        if self.absorbnull:
            text = 'damage absorb shield'
            self.filters.append(lambda m, t=text: t in m.search.active_desc)

        if self.attabsorb:
            text = 'att. absorb shield'
            self.filters.append(lambda m, t=text: t in m.search.active_desc)

        if self.shield:
            text = 'damage taken by {}%'.format(self.shield)
            self.filters.append(lambda m, t=text: t in m.search.active_desc)

        if self.atk:
            self.filters.append(lambda m: m.search.atk and m.search.atk >= self.atk)

        if self.hp:
            self.filters.append(lambda m: m.search.hp and m.search.hp >= self.hp)

        if self.rcv:
            self.filters.append(lambda m: m.search.rcv and m.search.rcv >= self.rcv)

        if self.weighted:
            self.filters.append(
                lambda m: m.search.weighted_stats and m.search.weighted_stats >= self.weighted)

        # Multiple
        if self.reactive:
            filters = []
            for ft in self.reactive:
                text = ft.lower()
                filters.append(lambda m, t=text: re.search(t, m.search.active))
                self.regeces.append(text)
            self.re_filters.extend(filters)

        if self.active:
            filters = []
            for ft in self.active:
                text = "*" + ft.lower() + "*"
                filters.append(lambda m, t=text: fnmatch(m.search.active, t))
                self.globs.append(text)
            self.gl_filters.extend(filters)

        if self.board:
            filters = []
            for colors in self.board:
                filters.append(board_filter(colors))
            self.filters.append(self.or_filters(filters))

        if self.color:
            filters = []
            for ft in self.color:
                text = ft.lower()
                filters.append(lambda m, c=text: c in m.search.color)
            self.filters.append(self.or_filters(filters))

        if self.column:
            filters = []
            for ft in self.column:
                text = ft.lower()
                if text == 'any':
                    filters.append(lambda m: m.search.column_convert)
                else:
                    filters.append(lambda m, t=text: t in m.search.column_convert)
            self.filters.append(self.or_filters(filters))

        if self.hascolor:
            filters = []
            for ft in self.hascolor:
                text = ft.lower()
                filters.append(lambda m, c=text: c in m.search.hascolor)
            self.filters.append(self.or_filters(filters))

        if self.releader:
            filters = []
            for ft in self.releader:
                text = ft.lower()
                filters.append(lambda m, t=text: re.search(t, m.search.leader))
                self.regeces.append(text)
            self.re_filters.extend(filters)

        if self.leader:
            filters = []
            for ft in self.leader:
                text = "*" + ft.lower() + "*"
                filters.append(lambda m, t=text: fnmatch(m.search.leader, t))
                self.globs.append(text)
            self.gl_filters.extend(filters)

        if self.name:
            filters = []
            for ft in self.name:
                text = ft.lower()
                filters.append(lambda m, t=text: t in m.search.name)
            self.filters.append(self.or_filters(filters))

        if self.row:
            filters = []
            for ft in self.row:
                text = ft.lower()
                if text == 'any':
                    filters.append(lambda m: m.search.row_convert)
                else:
                    filters.append(lambda m, t=text: t in m.search.row_convert)
            self.filters.append(self.or_filters(filters))

        if self.types:
            filters = []
            for ft in self.types:
                text = ft.lower()
                filters.append(lambda m, t=text: t in m.search.types)
            self.filters.append(self.or_filters(filters))

        if self.remove:
            filters = []
            for ft in self.remove:
                text = ft.lower()
                filters.append(lambda m, t=text: t not in m.search.name)
            self.filters.append(self.or_filters(filters))
        if not self.filters and not self.re_filters and not self.gl_filters:
            raise commands.UserFeedbackCheckFailure('You need to specify at least one filter')

    def check_filters(self, m):
        for f in self.filters:
            if not f(m):
                return False
        return True

    async def check_re_filters(self, ms, ctx):
        try:
            return filt_timeout(self.re_filters, ms)
        except TimeoutError:
            logger.error("Timeout with patttern: \"{}\" by user {} ({})".format(
                '", "'.join(self.regeces), ctx.author.name, ctx.author.id))
            raise commands.UserFeedbackCheckFailure("Regex took too long to compile.  Stop trying to break the bot")
        except re.error as e:
            raise commands.UserFeedbackCheckFailure("Regex search threw error '{}'".format(e.msg))

    async def check_glob_filters(self, ms, ctx):
        try:
            return filt_timeout(self.gl_filters, ms)
        except TimeoutError:
            logger.error("Timeout with patttern: \"{}\" by user {} ({})".format(
                '", "'.join(self.globs), ctx.author.name, ctx.author.id))
            raise commands.UserFeedbackCheckFailure("Glob took too long to compile.  Stop trying to break the bot")

    def or_filters(self, filters):
        def fn(m, filters=filters):
            for f in filters:
                if f(m):
                    return True
            return False

        return fn

    def setIfType(self, expected_type, given_type, current_value, new_value):
        if expected_type != given_type:
            return current_value
        if current_value is not None:
            raise commands.UserFeedbackCheckFailure('You set {} more than once'.format(given_type))
        return new_value


class PadSearch(commands.Cog):
    """PAD data searching."""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        return

    @commands.command()
    async def helpsearch(self, ctx):
        """Help info for the search command."""
        await ctx.author.send(box(HELP_MSG.format(ctx)))

    @commands.command()
    async def search(self, ctx, *, filter_spec: str):
        """Searches for monsters based on a filter you specify.
        Use [p]helpsearch for more info.
        """
        try:
            config = self._make_search_config(filter_spec)
        except Exception as ex:
            # Try to correct for missing closing tag
            try:
                config = self._make_search_config(filter_spec + ')')
            except:
                # If it still failed, raise the original exception
                raise ex
        dgcog = self.bot.get_cog('Dadguide')
        if dgcog is None:
            await ctx.send("Dadguide cog not loaded.")
            return
        monsters = dgcog.database.get_all_monsters()

        rmvGemFilter = self._make_search_config('remove( gem)')
        monsters = list(filter(rmvGemFilter.check_filters, monsters))

        matched_monsters = [m for m in monsters if config.check_filters(m)]
        # Running regeces/globs on a timer
        matched_monsters = await config.check_re_filters(matched_monsters, ctx)
        matched_monsters = await config.check_glob_filters(matched_monsters, ctx)

        # Removing entry with names that have gems in it

        matched_monsters.sort(key=lambda m: m.monster_no_na, reverse=True)

        msg = 'Matched {} monsters'.format(len(matched_monsters))
        dm_required = False
        if len(matched_monsters) == len(monsters):
            await ctx.send("All monsters were matched.  Try with a more specific query.")
            return
        if len(matched_monsters) > 10:
            if not config.all:
                msg += " (limited to 10, use 'all' to get more)"
                matched_monsters = matched_monsters[0:10]
            else:
                dm_required = True
                header = msg

            if len(matched_monsters) > 200:
                msg += " (limited to 200)"
                matched_monsters = matched_monsters[0:200]

        for m in matched_monsters:
            msg += '\n\t[{}] {}'.format(m.monster_no_na, m.name_en)

        if dm_required:
            header += '\nList too long to display; sent via DM'
            await ctx.send(box(header))
            for page in pagify(msg):
                await ctx.author.send(box(page))
        else:
            await ctx.send(box(msg))

    def _make_search_config(self, input):
        lexer = PadSearchLexer().build()
        lexer.input(input)
        db_context = self.bot.get_cog("Dadguide").database
        return SearchConfig(lexer, db_context)
