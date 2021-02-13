import asyncio
import logging
import os
import random
import re
import urllib.parse
from collections import OrderedDict
from io import BytesIO
from typing import TYPE_CHECKING, List

import discord
import tsutils
from discord import Color
from discordmenu.emoji.emoji_cache import emoji_cache
from discordmenu.intra_message_state import IntraMessageState
from redbot.core import checks, commands, data_manager, Config
from redbot.core.utils.chat_formatting import box, inline, bold, pagify, text_to_file
from tabulate import tabulate
from tsutils import EmojiUpdater, Menu, char_to_emoji, is_donor, rmdiacritics

from padinfo.MonsterListMenu import MonsterListMenu, MonsterListMenuPanes
from padinfo.common.config import BotConfig
from padinfo.common.emoji_map import get_attribute_emoji_by_enum, get_awakening_emoji, get_type_emoji, \
    get_attribute_emoji_by_monster
from padinfo.core import find_monster as fm
from padinfo.core.button_info import button_info
from padinfo.core.find_monster import find_monster, findMonster3, \
    calc_ratio_name, calc_ratio_modifier, find_monster_search, findMonsterCustom
from padinfo.core.historic_lookups import historic_lookups
from padinfo.core.leader_skills import perform_leaderskill_query
from padinfo.core.padinfo_settings import settings
from padinfo.core.transforminfo import perform_transforminfo_query
from padinfo.id_menu import IdMenu, IdMenuPanes
from padinfo.id_menu_old import IdMenu as IdMenuOld
from padinfo.idtest_mixin import IdTest
from padinfo.ls_menu import LeaderSkillMenu, emoji_button_names as ls_menu_emoji_button_names
from padinfo.pane_names import global_emoji_responses
from padinfo.tf_menu import TransformInfoMenu, emoji_button_names as tf_menu_emoji_button_names
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.reaction_list import get_id_menu_initial_reaction_list
from padinfo.view_state.evos import EvosViewState
from padinfo.view_state.id import IdViewState
from padinfo.view_state.leader_skill import LeaderSkillViewState
from padinfo.view_state.materials import MaterialsViewState
from padinfo.view_state.monster_list import MonsterListViewState
from padinfo.view_state.otherinfo import OtherInfoViewState
from padinfo.view_state.pantheon import PantheonViewState
from padinfo.view_state.pic import PicViewState
from padinfo.view_state.transforminfo import TransformInfoViewState

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel

logger = logging.getLogger('red.padbot-cogs.padinfo')

EMBED_NOT_GENERATED = -1

IDGUIDE = "https://github.com/TsubakiBotPad/pad-cogs/wiki/id-user-guide"


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


class PadInfo(commands.Cog, IdTest):
    """Info for PAD Cards"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.menu = Menu(bot)

        # These emojis are the keys into the idmenu submenus
        self.ls_emoji = '\N{HOUSE BUILDING}'
        self.left_emoji = char_to_emoji('l')
        self.right_emoji = char_to_emoji('r')
        self.remove_emoji = self.menu.emoji['no']

        self.config = Config.get_conf(self, identifier=9401770)
        self.config.register_user(survey_mode=0, color=None, beta_id3=False, lastaction=None)
        self.config.register_global(sometimes_perc=20, good=0, bad=0, do_survey=False, test_suite={}, fluff_suite=[])

        self.fm3 = lambda q: fm.findMonsterCustom(bot.get_cog("Dadguide"), q)

        self.get_attribute_emoji_by_monster = get_attribute_emoji_by_monster

    def cog_unload(self):
        """Manually nulling out database because the GC for cogs seems to be pretty shitty"""
        # TODO.... manage historic_lookups??? probably not.

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        return

    async def reload_nicknames(self):
        await self.bot.wait_until_ready()
        while self == self.bot.get_cog('PadInfo'):
            wait_time = 60 * 60 * 1
            try:
                emoji_cache.set_guild_ids([g.id for g in self.bot.guilds])
                emoji_cache.refresh_from_discord_bot(self.bot)
                dg_cog = self.bot.get_cog('Dadguide')
                await dg_cog.wait_until_ready()
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

    def get_monster(self, monster_id: int):
        dg_cog = self.bot.get_cog('Dadguide')
        return dg_cog.get_monster(monster_id)

    @commands.Cog.listener('on_reaction_add')
    async def test_reaction_add(self, reaction, member):
        emoji_obj = reaction.emoji
        if isinstance(emoji_obj, str):
            emoji_clicked = emoji_obj
        else:
            emoji_clicked = emoji_obj.name

        if not (emoji_clicked in ls_menu_emoji_button_names or
                emoji_clicked in IdMenuPanes.emoji_names() or
                emoji_clicked in MonsterListMenuPanes.emoji_names() or
                emoji_clicked in tf_menu_emoji_button_names):
            return

        message = reaction.message
        ims = message.embeds and IntraMessageState.extract_data(message.embeds[0])
        if not ims:
            return

        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        menu_map = {
            LeaderSkillMenu.MENU_TYPE: LeaderSkillMenu.menu,
            IdMenu.MENU_TYPE: IdMenu.menu,
            TransformInfoMenu.MENU_TYPE: TransformInfoMenu.menu,
            MonsterListMenu.MENU_TYPE: MonsterListMenu.menu,
        }

        respond_with_child = [
            (MonsterListMenu.MENU_TYPE, '\N{EYES}')
        ]

        menu_func = menu_map.get(menu_type)

        if not menu_func:
            return

        friend_cog = self.bot.get_cog("Friend")
        friends = (await friend_cog.get_friends(original_author_id)) if friend_cog else []
        embed_menu = menu_func(original_author_id, friends, self.bot.user.id)
        if not (await embed_menu.should_respond(message, reaction, member)):
            return

        dgcog = await self.get_dgcog()
        user_config = await BotConfig.get_user(self.config, original_author_id)
        data = {
            'dgcog': dgcog,
            'user_config': user_config
        }
        if ims.get('child_message_id') and (ims['menu_type'], emoji_clicked) in respond_with_child:
            await message.remove_reaction(emoji_clicked, member)
            fctx = await self.bot.get_context(message)
            child_message = await fctx.fetch_message(int(ims['child_message_id']))
            child_message_ims = child_message.embeds and IntraMessageState.extract_data(child_message.embeds[0])
            if child_message_ims:
                data['child_message_ims'] = child_message_ims
            ims['menu_type'] = IdMenu.MENU_TYPE
            
            # The order here is really important!! The set of emojis attached to the ims is going to be changed in
            # the second transition, so it's VITAL that we reset prior to showing the child menu.
            # It's also better from a perceived performance standard becuase the emojis are so rate-limited and
            # the reset wouldn't happen until all emojis showed up in the child, so this way it feels like everything
            # happens faster, but regardless the reset must happen first.
            await embed_menu.transition(message, ims, global_emoji_responses['reset'], member, **data)
            await embed_menu.transition(child_message, ims, emoji_clicked, member, **data)
            return
        await embed_menu.transition(message, ims, emoji_clicked, member, **data)

    @commands.command()
    async def jpname(self, ctx, *, query: str):
        """Show the Japanese name of a monster"""
        dgcog = await self.get_dgcog()
        m, err, debug_info = await findMonsterCustom(dgcog, query)
        if m is not None:
            await ctx.send(MonsterHeader.short(m))
            await ctx.send(box(m.name_ja))
        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command(name="id", aliases=["iD", "Id", "ID"])
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
        friend_cog = self.bot.get_cog("Friend")
        friends = (await friend_cog.get_friends(original_author_id)) if friend_cog else []

        goodquery = None
        if query[0] in dgcog.token_maps.ID1_SUPPORTED and query[1:] in dgcog.index2.all_name_tokens:
            goodquery = [query[0], query[1:]]
        elif query[:2] in dgcog.token_maps.ID1_SUPPORTED and query[2:] in dgcog.index2.all_name_tokens:
            goodquery = [query[:2], query[2:]]

        if goodquery:
            bad = False
            for m in dgcog.index2.all_name_tokens[goodquery[1]]:
                for p in dgcog.index2.modifiers[m]:
                    if p == 'xm' and goodquery[0] == 'x':
                        goodquery[0] = 'xm'
                    if p == goodquery[0]:
                        bad = True
            if bad and query not in dgcog.index2.all_name_tokens:
                await ctx.send(f"Uh oh, it looks like you tried a query that isn't supported anymore!"
                               f" Try using `{' '.join(goodquery)}` (with a space) instead! For more"
                               f" info about `id3` check out"
                               f" <{IDGUIDE}>!")

        monster, err, debug_info = await findMonsterCustom(dgcog, raw_query)

        if not monster:
            await self.makeFailureMsg(ctx, query, err)
            return

        async def send_error(error):
            if error:
                await asyncio.sleep(1)
                await ctx.send(error)

        asyncio.create_task(send_error(err))

        # id3 messaging stuff
        if monster and monster.monster_no_na != monster.monster_no_jp:
            await ctx.send("The NA ID and JP ID of this card differ! "
                           "The JP ID is 1053 you can query with {0.prefix}id jp1053.".format(ctx) +
                           (" Make sure you use the **JP id number** when updating the Google doc!!!!!" if
                            ctx.author.id in self.bot.get_cog("PadGlobal").settings.bot_settings['admins'] else ""))

        if await self.config.do_survey():
            asyncio.create_task(self.send_survey_after(ctx, query, monster))

        transform_base, true_evo_type_raw, acquire_raw, base_rarity, alt_monsters = \
            await IdViewState.query(dgcog, monster)
        full_reaction_list = [emoji_cache.get_by_name(e) for e in IdMenuPanes.emoji_names()]
        initial_reaction_list = await get_id_menu_initial_reaction_list(ctx, dgcog, monster, full_reaction_list)

        state = IdViewState(original_author_id, IdMenu.MENU_TYPE, raw_query, query, color,
                            monster, transform_base, true_evo_type_raw, acquire_raw, base_rarity, alt_monsters,
                            use_evo_scroll=settings.checkEvoID(ctx.author.id),
                            reaction_list=initial_reaction_list)
        menu = IdMenu.menu(original_author_id, friends, self.bot.user.id)
        await menu.create(ctx, state)

    async def send_survey_after(self, ctx, query, result_monster):
        dgcog = await self.get_dgcog()
        sm = await self.config.user(ctx.author).survey_mode()
        sms = [1, await self.config.sometimes_perc() / 100, 0][sm]
        if random.random() < sms:
            mid1 = historic_lookups.get(query)
            m1 = mid1 and dgcog.get_monster(mid1)
            id1res = "Not Historic" if mid1 is None else f"{m1.name_en} ({m1.monster_id})" if mid1 > 0 else "None"
            id3res = f"{result_monster.name_en} ({result_monster.monster_id})" if result_monster else "None"
            params = urllib.parse.urlencode(
                {'usp': 'pp_url', 'entry.154088017': query, 'entry.173096863': id3res, 'entry.1016180044': id1res})
            url = "https://docs.google.com/forms/d/e/1FAIpQLSeA2EBYiZTOYfGLNtTHqYdL6gMZrfurFZonZ5dRQa3XPHP9yw/viewform?" + params
            await asyncio.sleep(1)
            userres = await tsutils.confirm_message(ctx, "Was this the monster you were looking for?",
                                                    yemoji=char_to_emoji('y'), nemoji=char_to_emoji('n'))
            if userres is True:
                await self.config.good.set(await self.config.good() + 1)
            elif userres is False:
                await self.config.bad.set(await self.config.bad() + 1)
                m = await ctx.send(f"Oh no!  You can help the Tsubaki team give better results"
                                   f" by filling out this survey!\nPRO TIP: Use `{ctx.prefix}idset"
                                   f" survey` to adjust how often this shows.\n\n<{url}>")
                await asyncio.sleep(15)
                await m.delete()

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
    async def id2(self, ctx, *, query: str):
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
        friend_cog = self.bot.get_cog("Friend")
        friends = (await friend_cog.get_friends(original_author_id)) if friend_cog else []

        monster, err, debug_info = await findMonsterCustom(dgcog, raw_query)

        if monster is None:
            await self.makeFailureMsg(ctx, query, err)
            return

        alt_versions, gem_versions = await EvosViewState.query(dgcog, monster)

        if alt_versions is None:
            await ctx.send('Your query `{}` found [{}] {}, '.format(query, monster.monster_id,
                                                                    monster.name_en) + 'which has no alt evos or gems.')
            return

        full_reaction_list = [emoji_cache.get_by_name(e) for e in IdMenuPanes.emoji_names()]
        initial_reaction_list = await get_id_menu_initial_reaction_list(ctx, dgcog, monster, full_reaction_list)

        state = EvosViewState(original_author_id, IdMenu.MENU_TYPE, raw_query, query, color,
                              monster, alt_versions, gem_versions,
                              reaction_list=initial_reaction_list,
                              use_evo_scroll=settings.checkEvoID(ctx.author.id))
        menu = IdMenu.menu(original_author_id, friends, self.bot.user.id, initial_control=IdMenu.evos_control)
        await menu.create(ctx, state)

    @commands.command(name="mats", aliases=['evomats', 'evomat', 'skillups'])
    @checks.bot_has_permissions(embed_links=True)
    async def evomats(self, ctx, *, query: str):
        """Monster info (evo materials tab)"""
        dgcog = await self.get_dgcog()
        raw_query = query
        color = await self.get_user_embed_color(ctx)
        original_author_id = ctx.message.author.id
        friend_cog = self.bot.get_cog("Friend")
        friends = (await friend_cog.get_friends(original_author_id)) if friend_cog else []
        monster, err, debug_info = await findMonsterCustom(dgcog, raw_query)

        if not monster:
            await self.makeFailureMsg(ctx, query, err)
            return

        mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link, gem_override = \
            await MaterialsViewState.query(dgcog, monster)

        if mats is None:
            await ctx.send(inline("This monster has no mats or skillups and isn't used in any evolutions"))
            return

        full_reaction_list = [emoji_cache.get_by_name(e) for e in IdMenuPanes.emoji_names()]
        initial_reaction_list = await get_id_menu_initial_reaction_list(ctx, dgcog, monster, full_reaction_list)

        state = MaterialsViewState(original_author_id, IdMenu.MENU_TYPE, raw_query, query, color, monster,
                                   mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link, gem_override,
                                   reaction_list=initial_reaction_list,
                                   use_evo_scroll=settings.checkEvoID(ctx.author.id))
        menu = IdMenu.menu(original_author_id, friends, self.bot.user.id, initial_control=IdMenu.mats_control)
        await menu.create(ctx, state)

    @commands.command(aliases=["series"])
    @checks.bot_has_permissions(embed_links=True)
    async def pantheon(self, ctx, *, query: str):
        """Monster info (pantheon tab)"""
        dgcog = await self.get_dgcog()
        raw_query = query
        color = await self.get_user_embed_color(ctx)
        original_author_id = ctx.message.author.id
        friend_cog = self.bot.get_cog("Friend")
        friends = (await friend_cog.get_friends(original_author_id)) if friend_cog else []

        monster, err, debug_info = await findMonsterCustom(dgcog, raw_query)

        if monster is None:
            await self.makeFailureMsg(ctx, query, err)
            return

        pantheon_list, series_name = await PantheonViewState.query(dgcog, monster)
        if pantheon_list is None:
            await ctx.send(inline('Too many monsters in this series to display'))
            return

        full_reaction_list = [emoji_cache.get_by_name(e) for e in IdMenuPanes.emoji_names()]
        initial_reaction_list = await get_id_menu_initial_reaction_list(ctx, dgcog, monster, full_reaction_list)

        state = PantheonViewState(original_author_id, IdMenu.MENU_TYPE, raw_query, query, color,
                                  monster, pantheon_list, series_name,
                                  reaction_list=initial_reaction_list,
                                  use_evo_scroll=settings.checkEvoID(ctx.author.id))
        menu = IdMenu.menu(original_author_id, friends, self.bot.user.id, initial_control=IdMenu.pantheon_control)
        await menu.create(ctx, state)

    async def _do_menu(self, ctx, starting_menu_emoji, emoji_to_embed, timeout=30):
        if starting_menu_emoji not in emoji_to_embed.emoji_dict:
            # Selected menu wasn't generated for this monster
            return EMBED_NOT_GENERATED

        emoji_to_embed.emoji_dict[self.remove_emoji] = self.menu.reaction_delete_message

        try:
            result_msg, result_embed = await self.menu.custom_menu(ctx, emoji_to_embed,
                                                                   starting_menu_emoji, timeout=timeout)
            if result_msg and result_embed:
                # Message is finished but not deleted, clear the footer
                result_embed.set_footer(text=discord.Embed.Empty)
                await result_msg.edit(embed=result_embed)
        except Exception as ex:
            logger.error('Menu failure', exc_info=True)

    @commands.command(aliases=['img'])
    @checks.bot_has_permissions(embed_links=True)
    async def pic(self, ctx, *, query: str):
        """Monster info (full image tab)"""
        dgcog = await self.get_dgcog()
        raw_query = query
        color = await self.get_user_embed_color(ctx)
        original_author_id = ctx.message.author.id
        friend_cog = self.bot.get_cog("Friend")
        friends = (await friend_cog.get_friends(original_author_id)) if friend_cog else []

        monster, err, debug_info = await findMonsterCustom(dgcog, raw_query)

        if monster is None:
            await self.makeFailureMsg(ctx, query, err)
            return

        full_reaction_list = [emoji_cache.get_by_name(e) for e in IdMenuPanes.emoji_names()]
        initial_reaction_list = await get_id_menu_initial_reaction_list(ctx, dgcog, monster, full_reaction_list)

        state = PicViewState(original_author_id, IdMenu.MENU_TYPE, raw_query, query, color,
                             monster,
                             reaction_list=initial_reaction_list,
                             use_evo_scroll=settings.checkEvoID(ctx.author.id))
        menu = IdMenu.menu(original_author_id, friends, self.bot.user.id, initial_control=IdMenu.pic_control)
        await menu.create(ctx, state)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def links(self, ctx, *, query: str):
        """Monster links"""
        dgcog = await self.get_dgcog()
        m, err, debug_info = await findMonsterCustom(dgcog, query)
        if m is not None:
            menu = IdMenuOld(ctx)
            embed = await menu.make_links_embed(m)
            await ctx.send(embed=embed)

        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command(aliases=['stats'])
    @checks.bot_has_permissions(embed_links=True)
    async def otherinfo(self, ctx, *, query: str):
        """Monster info (misc info tab)"""
        dgcog = await self.get_dgcog()
        raw_query = query
        color = await self.get_user_embed_color(ctx)
        original_author_id = ctx.message.author.id
        friend_cog = self.bot.get_cog("Friend")
        friends = (await friend_cog.get_friends(original_author_id)) if friend_cog else []

        monster, err, debug_info = await findMonsterCustom(dgcog, raw_query)

        if monster is None:
            await self.makeFailureMsg(ctx, query, err)
            return

        full_reaction_list = [emoji_cache.get_by_name(e) for e in IdMenuPanes.emoji_names()]
        initial_reaction_list = await get_id_menu_initial_reaction_list(ctx, dgcog, monster, full_reaction_list)

        state = OtherInfoViewState(original_author_id, IdMenu.MENU_TYPE, raw_query, query, color,
                                   monster,
                                   reaction_list=initial_reaction_list,
                                   use_evo_scroll=settings.checkEvoID(ctx.author.id))
        menu = IdMenu.menu(original_author_id, friends, self.bot.user.id, initial_control=IdMenu.otherinfo_control)
        await menu.create(ctx, state)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def buttoninfo(self, ctx, *, query: str):
        """Button farming theorycrafting info"""
        dgcog = await self.get_dgcog()
        monster, err, _ = await findMonsterCustom(dgcog, query)
        if monster is None:
            await self.makeFailureMsg(ctx, query, err)
            return
        DGCOG = self.bot.get_cog("Dadguide")
        info = button_info.get_info(DGCOG, monster)
        info_str = button_info.to_string(monster, info)
        for page in pagify(info_str):
            await ctx.send(box(page))

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def lookup(self, ctx, *, query: str):
        """Short info results for a monster query"""
        dgcog = await self.get_dgcog()
        m, err, debug_info = await findMonsterCustom(dgcog, query)
        if m is not None:
            menu = IdMenuOld(ctx, allowed_emojis=self.get_emojis())
            embed = await menu.make_lookup_embed(m)
            await ctx.send(embed=embed)
        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def evolist(self, ctx, *, query):
        dgcog = await self.get_dgcog()
        monster, err, debug_info = await findMonsterCustom(dgcog, query)

        if monster is None:
            await self.makeFailureMsg(ctx, query, err)
            return

        alt_versions, _ = await EvosViewState.query(dgcog, monster)
        if alt_versions is None:
            await ctx.send('Your query `{}` found [{}] {}, '.format(query, monster.monster_id,
                                                                    monster.name_en) + 'which has no alt evos.')
            return
        await self._do_monster_list(ctx, dgcog, query, alt_versions)

    async def _do_monster_list(self, ctx, dgcog, query, monster_list: List["MonsterModel"]):
        raw_query = query
        original_author_id = ctx.message.author.id
        friend_cog = self.bot.get_cog("Friend")
        friends = (await friend_cog.get_friends(original_author_id)) if friend_cog else []
        color = await self.get_user_embed_color(ctx)
        initial_reaction_list = MonsterListMenuPanes.get_initial_reaction_list(len(monster_list))

        state = MonsterListViewState(original_author_id, MonsterListMenu.MENU_TYPE, raw_query, query, color,
                                     monster_list, 'Evolution List',
                                     reaction_list=initial_reaction_list
                                     )
        parent_menu = MonsterListMenu.menu(original_author_id, friends, self.bot.user.id)
        message = await parent_menu.create(ctx, state)
        child_message = await ctx.send('Click \N{EYES} to see a full menu embedded here.')
        ims = state.serialize()
        user_config = await BotConfig.get_user(self.config, ctx.author.id)
        data = {
            'dgcog': dgcog,
            'user_config': user_config,
            'child_message_id': child_message.id,
        }
        try:
            await parent_menu.transition(message, ims, MonsterListMenuPanes.emoji_name_to_emoji('refresh'), ctx.author, **data)
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
        l_err, l_mon, l_query, r_err, r_mon, r_query = await perform_leaderskill_query(dgcog, raw_query)

        err_msg = '{} query failed to match a monster: [ {} ]. If your query is multiple words, try separating the queries with / or wrap with quotes.'
        if l_err:
            await ctx.send(inline(err_msg.format('Left', l_query)))
            return
        if r_err:
            await ctx.send(inline(err_msg.format('Right', r_query)))
            return

        color = await self.get_user_embed_color(ctx)
        original_author_id = ctx.message.author.id
        friend_cog = self.bot.get_cog("Friend")
        friends = friend_cog and (await friend_cog.get_friends(original_author_id))
        state = LeaderSkillViewState(original_author_id, LeaderSkillMenu.MENU_TYPE, raw_query, color, l_mon, r_mon,
                                     l_query, r_query)
        menu = LeaderSkillMenu.menu(original_author_id, friends, self.bot.user.id)
        await menu.create(ctx, state)

    async def get_user_embed_color(self, ctx):
        color = await self.config.user(ctx.author).color()
        return self.user_color_to_discord_color(color)

    def user_color_to_discord_color(self, color):
        if color is None:
            return Color.default()
        elif color == "random":
            return Color(random.randint(0x000000, 0xffffff))
        else:
            return discord.Color(color)

    @commands.command(aliases=['lssingle'])
    @checks.bot_has_permissions(embed_links=True)
    async def leaderskillsingle(self, ctx, *, query):
        dgcog = await self.get_dgcog()
        m, err, debug_info = await findMonsterCustom(dgcog, query)
        if err:
            await ctx.send(err)
            return
        menu = IdMenuOld(ctx, dgcog=dgcog, allowed_emojis=self.get_emojis())
        emoji_to_embed = OrderedDict()
        emoji_to_embed[self.ls_emoji] = await menu.make_lssingle_embed(m)
        emoji_to_embed[self.left_emoji] = await menu.make_id_embed(m)

        await self._do_menu(ctx, self.ls_emoji, EmojiUpdater(emoji_to_embed))

    @commands.command(aliases=['tfinfo', 'xforminfo'])
    @checks.bot_has_permissions(embed_links=True)
    async def transforminfo(self, ctx, *, query):
        """Show info about a transform card, including some helpful details about the base card."""
        dgcog = await self.get_dgcog()
        base_mon, err, debug_info, transformed_mon = \
            await perform_transforminfo_query(dgcog, query)

        if not base_mon:
            await self.makeFailureMsg(ctx, query, err)
            return

        if not transformed_mon:
            await ctx.send('Your query `{}` found [{}] {}, '.format(query, base_mon.monster_id,
                                                                    base_mon.name_en) + 'which has no evos that transform.')
            return

        if err:
            await ctx.send(err)
            return

        color = await self.get_user_embed_color(ctx)
        original_author_id = ctx.message.author.id
        friend_cog = self.bot.get_cog("Friend")
        friends = (await friend_cog.get_friends(original_author_id)) if friend_cog else []
        acquire_raw, base_rarity, true_evo_type_raw = \
            await TransformInfoViewState.query(dgcog, base_mon, transformed_mon)
        state = TransformInfoViewState(original_author_id, TransformInfoMenu.MENU_TYPE, query,
                                       color, base_mon, transformed_mon, base_rarity, acquire_raw,
                                       true_evo_type_raw)
        menu = TransformInfoMenu.menu(original_author_id, friends, self.bot.user.id)
        await menu.create(ctx, state)

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
        m, err, debug_info = await findMonsterCustom(dgcog, query)
        if m is not None:
            voice_id = m.voice_id_jp if server == 'jp' else m.voice_id_na
            if voice_id is None:
                await ctx.send(inline("No voice file found for " + m.name_en))
                return
            base_dir = settings.voiceDir()
            voice_file = os.path.join(base_dir, server, '{0:03d}.wav'.format(voice_id))
            header = '{} ({})'.format(MonsterHeader.short(m), server)
            if not os.path.exists(voice_file):
                await ctx.send(inline('Could not find voice for ' + header))
                return
            await ctx.send('Speaking for ' + header)
            await speech_cog.play_path(channel, voice_file)
        else:
            await self.makeFailureMsg(ctx, query, err)

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

    @idset.command()
    async def beta(self, ctx, *, text=""):
        """Discontinued"""
        await ctx.send(f"`id3 `is now enabled globally, see"
                       f" <{IDGUIDE}> for more information.")

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
        ess = settings.emojiServers()
        if server_id not in ess:
            ess.append(server_id)
            settings.save_settings()
        await ctx.tick()

    @emojiservers.command(name="remove", aliases=['rm', 'del'])
    @checks.is_owner()
    async def es_rm(self, ctx, server_id: int):
        """Remove the emoji server by ID"""
        ess = settings.emojiServers()
        if server_id not in ess:
            await ctx.send("That emoji server is not set.")
            return
        ess.remove(server_id)
        settings.save_settings()
        await ctx.tick()

    @emojiservers.command(name="list", aliases=['show'])
    @checks.is_owner()
    async def es_show(self, ctx):
        """List the emoji servers by ID"""
        ess = settings.emojiServers()
        await ctx.send(box("\n".join(str(s) for s in ess)))

    @padinfo.command()
    @checks.is_owner()
    async def setvoicepath(self, ctx, *, path=''):
        """Set path to the voice direcory"""
        settings.setVoiceDir(path)
        await ctx.tick()

    def get_emojis(self):
        server_ids = [int(sid) for sid in settings.emojiServers()]
        return [e for g in self.bot.guilds if g.id in server_ids for e in g.emojis]

    async def makeFailureMsg(self, ctx, query: str, err):
        await ctx.send("Sorry, your query {0} didn't match any results :(\n"
                       "See <{2}> for "
                       "documentation on `{1.prefix}id`! You can also  run `{1.prefix}idhelp <monster id>` to get "
                       "help with querying a specific monster.".format(inline(query), ctx, IDGUIDE))

    @commands.command(aliases=["iddebug"])
    async def debugid(self, ctx, *, query):
        """Get helpful id information about a monster"""
        dgcog = self.bot.get_cog("Dadguide")
        m = await findMonster3(dgcog, query)
        if m is None:
            await ctx.send(box("Your query didn't match any monsters."))
            return
        bm = dgcog.database.graph.get_base_monster(m)
        pfxs = dgcog.index2.modifiers[m]
        manmods = dgcog.index2.manual_prefixes[m.monster_id]
        EVOANDTYPE = dgcog.token_maps.EVO_TOKENS.union(dgcog.token_maps.TYPE_TOKENS)
        o = (f"[{m.monster_id}] {m.name_en}\n"
             f"Base: [{bm.monster_id}] {bm.name_en}\n"
             f"Series: {m.series.name_en} ({m.series_id}, {m.series.series_type})\n\n"
             f"[Name Tokens] {' '.join(sorted(t for t, ms in dgcog.index2.name_tokens.items() if m in ms))}\n"
             f"[Fluff Tokens] {' '.join(sorted(t for t, ms in dgcog.index2.fluff_tokens.items() if m in ms))}\n\n"
             f"[Manual Tokens]\n"
             f"     Treenames: {' '.join(sorted(t for t, ms in dgcog.index2.manual_tree.items() if m in ms))}\n"
             f"     Nicknames: {' '.join(sorted(t for t, ms in dgcog.index2.manual_nick.items() if m in ms))}\n\n"
             f"[Modifier Tokens]\n"
             f"     Attribute: {' '.join(sorted(t for t in pfxs if t in dgcog.token_maps.COLOR_TOKENS))}\n"
             f"     Awakening: {' '.join(sorted(t for t in pfxs if t in dgcog.token_maps.AWAKENING_TOKENS))}\n"
             f"    Evo & Type: {' '.join(sorted(t for t in pfxs if t in EVOANDTYPE))}\n"
             f"         Other: {' '.join(sorted(t for t in pfxs if t not in dgcog.token_maps.OTHER_HIDDEN_TOKENS))}\n"
             f"Manually Added: {' '.join(sorted(manmods))}\n")
        for page in pagify(o):
            await ctx.send(box(page))

    @commands.command()
    async def debugiddist(self, ctx, s1, s2):
        """Find the distance between two queries.

        For name tokens, the full word goes second as name token matching is not commutitive
        """

        dgcog = self.bot.get_cog("Dadguide")

        dist = calc_ratio_modifier(s1, s2)
        dist2 = calc_ratio_name(s1, s2, dgcog.index2)
        yes = '\N{WHITE HEAVY CHECK MARK}'
        no = '\N{CROSS MARK}'
        await ctx.send(f"Printing info for {inline(s1)}, {inline(s2)}\n" +
                       box(f"Jaro-Winkler Distance:    {round(dist, 4)}\n"
                           f"Name Matching Distance:   {round(dist2, 4)}\n"
                           f"Modifier token threshold: {find_monster.MODIFIER_JW_DISTANCE}  "
                           f"{yes if dist >= find_monster.MODIFIER_JW_DISTANCE else no}\n"
                           f"Name token threshold:     {find_monster.TOKEN_JW_DISTANCE}   "
                           f"{yes if dist2 >= find_monster.TOKEN_JW_DISTANCE else no}"))

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
        tms = DGCOG.token_maps
        awakenings = {a.awoken_skill_id: a for a in DGCOG.database.get_all_awoken_skills()}
        series = {s.series_id: s for s in DGCOG.database.get_all_series()}

        o = ("Jump to:\n\n"
             "* [Types](#types)\n"
             "* [Evolutions](#evolutions)\n"
             "* [Misc](#misc)\n"
             "* [Awakenings](#awakenings)\n"
             "* [Series](#series)\n"
             "* [Attributes](#attributes)\n\n\n\n")

        etable = [(k.value, ", ".join(map(inline, v))) for k, v in tms.EVO_MAP.items()]
        o += "\n\n### Evolutions\n\n" + tabulate(etable, headers=["Meaning", "Tokens"], tablefmt="github")
        ttable = [(k.name, ", ".join(map(inline, v))) for k, v in tms.TYPE_MAP.items()]
        o += "\n\n### Types\n\n" + tabulate(ttable, headers=["Meaning", "Tokens"], tablefmt="github")
        mtable = [(k.value, ", ".join(map(inline, v))) for k, v in tms.MISC_MAP.items()]
        o += "\n\n### Misc\n\n" + tabulate(mtable, headers=["Meaning", "Tokens"], tablefmt="github")
        atable = [(awakenings[k.value].name_en, ", ".join(map(inline, v))) for k, v in tms.AWOKEN_MAP.items()]
        o += "\n\n### Awakenings\n\n" + tabulate(atable, headers=["Meaning", "Tokens"], tablefmt="github")
        stable = [(series[k].name_en, ", ".join(map(inline, v)))
                  for k, v in DGCOG.index2.series_id_to_pantheon_nickname.items()]
        o += "\n\n### Series\n\n" + tabulate(stable, headers=["Meaning", "Tokens"], tablefmt="github")
        ctable = [(k.name.replace("Nil", "None"), ", ".join(map(inline, v))) for k, v in tms.COLOR_MAP.items()]
        ctable += [("Sub " + k.name.replace("Nil", "None"), ", ".join(map(inline, v))) for k, v in
                   tms.SUB_COLOR_MAP.items()]
        for k, v in tms.DUAL_COLOR_MAP.items():
            k0name = k[0].name.replace("Nil", "None")
            k1name = k[1].name.replace("Nil", "None")
            ctable.append((k0name + "/" + k1name, ", ".join(map(inline, v))))
        o += "### Attributes\n\n" + tabulate(ctable, headers=["Meaning", "Tokens"], tablefmt="github")

        await ctx.send(file=text_to_file(o, filename="table.md"))

    @commands.command(aliases=["idcheckmod", "lookupmod", "idlookupmod"])
    async def idmeaning(self, ctx, *, token):
        """Get all the meanings of a token (bold signifies base of a tree)"""
        token = token.replace(" ", "")
        DGCOG = self.bot.get_cog("Dadguide")

        await DGCOG.wait_until_ready()

        tms = DGCOG.token_maps
        awokengroup = "(" + "|".join(re.escape(aw) for aws in tms.AWOKEN_MAP.values() for aw in aws) + ")"
        awakenings = {a.awoken_skill_id: a for a in DGCOG.database.get_all_awoken_skills()}
        series = {s.series_id: s for s in DGCOG.database.get_all_series()}

        o = ""

        def write_name_token(dict, type, mwtoken=False):
            def f(m, s):
                return bold(s) if DGCOG.database.graph.monster_is_base(m) else s

            o = ""
            so = []
            for m in sorted(dict[token], key=lambda m: m.monster_id):
                if (m in DGCOG.index2.mwtoken_creators[token]) == mwtoken:
                    so.append(m)
            if len(so) > 5:
                o += f"\n\n{type}\n" + ", ".join(f(m, str(m.monster_id)) for m in so[:10])
                o += f"... ({len(so)} total)" if len(so) > 10 else ""
            elif so:
                o += f"\n\n{type}\n" + "\n".join(f(m, f"{str(m.monster_id).rjust(4)}. {m.name_en}") for m in so)
            return o

        o += write_name_token(DGCOG.index2.manual, "\N{LARGE PURPLE CIRCLE} [Multi-Word Tokens]", True)
        o += write_name_token(DGCOG.index2.manual, "[Manual Tokens]")
        o += write_name_token(DGCOG.index2.name_tokens, "[Name Tokens]")
        o += write_name_token(DGCOG.index2.fluff_tokens, "[Fluff Tokens]")

        submwtokens = [t for t in DGCOG.index2.multi_word_tokens if token in t]
        if submwtokens:
            o += "\n\n[Multi-word Super-tokens]\n"
            for t in submwtokens:
                if not DGCOG.index2.all_name_tokens[''.join(t)]:
                    continue
                creators = sorted(DGCOG.index2.mwtoken_creators["".join(t)], key=lambda m: m.monster_id)
                o += f"{' '.join(t).title()}"
                o += f" ({', '.join(f'{m.monster_id}' for m in creators)})" if creators else ''
                o += (" ( \u2014> " +
                      str(find_monster.get_most_eligable_monster(DGCOG.index2.all_name_tokens[''.join(t)],
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
              for k, v in tms.AWOKEN_MAP.items() if token in v],
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
              for k, v in DGCOG.index2.series_id_to_pantheon_nickname.items() if token in v],

            *["Rarity: " + m for m in re.findall(r"^(\d+)\*$", token)],
            *["Base rarity: " + m for m in re.findall(r"^(\d+)\*b$", token)],
            *[f"[UNSUPPORTED] Multiple awakenings: {m}x {awakenings[a.value].name_en}"
              f"{additmods([f'{m}*{d}' for d in v], token)}"
              for m, ag in re.findall(r"^(\d+)\*{}$".format(awokengroup), token)
              for a, v in tms.AWOKEN_MAP.items() if ag in v]
        ])

        if meanings or o:
            for page in pagify(meanings + "\n\n" + o.strip()):
                await ctx.send(page)
        else:
            await ctx.send(f"There are no modifiers that match `{token}`.")

    @commands.command(aliases=["tracebackid", "tbid", "idtb"])
    async def idtraceback(self, ctx, *, query):
        """Get the traceback of an id query"""
        mid = None
        if "/" in query:
            query, mid = query.split("/", 1)
            if not mid.strip().isdigit():
                await ctx.send("Monster id must be an int.")
                return
            mid = int(mid.strip())

        dgcog = self.bot.get_cog("Dadguide")
        await dgcog.wait_until_ready()

        query = rmdiacritics(query).strip().lower().replace(",", "")
        tokenized_query = query.split()
        mw_tokenized_query = find_monster.merge_multi_word_tokens(tokenized_query, dgcog.index2.multi_word_tokens)

        bestmatch, matches = max(
            await find_monster_search(tokenized_query, dgcog),
            await find_monster_search(mw_tokenized_query, dgcog)
            if tokenized_query != mw_tokenized_query else (None, {}),
            key=lambda t: t[1][t[0]].score if t[0] else 0
        )

        if bestmatch is None:
            await ctx.send("No monster matched.")
            return

        if mid is not None:
            selected = {m for m in matches if m.monster_id == mid}
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
        if len(lower_prio) > 10:
            lpstr = f"{len(lower_prio)} other monsters."
        else:
            lpstr = "\n".join(f"{get_attribute_emoji_by_monster(m)} {m.name_en} ({m.monster_id})" for m in lower_prio)

        mtokenstr = '\n'.join(sorted(mtokens))
        ntokenstr = '\n'.join(sorted(ntokens))

        await ctx.send(f"**Monster matched**: "
                       f"{get_attribute_emoji_by_monster(monster)} {monster.name_en} ({monster.monster_id})\n"
                       f"**Total Score**: {score}\n\n"
                       f"**Matched Name Tokens**:\n{ntokenstr}\n\n"
                       f"**Matched Mod Tokens**:\n{mtokenstr}\n\n" +
                       (f"**Equally Scoring Matches**:\n{lpstr}" if lower_prio else ""))

    @commands.command(aliases=["ids"])
    async def idsearch(self, ctx, query):
        dgcog = self.bot.get_cog("Dadguide")
        await dgcog.wait_until_ready()

        query = rmdiacritics(query).strip().lower().replace(",", "")
        tokenized_query = query.split()
        mw_tokenized_query = find_monster.merge_multi_word_tokens(tokenized_query, dgcog.index2.multi_word_tokens)

        monster, matches = max(
            await find_monster_search(tokenized_query, dgcog),
            await find_monster_search(mw_tokenized_query, dgcog)
            if tokenized_query != mw_tokenized_query else (None, {}),
            key=lambda t: t[1][t[0]].score if t[0] else 0
        )
        if monster is None:
            await ctx.send("No monster matched.")
            return

        lower_prio = {m for m in matches if matches[m].score == matches[monster].score}.difference({monster})
        monster_list = [monster] + list(lower_prio)[:10]
        await self._do_monster_list(ctx, dgcog, query, monster_list)
