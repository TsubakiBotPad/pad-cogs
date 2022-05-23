import asyncio
import logging

import discord
from io import BytesIO

from redbot.core import checks, commands
from redbot.core.utils.chat_formatting import box, pagify

from typing import Dict, List, Optional, TYPE_CHECKING

from tsutils.cog_settings import CogSettings
from tsutils.formatting import contains_ja

if TYPE_CHECKING:
    from dbcog.database_context import DbContext
    from dbcog.models.monster_model import MonsterModel

logger = logging.getLogger('red.padbot-cogs.padmonitor')


class PadMonitor(commands.Cog):
    """Monitor PAD and announce new cards"""
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.settings = PadMonitorSettings("padmonitor")

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        return

    async def check_seen_loop(self):
        await self.bot.wait_until_ready()
        while self == self.bot.get_cog('PadMonitor'):
            try:
                await self.check_seen()
            except Exception as ex:
                logger.exception("check seen loop caught exception " + str(ex))

            await asyncio.sleep(60 * 5)

    async def check_seen(self):
        """Refresh the monster indexes."""
        dbcog = self.bot.get_cog('DBCog')
        await dbcog.wait_until_ready()
        all_monsters = [*dbcog.database.get_all_monsters()]
        jp_monster_map = {m.monster_id: m for m in all_monsters if m.on_jp}
        na_monster_map = {m.monster_id: m for m in all_monsters if m.on_na}

        def process(existing: List[int], new_map: Dict[int, "MonsterModel"], name: str)\
                -> Optional[str]:
            if not existing:
                # If everything is new, assume nothing is and log all current monsters as seen
                logger.info('preloading %i', len(new_map))
                existing.extend(new_map.keys())
                self.settings.save_settings()
                return None

            delta_set = set(new_map.keys()).difference(existing)

            if not delta_set:
                # There are no new monsters
                return None

            existing.extend(delta_set)
            self.settings.save_settings()
            msg = 'New monsters added to {}:'.format(name)
            for mid in sorted(delta_set):
                m = new_map[mid]
                msg += f'\n\t[{m.monster_id}] {m.unoverridden_name_en}'
                if contains_ja(m.name_en) and m.name_en_override is not None:
                    msg += f' ({m.name_en_override})'
            return msg

        if (jp_results := process(self.settings.jp_seen(), jp_monster_map, 'JP')):
            for channel_id in self.settings.new_monster_channels():
                await self.announce(channel_id, jp_results)
        if (na_results := process(self.settings.na_seen(), na_monster_map, 'NA')):
            for channel_id in self.settings.new_monster_channels():
                await self.announce(channel_id, na_results)

    async def announce(self, channel_id: int, message: str):
        try:
            channel = self.bot.get_channel(int(channel_id))
            for page in pagify(message):
                await channel.send(box(page))
        except Exception as ex:
            logger.exception('failed to send message to {}:'.format(channel_id))

    @commands.group(aliases=['pdm'])
    async def padmonitor(self, ctx):
        """PAD info monitoring"""
        pass

    @padmonitor.command()
    @checks.is_owner()
    async def reload(self, ctx):
        """Update PDM channels"""
        async with ctx.typing():
            await self.check_seen()
        await ctx.tick()

    @padmonitor.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def addchannel(self, ctx, channel: discord.TextChannel = None):
        """Sets announcements for the current channel."""
        if channel is None:
            channel = ctx.channel
        self.settings.add_new_monster_channel(channel.id)
        await ctx.tick()

    @padmonitor.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def rmchannel(self, ctx, channel: discord.TextChannel = None):
        """Removes announcements for the current channel."""
        if channel is None:
            channel = ctx.channel
        self.settings.rm_new_monster_channel(channel.id)
        await ctx.tick()


class PadMonitorSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'jp_seen_ids': [],
            'na_seen_ids': [],
            'new_monster_channels': [],
        }
        return config

    def jp_seen(self) -> List[int]:
        return self.bot_settings['jp_seen_ids']

    def na_seen(self) -> List[int]:
        return self.bot_settings['na_seen_ids']

    def add_jp_seen(self, monster_id: int) -> None:
        ids = self.jp_seen()
        if monster_id not in ids:
            ids.append(monster_id)
            self.save_settings()

    def add_na_seen(self, monster_id: int) -> None:
        ids = self.na_seen()
        if monster_id not in ids:
            ids.append(monster_id)
            self.save_settings()

    def new_monster_channels(self) -> List[int]:
        return self.bot_settings['new_monster_channels']

    def add_new_monster_channel(self, channel_id: int) -> None:
        channels = self.new_monster_channels()
        if channel_id not in channels:
            channels.append(channel_id)
            self.save_settings()

    def rm_new_monster_channel(self, channel_id: int) -> None:
        channels = self.new_monster_channels()
        if channel_id in channels:
            channels.remove(channel_id)
            self.save_settings()
