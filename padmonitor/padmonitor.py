import asyncio
import logging
import tsutils
import discord
from io import BytesIO
from redbot.core import checks, commands
from redbot.core.utils.chat_formatting import box, pagify

from typing import TYPE_CHECKING

logger = logging.getLogger('red.padbot-cogs.padmonitor')
if TYPE_CHECKING:
    from dadguide.database_context import DbContext


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
        DGCOG = self.bot.get_cog('Dadguide')
        await DGCOG.wait_until_ready()
        db_context: "DbContext" = DGCOG.database
        all_monsters = db_context.get_all_monsters(as_generator=False)
        jp_monster_map = {m.monster_id: m for m in all_monsters if m.on_jp}
        na_monster_map = {m.monster_id: m for m in all_monsters if m.on_na}

        def process(existing, new_map, name):
            if not existing:
                logger.info('preloading %i', len(new_map))
                existing.extend(new_map.keys())
                self.settings.save_settings()
                return None

            existing_set = set(existing)
            new_set = set(new_map.keys())
            delta_set = new_set - existing_set

            if delta_set:
                existing.extend(delta_set)
                self.settings.save_settings()

                msg = 'New monsters added to {}:'.format(name)
                for m in [new_map[x] for x in delta_set]:
                    msg += '\n\t[{}] {}'.format(m.monster_id, m.unoverridden_name_en)
                    if tsutils.contains_ja(m.name_en) and m.name_en_override is not None:
                        msg += ' ({})'.format(m.name_en_override)
                return msg
            else:
                return None

        jp_results = process(self.settings.jp_seen(), jp_monster_map, 'JP')
        na_results = process(self.settings.na_seen(), na_monster_map, 'NA')

        for msg in [jp_results, na_results]:
            if not msg:
                continue
            for channel_id in self.settings.new_monster_channels():
                await self.announce(channel_id, msg)

    async def announce(self, channel_id, message):
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


class PadMonitorSettings(tsutils.CogSettings):
    def make_default_settings(self):
        config = {
            'jp_seen_ids': [],
            'na_seen_ids': [],
            'new_monster_channels': [],
        }
        return config

    def jp_seen(self):
        return self.bot_settings['jp_seen_ids']

    def na_seen(self):
        return self.bot_settings['na_seen_ids']

    def add_jp_seen(self, monster_id: int):
        ids = self.jp_seen()
        if monster_id not in ids:
            ids.append(monster_id)
            self.save_settings()

    def add_na_seen(self, monster_id: int):
        ids = self.na_seen()
        if monster_id not in ids:
            ids.append(monster_id)
            self.save_settings()

    def new_monster_channels(self):
        return self.bot_settings['new_monster_channels']

    def add_new_monster_channel(self, channel_id):
        channels = self.new_monster_channels()
        if channel_id not in channels:
            channels.append(channel_id)
            self.save_settings()

    def rm_new_monster_channel(self, channel_id):
        channels = self.new_monster_channels()
        if channel_id in channels:
            channels.remove(channel_id)
            self.save_settings()
