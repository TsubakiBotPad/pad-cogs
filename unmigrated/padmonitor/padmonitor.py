from __main__ import send_cmd_help

from . import rpadutils
from .rpadutils import *
from .rpadutils import CogSettings
from .utils import checks
from .utils.chat_formatting import *


class PadMonitor:
    def __init__(self, bot):
        self.bot = bot
        self.settings = PadMonitorSettings("padmonitor")

    async def check_seen_loop(self):
        await self.bot.wait_until_ready()
        while self == self.bot.get_cog('PadMonitor'):
            try:
                await self.check_seen()
                print('Done refreshing PadMonitor')
            except Exception as ex:
                print("check seen loop caught exception " + str(ex))

            await asyncio.sleep(60 * 5)

    async def check_seen(self):
        """Refresh the monster indexes."""
        pg_cog = self.bot.get_cog('Dadguide')
        await pg_cog.wait_until_ready()
        all_monsters = pg_cog.database.get_all_monsters(as_generator=False)
        jp_monster_map = {m.monster_no: m for m in all_monsters if m.on_jp}
        na_monster_map = {m.monster_no: m for m in all_monsters if m.on_na}

        def process(existing, new_map, name):
            if not existing:
                print('preloading', len(new_map))
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
                    msg += '\n\tNo. {} {}'.format(m.monster_no, m.name_na)
                    if rpadutils.containsJp(m.name_na) and m.name_na_override != m.name_na and m.name_na_override is not None:
                        msg += ' ({})'.format(m.name_na_override)
                return msg
            else:
                print('no monsters')
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
            channel = self.bot.get_channel(channel_id)
            for page in pagify(message):
                await self.bot.send_message(channel, box(page))
        except Exception as ex:
            print('failed to send message to', channel_id, ' : ', ex)

    @commands.group(pass_context=True)
    @checks.mod_or_permissions(manage_server=True)
    async def padmonitor(self, ctx):
        """PAD info monitoring"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @padmonitor.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_server=True)
    async def addnewchannel(self, ctx):
        """Sets announcements for the current channel."""
        self.settings.add_new_monster_channel(ctx.message.channel.id)
        await self.bot.say(inline('done'))

    @padmonitor.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_server=True)
    async def rmnewchannel(self, ctx):
        """Removes announcements for the current channel."""
        self.settings.rm_new_monster_channel(ctx.message.channel.id)
        await self.bot.say(inline('done'))


def setup(bot):
    n = PadMonitor(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.check_seen_loop())
    print('done adding padinfo bot')


class PadMonitorSettings(CogSettings):
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

    def add_na_seen(self):
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
