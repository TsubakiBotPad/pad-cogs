import asyncio
import logging
from io import BytesIO
from typing import Dict, List, Optional, TYPE_CHECKING

import discord
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import box, pagify
from tsutils.formatting import contains_ja

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel
    from dbcog.models.dungeon_model import DungeonModel

logger = logging.getLogger('red.padbot-cogs.padmonitor')


class PadMonitor(commands.Cog):
    """Monitor PAD and announce new cards"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        self.config = Config.get_conf(self, identifier=9407071702)
        self.config.register_global(seen_jp_monsters=[], seen_na_monsters=[],
                                    monster_announce_channels=[],
                                    seen_jp_dungeons=[], seen_na_dungeons=[],
                                    dungeon_announce_channels=[], )

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
                await self.check_seen_monsters()
                await self.check_seen_dungeons()
            except Exception:
                logger.exception("Error in PadMonitor loop:")

            await asyncio.sleep(60 * 5)

    async def check_seen_monsters(self):
        """Refresh the monster indexes."""

        def process(existing: List[int],  # Will be mutated
                    new_map: Dict[int, "MonsterModel"],
                    region: str) -> Optional[str]:
            if not existing:
                # If everything is new, assume nothing is and log all current monsters as seen
                logger.info('preloading %i monsters', len(new_map))
                existing.extend(new_map.keys())
                return None

            delta_set = set(new_map.keys()).difference(existing)

            if not delta_set:
                # There are no new monsters
                return None

            existing.extend(delta_set)
            msg = f'New monsters added to {region}:'
            for mid in sorted(delta_set):
                m = new_map[mid]
                msg += f'\n\t[{m.monster_id}] {m.unoverridden_name_en}'
                if contains_ja(m.name_en) and m.name_en_override:
                    msg += f' ({m.name_en_override})'
            return msg

        dbcog = self.bot.get_cog('DBCog')
        await dbcog.wait_until_ready()
        all_monsters = dbcog.database.get_all_monsters()

        jp_monster_map = {m.monster_id: m for m in all_monsters if m.on_jp}
        async with self.config.seen_jp_monsters() as jp_seen:
            if (jp_results := process(jp_seen, jp_monster_map, 'JP')):
                for channel_id in await self.config.monster_announce_channels():
                    await self.announce(channel_id, jp_results)
        na_monster_map = {m.monster_id: m for m in all_monsters if m.on_na}
        async with self.config.seen_na_monsters() as na_seen:
            if (na_results := process(na_seen, na_monster_map, 'NA')):
                for channel_id in await self.config.monster_announce_channels():
                    await self.announce(channel_id, na_results)

    async def check_seen_dungeons(self):
        """Refresh the dungeons indexes."""

        def process(existing: List[int],  # Will be mutated
                    new_map: Dict[int, "DungeonModel"]) -> Optional[str]:
            # TODO: Don't repeat so much code here
            if not existing:
                # If everything is new, assume nothing is and log all current dungeons as seen
                logger.info('preloading %i dungeons', len(new_map))
                existing.extend(new_map.keys())
                return None

            delta_set = set(new_map.keys()).difference(existing)

            if not delta_set:
                # There are no new dungeons
                return None

            existing.extend(delta_set)
            msg = f'New dungeons added:'
            for mid in sorted(delta_set):
                msg += f'\n\t{new_map[mid].name_en}'
            return msg

        dbcog = self.bot.get_cog('DBCog')
        await dbcog.wait_until_ready()
        all_dungeons = dbcog.database.dungeon.get_all_dungeons()

        dungeon_map = {m.dungeon_id: m for m in all_dungeons}  # TODO: Find a way to test server
        async with self.config.seen_jp_dungeons() as seen:
            if (results := process(seen, dungeon_map)):
                for channel_id in await self.config.dungeon_announce_channels():
                    await self.announce(channel_id, results)

    async def announce(self, channel_id: int, message: str):
        try:
            channel = self.bot.get_channel(channel_id)
            for page in pagify(message):
                await channel.send(box(page))
        except Exception as ex:
            logger.exception(f'Failed to send message to {channel_id}:')

    @commands.group(aliases=['pdm'])
    async def padmonitor(self, ctx):
        """PAD info monitoring"""
        pass

    @padmonitor.command()
    @checks.is_owner()
    async def reload(self, ctx):
        """Update PDM channels"""
        async with ctx.typing():
            await self.check_seen_monsters()
            await self.check_seen_dungeons()
        await ctx.tick()

    @padmonitor.group(name='monsters', aliases=['monster'])
    async def pdm_monsters(self, ctx):
        """New monster announcement"""
        pass

    @pdm_monsters.command(name='addchannel')
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def pdm_m_addchannel(self, ctx, channel: discord.TextChannel = None):
        """Sets announcements for the current channel."""
        channel = channel or ctx.channel
        async with self.config.monster_announce_channels() as announce_channels:
            if channel.id in announce_channels:
                return await ctx.send(f"{channel} is already a monster announcement channel.")
            announce_channels.append(channel.id)
        await ctx.tick()

    @pdm_monsters.command(name='rmchannel', aliases=['removechannel'])
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def pdm_m_rmchannel(self, ctx, channel: discord.TextChannel = None):
        """Removes announcements for the current channel."""
        channel = channel or ctx.channel
        async with self.config.monster_announce_channels() as announce_channels:
            if channel.id not in announce_channels:
                return await ctx.send(f"{channel} is not a monster announcement channel.")
            announce_channels.remove(channel.id)
        await ctx.tick()

    @padmonitor.group(name='dungeons', aliases=['dungeon'])
    async def pdm_dungeons(self, ctx):
        """New dungeon announcement"""
        pass

    @pdm_dungeons.command(name='addchannel')
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def pdm_d_addchannel(self, ctx, channel: discord.TextChannel = None):
        """Sets announcements for the current channel."""
        channel = channel or ctx.channel
        async with self.config.dungeon_announce_channels() as announce_channels:
            if channel.id in announce_channels:
                return await ctx.send(f"{channel} is already a dungeon announcement channel.")
            announce_channels.append(channel.id)
        await ctx.tick()

    @pdm_dungeons.command(name='rmchannel', aliases=['removechannel'])
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def pdm_d_rmchannel(self, ctx, channel: discord.TextChannel = None):
        """Removes announcements for the current channel."""
        channel = channel or ctx.channel
        async with self.config.dungeon_announce_channels() as announce_channels:
            if channel.id not in announce_channels:
                return await ctx.send(f"{channel} is not a dungeon announcement channel.")
            announce_channels.remove(channel.id)
        await ctx.tick()
