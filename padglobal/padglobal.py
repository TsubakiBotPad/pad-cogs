import asyncio
import datetime
import difflib
import json
import logging
import os
import re
from collections import defaultdict
from io import BytesIO

import discord
import prettytable
import pytz
from redbot.core import checks, commands, data_manager, errors
from redbot.core.utils.chat_formatting import bold, box, humanize_timedelta, inline, pagify
from tsutils.cog_settings import CogSettings
from tsutils.cogs.globaladmin import auth_check
from tsutils.emoji import fix_emojis_for_server, replace_emoji_names_with_code
from tsutils.formatting import clean_global_mentions, strip_right_multiline
from tsutils.json_utils import safe_read_json
from tsutils.menu.view.closable_embed import ClosableEmbedViewState
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.time import NA_TIMEZONE
from tsutils.tsubaki.custom_emoji import get_attribute_emoji_by_monster
from tsutils.tsubaki.links import CLOUDFRONT_URL
from tsutils.user_interaction import get_user_confirmation, get_user_reaction

from padglobal.menu.closable_embed import ClosableEmbedMenu
from padglobal.menu.menu_map import padglobal_menu_map
from padglobal.view.which import UNKNOWN_EDIT_TIMESTAMP, WhichView, WhichViewProps

logger = logging.getLogger('red.padbot-cogs.padglobal')


def _data_file(file_name: str) -> str:
    return os.path.join(str(data_manager.cog_data_path(raw_name='padglobal')), file_name)


DATA_EXPORT_PATH = _data_file('padglobal_data.json')

PAD_CMD_HEADER = """
PAD Global Commands
{0}pad      : general command list
{0}padfaq   : FAQ command list
{0}boards   : optimal boards
{0}glossary : common PAD definitions
{0}boss     : boss mechanics
{0}which    : which monster evo info
"""

BLACKLISTED_CHARACTERS = '^[]*`~_'

PORTRAIT_TEMPLATE = CLOUDFRONT_URL + '/media/portraits/{0:05d}.png'

DISABLED_MSG = 'PAD Global info disabled on this server'

FARMABLE_MSG = 'This monster is **farmable** so make as many copies of whichever evos you like.'
MP_BUY_MSG = ('This monster can be purchased with MP. **DO NOT** buy MP cards without a good reason'
              ', check `{}mpdra?` for specific recommendations.')
SIMPLE_TREE_MSG = 'This monster appears to be uncontroversial because the skill never changes & there are no branching evos; use the highest evolution: `[{}] {}`.'

MAX_WHICH_LIST_BEFORE_DM_PROMPT = 30


def mod_help(self, ctx, help_type):
    hs = getattr(self, help_type)
    return self.format_text_for_context(ctx, hs).format(ctx) if hs else hs


commands.Command.format_help_for_context = lambda s, c: mod_help(s, c, "help")
commands.Command.format_shortdoc_for_context = lambda s, c: mod_help(s, c, "short_doc")


async def check_enabled(ctx):
    """If the server is disabled, raise a warning and return False"""
    if ctx.bot.get_cog("PadGlobal").settings.checkDisabled(ctx.message):
        msg = await ctx.send(inline(DISABLED_MSG))
        await asyncio.sleep(3)
        await msg.delete()
        return False
    return True


class PadGlobal(commands.Cog):
    """Global PAD commands."""

    menu_map = padglobal_menu_map

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        GADMIN_COG = self.bot.get_cog("GlobalAdmin")
        if GADMIN_COG:
            GADMIN_COG.register_perm("contentadmin")
        else:
            raise errors.CogLoadError("Global Administration cog must be loaded.  Make sure it's "
                                      "installed from core-cogs and load it via `^load globaladmin`")

        self.file_path = _data_file('commands.json')
        self.c_commands = safe_read_json(self.file_path)
        self.settings = PadGlobalSettings("padglobal")

        self._export_data()

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        return

    async def register_menu(self):
        await self.bot.wait_until_ready()
        menulistener = self.bot.get_cog("MenuListener")
        if menulistener is None:
            logger.warning("MenuListener is not loaded.")
            return
        await menulistener.register(self)

    async def get_menu_default_data(self, ims):
        data = {}
        return data

    def _export_data(self):
        faq_and_boards = self.settings.faq() + self.settings.boards()
        general = {k: v for k, v in self.c_commands.items() if k not in faq_and_boards}
        faq = {k: v for k, v in self.c_commands.items() if k in self.settings.faq()}
        boards = {k: v for k, v in self.c_commands.items() if k in self.settings.boards()}
        glossary = self.settings.glossary()
        bosses = self.settings.boss()
        which = self.settings.which()
        dungeon_guide = self.settings.dungeonGuide()
        leader_guide = self.settings.leaderGuide()

        results = {
            'general': general,
            'faq': faq,
            'boards': boards,
            'glossary': glossary,
            'boss': bosses,
            'which': which,
            'dungeon_guide': dungeon_guide,
            'leader_guide': leader_guide,
        }

        with open(DATA_EXPORT_PATH, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4)

    @commands.command()
    @auth_check('contentadmin')
    async def breakglass(self, ctx, *, reason: str):
        """Shuts down the bot, for emergency use only.

        If the bot needs to be restarted in an emergency, you can use this to do it.
        Since the bot automatically restarts after being shut down for 30s, this
        command just kills the bot.

        Obviously this will only work if the bot can read messages, but there is a
        class of problems where the bot can read messages but not respond, so this
        could handle those cases.
        """
        msg = '------------------------\n'
        msg += '{} shut down the bot because: {}\n'.format(ctx.author.name, reason)
        msg += '------------------------\n'
        logger.critical(msg)

        try:
            for uid in self.bot.owner_ids:
                await self.bot.get_user(uid).send(msg)
            await ctx.send("Owners have been notified, shutting down...")
        except Exception as ex:
            logger.exception("Failed to notifiy for breakglass.")

        await self.bot.shutdown(restart=True)

    @commands.command()
    @checks.admin_or_permissions(manage_guild=True)
    async def togglepadglobal(self, ctx):
        """Enable or disable PAD Global commands for the server."""
        server_id = ctx.guild.id
        if server_id in self.settings.disabledServers():
            self.settings.rmDisabledServer(server_id)
        else:
            self.settings.addDisabledServer(server_id)
        status = 'disabled' if self.settings.checkDisabled(ctx.message) else 'enabled'
        await ctx.send(inline('PAD Global commands {} on this server').format(status))

    @commands.group(aliases=['pdg'])
    @auth_check('contentadmin')
    async def padglobal(self, ctx):
        """PAD global custom commands.

        See also `[p]pglossary`, `[p]pboss`, `[p]pwhich`, and `[p]pguide`.
        """

    @padglobal.command()
    async def say(self, ctx, *, text: str):
        """Test a padglobal command with emoji replacements."""
        text = replace_emoji_names_with_code(self._get_emojis(), text)
        await ctx.send(text)

    @padglobal.command(aliases=['addalias', 'alias'])
    async def add(self, ctx, command: str, *, text: str):
        """Create a custom command or alias"""
        await self._add(ctx, command, text, True)

    @padglobal.command(aliases=['editalias'])
    async def edit(self, ctx, command: str, *, text: str):
        """Edit a custom command or alias"""
        await self._add(ctx, command, text, False)

    async def _add(self, ctx, command, text, confirm=True):
        command = command.lower()
        text = clean_global_mentions(text)
        text = text.replace(u'\u200b', '')
        text = replace_emoji_names_with_code(self._get_emojis(), text)
        if command in self.bot.all_commands.keys():
            await ctx.send("That is already a standard command.")
            return

        for c in list(BLACKLISTED_CHARACTERS) + [ctx.prefix]:
            if c in command:
                await ctx.send("Invalid character in name: {}".format(c))
                return

        if not self.c_commands:
            self.c_commands = {}

        if text in self.c_commands:
            op = 'aliased'
            if text == command:
                await ctx.send('You cannot alias something to itself.')
                return
            if self.c_commands[text] in self.c_commands:
                source = self.c_commands[text]
                if await get_user_confirmation(ctx, f'{inline(text)} is already an alias for {inline(source)},'
                                                    f' and you can\'t alias to an alias. Would you like to'
                                                    f' alias to {inline(source)} instead?'):
                    # change target
                    text = source
                else:
                    return
        elif command in self.c_commands:
            op = 'edited'
            ted = self.c_commands[command]
            alias = False
            while ted in self.c_commands:
                ted = self.c_commands[ted]
                alias = True
            if confirm:
                conf = await get_user_confirmation(ctx, "Are you sure you want to edit the {}command {}?"
                                                        "".format("alias to " if alias else "", ted))
                if not conf:
                    return
        else:
            op = 'added'

        self.c_commands[command] = text
        json.dump(self.c_commands, open(self.file_path, 'w+'))
        await ctx.send("PAD command successfully {}.".format(bold(op)))

    @padglobal.command(aliases=['rmalias', 'delalias', 'remove', 'rm', 'del'])
    async def delete(self, ctx, command: str):
        """Deletes a PAD global command or alias

        Example:
        [p]padglobal delete yourcommand"""
        command = command.lower()

        aliases = await self._find_aliases(command)
        if aliases:
            if not await get_user_confirmation(ctx,
                                               'Are you sure? `{}` has {} alias(es): `{}` which will also be deleted.'
                                               ''.format(command, bold(str(len(aliases))), '`, `'.join(aliases))):
                await ctx.send('Cancelling delete of `{}`.'.format(command))
                return

        if command in self.c_commands:
            alias = self.c_commands[command] in self.c_commands
            ocm = self.c_commands.copy()
            self.c_commands.pop(command, None)
            todel = [command]
            while ocm != self.c_commands:
                ocm = self.c_commands.copy()
                for comm in ocm:
                    if self.c_commands[comm] in todel:
                        self.c_commands.pop(comm, None)
                        todel.append(comm)
            json.dump(self.c_commands, open(self.file_path, 'w+'))
            await ctx.send("PAD {} successfully deleted.".format(bold('alias' if alias else 'command')))
        else:
            await ctx.send("PAD command doesn't exist.")

    @padglobal.command()
    async def prepend(self, ctx, command: str, *, addition):
        """Prepend the additional text to an existing command before a blank line."""
        await self._concatenate(ctx, command, 'prepend', addition)

    @padglobal.command()
    async def append(self, ctx, command: str, *, addition):
        """Append the additional text to an existing command after a blank line."""
        await self._concatenate(ctx, command, 'append', addition)

    async def _concatenate(self, ctx, command: str, operation: str, addition):
        # the same cleaning that padglobal add does
        command = command.lower()
        addition = clean_global_mentions(addition)
        addition = addition.replace(u'\u200b', '')
        addition = replace_emoji_names_with_code(self._get_emojis(), addition)

        corrected_cmd = self._lookup_command(command)
        alias = False
        if not corrected_cmd:
            await ctx.send("Could not find a good match for command `{}`.".format(command))
            return
        result = self.c_commands.get(corrected_cmd, None)
        # go a level deeper if trying to append to an alias
        source_cmd = None
        if result in self.c_commands:
            alias = True
            source_cmd = result
            result = self.c_commands[result]

        if operation == 'prepend':
            result = "{}\n\n{}".format(addition, result)
        elif operation == 'append':
            result = "{}\n\n{}".format(result, addition)
        else:
            raise KeyError("Invalid operation: Must be \'prepend\' or \'append\'")

        if alias:
            self.c_commands[source_cmd] = result
        else:
            self.c_commands[corrected_cmd] = result
        json.dump(self.c_commands, open(self.file_path, 'w+'))

        await ctx.send("Successfully {}ed to {}PAD command `{}`.".format(operation, "source " if alias else "",
                                                                         source_cmd if alias else corrected_cmd))

    @padglobal.command()
    async def eventswap(self, ctx):
        """Shift contents of nextevent command to currentevent"""
        if 'currentevent' not in self.c_commands or 'nextevent' not in self.c_commands:
            await ctx.send(f"Please populate both {inline('currentevent')} and {inline('nextevent')} first."
                           f" Cancelling.")
            return

        current_text = self.c_commands['currentevent']
        next_text = self.c_commands['nextevent']

        if not await get_user_confirmation(ctx, "Are you sure you want to update for the new event?"):
            await ctx.send("Making no change to current and next event.")
            return

        self.c_commands['lastevent'] = current_text
        self.c_commands['currentevent'] = next_text
        self.c_commands['nextevent'] = "N/A"

        json.dump(self.c_commands, open(self.file_path, 'w+'))
        await ctx.send(f"Okay, I've updated {inline('lastevent')} and {inline('currentevent')} accordingly,"
                       f" and cleared {inline('nextevent')}.")
    
    @padglobal.command()
    async def rename(self, ctx, old_name, new_name):
        """Rename a PAD global command"""
        if old_name not in self.c_commands:
            await ctx.send(f"Please populate {inline(old_name)} first.")
            return
        if new_name in self.c_commands:
            await ctx.send("A command already exists with that name.")
            return
        if not await get_user_confirmation(ctx, f"Are you sure you want to rename command {inline(old_name)} to {inline(new_name)}?"):
            await ctx.send("The command was not renamed.")
            return
        aliases = await self._find_aliases(old_name)
        for alias in aliases:
            self.c_commands[alias] = new_name

        self.c_commands[new_name] = self.c_commands[old_name]
        self.c_commands.pop(old_name)

        json.dump(self.c_commands, open(self.file_path, 'w+'))
        await ctx.send(f"Okay, I've deleted {inline(old_name)} and moved its contents to {inline(new_name)}.")

    async def _find_aliases(self, command: str):
        aliases = []
        for cmd in self.c_commands:
            if self.c_commands[cmd] == command:
                aliases.append(cmd)
        return aliases

    @padglobal.command()
    async def setgeneral(self, ctx, command: str):
        """Sets a command to show up in [p]pad (the default).

        Example:
        [p]padglobal setgeneral yourcommand"""
        command = command.lower()
        if command not in self.c_commands:
            await ctx.send("PAD command doesn't exist.")
            return

        self.settings.setGeneral(command)
        await ctx.send("PAD command set to general.")

    @padglobal.command()
    async def setfaq(self, ctx, command: str):
        """Sets a command to show up in [p]padfaq.

        Example:
        [p]padglobal setfaq yourcommand"""
        command = command.lower()
        if command not in self.c_commands:
            await ctx.send("PAD command doesn't exist.")
            return

        self.settings.setFaq(command)
        await ctx.send("PAD command set to faq.")

    @padglobal.command()
    async def setboards(self, ctx, command: str):
        """Sets a command to show up in [p]boards.

        Example:
        [p]padglobal setboards yourcommand"""
        command = command.lower()
        if command not in self.c_commands:
            await ctx.send("PAD command doesn't exist.")
            return

        self.settings.setBoards(command)
        await ctx.send("PAD command set to boards.")

    @padglobal.command()
    async def checktype(self, ctx, command: str):
        """Checks if a command is board, FAQ, or general"""
        command = command.lower()
        if command in self.settings.boards():
            await ctx.send('{} is a board.'.format(command))
        elif command in self.settings.faq():
            await ctx.send('{} is a FAQ.'.format(command))
        elif command in self.c_commands:
            await ctx.send('{} is a general padglobal command.'.format(command))
        else:
            await ctx.send('{} is not a padglobal command. It might be a meme or a custom command.'.format(command))

    @commands.command()
    @commands.check(check_enabled)
    async def pad(self, ctx):
        """Shows PAD global command list"""
        configured = self.settings.faq() + self.settings.boards()
        cmdlist = {k: v for k, v in self.c_commands.items() if k not in configured}
        await self.send_cmdlist(ctx, cmdlist)

    @commands.command()
    @commands.check(check_enabled)
    async def padfaq(self, ctx):
        """Shows PAD FAQ command list"""
        cmdlist = {k: v for k, v in self.c_commands.items() if k in self.settings.faq()}
        await self.send_cmdlist(ctx, cmdlist)

    @commands.command()
    @commands.check(check_enabled)
    async def boards(self, ctx):
        """Shows PAD Boards command list"""
        cmdlist = {k: v for k, v in self.c_commands.items() if k in self.settings.boards()}
        await self.send_cmdlist(ctx, cmdlist)

    async def send_cmdlist(self, ctx, cmdlist, write_inline=False):
        if not cmdlist:
            await ctx.send("There are no padglobal commands yet")
            return

        prefixes = defaultdict(list)

        for c in cmdlist:
            m = re.match(r'^([a-zA-Z]+)(\d+)$', c)
            if m:
                prefixes[m.group(1)].append(m.group(2))

        prefix_to_suffix = {cmd: cnt for cmd, cnt in prefixes.items() if len(cnt) > 1}

        msg = PAD_CMD_HEADER.format(ctx.prefix) + "\n"

        done_prefixes = []

        for cmd in sorted(cmdlist):
            m = re.match(r'^([a-zA-Z]+)\d+$', cmd)
            if m:
                prefix = m.group(1)
                if prefix in prefix_to_suffix and prefix not in done_prefixes:
                    msg += " {}{}[n]:\n  ".format(ctx.prefix, prefix)
                    for suffix in sorted(map(int, prefix_to_suffix[prefix])):
                        msg += " {}{}".format(prefix, suffix)
                    msg += '\n'
                    done_prefixes.append(prefix)
            else:
                msg += " {}{}\n".format(ctx.prefix, cmd)

        for page in pagify(msg):
            await ctx.author.send(box(page))

    @commands.command()
    @commands.check(check_enabled)
    async def glossaryto(self, ctx, to_user: discord.Member, *, term: str):
        """Send a user a glossary entry

        [p]glossaryto @{0.author.name} godfest
        """
        corrected_term, result = self.lookup_glossary(term)
        await self._do_send_term(ctx, to_user, term, corrected_term, result)

    @commands.command()
    @commands.check(check_enabled)
    async def padto(self, ctx, to_user: discord.Member, *, term: str):
        """Send a user a pad/padfaq entry

        [p]padto @{0.author.name} jewels?
        """
        corrected_term = self._lookup_command(term)
        result = self.c_commands.get(corrected_term, None)
        # go a level deeper if this is an alias
        if result in self.c_commands:
            result = self.c_commands[result]

        await self._do_send_term(ctx, to_user, term, corrected_term, result)

    async def _do_send_term(self, ctx, to_user: discord.Member, term, corrected_term, result):
        """Does the heavy lifting shared by padto and glossaryto."""
        if result:
            result_output = '**{}** : {}'.format(corrected_term, result)
            result = "{} asked me to send you this:\n{}".format(
                ctx.author.name, result_output)
            await to_user.send(result)
            msg = "Sent that info to {}".format(to_user.name)
            if term != corrected_term:
                msg += ' (corrected to {})'.format(corrected_term)
            await ctx.send(inline(msg))
        else:
            await ctx.send(inline('No definition found'))

    @commands.command()
    @commands.check(check_enabled)
    async def glossary(self, ctx, *, term: str = None):
        """Shows PAD Glossary entries"""

        if term:
            term, definition = self.lookup_glossary(term)
            if definition:
                definition_output = '**{}** : {}'.format(term, definition)
                await ctx.send(self.emojify(definition_output))
            else:
                await ctx.send(inline('No definition found'))
            return

        msg = self.glossary_to_text(ctx)
        for page in pagify(msg):
            await ctx.author.send(page)

    def glossary_to_text(self, ctx):
        glossary = self.settings.glossary()
        msg = '__**PAD Glossary terms (also check out {0}pad / {0}padfaq / {0}boards / {0}which)**__'.format(ctx.prefix)
        for term in sorted(glossary.keys()):
            definition = glossary[term]
            msg += '\n**{}** : {}'.format(term, definition)
        return msg

    def lookup_glossary(self, term):
        glossary = self.settings.glossary()
        term = term.lower()
        definition = glossary.get(term, None)

        if definition:
            return term, definition

        matches = self._get_corrected_cmds(term, glossary.keys())

        if not matches:
            matches = difflib.get_close_matches(term, glossary.keys(), n=1, cutoff=.8)

        if not matches:
            return term, None
        else:
            term = matches[0]
            return term, glossary[term]

    @commands.group()
    @auth_check('contentadmin')
    async def pglossary(self, ctx):
        """Commands related to the PAD global glossary."""

    @pglossary.command(name='add')
    async def pglossary_add(self, ctx, term, *, definition):
        """Adds a term to the glossary.
        If you want to use a multiple word term, enclose it in quotes.

        e.x. [p]pglossary add alb Awoken Liu Bei
        e.x. [p]pglossary add "never dathena" NA will never get dathena
        """
        await self._pglossary_add(ctx, term, definition, True)

    @pglossary.command(name='edit')
    async def pglossary_edit(self, ctx, term, *, definition):
        """Edit a term from the glossary."""
        await self._pglossary_add(ctx, term, definition, False)

    async def _pglossary_add(self, ctx, term, definition, need_confirm=True):
        term = term.lower()
        definition = clean_global_mentions(definition)
        definition = definition.replace(u'\u200b', '')
        definition = replace_emoji_names_with_code(self._get_emojis(), definition)

        op = 'edited' if term in self.settings.glossary() else 'added'
        if op == 'edited' and need_confirm:
            if not await get_user_confirmation(ctx,
                                               "Are you sure you want to edit the glossary info for {}?".format(term)):
                return
        self.settings.addGlossary(term, definition)
        await ctx.send("PAD glossary term successfully {}.".format(bold(op)))

    @pglossary.command(name='remove', aliases=['rm', 'delete', 'del'])
    async def pglossary_remove(self, ctx, *, term):
        """Removes a term from the glossary."""
        term = term.lower()
        if term not in self.settings.glossary():
            await ctx.send("Glossary item doesn't exist.")
            return
        if not await get_user_confirmation(ctx,
                                           "Are you sure you want to globally remove the glossary data for {}?".format(
                                               term)):
            return
        self.settings.rmGlossary(term)
        await ctx.tick()

    @commands.command()
    @commands.check(check_enabled)
    async def boss(self, ctx, *, term: str = None):
        """Shows boss skill entries"""
        if term:
            name, definition = await self.lookup_boss(term, ctx)
            if definition:
                await ctx.send(self.emojify(definition))
            else:
                await ctx.send(inline('No mechanics found'))
            return
        msg = await self.boss_to_text(ctx)
        for page in pagify(msg):
            await ctx.author.send(page)

    @commands.command()
    @commands.check(check_enabled)
    async def bosslist(self, ctx):
        """Shows boss skill entries"""
        msg = self.boss_to_text_index(ctx)
        for page in pagify(msg):
            await ctx.author.send(page)

    async def lookup_boss(self, term, ctx):
        dbcog = await self.get_dbcog()

        term = term.lower().replace('?', '')
        m = await dbcog.find_monster(term, ctx.author.id)
        if m is None:
            return None, None

        m = dbcog.database.graph.get_base_monster(m)
        name = get_attribute_emoji_by_monster(m) + " " + m.name_en.split(",")[-1].strip()
        monster_id = m.monster_id
        definition = self.settings.boss().get(monster_id, None)

        return name, definition

    async def boss_to_text(self, ctx):
        bosses = self.settings.boss()
        dbcog = await self.get_dbcog()
        msg = '__**Available PAD Boss Mechanics (also check out {0}pad / {0}padfaq / {0}boards / {0}which / {0}glossary)**__'.format(
            ctx.prefix)
        for term in sorted(bosses.keys()):
            m = await dbcog.find_monster(str(term), ctx.author.id)
            if not m:  # monster not found
                continue
            msg += '\n[{}] {}'.format(term, m.name_en)
        return msg

    def boss_to_text_index(self, ctx):
        bosses = self.settings.boss()
        msg = '__**Available PAD Boss Mechanics (also check out {0}pad / {0}padfaq / {0}boards / {0}which / {0}glossary)**__'.format(
            ctx.prefix)
        msg = msg + '\n' + ',\n'.join(map(str, sorted(bosses.keys())))
        return msg

    @commands.group()
    @auth_check('contentadmin')
    async def pboss(self, ctx):
        """Commands related to PAD global boss mechanics."""

    @pboss.command(name='add')
    async def pboss_add(self, ctx, term, *, definition):
        """Adds a set of boss mechanics.

        If you want to use a multiple word boss name, enclose it in quotes.
        """
        await self._pboss_add(ctx, term, definition, True)

    @pboss.command(name='edit')
    async def pboss_edit(self, ctx, term, *, definition):
        """Edit a set of boss mechanics."""
        await self._pboss_add(ctx, term, definition, False)

    async def _pboss_add(self, ctx, term, definition, need_confirm=True):
        dbcog = await self.get_dbcog()
        pdicog = self.bot.get_cog("PadInfo")

        term = term.lower()
        m = await dbcog.find_monster(term, ctx.author.id)
        if m is None:
            await ctx.send(f"No monster found for `{term}`")
            return

        base = dbcog.database.graph.get_base_monster(m)

        op = 'edited' if base.monster_id in self.settings.boss() else 'added'
        if op == 'edited' and need_confirm:
            if not await get_user_confirmation(ctx,
                                               "Are you sure you want to edit the boss info for {}?".format(
                                                   base.name_en)):
                return
        definition = clean_global_mentions(definition)
        definition = definition.replace(u'\u200b', '')
        definition = replace_emoji_names_with_code(self._get_emojis(), definition)
        self.settings.addBoss(base.monster_id, definition)
        await ctx.send("PAD boss mechanics successfully {}.".format(bold(op)))

    @pboss.command(name='remove', aliases=['rm', 'delete', 'del'])
    async def pboss_remove(self, ctx, *, term):
        """Removes a set of boss mechanics."""
        dbcog = await self.get_dbcog()
        pdicog = self.bot.get_cog("PadInfo")

        term = term.lower()
        m = await dbcog.find_monster(term, ctx.author.id)
        if m is None:
            await ctx.send(f"No monster found for `{term}`.  Make sure you didn't use quotes.")
            return

        base = dbcog.database.graph.get_base_monster(m)

        if base.monster_id not in self.settings.boss():
            await ctx.send("Boss mechanics item doesn't exist.")
            return
        if not await get_user_confirmation(ctx,
                                           "Are you sure you want to globally remove the boss data for {}?".format(
                                               base.name_en)):
            return

        self.settings.rmBoss(base.monster_id)
        await ctx.tick()

    @commands.command()
    @commands.check(check_enabled)
    async def which(self, ctx, *, term: str = None):
        """Shows PAD Which Monster entries"""

        if term is None:
            await ctx.author.send(
                '__**PAD Which Monster**__ *(also check out {0}pad / {0}padfaq / {0}boards / {0}glossary)*'.format(
                    ctx.prefix))
            msg = await self.which_to_text()
            for page in pagify(msg):
                await ctx.author.send(box(page))
            return

        monster, definition, timestamp, success = await self._resolve_which(ctx, term)
        if monster is None or definition is None:
            return
        qs = await QuerySettings.extract_raw(ctx.author, self.bot, term)
        original_author_id = ctx.message.author.id
        menu = ClosableEmbedMenu.menu()
        props = WhichViewProps(monster=monster, definition=definition, timestamp=timestamp, success=success)
        state = ClosableEmbedViewState(original_author_id, ClosableEmbedMenu.MENU_TYPE, term,
                                       qs, WhichView.VIEW_TYPE, props)
        await menu.create(ctx, state)

    async def _resolve_which(self, ctx, term):
        dbcog = await self.get_dbcog()
        db_context = dbcog.database

        term = term.lower().replace('?', '')
        m = await dbcog.find_monster(term, ctx.author.id)
        if m is None:
            await ctx.send(inline('No monster matched that query'))
            return None, None, None, None

        m = db_context.graph.get_base_monster(m)

        monster_id = m.monster_id
        definition = self.settings.which().get(monster_id, None)
        timestamp = UNKNOWN_EDIT_TIMESTAMP

        if isinstance(definition, list):
            definition, timestamp = definition

        if definition is not None:
            return m, definition, timestamp, True

        monster = dbcog.get_monster(monster_id)

        if db_context.graph.monster_is_mp_evo(monster) and not monster.in_rem:
            return name, MP_BUY_MSG.format(ctx.prefix), None, False
        elif db_context.graph.monster_is_farmable_evo(monster):
            return name, FARMABLE_MSG, None, False
        elif check_simple_tree(monster, db_context):
            top_monster = db_context.graph.get_numerical_sort_top_monster(monster)
            return name, SIMPLE_TREE_MSG.format(top_monster.monster_id, top_monster.name_en), None, False
        else:
            await ctx.send('No which info for {} (#{})'.format(name, monster_id))
            return None, None, None, None

    @commands.command()
    @commands.check(check_enabled)
    async def whichto(self, ctx, to_user: discord.Member, *, term: str):
        """Send a user a which monster entry.

        [p]whichto @{0.author.name} saria
        """
        name, definition, timestamp, success = await self._resolve_which(ctx, term)
        if name is None or definition is None:
            return

        if not success:
            await ctx.send('Which {}\n{}'.format(name, definition))
            return
        await self._do_send_which(ctx, to_user, name, definition, timestamp)

    async def which_to_text(self):
        monsters = defaultdict(list)
        for monster_id in self.settings.which():
            m = (await self.get_dbcog()).get_monster(monster_id)
            if m is None:
                continue
            name = m.name_en.split(", ")[-1]
            grp = m.series.name
            monsters[grp].append(name)

        tbl = prettytable.PrettyTable(['Group', 'Members'])
        tbl.hrules = prettytable.HEADER
        tbl.vrules = prettytable.NONE
        tbl.align = "l"
        for grp in sorted(monsters.keys()):
            tbl.add_row([grp, ', '.join(sorted(monsters[grp]))])

        tbl_string = strip_right_multiline(tbl.get_string())
        return tbl_string

    async def _do_send_which(self, ctx, to_user: discord.Member, name, definition, timestamp):
        """Does the heavy lifting for whichto."""
        result_output = '**Which {} - Last Updated {}**\n{}'.format(name, timestamp, definition)

        result = "{} asked me to send you this:\n{}".format(
            ctx.author.name, result_output)
        for page in pagify(result):
            await to_user.send(page)
        await ctx.send("Sent info on {} to {}".format(name, to_user.name))

    @commands.group()
    @auth_check('contentadmin')
    async def pwhich(self, ctx):
        """Commands related to PAD global which definitions."""

    @pwhich.command(name='add')
    async def pwhich_add(self, ctx, term, *, definition):
        """Adds an entry to the which monster evo list.

        Accepts queries. The which text will be entered for the resulting monster's tree.
        e.x. [p]pwhich add 3818 take the pixel one
        """
        await self._pwhich_add(ctx, term, definition, True)

    @pwhich.command(name='edit')
    async def pwhich_edit(self, ctx, term, *, definition):
        """Edit an entry from the which monster evo list."""
        await self._pwhich_add(ctx, term, definition, False)

    async def _pwhich_add(self, ctx, term, definition, need_confirm=True):
        dbcog = await self.get_dbcog()

        term = term.lower()
        m = await dbcog.find_monster(term, ctx.author.id)
        if m is None:
            await ctx.send(f"No monster found for `{term}`")
            return

        base_monster = dbcog.database.graph.get_base_monster(m)
        if m != base_monster:
            m = base_monster
            await ctx.send("I think you meant {} for {}.".format(m.monster_no, m.name_en))
        name = m.monster_id

        is_int = re.fullmatch(r'\d+', term)

        op = 'edited' if name in self.settings.which() else 'added'
        if not is_int or op == 'edited' and need_confirm:
            if not await get_user_confirmation(ctx, "Are you sure you want to {} which info for {} [{}] {}?".format(
                    'edit the' if op == 'edited' else 'add new',
                    get_attribute_emoji_by_monster(m),
                    m.monster_no,
                    m.name_en)):
                return

        definition = clean_global_mentions(definition)
        definition = definition.replace(u'\u200b', '')
        definition = replace_emoji_names_with_code(self._get_emojis(), definition)
        self.settings.addWhich(name, definition)
        await ctx.send("PAD which info successfully {} for [{}] {}.".format(bold(op), m.monster_no, m.name_en))

    @pwhich.command(name='remove', aliases=['rm', 'delete', 'del'])
    async def pwhich_remove(self, ctx, *, monster_id: int):
        """Removes an entry from the which monster evo list."""
        dbcog = await self.get_dbcog()
        m = dbcog.get_monster(monster_id)
        base_monster = dbcog.database.graph.get_base_monster(m)
        if m != base_monster:
            m = base_monster
            await ctx.send("I think you meant {} for {}.".format(m.monster_no, m.name_en))
        if not await get_user_confirmation(ctx,
                                           "Are you sure you want to globally remove the which data for {}?".format(
                                               m.name_en)):
            return
        name = m.monster_id

        if name not in self.settings.which():
            await ctx.send("Which item doesn't exist.")
            return

        self.settings.rmWhich(name)
        await ctx.tick()

    @pwhich.command(name='prepend')
    async def pwhich_prepend(self, ctx, term: str, *, addition):
        """Prepend the additional text to an existing which entry before a blank line."""
        await self._concatenate_which(ctx, term, 'prepend', addition)

    @pwhich.command(name='append')
    async def pwhich_append(self, ctx, term: str, *, addition):
        """Append the additional text to an existing which entry after a blank line."""
        await self._concatenate_which(ctx, term, 'append', addition)

    async def _concatenate_which(self, ctx, term: str, operation: str, addition):
        dbcog = await self.get_dbcog()

        term = term.lower()
        m = await dbcog.find_monster(term, ctx.author.id)
        if m is None:
            await ctx.send(f"No monster found for `{term}`")
            return

        base_monster = dbcog.database.graph.get_base_monster(m)
        if m != base_monster:
            m = base_monster
            await ctx.send("I think you meant {} for {}.".format(m.monster_no, m.name_en))
        mon_id = m.monster_id

        # ask for extra confirmation if the term was not an id
        if not re.fullmatch(r'\d+', term):
            if not await get_user_confirmation(ctx,
                                               'Are you sure you want to {} to the which info for {} [{}] {}?'.format(
                                                   operation,
                                                   get_attribute_emoji_by_monster(m),
                                                   m.monster_no,
                                                   m.name_en)):
                return

        if mon_id not in self.settings.which():
            if await get_user_confirmation(ctx,
                                           "No which info exists for {}. Would you like to add a new entry?".format(
                                               m.name_en)):
                self.settings.addWhich(mon_id, addition)
                await ctx.send("PAD which info successfully {}.".format(bold('added')))
            return

        definition, _ = self.settings.which().get(mon_id, None)

        addition = clean_global_mentions(addition)
        addition = addition.replace(u'\u200b', '')
        addition = replace_emoji_names_with_code(self._get_emojis(), addition)

        if operation == 'prepend':
            self.settings.addWhich(mon_id, '{}\n\n{}'.format(addition, definition))
            await ctx.send("Successfully {} to PAD which info for [{}] {}.".format(bold('prepended'), m.monster_no,
                                                                                   m.name_en))
        elif operation == 'append':
            self.settings.addWhich(mon_id, '{}\n\n{}'.format(definition, addition))
            await ctx.send("Successfully {} to PAD which info for [{}] {}.".format(bold('appended'), m.monster_no,
                                                                                   m.name_en))
        else:
            raise KeyError("Invalid operation: Must be \'prepend\' or \'append\'")

    @pwhich.command(name='dump')
    async def pwhich_dump(self, ctx, *, term: str):
        """Dump the raw text of an existing which entry, boxed."""
        _, definition, _, _ = await self._resolve_which(ctx, term)

        if definition is None:
            return
        else:
            for page in pagify(definition):
                content = box(page.replace('`', u'\u200b`'))
                await ctx.send(content)

    @pwhich.command(name='list')
    async def pwhich_list(self, ctx):
        """List all which commands."""
        channel = '\N{WHITE HEAVY CHECK MARK}'
        send_as_dm = '\N{ENVELOPE}'
        cancel = '\N{CROSS MARK}'
        destination = channel
        if len(self.settings.which()) > MAX_WHICH_LIST_BEFORE_DM_PROMPT:
            destination = await get_user_reaction(ctx,
                                                  'This will send a lot of messages. Are you sure? '
                                                  + '(Yes / DM me instead / Cancel)',
                                                  channel,
                                                  send_as_dm,
                                                  cancel)
        if destination == cancel or destination is None:
            return

        items = list()
        monsters = []
        for w in self.settings.which():
            w %= 10000

            m = (await self.get_dbcog()).get_monster(w)
            name = m.name_en.split(', ')[-1]

            result = self.settings.which()[w]
            if isinstance(result, list):
                monsters.append([name, result[1]])
            else:
                monsters.append([name, UNKNOWN_EDIT_TIMESTAMP])

        tbl = prettytable.PrettyTable(['Monster', 'Timestamp'])
        tbl.hrules = prettytable.HEADER
        tbl.vrules = prettytable.NONE
        tbl.align = "l"
        for mon in sorted(sorted(monsters), key=lambda x: x[1]):
            tbl.add_row(mon)

        msg = strip_right_multiline(tbl.get_string())

        for page in pagify(msg):
            if destination == channel:
                await ctx.send(box(page))
            else:
                await ctx.author.send(box(page))

    @padglobal.group()
    @checks.is_owner()
    async def emojiservers(self, ctx):
        """Emoji server subcommand"""

    @emojiservers.command(name="add")
    @checks.is_owner()
    async def es_add(self, ctx, server_id: int):
        """Add the emoji server by ID"""
        ess = self.settings.emojiServers()
        if server_id not in ess:
            ess.append(server_id)
            self.settings.save_settings()
        await ctx.tick()

    @emojiservers.command(name="remove", aliases=['rm', 'del'])
    @checks.is_owner()
    async def es_rm(self, ctx, server_id: int):
        """Remove the emoji server by ID"""
        ess = self.settings.emojiServers()
        if server_id not in ess:
            await ctx.send("That emoji server is not set.")
            return
        ess.remove(server_id)
        self.settings.save_settings()
        await ctx.tick()

    @emojiservers.command(name="list", aliases=['show'])
    @checks.is_owner()
    async def es_show(self, ctx):
        """List the emoji servers by ID"""
        ess = self.settings.emojiServers()
        await ctx.send(box("\n".join(str(s) for s in ess)))

    def _get_emojis(self):
        emojis = list()
        for server_id in self.settings.emojiServers():
            try:
                emojis.extend(self.bot.get_guild(int(server_id)).emojis)
            except Exception:
                pass
        return emojis

    # temporarily removed since emoji servers are full
    # @padglobal.command()
    # async def addemoji(self, ctx, monster_id: int, server: str = 'jp'):
    #     """Create padglobal monster emoji by id.

    #     Uses jp monster IDs by default. You only need to change to na if you want to add
    #     voltron or something.

    #     If you add a jp ID, it will look like ':pad_123:'.
    #     If you add a na ID, it will look like ':pad_na_123:'.
    #     """
    #     all_emoji_servers = self.settings.emojiServers()
    #     if not all_emoji_servers:
    #         await ctx.send('No emoji servers set')
    #         return

    #     if server not in ['na', 'jp']:
    #         await ctx.send('Server must be one of [jp, na]')
    #         return

    #     if monster_id <= 0:
    #         await ctx.send('Invalid monster id')
    #         return

    #     server_ids = self.settings.emojiServers()
    #     all_emojis = self._get_emojis()

    #     source_url = PORTRAIT_TEMPLATE.format(monster_id)
    #     emoji_name = 'pad_' + ('na_' if server == 'na' else '') + str(monster_id)

    #     for e in all_emojis:
    #         if emoji_name == e.name:
    #             await ctx.send(inline('Already exists'))
    #             return

    #     for server_id in server_ids:
    #         emoji_server = self.bot.get_guild(int(server_id))
    #         if len(emoji_server.emojis) < 50:
    #             break
    #     else:
    #         await ctx.send("There is no room.  Add a new emoji server to add more emoji.")
    #         return

    #     try:
    #         async with aiohttp.ClientSession() as sess:
    #             async with sess.get(source_url) as resp:
    #                 emoji_content = await resp.read()
    #                 await emoji_server.create_custom_emoji(name=emoji_name, image=emoji_content)
    #                 await ctx.send(inline('Done creating emoji named {}'.format(emoji_name)))
    #     except Exception as ex:
    #         await ctx.send(box('Error:\n' + str(ex)))

    @commands.Cog.listener('on_message')
    async def checkCC(self, message):
        if message.author.id == self.bot.user.id:
            return

        global_ignores = {'blacklist': []}  # self.bot.get_cog('Core').global_ignores
        if message.author.id in global_ignores["blacklist"]:
            return False

        if len(message.content) < 2:
            return

        prefix = await self.get_prefix(message)

        if not prefix:
            return

        cmd = message.content[len(prefix):]
        final_cmd = self._lookup_command(cmd)
        if final_cmd is None:
            return

        if self.settings.checkDisabled(message):
            await message.channel.send(inline(DISABLED_MSG))
            return

        if final_cmd != cmd:
            await message.channel.send(inline('Corrected to: {}'.format(final_cmd)))
        result = self.c_commands[final_cmd]
        while result in self.c_commands:
            result = self.c_commands[result]

        cmd = self.format_cc(result, message)

        for page in pagify(cmd):
            await message.channel.send(page)

    def _lookup_command(self, cmd):
        """Returns the corrected cmd name.

        Checks the raw command list, and if that fails, applies some corrections and takes
        the most likely result. Returns None if no good match.
        """
        cmdlist = self.c_commands.keys()
        if cmd in cmdlist:
            return cmd
        elif cmd.lower() in cmdlist:
            return cmd.lower()
        else:
            corrected_cmds = self._get_corrected_cmds(cmd, cmdlist)
            if corrected_cmds:
                return corrected_cmds[0]

        return None

    def _get_corrected_cmds(self, cmd, options):
        """Applies some corrections to cmd and returns the best matches in order."""
        cmd = cmd.lower()
        adjusted_cmd = [
            cmd + 's',
            cmd + '?',
            cmd + 's?',
            cmd.rstrip('?'),
            cmd.rstrip('s'),
            cmd.rstrip('s?'),
            cmd.rstrip('s?') + 's',
            cmd.rstrip('s?') + '?',
            cmd.rstrip('s?') + 's?',
        ]
        return [x for x in adjusted_cmd if x in options]

    async def get_prefix(self, message):
        for p in await self.bot.get_prefix(message):
            if message.content.startswith(p):
                return p
        return None

    def format_cc(self, command, message):
        results = re.findall(r"{([^}]+)}", command)
        for result in results:
            param = self.transform_parameter(result, message)
            command = command.replace("{" + result + "}", param)
        return self.emojify(command)

    def transform_parameter(self, result, message):
        """
        For security reasons only specific objects are allowed
        Internals are ignored
        """
        raw_result = "{" + result + "}"
        objects = {
            "message": message,
            "author": message.author,
            "channel": message.channel,
            "server": message.guild
        }
        if result in objects:
            return str(objects[result])
        try:
            first, second = result.split(".")
            if first in objects:
                return str(getattr(objects[first], second, raw_result))
        except (ValueError, KeyError):
            return raw_result

    @commands.command(aliases=["guides"])
    @commands.check(check_enabled)
    async def guide(self, ctx, *, term: str = None):
        """Shows Leader and Dungeon guide entries."""
        if term is None:
            await self.send_guide(ctx)
            return

        term, text, err = await self.get_guide_text(term, ctx)
        if text is None:
            await ctx.send(inline(err))
            return

        await ctx.send(self.emojify(text))

    async def get_guide_text(self, term: str, ctx):
        dbcog = await self.get_dbcog()

        term = term.lower()
        if term in self.settings.dungeonGuide():
            return term, self.settings.dungeonGuide()[term], None

        m = await dbcog.find_monster(term, ctx.author.id)
        if m is None:
            return None, None, 'No dungeon or monster matched that query'
        m = dbcog.database.graph.get_base_monster(m)

        name = m.name_en
        definition = self.settings.leaderGuide().get(m.monster_id, None)
        if definition is None:
            return None, None, 'A monster matched that query but has no guide'

        return name, definition, None

    async def send_guide(self, ctx):
        msg = await self.guide_to_text()
        for page in pagify(msg):
            await ctx.author.send(page)

    async def guide_to_text(self):
        msg = '__**Dungeon Guides**__'
        dungeon_guide = self.settings.dungeonGuide()
        for term in sorted(dungeon_guide.keys()):
            msg += '\n{}'.format(term)

        msg += '\n\n__**Leader Guides**__'
        for monster_id, definition in self.settings.leaderGuide().items():
            m = (await self.get_dbcog()).get_monster(monster_id)
            if m is None:
                continue
            name = m.name_en.split(', ')[-1].title()
            msg += '\n[{}] {}'.format(monster_id, name)

        return msg

    @commands.command()
    @commands.check(check_enabled)
    async def guideto(self, ctx, to_user: discord.Member, *, term: str):
        """Send a user a dungeon/leader guide entry.

        [p]guideto @{0.author.name} osc10
        """
        term, text, err = await self.get_guide_text(term, ctx)
        if text is None:
            await ctx.send(inline(err))
            return

        result_output = '**Guide for {}**\n{}'.format(term, text)
        result = "{} asked me to send you this:\n{}".format(
            ctx.author.name, result_output)
        await to_user.send(result)
        msg = "Sent guide for {} to {}".format(term, to_user.name)
        await ctx.send(inline(msg))

    @commands.group()
    @auth_check('contentadmin')
    async def pguide(self, ctx):
        """Commands related to PAD global dungeon and leader guides."""

    @pguide.group()
    async def dungeon(self, ctx):
        """Dungeon guide subcommands."""

    @dungeon.command(name='add')
    async def dungeon_add(self, ctx, term: str, *, definition: str):
        """Adds a dungeon guide to the [p]guide command"""
        await self._dungeon_add(ctx, term, definition, True)

    @dungeon.command(name='edit')
    async def dungeon_edit(self, ctx, term: str, *, definition: str):
        """Edit a dungeon guide from the [p]guide command."""
        await self._dungeon_add(ctx, term, definition, False)

    async def _dungeon_add(self, ctx, term: str, definition: str, need_confirm=True):
        term = term.lower()
        op = 'edited' if term in self.settings.dungeonGuide() else 'added'
        if op == 'edited' and need_confirm:
            if not await get_user_confirmation(ctx,
                                               "Are you sure you want to edit the dungeon guide info for {}?".format(
                                                   term)):
                return
        self.settings.addDungeonGuide(term, definition)
        await ctx.send("PAD dungeon guide successfully {}.".format(bold(op)))

    @dungeon.command(name='remove', aliases=['rm', 'delete', 'del'])
    async def dungeon_remove(self, ctx, term: str):
        """Removes a dungeon guide from the [p]guide command"""
        term = term.lower()
        if term not in self.settings.dungeonGuide():
            await ctx.send("DungeonGuide doesn't exist.")
            return
        if not await get_user_confirmation(ctx,
                                           "Are you sure you want to globally remove the dungeonguide data for {}?".format(
                                               term)):
            return
        self.settings.rmDungeonGuide(term)
        await ctx.tick()

    @pguide.group()
    async def leader(self, ctx):
        """Leader guide subcommands."""

    @leader.command(name='add')
    async def leader_add(self, ctx, monster_id: int, *, definition: str):
        """Adds a leader guide to the [p]guide command"""
        await self._leader_add(ctx, monster_id, definition, True)

    @leader.command(name='edit')
    async def leader_edit(self, ctx, monster_id: int, *, definition: str):
        """Edit a leader guide from the [p]guide command."""
        await self._leader_add(ctx, monster_id, definition, False)

    async def _leader_add(self, ctx, monster_id: int, definition: str, need_confirm=True):
        m = (await self.get_dbcog()).get_monster(monster_id)
        base_monster = (await self.get_dbcog()).database.graph.get_base_monster(m)
        if m != base_monster:
            m = base_monster
            await ctx.send("I think you meant {} for {}.".format(m.monster_no, m.name_en))
        name = m.monster_id

        op = 'edited' if name in self.settings.leaderGuide() else 'added'
        if op == 'edited' and need_confirm:
            if not await get_user_confirmation(ctx,
                                               "Are you sure you want to edit the leader guide for {}?".format(
                                                   m.name_en)):
                return
        self.settings.addLeaderGuide(name, definition)
        await ctx.send("PAD leader guide info successfully {}.".format(bold(op)))

    @leader.command(name='remove', aliases=['rm', 'delete', 'del'])
    async def leader_remove(self, ctx, monster_id: int):
        """Removes a leader guide from the [p]guide command"""
        dbcog = await self.get_dbcog()
        m = dbcog.get_monster(monster_id)
        base_monster = dbcog.database.graph.get_base_monster(m)
        if m != base_monster:
            m = base_monster
            await ctx.send("I think you meant {} for {}.".format(m.monster_no, m.name_en))
        if not await get_user_confirmation(ctx,
                                           "Are you sure you want to globally remove the leaderguide data for {}?".format(
                                               m.name_en)):
            return
        name = m.monster_id

        if name not in self.settings.leaderGuide():
            await ctx.send("LeaderGuide doesn't exist.")
            return

        self.settings.rmLeaderGuide(name)
        await ctx.tick()

    @commands.command(aliases=['currentinvade'])
    async def whichinvade(self, ctx):
        """Display which yinyangdra is currently invading for Mystics & Spectres event"""
        curtime = datetime.datetime.now(NA_TIMEZONE)
        if datetime.time(6) < curtime.time() < datetime.time(18):
            await ctx.send(self.c_commands['redinvadecurrent'])
            totime = curtime.replace(hour=18, minute=0, second=0, microsecond=0)
        else:
            await ctx.send(self.c_commands['blueinvadecurrent'])
            totime = curtime.replace(hour=6, minute=0, second=0, microsecond=0)
            if totime < curtime:
                totime += datetime.timedelta(1)
        await ctx.send(inline("Invade switches in: " + humanize_timedelta(timedelta=totime - curtime)))

    @commands.command(aliases=['resettime', 'newday', 'whenreset'])
    async def daychange(self, ctx):
        """Show DST information and how much time is left until the game day changes."""
        curtime = datetime.datetime.now(pytz.timezone("UTC"))
        reset = curtime.replace(hour=8, minute=0, second=0, microsecond=0)
        if reset < curtime:
            reset += datetime.timedelta(1)
        resetdelta = reset - curtime
        # strip leftover seconds
        resetdelta -= datetime.timedelta(seconds=resetdelta.total_seconds() % 60)
        totalresetmins = int(resetdelta.total_seconds() // 60)
        resethours = totalresetmins // 60
        newdayhours = resethours + 4
        mins = totalresetmins % 60

        pst = datetime.datetime.now(pytz.timezone("America/Los_Angeles"))
        if pst.dst():
            # earliest possible date of the first Sunday in November
            dstthresh = pst.replace(month=11, day=1)
        else:
            # earliest possible date of the second Sunday in March
            dstthresh = pst.replace(month=3, day=8)

        # calculate the day DST changes
        if dstthresh < pst:
            dstthresh = dstthresh.replace(year=(dstthresh.year + 1))
        # add days to make day of week equal 6 (Sunday, when Monday is 0)
        dstthresh += datetime.timedelta(6 - dstthresh.weekday())

        msg = "Reset (dungeons/events): **{}h {}m** ".format(resethours, mins)
        msg += "(1:00 am PDT)" if pst.dst() else "(12:00 midnight PST)"
        msg += ".\nNew day (mails): **{}h {}m** ".format(newdayhours, mins)
        msg += "(5:00 am PDT)" if pst.dst() else "(4:00 am PST)"
        msg += ".\nDST in North America is "
        msg += "ACTIVE" if pst.dst() else "NOT ACTIVE"
        msg += "! It will "
        msg += "end" if pst.dst() else "start"
        msg += " in " + humanize_timedelta(timedelta=dstthresh - pst) + "."

        await ctx.send(msg)

    async def get_dbcog(self):
        dbcog = self.bot.get_cog("DBCog")
        await dbcog.wait_until_ready()
        return dbcog

    def emojify(self, message):
        emojis = list()
        emoteservers = self.settings.emojiServers()
        for guild in emoteservers:
            if self.bot.get_guild(int(guild)):
                emojis.extend(self.bot.get_guild(int(guild)).emojis)
        for guild in self.bot.guilds:
            if guild.id in emoteservers:
                continue
            emojis.extend(guild.emojis)
        message = replace_emoji_names_with_code(emojis, message)
        return fix_emojis_for_server(emojis, message)


def check_simple_tree(monster, db_context):
    attr1 = monster.attr1
    active_skill = monster.active_skill
    for m in (evo_tree := db_context.graph.get_evo_tree(monster)):
        if m.attr1 != attr1 or m.active_skill.active_skill_id != active_skill.active_skill_id:
            return False
        if m.is_equip:
            return False
        if len(db_context.graph.get_next_evolutions(m)) > 1:
            return False
    # every evo has super awakenings (can limit break)
    if len(evo_tree) > 1 and all(m.superawakening_count for m in evo_tree):
        return False
    return True


class PadGlobalSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'admins': [],
            'faq': [],
            'boards': [],
            'glossary': {},
            'which': {},
            'boss': {},
            'disabled_servers': [],
            'dungeon_guide': {},
            'leader_guide': {},
            'emoji_servers': [],
        }
        return config

    def admins(self):
        return self.bot_settings['admins']

    def checkAdmin(self, user_id):
        admins = self.admins()
        return user_id in admins

    def addAdmin(self, user_id):
        admins = self.admins()
        if user_id not in admins:
            admins.append(user_id)
            self.save_settings()

    def rmAdmin(self, user_id):
        admins = self.admins()
        if user_id in admins:
            admins.remove(user_id)
            self.save_settings()

    def faq(self):
        return self.bot_settings['faq']

    def boards(self):
        return self.bot_settings['boards']

    def clearCmd(self, cmd):
        if cmd in self.faq():
            self.faq().remove(cmd)
        if cmd in self.boards():
            self.boards().remove(cmd)

    def setGeneral(self, cmd):
        self.clearCmd(cmd)
        self.save_settings()

    def setFaq(self, cmd):
        self.clearCmd(cmd)
        self.faq().append(cmd)
        self.save_settings()

    def setBoards(self, cmd):
        self.clearCmd(cmd)
        self.boards().append(cmd)
        self.save_settings()

    def glossary(self):
        return self.bot_settings['glossary']

    def addGlossary(self, term, definition):
        self.glossary()[term] = definition
        self.save_settings()

    def rmGlossary(self, term):
        glossary = self.glossary()
        if term in glossary:
            glossary.pop(term)
            self.save_settings()

    def boss(self):
        return self.bot_settings['boss']

    def addBoss(self, term, definition):
        self.boss()[term] = definition
        self.save_settings()

    def rmBoss(self, term):
        boss = self.boss()
        if term in boss:
            boss.pop(term)
            self.save_settings()

    def which(self):
        return self.bot_settings['which']

    def addWhich(self, name, text):
        self.which()[name] = [text, datetime.date.today().isoformat()]
        self.save_settings()

    def rmWhich(self, name):
        which = self.which()
        if name in which:
            which.pop(name)
            self.save_settings()

    def emojiServers(self):
        return self.bot_settings['emoji_servers']

    def setEmojiServers(self, emoji_servers):
        es = self.emojiServers()
        es.clear()
        es.extend(emoji_servers)
        self.save_settings()

    def leaderGuide(self):
        return self.bot_settings['leader_guide']

    def addLeaderGuide(self, name, text):
        self.leaderGuide()[name] = text
        self.save_settings()

    def rmLeaderGuide(self, name):
        options = self.leaderGuide()
        if name in options:
            options.pop(name)
            self.save_settings()

    def dungeonGuide(self):
        return self.bot_settings['dungeon_guide']

    def addDungeonGuide(self, name, text):
        self.dungeonGuide()[name] = text
        self.save_settings()

    def rmDungeonGuide(self, name):
        options = self.dungeonGuide()
        if name in options:
            options.pop(name)
            self.save_settings()

    def disabledServers(self):
        return self.bot_settings['disabled_servers']

    def checkDisabled(self, msg):
        if msg.guild is None:
            return False
        return msg.guild.id in self.disabledServers()

    def addDisabledServer(self, server_id):
        disabled_servers = self.disabledServers()
        if server_id not in disabled_servers:
            disabled_servers.append(server_id)
            self.save_settings()

    def rmDisabledServer(self, server_id):
        disabled_servers = self.disabledServers()
        if server_id in disabled_servers:
            disabled_servers.remove(server_id)
            self.save_settings()
