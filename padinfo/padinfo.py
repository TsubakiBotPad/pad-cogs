import asyncio
import json
import logging
import os
import random
import re
import urllib.parse
from io import BytesIO
from typing import List, Optional, TYPE_CHECKING, Type

import discord
from discord import Color
from discordmenu.emoji.emoji_cache import emoji_cache
from redbot.core import Config, checks, commands, data_manager
from redbot.core.commands import Literal as LiteralConverter
from redbot.core.utils.chat_formatting import bold, box, inline, pagify, text_to_file
from tabulate import tabulate
from tsutils.cogs.donations import is_donor
from tsutils.emoji import char_to_emoji
from tsutils.enums import Server
from tsutils.json_utils import safe_read_json
from tsutils.menu.components.config import BotConfig
from tsutils.menu.simple_text import SimpleTextMenu
from tsutils.menu.view.closable_embed import ClosableEmbedViewState
from tsutils.menu.view.simple_text import SimpleTextViewState
from tsutils.query_settings import validators
from tsutils.query_settings.enums import AltEvoSort, CardLevelModifier, CardModeModifier, CardPlusModifier, EvoGrouping, \
    LsMultiplier, \
    MonsterLinkTarget
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.tsubaki.custom_emoji import AWAKENING_ID_TO_EMOJI_NAME_MAP, get_attribute_emoji_by_enum, \
    get_attribute_emoji_by_monster, get_awakening_emoji, get_type_emoji
from tsutils.tsubaki.monster_header import MonsterHeader
from tsutils.user_interaction import get_user_confirmation, send_cancellation_message, send_confirmation_message

from padinfo.core.button_info import button_info
from padinfo.core.leader_skills import leaderskill_query
from padinfo.core.padinfo_settings import settings
from padinfo.core.transforminfo import perform_transforminfo_query
from padinfo.menu.awakening_list import AwakeningListMenu, AwakeningListMenuPanes
from padinfo.menu.button_info import ButtonInfoMenu, ButtonInfoMenuPanes
from padinfo.menu.closable_embed import ClosableEmbedMenu
from padinfo.menu.id import IdMenu, IdMenuPanes
from padinfo.menu.leader_skill import LeaderSkillMenu
from padinfo.menu.leader_skill_single import LeaderSkillSingleMenu
from padinfo.menu.menu_map import padinfo_menu_map
from padinfo.menu.monster_list import MonsterListEmoji, MonsterListMenu, MonsterListMenuPanes
from padinfo.menu.na_diff import NaDiffMenu, NaDiffMenuPanes
from padinfo.menu.scroll import ScrollMenuPanes
from padinfo.menu.series_scroll import SeriesScrollEmoji, SeriesScrollMenu, SeriesScrollMenuPanes
from padinfo.menu.transforminfo import TransformInfoMenu, TransformInfoMenuPanes
from padinfo.reaction_list import get_id_menu_initial_reaction_list
from padinfo.view.awakening_help import AwakeningHelpView, AwakeningHelpViewProps
from padinfo.view.awakening_list import AwakeningListSortTypes, AwakeningListViewState
from padinfo.view.button_info import ButtonInfoToggles, ButtonInfoViewState
from padinfo.view.common import invalid_monster_text
from padinfo.view.evos import EvosViewState
from padinfo.view.experience_curve import ExperienceCurveView, ExperienceCurveViewProps
from padinfo.view.id import IdViewState
from padinfo.view.id_traceback import IdTracebackView, IdTracebackViewProps
from padinfo.view.leader_skill import LeaderSkillViewState
from padinfo.view.leader_skill_single import LeaderSkillSingleViewState
from padinfo.view.links import LinksView
from padinfo.view.lookup import LookupView
from padinfo.view.materials import MaterialsViewState
from padinfo.view.monster_list.all_mats import AllMatsViewState
from padinfo.view.monster_list.id_search import IdSearchViewState
from padinfo.view.monster_list.monster_list import MonsterListViewState
from padinfo.view.monster_list.scroll import ScrollViewState
from padinfo.view.monster_list.static_monster_list import StaticMonsterListViewState
from padinfo.view.otherinfo import OtherInfoViewState
from padinfo.view.pantheon import PantheonViewState
from padinfo.view.pic import PicViewState
from padinfo.view.series_scroll import SeriesScrollViewState
from padinfo.view.transforminfo import TransformInfoViewState

if TYPE_CHECKING:
    from dbcog.dbcog import DBCog
    from dbcog.models.monster_model import MonsterModel
    from dbcog.models.series_model import SeriesModel

logger = logging.getLogger('red.padbot-cogs.padinfo')

EMBED_NOT_GENERATED = -1

IDGUIDE = "https://github.com/TsubakiBotPad/pad-cogs/wiki/id-user-guide"

HISTORY_DURATION = 11


def _data_file(file_name: str) -> str:
    return os.path.join(str(data_manager.cog_data_path(raw_name='padinfo')), file_name)


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

        self.historic_lookups_file_path = _data_file('historic_lookups_id3.json')
        self.historic_lookups = safe_read_json(self.historic_lookups_file_path)

        self.awoken_emoji_names = {v: k for k, v in AWAKENING_ID_TO_EMOJI_NAME_MAP.items()}
        self.get_attribute_emoji_by_monster = get_attribute_emoji_by_monster
        self.settings = settings

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        idhist = await self.config.user_from_id(user_id).id_history()
        if idhist:
            data = f"You have {len(idhist)} past queries stored.  Use" \
                   f" {(await self.bot.get_valid_prefixes())[0]}idhistory to see what they are.\n"
        else:
            data = f"No data is stored for user with ID {user_id}."
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        await self.config.user_from_id(user_id).clear()

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
            except Exception as ex:
                wait_time = 5
                logger.exception("reload padinfo loop caught exception " + str(ex))

            await asyncio.sleep(wait_time)

    async def get_dbcog(self) -> "DBCog":
        dbcog = self.bot.get_cog("DBCog")
        if dbcog is None:
            raise ValueError("DBCog cog is not loaded")
        await dbcog.wait_until_ready()
        return dbcog

    def save_historic_data(self, query, monster: Optional["MonsterModel"]):
        self.historic_lookups[query] = monster.monster_id if monster else -1
        json.dump(self.historic_lookups, open(self.historic_lookups_file_path, "w+"))

    async def get_menu_default_data(self, ims):
        data = {
            'dbcog': await self.get_dbcog(),
            'user_config': await BotConfig.get_user(self.config, ims['original_author_id'])
        }
        return data

    @commands.command()
    async def jpname(self, ctx, *, query: str):
        """Show the Japanese name of a monster"""
        dbcog = await self.get_dbcog()
        monster = await dbcog.find_monster(query, ctx.author.id)
        if monster is not None:
            await ctx.send(MonsterHeader.text_with_emoji(monster))
            await ctx.send(box(monster.name_ja))
        else:
            await self.send_id_failure_message(ctx, query)

    @commands.command(name="id", aliases=['I\'d', 'ID'])
    @checks.bot_has_permissions(embed_links=True)
    async def _id(self, ctx, *, query: str):
        """Monster info (main tab)"""
        await self._do_id(ctx, query)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def idna(self, ctx, *, query: str):
        """Monster info (limited to NA monsters ONLY)"""
        await self._do_id(ctx, "--na " + query)

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

    async def _get_monster(self, ctx, query: str) -> Optional["MonsterModel"]:
        dbcog = await self.get_dbcog()
        raw_query = query

        goodquery = None
        ID1_SUPPORTED = dbcog.token_maps.ID1_SUPPORTED
        if query[0] in ID1_SUPPORTED and query[1:] in dbcog.indexes[Server.COMBINED].all_name_tokens:
            goodquery = [query[0], query[1:]]
        elif query[:2] in ID1_SUPPORTED and query[2:] in dbcog.indexes[Server.COMBINED].all_name_tokens:
            goodquery = [query[:2], query[2:]]

        if goodquery:
            bad = False
            for monster in dbcog.indexes[Server.COMBINED].all_name_tokens[goodquery[1]]:
                for modifier in dbcog.indexes[Server.COMBINED].modifiers[monster]:
                    if modifier == 'xm' and goodquery[0] == 'x':
                        goodquery[0] = 'xm'
                    if modifier == goodquery[0]:
                        bad = True
            if bad and query not in dbcog.indexes[Server.COMBINED].all_name_tokens:
                async def send_message():
                    await asyncio.sleep(1)
                    await ctx.send(f"Uh oh, it looks like you tried a query that isn't supported anymore!"
                                   f" Try using `{' '.join(goodquery)}` (with a space) instead! For more"
                                   f" info about the new id changes, check out"
                                   f" <{IDGUIDE}>!")

                asyncio.create_task(send_message())
                async with self.config.bad_queries() as bad_queries:
                    bad_queries.append((raw_query, ctx.author.id))

        monster = await dbcog.find_monster(raw_query, ctx.author.id)

        if monster is None:
            await self.send_id_failure_message(ctx, query)
        return monster

    async def _do_id(self, ctx, query: str):
        dbcog = await self.get_dbcog()
        original_author_id = ctx.message.author.id
        raw_query = query

        if (monster := await self._get_monster(ctx, query)) is None:
            self.save_historic_data(query, monster)
            return

        # id3 messaging stuff
        if monster and monster.monster_no_na != monster.monster_no_jp:
            await ctx.send(f"The NA ID and JP ID of this card differ! The JP ID is {monster.monster_id}, so "
                           f"you can query with {ctx.prefix}id jp{monster.monster_id}." +
                           (" Make sure you use the **JP id number** when updating the Google doc!!!!!" if
                            ctx.author.id in self.bot.get_cog("PadGlobal").settings.bot_settings['admins'] else ""))

        if await self.config.do_survey():
            asyncio.create_task(self.send_survey_after(ctx, query, monster))

        alt_monsters = IdViewState.get_alt_monsters_and_evos(dbcog, monster)
        id_queried_props = await IdViewState.do_query(dbcog, monster)
        full_reaction_list = IdMenuPanes.emoji_names()
        initial_reaction_list = await get_id_menu_initial_reaction_list(ctx, dbcog, monster, full_reaction_list)
        is_jp_buffed = dbcog.database.graph.monster_is_discrepant(monster)
        query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, query)

        state = IdViewState(original_author_id, IdMenu.MENU_TYPE, raw_query, query, monster,
                            alt_monsters, is_jp_buffed, query_settings, id_queried_props,
                            reaction_list=initial_reaction_list)
        menu = IdMenu.menu()
        await menu.create(ctx, state)
        await self.log_id_result(ctx, monster.monster_id)
        self.save_historic_data(query, monster)

    async def send_survey_after(self, ctx, query, result_monster):
        dbcog = await self.get_dbcog()
        survey_mode = await self.config.user(ctx.author).survey_mode()
        survey_chance = (1, await self.config.sometimes_perc() / 100, 0)[survey_mode]
        if random.random() < survey_chance:
            mid1 = self.historic_lookups.get(query)
            m1 = mid1 and dbcog.get_monster(mid1)
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
            userres = await get_user_confirmation(ctx, "Was this the monster you were looking for?",
                                                  yes_emoji=char_to_emoji('y'), no_emoji=char_to_emoji('n'))
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

    @staticmethod
    async def send_invalid_monster_message(ctx, query: str, monster: "MonsterModel", append_text: str):
        await ctx.send(invalid_monster_text(query, monster, append_text))

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def nadiff(self, ctx, *, query: str):
        """Show differences between NA & JP versions of a card"""
        dbcog = await self.get_dbcog()
        raw_query = query
        original_author_id = ctx.message.author.id

        monster = await dbcog.find_monster(raw_query, ctx.author.id)
        if monster is None:
            await self.send_id_failure_message(ctx, query)
            self.save_historic_data(query, monster)
            return

        alt_monsters = IdViewState.get_alt_monsters_and_evos(dbcog, monster)
        id_queried_props = await IdViewState.do_query(dbcog, monster)

        is_jp_buffed = dbcog.database.graph.monster_is_discrepant(monster)
        query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, query)

        state = IdViewState(original_author_id, NaDiffMenu.MENU_TYPE, raw_query, query, monster,
                            alt_monsters, is_jp_buffed, query_settings, id_queried_props)
        menu = NaDiffMenu.menu()
        message = state.get_na_diff_invalid_message()
        if message:
            state = SimpleTextViewState(original_author_id, NaDiffMenu.MENU_TYPE,
                                        raw_query, query_settings, message)
            menu = NaDiffMenu.menu(initial_control=NaDiffMenu.message_control)
        await menu.create(ctx, state)
        await self.log_id_result(ctx, monster.monster_id)
        self.save_historic_data(query, monster)

    @commands.command(name="evos")
    @checks.bot_has_permissions(embed_links=True)
    async def evos(self, ctx, *, query: str):
        """Monster info (evolutions tab)"""
        dbcog = await self.get_dbcog()
        raw_query = query
        original_author_id = ctx.message.author.id

        monster = await dbcog.find_monster(raw_query, ctx.author.id)

        if monster is None:
            await self.send_id_failure_message(ctx, query)
            self.save_historic_data(query, monster)
            return

        alt_monsters = EvosViewState.get_alt_monsters_and_evos(dbcog, monster)
        alt_versions, gem_versions = await EvosViewState.do_query(dbcog, monster)
        is_jp_buffed = dbcog.database.graph.monster_is_discrepant(monster)
        query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, query)

        if alt_versions is None:
            await self.send_invalid_monster_message(ctx, query, monster, ', which has no alt evos or gems')
            return

        full_reaction_list = IdMenuPanes.emoji_names()
        initial_reaction_list = await get_id_menu_initial_reaction_list(ctx, dbcog, monster, full_reaction_list)

        state = EvosViewState(original_author_id, IdMenu.MENU_TYPE, raw_query, query, monster,
                              alt_monsters, is_jp_buffed, query_settings,
                              alt_versions, gem_versions,
                              reaction_list=initial_reaction_list
                              )
        menu = IdMenu.menu(initial_control=IdMenu.evos_control)
        await menu.create(ctx, state)
        await self.log_id_result(ctx, monster.monster_id)
        self.save_historic_data(query, monster)

    @commands.command(name="mats", aliases=['evomats', 'evomat', 'skillups'])
    @checks.bot_has_permissions(embed_links=True)
    async def evomats(self, ctx, *, query: str):
        """Monster info (evo materials tab)"""
        dbcog = await self.get_dbcog()
        raw_query = query
        original_author_id = ctx.message.author.id
        monster = await dbcog.find_monster(raw_query, ctx.author.id)

        if not monster:
            await self.send_id_failure_message(ctx, query)
            self.save_historic_data(query, monster)
            return

        mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link, gem_override = \
            await MaterialsViewState.do_query(dbcog, monster)

        if mats is None:
            await ctx.send(inline("This monster has no mats or skillups and isn't used in any evolutions"))
            return

        alt_monsters = MaterialsViewState.get_alt_monsters_and_evos(dbcog, monster)
        is_jp_buffed = dbcog.database.graph.monster_is_discrepant(monster)
        query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, query)
        full_reaction_list = IdMenuPanes.emoji_names()
        initial_reaction_list = await get_id_menu_initial_reaction_list(ctx, dbcog, monster, full_reaction_list)

        state = MaterialsViewState(original_author_id, IdMenu.MENU_TYPE, raw_query, query, monster,
                                   alt_monsters, is_jp_buffed, query_settings,
                                   mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link, gem_override,
                                   reaction_list=initial_reaction_list
                                   )
        menu = IdMenu.menu(initial_control=IdMenu.mats_control)
        await menu.create(ctx, state)
        await self.log_id_result(ctx, monster.monster_id)
        self.save_historic_data(query, monster)

    @commands.command(aliases=["series", "panth"])
    @checks.bot_has_permissions(embed_links=True)
    async def pantheon(self, ctx, *, query: str):
        """Monster info (pantheon tab)"""
        dbcog = await self.get_dbcog()
        raw_query = query
        original_author_id = ctx.message.author.id

        monster = await dbcog.find_monster(raw_query, ctx.author.id)

        if monster is None:
            await self.send_id_failure_message(ctx, query)
            self.save_historic_data(query, monster)
            return

        pantheon_list, series_name, base_monster = await PantheonViewState.do_query(dbcog, monster)
        if pantheon_list is None:
            await ctx.send('Unable to find a pantheon for the result of your query,'
                           + ' [{}] {}.'.format(monster.monster_id, monster.name_en))
            return
        alt_monsters = PantheonViewState.get_alt_monsters_and_evos(dbcog, monster)
        is_jp_buffed = dbcog.database.graph.monster_is_discrepant(monster)
        query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, query)
        full_reaction_list = IdMenuPanes.emoji_names()
        initial_reaction_list = await get_id_menu_initial_reaction_list(ctx, dbcog, monster, full_reaction_list)

        state = PantheonViewState(original_author_id, IdMenu.MENU_TYPE, raw_query, query, monster,
                                  alt_monsters, is_jp_buffed, query_settings,
                                  pantheon_list, series_name, base_monster,
                                  reaction_list=initial_reaction_list
                                  )
        menu = IdMenu.menu(initial_control=IdMenu.pantheon_control)
        await menu.create(ctx, state)
        await self.log_id_result(ctx, monster.monster_id)
        self.save_historic_data(query, monster)

    @commands.command(aliases=['img'])
    @checks.bot_has_permissions(embed_links=True)
    async def pic(self, ctx, *, query: str):
        """Monster info (full image tab)"""
        dbcog = await self.get_dbcog()
        raw_query = query
        original_author_id = ctx.message.author.id

        monster = await dbcog.find_monster(raw_query, ctx.author.id)

        if monster is None:
            await self.send_id_failure_message(ctx, query)
            self.save_historic_data(query, monster)
            return

        alt_monsters = PicViewState.get_alt_monsters_and_evos(dbcog, monster)
        is_jp_buffed = dbcog.database.graph.monster_is_discrepant(monster)
        query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, query)
        full_reaction_list = IdMenuPanes.emoji_names()
        initial_reaction_list = await get_id_menu_initial_reaction_list(ctx, dbcog, monster, full_reaction_list)

        state = PicViewState(original_author_id, IdMenu.MENU_TYPE, raw_query, query, monster,
                             alt_monsters, is_jp_buffed, query_settings,
                             reaction_list=initial_reaction_list
                             )
        menu = IdMenu.menu(initial_control=IdMenu.pic_control)
        await menu.create(ctx, state)
        await self.log_id_result(ctx, monster.monster_id)
        self.save_historic_data(query, monster)

    @commands.command(aliases=['stats'])
    @checks.bot_has_permissions(embed_links=True)
    async def otherinfo(self, ctx, *, query: str):
        """Monster info (misc info tab)"""
        dbcog = await self.get_dbcog()
        raw_query = query
        original_author_id = ctx.message.author.id

        monster = await dbcog.find_monster(raw_query, ctx.author.id)

        if monster is None:
            await self.send_id_failure_message(ctx, query)
            self.save_historic_data(query, monster)
            return

        alt_monsters = PicViewState.get_alt_monsters_and_evos(dbcog, monster)
        is_jp_buffed = dbcog.database.graph.monster_is_discrepant(monster)
        query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, query)
        full_reaction_list = IdMenuPanes.emoji_names()
        initial_reaction_list = await get_id_menu_initial_reaction_list(ctx, dbcog, monster, full_reaction_list)

        state = OtherInfoViewState(original_author_id, IdMenu.MENU_TYPE, raw_query, query, monster,
                                   alt_monsters, is_jp_buffed, query_settings,
                                   reaction_list=initial_reaction_list
                                   )
        menu = IdMenu.menu(initial_control=IdMenu.otherinfo_control)
        await menu.create(ctx, state)
        await self.log_id_result(ctx, monster.monster_id)
        self.save_historic_data(query, monster)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def links(self, ctx, *, query: str):
        """Monster links"""
        dbcog = await self.get_dbcog()
        monster = await dbcog.find_monster(query, ctx.author.id)
        if monster is None:
            await self.send_id_failure_message(ctx, query)
            self.save_historic_data(query, monster)
            return
        await self.log_id_result(ctx, monster.monster_id)
        query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, query)
        embed = LinksView.embed(monster, query_settings).to_embed()
        await ctx.send(embed=embed)
        await self.log_id_result(ctx, monster.monster_id)
        self.save_historic_data(query, monster)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def lookup(self, ctx, *, query: str):
        """Short info results for a monster query"""
        dbcog = await self.get_dbcog()
        monster = await dbcog.find_monster(query, ctx.author.id)
        if monster is None:
            await self.send_id_failure_message(ctx, query)
            self.save_historic_data(query, monster)
            return
        await self.log_id_result(ctx, monster.monster_id)
        query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, query)
        embed = LookupView.embed(monster, query_settings).to_embed()
        await ctx.send(embed=embed)
        await self.log_id_result(ctx, monster.monster_id)
        self.save_historic_data(query, monster)

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
        dbcog = await self.get_dbcog()
        monster = await dbcog.find_monster(query, ctx.author.id)
        if monster is None:
            await self.send_id_failure_message(ctx, query)
            return

        original_author_id = ctx.message.author.id
        info = button_info.get_info(dbcog, monster)
        query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, query)
        display_options = ButtonInfoToggles()
        alt_monsters = ButtonInfoViewState.get_alt_monsters_and_evos(dbcog, monster)
        state = ButtonInfoViewState(original_author_id, ButtonInfoMenu.MENU_TYPE, query, display_options,
                                    monster, alt_monsters, info, query_settings,
                                    reaction_list=ButtonInfoMenuPanes.get_user_reaction_list(display_options))
        menu = ButtonInfoMenu.menu()
        await menu.create(ctx, state)

    @commands.command(aliases=["ids"])
    @checks.bot_has_permissions(embed_links=True)
    async def idsearch(self, ctx, *, query):
        await self._do_idsearch(ctx, query)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def nadiffs(self, ctx, *, query):
        await self._do_idsearch(ctx, query, child_menu_type=NaDiffMenu.MENU_TYPE,
                                child_reaction_list=NaDiffMenuPanes.emoji_names())

    async def _do_idsearch(self, ctx, query, child_menu_type=None,
                           child_reaction_list=None):
        dbcog = await self.get_dbcog()
        query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, query)
        monster_list = await IdSearchViewState.do_query(dbcog, query, ctx.author.id, query_settings)

        if not monster_list:
            await ctx.send("No monster matched.")
            return

        await self._do_monster_list(ctx, dbcog, query, monster_list, 'ID Search Results',
                                    IdSearchViewState,
                                    child_menu_type=child_menu_type,
                                    child_reaction_list=child_reaction_list)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def allmats(self, ctx, *, query: str):
        """Monster info (evo materials tab)"""
        dbcog = await self.get_dbcog()
        monster = await dbcog.find_monster(query, ctx.author.id)

        if not monster:
            await self.send_id_failure_message(ctx, query)
            return
        monster_list = await AllMatsViewState.do_query(dbcog, monster)
        if not monster_list:
            await ctx.send(inline("This monster is not a mat for anything nor does it have a gem"))
            return

        _, usedin, _, gemusedin, _, _, _, _ = await MaterialsViewState.do_query(dbcog, monster)

        title = 'Material For' if usedin else 'Gem is Material For'
        await self._do_monster_list(ctx, dbcog, query, monster_list, title, AllMatsViewState)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def evolist(self, ctx, *, query):
        dbcog = await self.get_dbcog()
        monster = await dbcog.find_monster(query, ctx.author.id)

        if monster is None:
            await self.send_id_failure_message(ctx, query)
            return

        monster_list, _ = await EvosViewState.do_query(dbcog, monster)
        if monster_list is None:
            await self.send_invalid_monster_message(ctx, query, monster, ', which has no alt evos')
            return
        await self._do_monster_list(ctx, dbcog, query, monster_list, 'Evolution List', StaticMonsterListViewState)

    async def _do_monster_list(self, ctx, dbcog, query, monster_list: List["MonsterModel"],
                               title, view_state_type: Type[MonsterListViewState],
                               child_menu_type: Optional[str] = None,
                               child_reaction_list: Optional[List] = None
                               ):
        raw_query = query
        original_author_id = ctx.message.author.id
        query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, query)
        initial_reaction_list = MonsterListMenuPanes.get_initial_reaction_list(len(monster_list))
        instruction_message = 'Click a reaction to see monster details!'

        if child_menu_type is None:
            child_menu_type = query_settings.child_menu_type.name
            _, child_panes_class = padinfo_menu_map[child_menu_type]
            child_reaction_list = child_panes_class.emoji_names()

        state = view_state_type(original_author_id, view_state_type.VIEW_STATE_TYPE, query,
                                monster_list, query_settings,
                                title, instruction_message,
                                child_menu_type=child_menu_type,
                                child_reaction_list=child_reaction_list,
                                reaction_list=initial_reaction_list
                                )
        parent_menu = MonsterListMenu.menu()
        message = await ctx.send('Setting up!')

        ims = state.serialize()
        user_config = await BotConfig.get_user(self.config, ctx.author.id)
        data = {
            'dbcog': dbcog,
            'user_config': user_config,
        }
        child_state = SimpleTextViewState(original_author_id, view_state_type.VIEW_STATE_TYPE,
                                          raw_query, query_settings,
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

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def scroll(self, ctx, *, query: str):
        dbcog = await self.get_dbcog()
        monster = await dbcog.find_monster(query, ctx.author.id)

        if not monster:
            await self.send_id_failure_message(ctx, query)
            return
        monster_list = await ScrollViewState.do_query(dbcog, monster)
        title = 'Monster Book Scroll'
        raw_query = query
        original_author_id = ctx.message.author.id
        query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, query)
        initial_reaction_list = ScrollMenuPanes.get_initial_reaction_list(len(monster_list))
        instruction_message = 'Click a reaction to see monster details!'

        state = ScrollViewState(original_author_id, ScrollViewState.VIEW_STATE_TYPE, query,
                                monster_list, query_settings,
                                title, instruction_message, monster.monster_id,
                                child_menu_type=IdMenu.MENU_TYPE,
                                child_reaction_list=IdMenuPanes.emoji_names(),
                                reaction_list=initial_reaction_list
                                )
        parent_menu = MonsterListMenu.menu()
        message = await ctx.send('Setting up!')

        ims = state.serialize()
        user_config = await BotConfig.get_user(self.config, ctx.author.id)
        data = {
            'dbcog': dbcog,
            'user_config': user_config,
        }

        alt_monsters = IdViewState.get_alt_monsters_and_evos(dbcog, monster)
        id_queried_props = await IdViewState.do_query(dbcog, monster)
        full_reaction_list = IdMenuPanes.emoji_names()
        is_jp_buffed = dbcog.database.graph.monster_is_discrepant(monster)

        child_state = IdViewState(original_author_id, IdMenu.MENU_TYPE, raw_query, query, monster,
                                  alt_monsters, is_jp_buffed, query_settings, id_queried_props,
                                  reaction_list=full_reaction_list)
        child_menu = IdMenu.menu()
        child_message = await child_menu.create(ctx, child_state)

        data['child_message_id'] = child_message.id
        try:
            await parent_menu.transition(message, ims, MonsterListEmoji.refresh, ctx.author, **data)
            await message.edit(content=None)
        except discord.errors.NotFound:
            # The user could delete the menu before we can do this
            pass

    @commands.command(aliases=['collabscroll', 'ss'])
    @checks.bot_has_permissions(embed_links=True)
    async def seriesscroll(self, ctx, *, query):
        dbcog = await self.get_dbcog()
        monster = await dbcog.find_monster(query, ctx.author.id)

        if monster is None:
            await self.send_id_failure_message(ctx, query)
            return
        series_id = monster.series_id
        series_object: "SeriesModel" = monster.series
        title = series_object.name_en
        paginated_monsters = None
        query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, query)
        rarity = None
        for rarity in SeriesScrollMenu.RARITY_INITIAL_TRY_ORDER:
            paginated_monsters = await SeriesScrollViewState.do_query(dbcog, monster.series_id,
                                                                      rarity, monster.server_priority)
            if paginated_monsters:
                break
        all_rarities = SeriesScrollViewState.query_all_rarities(dbcog, series_id, monster.server_priority)

        raw_query = query
        original_author_id = ctx.message.author.id
        initial_reaction_list = SeriesScrollMenuPanes.get_initial_reaction_list(len(paginated_monsters))
        instruction_message = 'Click a reaction to see monster details!'

        state = SeriesScrollViewState(original_author_id, SeriesScrollMenu.MENU_TYPE, raw_query, query,
                                      series_id, paginated_monsters, 0, int(rarity),
                                      query_settings,
                                      all_rarities,
                                      title, instruction_message,
                                      reaction_list=initial_reaction_list)
        parent_menu = SeriesScrollMenu.menu()
        message = await ctx.send('Setting up!')

        ims = state.serialize()
        user_config = await BotConfig.get_user(self.config, ctx.author.id)
        data = {
            'dbcog': dbcog,
            'user_config': user_config,
        }
        child_state = SimpleTextViewState(original_author_id, SeriesScrollMenu.MENU_TYPE,
                                          raw_query, query_settings,
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
        dbcog = await self.get_dbcog()
        l_mon, l_query, r_mon, r_query = await leaderskill_query(dbcog, raw_query, ctx.author.id)

        err_msg = ('{} query failed to match a monster: [ {} ]. If your query is multiple words,'
                   ' try separating the queries with / or wrap with quotes.')
        if l_mon is None:
            await ctx.send(inline(err_msg.format('Left', l_query)))
            return
        if r_mon is None:
            await ctx.send(inline(err_msg.format('Right', r_query)))
            return

        l_query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, l_query)
        r_query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, r_query or '')

        original_author_id = ctx.message.author.id
        state = LeaderSkillViewState(original_author_id, LeaderSkillMenu.MENU_TYPE, raw_query, l_mon, r_mon,
                                     l_query, r_query, l_query_settings, r_query_settings)
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
        return (await friend_cog.get_friends(original_author_id)) if friend_cog else []

    @commands.command(aliases=['lssingle'])
    @checks.bot_has_permissions(embed_links=True)
    async def leaderskillsingle(self, ctx, *, query):
        dbcog = await self.get_dbcog()
        monster = await dbcog.find_monster(query, ctx.author.id)
        if not monster:
            await self.send_id_failure_message(ctx, query)
            return

        query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, query)

        original_author_id = ctx.message.author.id
        state = LeaderSkillSingleViewState(original_author_id, LeaderSkillSingleMenu.MENU_TYPE, query, query_settings,
                                           monster)
        menu = LeaderSkillSingleMenu.menu()
        await menu.create(ctx, state)

    @commands.command(aliases=['tfinfo', 'xforminfo'])
    @checks.bot_has_permissions(embed_links=True)
    async def transforminfo(self, ctx, *, query):
        """Show info about a transform card, including some helpful details about the base card."""
        dbcog = await self.get_dbcog()
        base_mon, transformed_mon, monster_ids = await perform_transforminfo_query(dbcog, query, ctx.author.id)

        if not base_mon:
            await self.send_id_failure_message(ctx, query)
            return

        if not transformed_mon:
            await self.send_invalid_monster_message(ctx, query, base_mon, ', which has no evos that transform')
            return

        original_author_id = ctx.message.author.id
        tfinfo_queried_props = await TransformInfoViewState.do_query(dbcog, transformed_mon)
        reaction_list = TransformInfoMenuPanes.get_user_reaction_list(len(monster_ids))
        is_jp_buffed = dbcog.database.graph.monster_is_discrepant(base_mon)
        query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, query)

        state = TransformInfoViewState(original_author_id, TransformInfoMenu.MENU_TYPE, query,
                                       base_mon, transformed_mon, tfinfo_queried_props, monster_ids,
                                       is_jp_buffed,
                                       query_settings,
                                       reaction_list=reaction_list)
        menu = TransformInfoMenu.menu()
        await menu.create(ctx, state)

    @commands.command(aliases=['awakehelp', 'awakeningshelp', 'awohelp', 'awokenhelp', 'awakeninghelp'])
    @checks.bot_has_permissions(embed_links=True)
    async def awakenings(self, ctx, *, query=None):
        """Describe a monster's regular and super awakenings in detail.

        Leave <query> blank to see a list of every awakening in the game."""
        dbcog = await self.get_dbcog()
        query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, query or '')

        if not query:
            sort_type = AwakeningListSortTypes.numerical
            paginated_skills = await AwakeningListViewState.do_query(dbcog, sort_type)
            menu = AwakeningListMenu.menu()
            state = AwakeningListViewState(ctx.message.author.id, AwakeningListMenu.MENU_TYPE, query_settings,
                                           sort_type, paginated_skills, 0,
                                           reaction_list=AwakeningListMenuPanes.get_user_reaction_list(sort_type))
            await menu.create(ctx, state)
            return

        monster = await dbcog.find_monster(query, ctx.author.id)

        if not monster:
            await self.send_id_failure_message(ctx, query)
            return

        original_author_id = ctx.message.author.id
        menu = ClosableEmbedMenu.menu()
        props = AwakeningHelpViewProps(monster=monster)
        state = ClosableEmbedViewState(original_author_id, ClosableEmbedMenu.MENU_TYPE, query,
                                       query_settings, AwakeningHelpView.VIEW_TYPE, props)
        await menu.create(ctx, state)

    @commands.command(aliases=['idhist'])
    @checks.bot_has_permissions(embed_links=True)
    async def idhistory(self, ctx):
        """Show a list of the 11 most recent monsters that the user looked up."""
        dbcog = await self.get_dbcog()
        history = await self.config.user(ctx.author).id_history()

        monster_list = [dbcog.get_monster(m) for m in history]

        if not monster_list:
            await ctx.send('Did not find any recent queries in history.')
            return
        await self._do_monster_list(ctx, dbcog, '', monster_list, 'Result History', StaticMonsterListViewState)

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

        dbcog = await self.get_dbcog()
        monster = await dbcog.find_monster(query, ctx.author.id)
        if monster is not None:
            voice_id = monster.voice_id_jp if server == 'jp' else monster.voice_id_na
            if voice_id is None:
                await ctx.send(inline("No voice file found for " + monster.name_en))
                return
            base_dir = settings.voiceDir()
            voice_file = os.path.join(base_dir, server, '{0:03d}.wav'.format(voice_id))
            header = '{} ({})'.format(MonsterHeader.text_with_emoji(monster), server)
            if not os.path.exists(voice_file):
                await ctx.send(inline('Could not find voice for ' + header))
                return
            await ctx.send('Speaking for ' + header)
            await speech_cog.play_path(channel, voice_file)
        else:
            await self.send_id_failure_message(ctx, query)

    @commands.group(aliases=['idmode'])
    async def idset(self, ctx):
        """`[p]id` settings configuration"""

    @idset.command(name="list")
    async def idset_list(self, ctx):
        """`[p]id` settings list"""
        await ctx.send("This command is still in progress!")

    @idset.command()
    async def survey(self, ctx, value):
        """How often you see the id survey

        [p]idset survey always     (Always see survey after using id)
        [p]idset survey sometimes  (See survey some of the time after using id)
        [p]idset survey never      (Never see survey after using id D:)"""
        vals = ['always', 'sometimes', 'never']
        if value in vals:
            await self.config.user(ctx.author).survey_mode.set(vals.index(value))
            await ctx.tick()
        else:
            await send_cancellation_message(
                ctx, "value must be `always`, `sometimes`, or `never`")

    @is_donor()
    @idset.command()
    async def embedcolor(self, ctx, *, color: validators.EmbedColor):
        """(DONOR ONLY) The color of all your `[p]id` embeds!

        Examples:
        [p]idset embedcolor green
        [p]idset embedcolor #a10000
        [p]idset embedcolor random

        Picking random will choose a random hex code every time you use [p]id!
        """

        async with self.bot.get_cog("DBCog").config.user(ctx.author).fm_flags() as fm_flags:
            fm_flags['embedcolor'] = color
        await ctx.tick()

    @idset.command(usage="<on/off>")
    async def naprio(self, ctx, value: bool):
        """Whether `[p]id` will default away from new evos of monsters that aren't in NA yet"""
        async with self.bot.get_cog("DBCog").config.user(ctx.author).fm_flags() as fm_flags:
            # The current na_prio enum has 0 and 1 instead of False and True as its values
            fm_flags['na_prio'] = int(value)
        await send_confirmation_message(
            ctx, f"NA monster prioritization has been **{'en' if value else 'dis'}abled**.")

    @idset.command()
    async def server(self, ctx, server: str):
        """The server used for your `[p]id` queries

        `[p]idset server default`: Include both NA & JP cards. You can still use `--na` as needed.
        `[p]idset server na`: Include only NA cards. You can still use `--allservers` as needed.
        """
        dbcog = await self.get_dbcog()
        async with self.bot.get_cog("DBCog").config.user(ctx.author).fm_flags() as fm_flags:
            if server.upper() == "DEFAULT":
                fm_flags['server'] = dbcog.DEFAULT_SERVER.value
            elif server.upper() in [s.value for s in dbcog.SERVERS]:
                fm_flags['server'] = server.upper()
            else:
                if dbcog.DEFAULT_SERVER == Server.COMBINED:
                    await send_cancellation_message(ctx, "Server must be `default` or `na`")
                else:
                    await send_cancellation_message(ctx, "Server must be `na` or `combined`")
                return
        await ctx.tick()

    @idset.command()
    async def evosort(self, ctx, value: str):
        """The order for scrolling alt evos in your `[p]id` queries

        `[p]idset evosort numerical`: Show alt evos sorted by card ID number.
        `[p]idset evosort dfs`: Show alt evos in a depth-first-sort order, starting with the base of the tree.
        """
        async with self.bot.get_cog("DBCog").config.user(ctx.author).fm_flags() as fm_flags:
            value = value.lower()
            if value == "dfs":
                fm_flags['evosort'] = AltEvoSort.dfs.value
            elif value == "numerical":
                fm_flags['evosort'] = AltEvoSort.numerical.value
            else:
                await send_cancellation_message(
                    ctx,
                    f'Please input an allowed value, either `{AltEvoSort.dfs.name}` or `{AltEvoSort.numerical.name}`.')
                return
        await send_confirmation_message(
            ctx, f"Your `{ctx.prefix}id` evo sort preference has been set to **{value}**.")

    @idset.command()
    async def lsmultiplier(self, ctx, value: str):
        """The display of LS multipliers in your `[p]id` queries

        `[p]idset lsmultiplier double`: [Default] Show leader skill multipliers assuming the card is paired with itself.
        `[p]idset lsmultiplier single`: Show leader skill multipliers of just the single card.
        """
        async with self.bot.get_cog("DBCog").config.user(ctx.author).fm_flags() as fm_flags:
            value = value.lower()
            if value == "double":
                fm_flags['lsmultiplier'] = LsMultiplier.lsdouble.value
                not_value = 'single'
                not_value_flag = 'lssingle'
            elif value == "single":
                fm_flags['lsmultiplier'] = LsMultiplier.lssingle.value
                not_value = 'double'
                not_value_flag = 'lsdouble'
            else:
                await send_cancellation_message(
                    ctx,
                    f'Please input an allowed value, either `double` or `single`.')
                return
        await send_confirmation_message(
            ctx,
            f"Your default `{ctx.prefix}id` lsmultiplier preference has been set to **{value}**. You can temporarily access `{not_value}` with the flag `--{not_value_flag}` in your queries.")

    @idset.command()
    async def cardplus(self, ctx, value: str):
        """The monster stat plus points amount in your `[p]id` queries

        `[p]idset cardplus 297`: [Default] Show cards with +297 stats.
        `[p]idset cardplus 0`: Show cards with +0 stats.
        """
        async with self.bot.get_cog("DBCog").config.user(ctx.author).fm_flags() as fm_flags:
            value = value.lower()
            if value == "297":
                fm_flags['cardplus'] = CardPlusModifier.plus297.value
                not_value = '0'
                not_value_flag = 'plus0'
            elif value == "0":
                fm_flags['cardplus'] = CardPlusModifier.plus0.value
                not_value = '297'
                not_value_flag = 'plus297'
            else:
                await send_cancellation_message(
                    ctx,
                    f'Please input an allowed value, either `297` or `0`.')
                return
        await send_confirmation_message(
            ctx,
            f"Your default `{ctx.prefix}id` cardplus preference has been set to **{value}**. You can temporarily access `{not_value}` with the flag `--{not_value_flag}` in your queries.")

    @idset.command()
    async def cardmode(self, ctx, value: str):
        """Switch between solo and coop

        `[p]idset mode solo`: [Default] Show cards with stats in solo
        `[p]idset mode coop`: Show cards with stats in coop (i.e. multiboost)
        """
        async with self.bot.get_cog("DBCog").config.user(ctx.author).fm_flags() as fm_flags:
            value = value.lower()
            if value == "solo":
                fm_flags['cardmode'] = CardModeModifier.solo.value
                not_value = 'coop'
                not_value_flag = 'coop'
            elif value == "coop":
                fm_flags['cardmode'] = CardModeModifier.coop.value
                not_value = 'solo'
                not_value_flag = 'solo'
            else:
                await send_cancellation_message(
                    ctx,
                    f'Please input an allowed value, either `coop` or `solo`.')
                return
        await send_confirmation_message(
            ctx,
            f"Your default `{ctx.prefix}id` cardmode preference has been set to **{value}**. You can temporarily access `{not_value}` with the flag `--{not_value_flag}` in your queries.")

    @idset.command()
    async def cardlevel(self, ctx, value: str):
        """The limitbreak level in your `[p]id` queries

        `[p]idset cardlevel 110`: [Default] Show LB stats at 110.
        `[p]idset cardlevel 120`: Show LB stats at 120.
        """
        async with self.bot.get_cog("DBCog").config.user(ctx.author).fm_flags() as fm_flags:
            value = value.lower()
            if value == "120":
                fm_flags['cardlevel'] = CardLevelModifier.lv120.value
                not_value = '110'
                not_value_flag = 'lv110'
            elif value == "110":
                fm_flags['cardlevel'] = CardLevelModifier.lv110.value
                not_value = '120'
                not_value_flag = 'lv120'
            else:
                await send_cancellation_message(
                    ctx,
                    f'Please input an allowed value, either `110` or `120`.')
                return
        await send_confirmation_message(
            ctx,
            f"Your default `{ctx.prefix}id` cardlevel preference has been set to **{value}**. You can temporarily access `{not_value}` with the flag `--{not_value_flag}` in your queries.")

    @idset.command()
    async def evogrouping(self, ctx, value: str):
        """If trees are combined in your `[p]ids` queries

        `[p]idset evogrouping grouped`: [Default] Show trees grouped.
        `[p]idset evogrouping split`: Show individual evos of trees split apart.
        """
        async with self.bot.get_cog("DBCog").config.user(ctx.author).fm_flags() as fm_flags:
            value = value.lower()
            if value == "split":
                fm_flags['evogrouping'] = EvoGrouping.splitevos.value
                not_value = 'grouped'
                not_value_flag = 'groupevos'
            elif value == "grouped":
                fm_flags['evogrouping'] = EvoGrouping.groupevos.value
                not_value = 'split'
                not_value_flag = 'splitevos'
            else:
                await send_cancellation_message(
                    ctx,
                    f'Please input an allowed value, either `grouped` or `split`.')
                return
        await send_confirmation_message(
            ctx,
            f"Your default `{ctx.prefix}id` cardlevel preference has been set to **{value}**. You can temporarily access `{not_value}` with the flag `--{not_value_flag}` in your queries.")

    @idset.command()
    async def linktarget(self, ctx, value: str):
        """Monster link targets in your `[p]ids` queries

        `[p]idset linktarget padindex`: [Default] Link to PADIndex always.
        `[p]idset linktarget ilmina`: Link to Ilmina for cards that are in NA.
        """
        setting_name = 'linktarget'
        value1 = 'padindex'
        value1_flag = 'padindex'
        value2 = 'ilmina'
        value2_flag = 'ilmina'
        async with self.bot.get_cog("DBCog").config.user(ctx.author).fm_flags() as fm_flags:
            value = value.lower()
            if value == value1:
                fm_flags[setting_name] = MonsterLinkTarget.padindex.value
                not_value = value2
                not_value_flag = value2_flag
            elif value == value2:
                fm_flags[setting_name] = MonsterLinkTarget.ilmina.value
                not_value = value1
                not_value_flag = value1_flag
            else:
                await send_cancellation_message(
                    ctx,
                    f'Please input an allowed value, either `{value1}` or `{value2}`.')
                return
        await send_confirmation_message(
            ctx,
            f"Your default `{ctx.prefix}id` {setting_name} preference has been set to **{value}**. You can temporarily access `{not_value}` with the flag `--{not_value_flag}` in your queries.")

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
    async def debugid(self, ctx, server: Optional[Server] = Server.COMBINED, *, query):
        """Get helpful id information about a monster"""
        dbcog = await self.get_dbcog()
        mon = await dbcog.find_monster(query, ctx.author.id)
        if mon is None:
            await ctx.send(box("Your query didn't match any monsters."))
            return
        base_monster = dbcog.database.graph.get_base_monster(mon)
        mods = dbcog.indexes[server].modifiers[mon]
        manual_modifiers = dbcog.indexes[server].manual_modifiers[mon.monster_id]
        EVOANDTYPE = dbcog.token_maps.EVO_TOKENS.union(dbcog.token_maps.TYPE_TOKENS)
        ret = (f"[{mon.monster_id}] {mon.name_en}\n"
               f"Base: [{base_monster.monster_id}] {base_monster.name_en}\n"
               f"Series: {mon.series.name_en} ({mon.series_id}, {mon.series.series_type})\n\n"
               f"[Name Tokens] {' '.join(sorted(t for t, ms in dbcog.indexes[server].name_tokens.items() if mon in ms))}\n"
               f"[Fluff Tokens] {' '.join(sorted(t for t, ms in dbcog.indexes[server].fluff_tokens.items() if mon in ms))}\n\n"
               f"[Manual Tokens]\n"
               f"     Treenames: {' '.join(sorted(t for t, ms in dbcog.indexes[server].manual_treenames.items() if mon in ms))}\n"
               f"     Nicknames: {' '.join(sorted(t for t, ms in dbcog.indexes[server].manual_cardnames.items() if mon in ms))}\n\n"
               f"[Modifier Tokens]\n"
               f"     Attribute: {' '.join(sorted(t for t in mods if t in dbcog.token_maps.COLOR_TOKENS))}\n"
               f"     Awakening: {' '.join(sorted(t for t in mods if t in dbcog.token_maps.AWAKENING_TOKENS))}\n"
               f"    Evo & Type: {' '.join(sorted(t for t in mods if t in EVOANDTYPE))}\n"
               f"         Other: {' '.join(sorted(t for t in mods if t not in dbcog.token_maps.OTHER_HIDDEN_TOKENS))}\n"
               f"Manually Added: {' '.join(sorted(manual_modifiers))}\n")
        for page in pagify(ret):
            await ctx.send(box(page))

    @commands.command()
    async def debugiddist(self, ctx, s1, s2):
        """Find the distance between two queries.

        For name tokens, the full word goes second as name token matching is not commutitive
        """

        dbcog = await self.get_dbcog()

        dist = dbcog.mon_finder.calc_ratio_modifier(s1, s2)
        dist2 = dbcog.mon_finder.calc_ratio_name(s1, s2)
        yes = '\N{WHITE HEAVY CHECK MARK}'
        no = '\N{CROSS MARK}'
        await ctx.send(f"Printing info for {inline(s1)}, {inline(s2)}\n" +
                       box(f"Jaro-Winkler Distance:    {round(dist, 4)}\n"
                           f"Name Matching Distance:   {round(dist2, 4)}\n"
                           f"Modifier token threshold: {dbcog.mon_finder.MODIFIER_JW_DISTANCE}  "
                           f"{yes if dist >= dbcog.mon_finder.MODIFIER_JW_DISTANCE else no}\n"
                           f"Name token threshold:     {dbcog.mon_finder.TOKEN_JW_DISTANCE}   "
                           f"{yes if dist2 >= dbcog.mon_finder.TOKEN_JW_DISTANCE else no}"))

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
    async def exportmodifiers(self, ctx, server: LiteralConverter["COMBINED", "NA"] = "COMBINED"):
        server = Server(server)
        DGCOG = await self.get_dbcog()
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
                  for k, v in DGCOG.indexes[server].series_id_to_pantheon_nickname.items()]
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
    async def idmeaning(self, ctx, token, server: Optional[Server] = Server.COMBINED):
        """Get all the meanings of a token (bold signifies base of a tree)"""
        token = token.replace(" ", "")
        DGCOG = await self.get_dbcog()

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
                if (mon in DGCOG.indexes[server].mwtoken_creators[token]) == is_multiword:
                    so.append(mon)
            if len(so) > 5:
                token_ret += f"\n\n{token_type}\n" + ", ".join(f(m, str(m.monster_id)) for m in so[:10])
                token_ret += f"... ({len(so)} total)" if len(so) > 10 else ""
            elif so:
                token_ret += f"\n\n{token_type}\n" + "\n".join(
                    f(m, f"{str(m.monster_id).rjust(4)}. {m.name_en}") for m in so)
            return token_ret

        ret += write_name_token(DGCOG.indexes[server].manual, "\N{LARGE PURPLE CIRCLE} [Multi-Word Tokens]", True)
        ret += write_name_token(DGCOG.indexes[server].manual, "[Manual Tokens]")
        ret += write_name_token(DGCOG.indexes[server].name_tokens, "[Name Tokens]")
        ret += write_name_token(DGCOG.indexes[server].fluff_tokens, "[Fluff Tokens]")

        submwtokens = [t for t in DGCOG.indexes[server].multi_word_tokens if token in t]
        if submwtokens:
            ret += "\n\n[Multi-word Super-tokens]\n"
            for t in submwtokens:
                if not DGCOG.indexes[server].all_name_tokens[''.join(t)]:
                    continue
                creators = sorted(DGCOG.indexes[server].mwtoken_creators["".join(t)], key=lambda m: m.monster_id)
                ret += f"{' '.join(t).title()}"
                ret += f" ({', '.join(f'{m.monster_id}' for m in creators)})" if creators else ''
                ret += (" ( \u2014> " +
                        str(DGCOG.mon_finder.get_most_eligable_monster(
                            DGCOG.indexes[server].all_name_tokens[''.join(t)]).monster_id)
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
              for k, v in DGCOG.indexes[server].series_id_to_pantheon_nickname.items() if token in v],

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

        dbcog = await self.get_dbcog()

        bestmatch, matches, _, _ = await dbcog.mon_finder.find_monster_debug(query)

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
                              f" ({round(dbcog.mon_finder.calc_ratio_modifier(t[0], t[1]), 2) if t[0] != t[1] else 'exact'})"
                              for t in sorted(mtokens))
        ntokenstr = '\n'.join(f"{inline(t[0])}{(': ' + t[1]) if t[0] != t[1] else ''}"
                              f" ({round(dbcog.mon_finder.calc_ratio_name(t[0], t[1]), 2) if t[0] != t[1] else 'exact'})"
                              f" {t[2]}"
                              for t in sorted(ntokens))

        original_author_id = ctx.message.author.id
        menu = ClosableEmbedMenu.menu()
        props = IdTracebackViewProps(monster=monster, score=score, name_tokens=ntokenstr, modifier_tokens=mtokenstr,
                                     lower_priority_monsters=lpstr if lower_prio else "None")
        state = ClosableEmbedViewState(original_author_id, ClosableEmbedMenu.MENU_TYPE, query,
                                       IdTracebackView.VIEW_TYPE, props)
        await menu.create(ctx, state)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def expcurve(self, ctx, start, end: Optional[int], *, query=''):
        if start.isdigit() and end is None and not query:
            start, end, query = '', None, start

        if start.isdigit() and end is not None:
            start, offset = int(start), 0
        elif (match := re.fullmatch(r'(\d+)\[(\d*\.?\d*)]', start)) and end is not None:
            start, offset = int(match.group(1)), float(match.group(2) or '0')
        elif (end is None and not start.isdigit()) or (query and not start and not end):
            start, offset, query = 1, 0, start + ' ' + query
        else:
            return await ctx.send("Invalid syntax for argument `start`.")

        if (monster := await self._get_monster(ctx, query)) is None:
            return

        if end is None:
            end = monster.level

        if monster.exp_to_level(start + 1) - monster.exp_to_level(start) < offset and start <= 99 \
                or offset > 5e6 and start <= 110 or offset > 20e6:
            return await send_cancellation_message(ctx, "Offset too large.")
        if start <= 0 or end > 120 or end < start or (start == end and offset):
            return await send_cancellation_message(ctx, f"Invalid bounds ({start}[{offset}] - {end}).")

        header = MonsterHeader.menu_title(monster, use_emoji=True).to_markdown()
        if not monster.limit_mult and end > 99:
            return await send_cancellation_message(ctx, f"{header} cannot limit break.")
        if monster.level < end <= 99:
            return await send_cancellation_message(ctx, f"{header} cannot get to level {end} "
                                                        f"(max level {monster.level}).")

        original_author_id = ctx.message.author.id
        menu = ClosableEmbedMenu.menu()
        props = ExperienceCurveViewProps(monster=monster, low=start, high=end, offset=offset)
        state = ClosableEmbedViewState(original_author_id, ClosableEmbedMenu.MENU_TYPE, query,
                                       ExperienceCurveView.VIEW_TYPE, props)
        await menu.create(ctx, state)
