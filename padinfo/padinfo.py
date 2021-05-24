import asyncio
import logging
import os
import random
import re
import urllib.parse
from io import BytesIO
from typing import TYPE_CHECKING, List

import discord
import tsutils
from discord import Color
from discordmenu.emoji.emoji_cache import emoji_cache
from redbot.core import checks, commands, data_manager, Config
from redbot.core.utils.chat_formatting import box, inline, bold, pagify, text_to_file
from tabulate import tabulate
from tsutils import char_to_emoji, is_donor, safe_read_json

from padinfo.common.config import BotConfig
from padinfo.common.emoji_map import get_attribute_emoji_by_enum, get_awakening_emoji, get_type_emoji, \
    get_attribute_emoji_by_monster, AWAKENING_ID_TO_EMOJI_NAME_MAP
from padinfo.core.button_info import button_info
from padinfo.core.leader_skills import perform_leaderskill_query
from padinfo.core.padinfo_settings import settings
from padinfo.core.transforminfo import perform_transforminfo_query
from padinfo.menu.awakening_list import AwakeningListMenu, AwakeningListMenuPanes
from padinfo.menu.closable_embed import ClosableEmbedMenu
from padinfo.menu.id import IdMenu, IdMenuPanes
from padinfo.menu.leader_skill import LeaderSkillMenu
from padinfo.menu.leader_skill_single import LeaderSkillSingleMenu
from padinfo.menu.menu_map import padinfo_menu_map
from padinfo.menu.monster_list import MonsterListMenu, MonsterListMenuPanes, MonsterListEmoji
from padinfo.menu.series_scroll import SeriesScrollMenuPanes, SeriesScrollMenu, SeriesScrollEmoji
from padinfo.menu.simple_text import SimpleTextMenu
from padinfo.menu.transforminfo import TransformInfoMenu, TransformInfoMenuPanes
from padinfo.reaction_list import get_id_menu_initial_reaction_list
from padinfo.view.awakening_help import AwakeningHelpView, AwakeningHelpViewProps
from padinfo.view.awakening_list import AwakeningListViewState, AwakeningListSortTypes
from padinfo.view.closable_embed import ClosableEmbedViewState
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.evos import EvosViewState
from padinfo.view.id import IdViewState
from padinfo.view.id_traceback import IdTracebackView, IdTracebackViewProps
from padinfo.view.leader_skill import LeaderSkillViewState
from padinfo.view.leader_skill_single import LeaderSkillSingleViewState
from padinfo.view.links import LinksView
from padinfo.view.lookup import LookupView
from padinfo.view.materials import MaterialsViewState
from padinfo.view.monster_list import MonsterListViewState
from padinfo.view.otherinfo import OtherInfoViewState
from padinfo.view.pantheon import PantheonViewState
from padinfo.view.pic import PicViewState
from padinfo.view.series_scroll import SeriesScrollViewState
from padinfo.view.simple_text import SimpleTextViewState
from padinfo.view.transforminfo import TransformInfoViewState

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel
    from dadguide.models.series_model import SeriesModel

logger = logging.getLogger('red.padbot-cogs.padinfo')

EMBED_NOT_GENERATED = -1

IDGUIDE = "https://github.com/TsubakiBotPad/pad-cogs/wiki/id-user-guide"

HISTORY_DURATION = 11


def _data_file(file_name: str) -> str:
    return os.path.join(str(data_manager.cog_data_path(raw_name='padinfo')), file_name)


COLORS = {
    **{c: getattr(discord.Colour, c)().value for c in discord.Colour.__dict__ if
       isinstance(discord.Colour.__dict__[c], classmethod) and
       discord.Colour.__dict__[c].__func__.__code__.co_argcount == 1 and
       isinstance(getattr(discord.Colour, c)(), discord.Colour)},
    'pink': 0xffa1dd,

    # Special
    'random': 'random',
    'clear': 0,
}


class PadInfo(commands.Cog):
    """Info for PAD Cards"""

    menu_map = padinfo_menu_map

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        # These emojis are the keys into the idmenu submenus
        self.ls_emoji = '\N{HOUSE BUILDING}'
        self.left_emoji = char_to_emoji('l')
        self.right_emoji = char_to_emoji('r')
        self.remove_emoji = '\N{CROSS MARK}'

        self.config = Config.get_conf(self, identifier=9401770)
        self.config.register_user(survey_mode=0, color=None, beta_id3=False, id_history=[])
        self.config.register_global(sometimes_perc=20, good=0, bad=0, bad_queries=[], do_survey=False)

        self.historic_lookups = safe_read_json(_data_file('historic_lookups_id3.json'))

        self.id_menu = IdMenu  # TODO: Support multi-menus for real
        self.awoken_emoji_names = {v: k for k, v in AWAKENING_ID_TO_EMOJI_NAME_MAP.items()}
        self.get_attribute_emoji_by_monster = get_attribute_emoji_by_monster
        self.settings = settings

    def cog_unload(self):
        """Manually nulling out database because the GC for cogs seems to be pretty shitty"""

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

    async def reload_nicknames(self):
        await self.bot.wait_until_ready()
        while self == self.bot.get_cog('PadInfo'):
            wait_time = 60 * 60 * 1
            try:
                emoji_cache.set_guild_ids([g.id for g in self.bot.guilds])
                emoji_cache.refresh_from_discord_bot(self.bot)
                dgcog = self.bot.get_cog('Dadguide')
                await dgcog.wait_until_ready()
            except Exception as ex:
                wait_time = 5
                logger.exception("reload padinfo loop caught exception " + str(ex))

            await asyncio.sleep(wait_time)

    async def get_dgcog(self):
        dgcog = self.bot.get_cog("Dadguide")
        if dgcog is None:
            raise ValueError("Dadguide cog is not loaded")
        await dgcog.wait_until_ready()
        return dgcog

    async def get_menu_default_data(self, ims):
        data = {
            'dgcog': await self.get_dgcog(),
            'user_config': await BotConfig.get_user(self.config, ims['original_author_id'])
        }
        return data

    def get_monster(self, monster_id: int):
        dgcog = self.bot.get_cog('Dadguide')
        return dgcog.get_monster(monster_id)

    @commands.command()
    async def jpname(self, ctx, *, query: str):
        """Show the Japanese name of a monster"""
        dgcog = await self.get_dgcog()
        monster = await dgcog.find_monster(query, ctx.author.id)
        if monster is not None:
            await ctx.send(MonsterHeader.short(monster))
            await ctx.send(box(monster.name_ja))
        else:
            await self.send_id_failure_message(ctx, query)

    @commands.command(name="id")
    @checks.bot_has_permissions(embed_links=True)
    async def _id(self, ctx, *, query: str):
        """Monster info (main tab)"""
        await self._do_id(ctx, query)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def idna(self, ctx, *, query: str):
        """Monster info (limited to NA monsters ONLY)"""
        await self._do_id(ctx, "inna " + query)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def idjp(self, ctx, *, query: str):
        """Monster info (limited to JP monsters ONLY)"""
        await self._do_id(ctx, "injp " + query)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def id3(self, ctx, *, query: str):
        """Monster info (main tab)"""
        await self._do_id(ctx, query)

    async def _do_id(self, ctx, query: str):
        dgcog = await self.get_dgcog()
        raw_query = query
        color = await self.get_user_embed_color(ctx)
        original_author_id = ctx.message.author.id

        goodquery = None
        if query[0] in dgcog.token_maps.ID1_SUPPORTED and query[1:] in dgcog.index.all_name_tokens:
            goodquery = [query[0], query[1:]]
        elif query[:2] in dgcog.token_maps.ID1_SUPPORTED and query[2:] in dgcog.index.all_name_tokens:
            goodquery = [query[:2], query[2:]]

        if goodquery:
            bad = False
            for monster in dgcog.index.all_name_tokens[goodquery[1]]:
                for modifier in dgcog.index.modifiers[monster]:
                    if modifier == 'xm' and goodquery[0] == 'x':
                        goodquery[0] = 'xm'
                    if modifier == goodquery[0]:
                        bad = True
            if bad and query not in dgcog.index.all_name_tokens:
                async def send_message():
                    await asyncio.sleep(1)
                    await ctx.send(f"Uh oh, it looks like you tried a query that isn't supported anymore!"
                                   f" Try using `{' '.join(goodquery)}` (with a space) instead! For more"
                                   f" info about the new id changes, check out"
                                   f" <{IDGUIDE}>!")

                asyncio.create_task(send_message())
                async with self.config.bad_queries() as bad_queries:
                    bad_queries.append((raw_query, ctx.author.id))

        monster = await dgcog.find_monster(raw_query, ctx.author.id)

        if not monster:
            await self.send_id_failure_message(ctx, query)
            return

        await self.log_id_result(ctx, monster.monster_id)

        # id3 messaging stuff
        if monster and monster.monster_no_na != monster.monster_no_jp:
            await ctx.send("The NA ID and JP ID of this card differ! "
                           "The JP ID is 1053 you can query with {0.prefix}id jp1053.".format(ctx) +
                           (" Make sure you use the **JP id number** when updating the Google doc!!!!!" if
                            ctx.author.id in self.bot.get_cog("PadGlobal").settings.bot_settings['admins'] else ""))

        if await self.config.do_survey():
            asyncio.create_task(self.send_survey_after(ctx, query, monster))

        alt_monsters = IdViewState.get_alt_monsters_and_evos(dgcog, monster)
        transform_base, true_evo_type_raw, acquire_raw, base_rarity = \
            await IdViewState.query(dgcog, monster)
        full_reaction_list = [emoji_cache.get_by_name(e) for e in IdMenuPanes.emoji_names()]
        initial_reaction_list = await get_id_menu_initial_reaction_list(ctx, dgcog, monster, full_reaction_list)

        state = IdViewState(original_author_id, IdMenu.MENU_TYPE, raw_query, query, color, monster, alt_monsters,
                            transform_base, true_evo_type_raw, acquire_raw, base_rarity,
                            use_evo_scroll=settings.checkEvoID(ctx.author.id), reaction_list=initial_reaction_list)
        menu = IdMenu.menu()
        await menu.create(ctx, state)

    async def send_survey_after(self, ctx, query, result_monster):
        dgcog = await self.get_dgcog()
        survey_mode = await self.config.user(ctx.author).survey_mode()
        survey_chance = (1, await self.config.sometimes_perc() / 100, 0)[survey_mode]
        if random.random() < survey_chance:
            mid1 = self.historic_lookups.get(query)
            m1 = mid1 and dgcog.get_monster(mid1)
            id1res = "Not Historic" if mid1 is None else f"{m1.name_en} ({m1.monster_id})" if mid1 > 0 else "None"
            id3res = f"{result_monster.name_en} ({result_monster.monster_id})" if result_monster else "None"
            params = urllib.parse.urlencode(
                {'usp': 'pp_url',
                 'entry.154088017': query,
                 'entry.173096863': id3res,
                 'entry.1016180044': id1res,
                 'entry.1787446565': str(ctx.author)})
            url = "https://docs.google.com/forms/d/e/1FAIpQLSeA2EBYiZTOYfGLNtTHqYdL6gMZrfurFZonZ5dRQa3XPHP9yw/viewform?" + params
            await asyncio.sleep(1)
            userres = await tsutils.confirm_message(ctx, "Was this the monster you were looking for?",
                                                    yemoji=char_to_emoji('y'), nemoji=char_to_emoji('n'))
            if userres is True:
                await self.config.good.set(await self.config.good() + 1)
            elif userres is False:
                await self.config.bad.set(await self.config.bad() + 1)
                message = await ctx.send(f"Oh no!  You can help the Tsubaki team give better results"
                                         f" by filling out this survey!\nPRO TIP: Use `{ctx.prefix}idset"
                                         f" survey` to adjust how often this shows.\n\n<{url}>")
                await asyncio.sleep(15)
                await message.delete()

    @commands.group()
    async def idsurvey(self, ctx):
        """Commands pertaining to the id survey"""

    @idsurvey.command()
    async def dosurvey(self, ctx, do_survey: bool):
        """Toggle the survey avalibility"""
        await self.config.do_survey.set(do_survey)
        await ctx.tick()

    @idsurvey.command()
    async def sometimesperc(self, ctx, percent: int):
        """Change what 'sometimes' means"""
        await self.config.sometimes_perc.set(percent)
        await ctx.tick()

    @idsurvey.command()
    async def checkbadness(self, ctx):
        """Check how good id is according to end users"""
        good = await self.config.good()
        bad = await self.config.bad()
        await ctx.send(f"{bad}/{good + bad} ({int(round(bad / (good + bad) * 100)) if good or bad else 'NaN'}%)")

    @commands.command()
    @checks.bot_has_permissions()
    async def id2(self, ctx):
        """Monster info (main tab)"""
        await ctx.send("id2 has been discontinued!".format(ctx.prefix))

    @commands.command(name="evos")
    @checks.bot_has_permissions(embed_links=True)
    async def evos(self, ctx, *, query: str):
        """Monster info (evolutions tab)"""
        dgcog = await self.get_dgcog()
        raw_query = query
        color = await self.get_user_embed_color(ctx)
        original_author_id = ctx.message.author.id

        monster = await dgcog.find_monster(raw_query, ctx.author.id)

        if monster is None:
            await self.send_id_failure_message(ctx, query)
            return

        await self.log_id_result(ctx, monster.monster_id)

        alt_monsters = EvosViewState.get_alt_monsters_and_evos(dgcog, monster)
        alt_versions, gem_versions = await EvosViewState.query(dgcog, monster)

        if alt_versions is None:
            await ctx.send('Your query `{}` found [{}] {}, '.format(query, monster.monster_id,
                                                                    monster.name_en) + 'which has no alt evos or gems.')
            return

        full_reaction_list = [emoji_cache.get_by_name(e) for e in IdMenuPanes.emoji_names()]
        initial_reaction_list = await get_id_menu_initial_reaction_list(ctx, dgcog, monster, full_reaction_list)

        state = EvosViewState(original_author_id, IdMenu.MENU_TYPE, raw_query, query, color,
                              monster, alt_monsters, alt_versions, gem_versions,
                              reaction_list=initial_reaction_list,
                              use_evo_scroll=settings.checkEvoID(ctx.author.id))
        menu = IdMenu.menu(initial_control=IdMenu.evos_control)
        await menu.create(ctx, state)

    @commands.command(name="mats", aliases=['evomats', 'evomat', 'skillups'])
    @checks.bot_has_permissions(embed_links=True)
    async def evomats(self, ctx, *, query: str):
        """Monster info (evo materials tab)"""
        dgcog = await self.get_dgcog()
        raw_query = query
        color = await self.get_user_embed_color(ctx)
        original_author_id = ctx.message.author.id
        monster = await dgcog.find_monster(raw_query, ctx.author.id)

        if not monster:
            await self.send_id_failure_message(ctx, query)
            return

        await self.log_id_result(ctx, monster.monster_id)

        mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link, gem_override = \
            await MaterialsViewState.query(dgcog, monster)

        if mats is None:
            await ctx.send(inline("This monster has no mats or skillups and isn't used in any evolutions"))
            return

        alt_monsters = MaterialsViewState.get_alt_monsters_and_evos(dgcog, monster)
        full_reaction_list = [emoji_cache.get_by_name(e) for e in IdMenuPanes.emoji_names()]
        initial_reaction_list = await get_id_menu_initial_reaction_list(ctx, dgcog, monster, full_reaction_list)

        state = MaterialsViewState(original_author_id, IdMenu.MENU_TYPE, raw_query, query, color, monster, alt_monsters,
                                   mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link, gem_override,
                                   reaction_list=initial_reaction_list,
                                   use_evo_scroll=settings.checkEvoID(ctx.author.id))
        menu = IdMenu.menu(initial_control=IdMenu.mats_control)
        await menu.create(ctx, state)

    @commands.command(aliases=["series", "panth"])
    @checks.bot_has_permissions(embed_links=True)
    async def pantheon(self, ctx, *, query: str):
        """Monster info (pantheon tab)"""
        dgcog = await self.get_dgcog()
        raw_query = query
        color = await self.get_user_embed_color(ctx)
        original_author_id = ctx.message.author.id

        monster = await dgcog.find_monster(raw_query, ctx.author.id)

        if monster is None:
            await self.send_id_failure_message(ctx, query)
            return

        await self.log_id_result(ctx, monster.monster_id)

        pantheon_list, series_name, base_monster = await PantheonViewState.query(dgcog, monster)
        if pantheon_list is None:
            await ctx.send('Unable to find a pantheon for the result of your query,'
                           + ' [{}] {}.'.format(monster.monster_id, monster.name_en))
            return
        alt_monsters = PantheonViewState.get_alt_monsters_and_evos(dgcog, monster)
        full_reaction_list = [emoji_cache.get_by_name(e) for e in IdMenuPanes.emoji_names()]
        initial_reaction_list = await get_id_menu_initial_reaction_list(ctx, dgcog, monster, full_reaction_list)

        state = PantheonViewState(original_author_id, IdMenu.MENU_TYPE, raw_query, query, color,
                                  monster, alt_monsters, pantheon_list, series_name, base_monster,
                                  reaction_list=initial_reaction_list,
                                  use_evo_scroll=settings.checkEvoID(ctx.author.id))
        menu = IdMenu.menu(initial_control=IdMenu.pantheon_control)
        await menu.create(ctx, state)

    @commands.command(aliases=['img'])
    @checks.bot_has_permissions(embed_links=True)
    async def pic(self, ctx, *, query: str):
        """Monster info (full image tab)"""
        dgcog = await self.get_dgcog()
        raw_query = query
        color = await self.get_user_embed_color(ctx)
        original_author_id = ctx.message.author.id

        monster = await dgcog.find_monster(raw_query, ctx.author.id)

        if monster is None:
            await self.send_id_failure_message(ctx, query)
            return

        await self.log_id_result(ctx, monster.monster_id)

        alt_monsters = PicViewState.get_alt_monsters_and_evos(dgcog, monster)
        full_reaction_list = [emoji_cache.get_by_name(e) for e in IdMenuPanes.emoji_names()]
        initial_reaction_list = await get_id_menu_initial_reaction_list(ctx, dgcog, monster, full_reaction_list)

        state = PicViewState(original_author_id, IdMenu.MENU_TYPE, raw_query, query, color,
                             monster, alt_monsters,
                             reaction_list=initial_reaction_list,
                             use_evo_scroll=settings.checkEvoID(ctx.author.id))
        menu = IdMenu.menu(initial_control=IdMenu.pic_control)
        await menu.create(ctx, state)

    @commands.command(aliases=['stats'])
    @checks.bot_has_permissions(embed_links=True)
    async def otherinfo(self, ctx, *, query: str):
        """Monster info (misc info tab)"""
        dgcog = await self.get_dgcog()
        raw_query = query
        color = await self.get_user_embed_color(ctx)
        original_author_id = ctx.message.author.id

        monster = await dgcog.find_monster(raw_query, ctx.author.id)

        if monster is None:
            await self.send_id_failure_message(ctx, query)
            return

        await self.log_id_result(ctx, monster.monster_id)

        alt_monsters = PicViewState.get_alt_monsters_and_evos(dgcog, monster)
        full_reaction_list = [emoji_cache.get_by_name(e) for e in IdMenuPanes.emoji_names()]
        initial_reaction_list = await get_id_menu_initial_reaction_list(ctx, dgcog, monster, full_reaction_list)

        state = OtherInfoViewState(original_author_id, IdMenu.MENU_TYPE, raw_query, query, color,
                                   monster, alt_monsters,
                                   reaction_list=initial_reaction_list,
                                   use_evo_scroll=settings.checkEvoID(ctx.author.id))
        menu = IdMenu.menu(initial_control=IdMenu.otherinfo_control)
        await menu.create(ctx, state)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def links(self, ctx, *, query: str):
        """Monster links"""
        dgcog = await self.get_dgcog()
        monster = await dgcog.find_monster(query, ctx.author.id)
        if monster is None:
            await self.send_id_failure_message(ctx, query)
            return
        await self.log_id_result(ctx, monster.monster_id)
        color = await self.get_user_embed_color(ctx)
        embed = LinksView.embed(monster, color).to_embed()
        await ctx.send(embed=embed)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def lookup(self, ctx, *, query: str):
        """Short info results for a monster query"""
        dgcog = await self.get_dgcog()
        monster = await dgcog.find_monster(query, ctx.author.id)
        if monster is None:
            await self.send_id_failure_message(ctx, query)
            return
        await self.log_id_result(ctx, monster.monster_id)
        color = await self.get_user_embed_color(ctx)
        embed = LookupView.embed(monster, color).to_embed()
        await ctx.send(embed=embed)

    async def log_id_result(self, ctx, monster_id: int):
        history = await self.config.user(ctx.author).id_history()
        if monster_id in history:
            history.remove(monster_id)
        history.insert(0, monster_id)
        if len(history) > HISTORY_DURATION:
            history.pop()
        await self.config.user(ctx.author).id_history.set(history)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def buttoninfo(self, ctx, *, query: str):
        """Button farming theorycrafting info"""
        dgcog = await self.get_dgcog()
        monster = await dgcog.find_monster(query, ctx.author.id)
        if monster is None:
            await self.send_id_failure_message(ctx, query)
            return
        DGCOG = self.bot.get_cog("Dadguide")
        info = button_info.get_info(DGCOG, monster)
        info_str = button_info.to_string(DGCOG, monster, info)
        for page in pagify(info_str):
            await ctx.send(box(page))

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def allmats(self, ctx, *, query: str):
        """Monster info (evo materials tab)"""
        dgcog = await self.get_dgcog()
        raw_query = query
        monster = await dgcog.find_monster(raw_query, ctx.author.id)

        if not monster:
            await self.send_id_failure_message(ctx, query)
            return

        await self.log_id_result(ctx, monster.monster_id)

        _, usedin, _, gemusedin, _, _, _, _ = \
            await MaterialsViewState.query(dgcog, monster)

        if usedin is None and gemusedin is None:
            await ctx.send(inline("This monster is not a mat for anything nor does it have a gem"))
            return

        monster_list = usedin or gemusedin
        title = 'Material For' if usedin else 'Gem is Material For'
        await self._do_monster_list(ctx, dgcog, query, monster_list, title)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def evolist(self, ctx, *, query):
        dgcog = await self.get_dgcog()
        monster = await dgcog.find_monster(query, ctx.author.id)

        if monster is None:
            await self.send_id_failure_message(ctx, query)
            return

        alt_versions, _ = await EvosViewState.query(dgcog, monster)
        if alt_versions is None:
            await ctx.send('Your query `{}` found [{}] {}, '.format(query, monster.monster_id,
                                                                    monster.name_en) + 'which has no alt evos.')
            return
        await self._do_monster_list(ctx, dgcog, query, alt_versions, 'Evolution List')

    async def _do_monster_list(self, ctx, dgcog, query, monster_list: List["MonsterModel"], title):
        raw_query = query
        original_author_id = ctx.message.author.id
        color = await self.get_user_embed_color(ctx)
        initial_reaction_list = MonsterListMenuPanes.get_initial_reaction_list(len(monster_list))
        instruction_message = 'Click a reaction to see monster details!'

        subtitle = None
        if len(monster_list) > MonsterListViewState.MAX_INTERNAL_STORE_SIZE:
            subtitle = 'List has been truncated to first {} items'.format(MonsterListViewState.MAX_INTERNAL_STORE_SIZE)
        monster_list = monster_list[:MonsterListViewState.MAX_INTERNAL_STORE_SIZE]
        paginated_monsters = MonsterListViewState.paginate(monster_list)
        state = MonsterListViewState(original_author_id, MonsterListMenu.MENU_TYPE, raw_query, query, color,
                                     paginated_monsters, len(paginated_monsters), 0,
                                     title, instruction_message,
                                     subtitle,
                                     reaction_list=initial_reaction_list
                                     )
        parent_menu = MonsterListMenu.menu()
        message = await ctx.send('Setting up!')

        ims = state.serialize()
        user_config = await BotConfig.get_user(self.config, ctx.author.id)
        data = {
            'dgcog': dgcog,
            'user_config': user_config,
        }
        child_state = SimpleTextViewState(original_author_id, MonsterListMenu.MENU_TYPE, raw_query, color,
                                          instruction_message,
                                          reaction_list=[]
                                          )
        child_menu = SimpleTextMenu.menu()
        child_message = await child_menu.create(ctx, child_state)

        data['child_message_id'] = child_message.id
        try:
            await parent_menu.transition(message, ims, MonsterListEmoji.refresh, ctx.author, **data)
            await message.edit(content=None)
        except discord.errors.NotFound:
            # The user could delete the menu before we can do this
            pass

    @commands.command(aliases=['seriesscroll', 'ss'])
    @checks.bot_has_permissions(embed_links=True)
    async def collabscroll(self, ctx, *, query):
        dgcog = await self.get_dgcog()
        monster = await dgcog.find_monster(query, ctx.author.id)

        if monster is None:
            await self.send_id_failure_message(ctx, query)
            return
        series_id = monster.series_id
        series_object: "SeriesModel" = monster.series
        title = series_object.name_en
        paginated_monsters = None
        rarity = None
        for rarity in SeriesScrollMenu.RARITY_INITIAL_TRY_ORDER:
            paginated_monsters = SeriesScrollViewState.query(dgcog, monster.series_id, rarity)
            if paginated_monsters:
                break
        all_rarities = SeriesScrollViewState.query_all_rarities(dgcog, series_id)

        raw_query = query
        original_author_id = ctx.message.author.id
        color = await self.get_user_embed_color(ctx)
        initial_reaction_list = SeriesScrollMenuPanes.get_initial_reaction_list(len(paginated_monsters))
        instruction_message = 'Click a reaction to see monster details!'

        state = SeriesScrollViewState(original_author_id, SeriesScrollMenu.MENU_TYPE, raw_query, query, color,
                                      series_id, 0, paginated_monsters[0], int(rarity), len(paginated_monsters),
                                      all_rarities,
                                      title, instruction_message,
                                      reaction_list=initial_reaction_list)
        parent_menu = SeriesScrollMenu.menu()
        message = await ctx.send('Setting up!')

        ims = state.serialize()
        user_config = await BotConfig.get_user(self.config, ctx.author.id)
        data = {
            'dgcog': dgcog,
            'user_config': user_config,
        }
        child_state = SimpleTextViewState(original_author_id, SeriesScrollMenu.MENU_TYPE, raw_query, color,
                                          instruction_message,
                                          reaction_list=[]
                                          )
        child_menu = SimpleTextMenu.menu()
        child_message = await child_menu.create(ctx, child_state)

        data['child_message_id'] = child_message.id
        try:
            await parent_menu.transition(message, ims, SeriesScrollEmoji.refresh, ctx.author, **data)
            await message.edit(content=None)
        except discord.errors.NotFound:
            # The user could delete the menu before we can do this
            pass

    @commands.command(aliases=['leaders', 'leaderskills', 'ls'], usage="<card_1> [card_2]")
    @checks.bot_has_permissions(embed_links=True)
    async def leaderskill(self, ctx, *, raw_query):
        """Display the multiplier and leaderskills for two monsters

        Gets two monsters separated by a slash, wrapping quotes, a comma,
        or spaces (if there's only two words).
        [p]ls r sonia/ revo lu bu
        [p]ls r sonia "revo lu bu"
        [p]ls sonia lubu
        """
        dgcog = await self.get_dgcog()
        l_mon, l_query, r_mon, r_query = await perform_leaderskill_query(dgcog, raw_query, ctx.author.id)

        err_msg = ('{} query failed to match a monster: [ {} ]. If your query is multiple words,'
                   ' try separating the queries with / or wrap with quotes.')
        if l_mon is None:
            await ctx.send(inline(err_msg.format('Left', l_query)))
            return
        if r_mon is None:
            await ctx.send(inline(err_msg.format('Right', r_query)))
            return

        color = await self.get_user_embed_color(ctx)
        original_author_id = ctx.message.author.id
        state = LeaderSkillViewState(original_author_id, LeaderSkillMenu.MENU_TYPE, raw_query, color, l_mon, r_mon,
                                     l_query, r_query)
        menu = LeaderSkillMenu.menu()
        await menu.create(ctx, state)

    async def get_user_embed_color(self, ctx):
        color = await self.config.user(ctx.author).color()
        return self.user_color_to_discord_color(color)

    @staticmethod
    def user_color_to_discord_color(color):
        if color is None:
            return Color.default()
        elif color == "random":
            return Color(random.randint(0x000000, 0xffffff))
        else:
            return discord.Color(color)

    async def get_user_friends(self, original_author_id):
        friend_cog = self.bot.get_cog("Friend")
        friends = (await friend_cog.get_friends(original_author_id)) if friend_cog else []
        return friends

    @commands.command(aliases=['lssingle'])
    @checks.bot_has_permissions(embed_links=True)
    async def leaderskillsingle(self, ctx, *, query):
        dgcog = await self.get_dgcog()
        monster = await dgcog.find_monster(query, ctx.author.id)
        if not monster:
            await self.send_id_failure_message(ctx, query)
            return

        color = await self.get_user_embed_color(ctx)
        original_author_id = ctx.message.author.id
        state = LeaderSkillSingleViewState(original_author_id, LeaderSkillSingleMenu.MENU_TYPE, query, color, monster)
        menu = LeaderSkillSingleMenu.menu()
        await menu.create(ctx, state)

    @commands.command(aliases=['tfinfo', 'xforminfo'])
    @checks.bot_has_permissions(embed_links=True)
    async def transforminfo(self, ctx, *, query):
        """Show info about a transform card, including some helpful details about the base card."""
        dgcog = await self.get_dgcog()
        base_mon, transformed_mon, monster_ids = await perform_transforminfo_query(dgcog, query, ctx.author.id)

        if not base_mon:
            await self.send_id_failure_message(ctx, query)
            return

        if not transformed_mon:
            await ctx.send('Your query `{}` '.format(query)
                           + 'found [{}] {}, '.format(base_mon.monster_id, base_mon.name_en)
                           + 'which has no evos that transform.')
            return

        color = await self.get_user_embed_color(ctx)
        original_author_id = ctx.message.author.id
        acquire_raw = await TransformInfoViewState.query(dgcog, base_mon, transformed_mon)
        reaction_list = TransformInfoMenuPanes.get_reaction_list(len(monster_ids))

        state = TransformInfoViewState(original_author_id, TransformInfoMenu.MENU_TYPE, query,
                                       color, base_mon, transformed_mon, acquire_raw, monster_ids,
                                       reaction_list=reaction_list)
        menu = TransformInfoMenu.menu()
        await menu.create(ctx, state)

    @commands.command(aliases=['awakehelp', 'awakeningshelp', 'awohelp', 'awokenhelp', 'awakeninghelp'])
    @checks.bot_has_permissions(embed_links=True)
    async def awakenings(self, ctx, *, query=None):
        """Describe a monster's regular and super awakenings in detail.

        Leave <query> blank to see a list of every awakening in the game."""
        dgcog = await self.get_dgcog()
        color = await self.get_user_embed_color(ctx)

        if not query:
            sort_type = AwakeningListSortTypes.numerical
            paginated_skills = await AwakeningListViewState.query(dgcog, sort_type)
            menu = AwakeningListMenu.menu()
            state = AwakeningListViewState(ctx.message.author.id, AwakeningListMenu.MENU_TYPE, color,
                                           sort_type, paginated_skills, 0,
                                           reaction_list=AwakeningListMenuPanes.get_reaction_list(sort_type))
            await menu.create(ctx, state)
            return

        monster = await dgcog.find_monster(query, ctx.author.id)

        if not monster:
            await self.send_id_failure_message(ctx, query)
            return

        original_author_id = ctx.message.author.id
        menu = ClosableEmbedMenu.menu()
        props = AwakeningHelpViewProps(monster=monster)
        state = ClosableEmbedViewState(original_author_id, ClosableEmbedMenu.MENU_TYPE, query,
                                       color, AwakeningHelpView.VIEW_TYPE, props)
        await menu.create(ctx, state)

    @commands.command(aliases=['idhist'])
    @checks.bot_has_permissions(embed_links=True)
    async def idhistory(self, ctx):
        """Show a list of the 11 most recent monsters that the user looked up."""
        dgcog = await self.get_dgcog()
        history = await self.config.user(ctx.author).id_history()

        monsters = [dgcog.get_monster(m) for m in history]

        if not monsters:
            await ctx.send('Did not find any recent queries in history.')
            return

        await self._do_monster_list(ctx, dgcog, '', monsters, 'Result History')

    @commands.command()
    async def padsay(self, ctx, server, *, query: str = None):
        """Speak the voice line of a monster into your current chat"""
        voice = ctx.author.voice
        if not voice:
            await ctx.send(inline('You must be in a voice channel to use this command'))
            return
        channel = voice.channel

        speech_cog = self.bot.get_cog('Speech')
        if not speech_cog:
            await ctx.send(inline('Speech seems to be offline'))
            return

        if server.lower() not in ['na', 'jp']:
            query = server + ' ' + (query or '')
            server = 'na'
        query = query.strip().lower()

        dgcog = await self.get_dgcog()
        monster = await dgcog.find_monster(query, ctx.author.id)
        if monster is not None:
            voice_id = monster.voice_id_jp if server == 'jp' else monster.voice_id_na
            if voice_id is None:
                await ctx.send(inline("No voice file found for " + monster.name_en))
                return
            base_dir = settings.voiceDir()
            voice_file = os.path.join(base_dir, server, '{0:03d}.wav'.format(voice_id))
            header = '{} ({})'.format(MonsterHeader.short(monster), server)
            if not os.path.exists(voice_file):
                await ctx.send(inline('Could not find voice for ' + header))
                return
            await ctx.send('Speaking for ' + header)
            await speech_cog.play_path(channel, voice_file)
        else:
            await self.send_id_failure_message(ctx, query)

    @commands.group(aliases=['idmode'])
    async def idset(self, ctx):
        """id settings configuration"""

    @idset.command()
    async def scroll(self, ctx, value):
        """Switch between number scroll and evo scroll

        [p]idset scroll number
        [p]idset scroll evo"""
        if value in ['evo', 'default']:
            if settings.setEvoID(ctx.author.id):
                await ctx.tick()
            else:
                await ctx.send(inline("You're already using evo mode"))
        elif value in ['number']:
            if settings.rmEvoID(ctx.author.id):
                await ctx.tick()
            else:
                await ctx.send(inline("You're already using number mode"))
        else:
            await ctx.send("id_type must be `number` or `evo`")

    @idset.command()
    async def survey(self, ctx, value):
        """Change how often you see the id survey

        [p]idset survey always     (Always see survey after using id)
        [p]idset survey sometimes  (See survey some of the time after using id)
        [p]idset survey never      (Never see survey after using id D:)"""
        vals = ['always', 'sometimes', 'never']
        if value in vals:
            await self.config.user(ctx.author).survey_mode.set(vals.index(value))
            await ctx.tick()
        else:
            await ctx.send("value must be `always`, `sometimes`, or `never`")

    @is_donor()
    @idset.command()
    async def embedcolor(self, ctx, *, color):
        """(DONOR ONLY) Change the color of all your ID embeds!

        Examples:
        [p]idset embedcolor green
        [p]idset embedcolor #a10000
        [p]idset embedcolor random

        Picking random will choose a random hex code every time you use [p]id!
        """
        if color in COLORS:
            await self.config.user(ctx.author).color.set(COLORS[color])
        elif re.match(r"^#?[0-9a-fA-F]{6}$", color):
            await self.config.user(ctx.author).color.set(int(color.lstrip("#"), 16))
        else:
            await ctx.send("Invalid color!  Valid colors are any hexcode and:\n" + ", ".join(COLORS))
            return
        await ctx.tick()

    @idset.command(usage="<on/off>")
    async def naprio(self, ctx, value: bool):
        """Change whether [p]id will default away from new evos of monsters that aren't in NA yet"""
        async with self.bot.get_cog("Dadguide").config.user(ctx.author).fm_flags() as fm_flags:
            fm_flags['na_prio'] = value
        await ctx.send(f"NA monster prioritization has been **{'en' if value else 'dis'}abled**.")

    @commands.group()
    @checks.is_owner()
    async def padinfo(self, ctx):
        """PAD info management"""

    @padinfo.group()
    @checks.is_owner()
    async def emojiservers(self, ctx):
        """Emoji server subcommand"""

    @emojiservers.command(name="add")
    @checks.is_owner()
    async def es_add(self, ctx, server_id: int):
        """Add the emoji server by ID"""
        emoji_servers = settings.emojiServers()
        if server_id not in emoji_servers:
            emoji_servers.append(server_id)
            settings.save_settings()
        await ctx.tick()

    @emojiservers.command(name="remove", aliases=['rm', 'del'])
    @checks.is_owner()
    async def es_rm(self, ctx, server_id: int):
        """Remove the emoji server by ID"""
        emoji_servers = settings.emojiServers()
        if server_id not in emoji_servers:
            await ctx.send("That emoji server is not set.")
            return
        emoji_servers.remove(server_id)
        settings.save_settings()
        await ctx.tick()

    @emojiservers.command(name="list", aliases=['show'])
    @checks.is_owner()
    async def es_show(self, ctx):
        """List the emoji servers by ID"""
        emoji_servers = settings.emojiServers()
        await ctx.send(box("\n".join(str(s) for s in emoji_servers)))

    @padinfo.command()
    @checks.is_owner()
    async def setvoicepath(self, ctx, *, path=''):
        """Set path to the voice direcory"""
        settings.setVoiceDir(path)
        await ctx.tick()

    def get_emojis(self):
        server_ids = [int(sid) for sid in settings.emojiServers()]
        return [e for g in self.bot.guilds if g.id in server_ids for e in g.emojis]

    @staticmethod
    async def send_id_failure_message(ctx, query: str):
        await ctx.send("Sorry, your query {0} didn't match any results :(\n"
                       "See <{2}> for "
                       "documentation on `{1.prefix}id`! You can also  run `{1.prefix}idhelp <monster id>` to get "
                       "help with querying a specific monster.".format(inline(query), ctx, IDGUIDE))

    @commands.command(aliases=["iddebug", "dbid", "iddb"])
    async def debugid(self, ctx, *, query):
        """Get helpful id information about a monster"""
        dgcog = self.bot.get_cog("Dadguide")
        mon = await dgcog.find_monster(query, ctx.author.id)
        if mon is None:
            await ctx.send(box("Your query didn't match any monsters."))
            return
        base_monster = dgcog.database.graph.get_base_monster(mon)
        mods = dgcog.index.modifiers[mon]
        manual_modifiers = dgcog.index.manual_prefixes[mon.monster_id]
        EVOANDTYPE = dgcog.token_maps.EVO_TOKENS.union(dgcog.token_maps.TYPE_TOKENS)
        ret = (f"[{mon.monster_id}] {mon.name_en}\n"
               f"Base: [{base_monster.monster_id}] {base_monster.name_en}\n"
               f"Series: {mon.series.name_en} ({mon.series_id}, {mon.series.series_type})\n\n"
               f"[Name Tokens] {' '.join(sorted(t for t, ms in dgcog.index.name_tokens.items() if mon in ms))}\n"
               f"[Fluff Tokens] {' '.join(sorted(t for t, ms in dgcog.index.fluff_tokens.items() if mon in ms))}\n\n"
               f"[Manual Tokens]\n"
               f"     Treenames: {' '.join(sorted(t for t, ms in dgcog.index.manual_tree.items() if mon in ms))}\n"
               f"     Nicknames: {' '.join(sorted(t for t, ms in dgcog.index.manual_nick.items() if mon in ms))}\n\n"
               f"[Modifier Tokens]\n"
               f"     Attribute: {' '.join(sorted(t for t in mods if t in dgcog.token_maps.COLOR_TOKENS))}\n"
               f"     Awakening: {' '.join(sorted(t for t in mods if t in dgcog.token_maps.AWAKENING_TOKENS))}\n"
               f"    Evo & Type: {' '.join(sorted(t for t in mods if t in EVOANDTYPE))}\n"
               f"         Other: {' '.join(sorted(t for t in mods if t not in dgcog.token_maps.OTHER_HIDDEN_TOKENS))}\n"
               f"Manually Added: {' '.join(sorted(manual_modifiers))}\n")
        for page in pagify(ret):
            await ctx.send(box(page))

    @commands.command()
    async def debugiddist(self, ctx, s1, s2):
        """Find the distance between two queries.

        For name tokens, the full word goes second as name token matching is not commutitive
        """

        dgcog = self.bot.get_cog("Dadguide")

        dist = dgcog.mon_finder.calc_ratio_modifier(s1, s2)
        dist2 = dgcog.mon_finder.calc_ratio_name(s1, s2)
        yes = '\N{WHITE HEAVY CHECK MARK}'
        no = '\N{CROSS MARK}'
        await ctx.send(f"Printing info for {inline(s1)}, {inline(s2)}\n" +
                       box(f"Jaro-Winkler Distance:    {round(dist, 4)}\n"
                           f"Name Matching Distance:   {round(dist2, 4)}\n"
                           f"Modifier token threshold: {dgcog.mon_finder.MODIFIER_JW_DISTANCE}  "
                           f"{yes if dist >= dgcog.mon_finder.MODIFIER_JW_DISTANCE else no}\n"
                           f"Name token threshold:     {dgcog.mon_finder.TOKEN_JW_DISTANCE}   "
                           f"{yes if dist2 >= dgcog.mon_finder.TOKEN_JW_DISTANCE else no}"))

    @commands.command(aliases=['helpid'])
    async def idhelp(self, ctx, *, query=""):
        """Get help with an id query"""
        await ctx.send(
            "See <{0}> for documentation on `{1.prefix}id`!"
            " Use `{1.prefix}idmeaning` to query the meaning of any modifier token."
            " Remember that other than `equip`, modifiers must be at the start of the query."
            "".format(IDGUIDE, ctx))
        if query:
            await self.debugid(ctx, query=query)

    @commands.command()
    async def exportmodifiers(self, ctx):
        DGCOG = self.bot.get_cog("Dadguide")
        maps = DGCOG.token_maps
        awakenings = {a.awoken_skill_id: a for a in DGCOG.database.get_all_awoken_skills()}
        series = {s.series_id: s for s in DGCOG.database.get_all_series()}

        ret = ("Jump to:\n\n"
               "* [Types](#types)\n"
               "* [Evolutions](#evolutions)\n"
               "* [Misc](#misc)\n"
               "* [Awakenings](#awakenings)\n"
               "* [Series](#series)\n"
               "* [Attributes](#attributes)\n\n\n\n")

        etable = [(k.value, ", ".join(map(inline, v))) for k, v in maps.EVO_MAP.items()]
        ret += "\n\n### Evolutions\n\n" + tabulate(etable, headers=["Meaning", "Tokens"], tablefmt="github")
        ttable = [(k.name, ", ".join(map(inline, v))) for k, v in maps.TYPE_MAP.items()]
        ret += "\n\n### Types\n\n" + tabulate(ttable, headers=["Meaning", "Tokens"], tablefmt="github")
        mtable = [(k.value, ", ".join(map(inline, v))) for k, v in maps.MISC_MAP.items()]
        ret += "\n\n### Misc\n\n" + tabulate(mtable, headers=["Meaning", "Tokens"], tablefmt="github")
        atable = [(awakenings[k.value].name_en, ", ".join(map(inline, v))) for k, v in maps.AWOKEN_SKILL_MAP.items()]
        ret += "\n\n### Awakenings\n\n" + tabulate(atable, headers=["Meaning", "Tokens"], tablefmt="github")
        stable = [(series[k].name_en, ", ".join(map(inline, v)))
                  for k, v in DGCOG.index.series_id_to_pantheon_nickname.items()]
        ret += "\n\n### Series\n\n" + tabulate(stable, headers=["Meaning", "Tokens"], tablefmt="github")
        ctable = [(k.name.replace("Nil", "None"), ", ".join(map(inline, v))) for k, v in maps.COLOR_MAP.items()]
        ctable += [("Sub " + k.name.replace("Nil", "None"), ", ".join(map(inline, v))) for k, v in
                   maps.SUB_COLOR_MAP.items()]
        for k, v in maps.DUAL_COLOR_MAP.items():
            k0name = k[0].name.replace("Nil", "None")
            k1name = k[1].name.replace("Nil", "None")
            ctable.append((k0name + "/" + k1name, ", ".join(map(inline, v))))
        ret += "### Attributes\n\n" + tabulate(ctable, headers=["Meaning", "Tokens"], tablefmt="github")

        await ctx.send(file=text_to_file(ret, filename="table.md"))

    @commands.command(aliases=["idcheckmod", "lookupmod", "idlookupmod", "luid", "idlu"])
    async def idmeaning(self, ctx, *, token):
        """Get all the meanings of a token (bold signifies base of a tree)"""
        token = token.replace(" ", "")
        DGCOG = self.bot.get_cog("Dadguide")

        await DGCOG.wait_until_ready()

        tms = DGCOG.token_maps
        awokengroup = "(" + "|".join(re.escape(aw) for aws in tms.AWOKEN_SKILL_MAP.values() for aw in aws) + ")"
        awakenings = {a.awoken_skill_id: a for a in DGCOG.database.get_all_awoken_skills()}
        series = {s.series_id: s for s in DGCOG.database.get_all_series()}

        ret = ""

        def write_name_token(token_dict, token_type, is_multiword=False):
            def f(m, s):
                return bold(s) if DGCOG.database.graph.monster_is_base(m) else s

            token_ret = ""
            so = []
            for mon in sorted(token_dict[token], key=lambda m: m.monster_id):
                if (mon in DGCOG.index.mwtoken_creators[token]) == is_multiword:
                    so.append(mon)
            if len(so) > 5:
                token_ret += f"\n\n{token_type}\n" + ", ".join(f(m, str(m.monster_id)) for m in so[:10])
                token_ret += f"... ({len(so)} total)" if len(so) > 10 else ""
            elif so:
                token_ret += f"\n\n{token_type}\n" + "\n".join(
                    f(m, f"{str(m.monster_id).rjust(4)}. {m.name_en}") for m in so)
            return token_ret

        ret += write_name_token(DGCOG.index.manual, "\N{LARGE PURPLE CIRCLE} [Multi-Word Tokens]", True)
        ret += write_name_token(DGCOG.index.manual, "[Manual Tokens]")
        ret += write_name_token(DGCOG.index.name_tokens, "[Name Tokens]")
        ret += write_name_token(DGCOG.index.fluff_tokens, "[Fluff Tokens]")

        submwtokens = [t for t in DGCOG.index.multi_word_tokens if token in t]
        if submwtokens:
            ret += "\n\n[Multi-word Super-tokens]\n"
            for t in submwtokens:
                if not DGCOG.index.all_name_tokens[''.join(t)]:
                    continue
                creators = sorted(DGCOG.index.mwtoken_creators["".join(t)], key=lambda m: m.monster_id)
                ret += f"{' '.join(t).title()}"
                ret += f" ({', '.join(f'{m.monster_id}' for m in creators)})" if creators else ''
                ret += (" ( \u2014> " +
                        str(DGCOG.mon_finder.get_most_eligable_monster(DGCOG.index.all_name_tokens[''.join(t)],
                                                                       DGCOG).monster_id)
                        + ")\n")

        def additmods(ms, om):
            if len(ms) == 1:
                return ""
            return "\n\tAlternate names: " + ', '.join(inline(m) for m in ms if m != om)

        meanings = '\n'.join([
            *["Evo: " + k.value + additmods(v, token)
              for k, v in tms.EVO_MAP.items() if token in v],
            *["Type: " + get_type_emoji(k) + ' ' + k.name + additmods(v, token)
              for k, v in tms.TYPE_MAP.items() if token in v],
            *["Misc: " + k.value + additmods(v, token)
              for k, v in tms.MISC_MAP.items() if token in v],
            *["Awakening: " + get_awakening_emoji(k) + ' ' + awakenings[k.value].name_en + additmods(v, token)
              for k, v in tms.AWOKEN_SKILL_MAP.items() if token in v],
            *["Main attr: " + get_attribute_emoji_by_enum(k, None) + ' ' + k.name.replace("Nil", "None") +
              additmods(v, token)
              for k, v in tms.COLOR_MAP.items() if token in v],
            *["Sub attr: " + get_attribute_emoji_by_enum(False, k) + ' ' + k.name.replace("Nil", "None") +
              additmods(v, token)
              for k, v in tms.SUB_COLOR_MAP.items() if token in v],
            *["Dual attr: " + get_attribute_emoji_by_enum(k[0], k[1]) + ' ' + k[0].name.replace("Nil", "None") +
              '/' + k[1].name.replace("Nil", "None") + additmods(v, token)
              for k, v in tms.DUAL_COLOR_MAP.items() if token in v],
            *["Series: " + series[k].name_en + additmods(v, token)
              for k, v in DGCOG.index.series_id_to_pantheon_nickname.items() if token in v],

            *["Rarity: " + m for m in re.findall(r"^(\d+)\*$", token)],
            *["Base rarity: " + m for m in re.findall(r"^(\d+)\*b$", token)],
            *[f"[UNSUPPORTED] Multiple awakenings: {m}x {awakenings[a.value].name_en}"
              f"{additmods([f'{m}*{d}' for d in v], token)}"
              for m, ag in re.findall(r"^(\d+)\*{}$".format(awokengroup), token)
              for a, v in tms.AWOKEN_SKILL_MAP.items() if ag in v]
        ])

        if meanings or ret:
            for page in pagify(meanings + "\n\n" + ret.strip()):
                await ctx.send(page)
        else:
            await ctx.send(f"There are no modifiers that match `{token}`.")

    @commands.command(aliases=["tracebackid", "tbid", "idtb"])
    async def idtraceback(self, ctx, *, query):
        """Get the traceback of an id query"""
        selected_monster_id = None
        if "/" in query:
            query, selected_monster_id = query.split("/", 1)
            if not selected_monster_id.strip().isdigit():
                await ctx.send("Monster id must be an int.")
                return
            selected_monster_id = int(selected_monster_id.strip())

        dgcog = self.bot.get_cog("Dadguide")

        bestmatch, matches, _, _ = await dgcog.mon_finder.find_monster_debug(query)

        if bestmatch is None:
            await ctx.send("No monster matched.")
            return

        if selected_monster_id is not None:
            selected = {m for m in matches if m.monster_id == selected_monster_id}
            if not selected:
                await ctx.send("The requested monster was not found as a result of the query.")
                return
            monster = selected.pop()
        else:
            monster = bestmatch

        score = matches[monster].score
        ntokens = matches[monster].name
        mtokens = matches[monster].mod
        lower_prio = {m for m in matches if matches[m].score == matches[monster].score}.difference({monster})
        if len(lower_prio) > 20:
            lpstr = f"{len(lower_prio)} other monsters."
        else:
            lpstr = "\n".join(f"{get_attribute_emoji_by_monster(m)} {m.name_en} ({m.monster_id})" for m in lower_prio)

        mtokenstr = '\n'.join(f"{inline(t[0])}{(': ' + t[1]) if t[0] != t[1] else ''}"
                              f" ({round(dgcog.mon_finder.calc_ratio_modifier(t[0], t[1]), 2) if t[0] != t[1] else 'exact'})"
                              for t in sorted(mtokens))
        ntokenstr = '\n'.join(f"{inline(t[0])}{(': ' + t[1]) if t[0] != t[1] else ''}"
                              f" ({round(dgcog.mon_finder.calc_ratio_name(t[0], t[1]), 2) if t[0] != t[1] else 'exact'})"
                              f" {t[2]}"
                              for t in sorted(ntokens))

        color = await self.get_user_embed_color(ctx)
        original_author_id = ctx.message.author.id
        menu = ClosableEmbedMenu.menu()
        props = IdTracebackViewProps(monster=monster, score=score, name_tokens=ntokenstr, modifier_tokens=mtokenstr,
                                     lower_priority_monsters=lpstr if lower_prio else "None")
        state = ClosableEmbedViewState(original_author_id, ClosableEmbedMenu.MENU_TYPE, query, color,
                                       IdTracebackView.VIEW_TYPE, props)
        await menu.create(ctx, state)

    @commands.command(aliases=["ids"])
    @checks.bot_has_permissions(embed_links=True)
    async def idsearch(self, ctx, *, query):
        dgcog = self.bot.get_cog("Dadguide")

        matched_monsters = await dgcog.find_monsters(query, ctx.author.id)

        if not matched_monsters:
            await ctx.send("No monster matched.")
            return

        used = set()
        monster_list = []
        for mon in matched_monsters:
            base_id = dgcog.database.graph.get_base_id(mon)
            if base_id not in used:
                used.add(base_id)
                monster_list.append(mon)

        await self._do_monster_list(ctx, dgcog, query, monster_list, 'ID Search Results')
