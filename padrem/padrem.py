import asyncio
import random
import traceback
from _collections import OrderedDict

from redbot.core import checks
from redbot.core import commands
from redbot.core.utils.chat_formatting import box, pagify

from dadguide import dadguide
from rpadutils import CogSettings, normalizeServer

SUPPORTED_SERVERS = ["NA", "JP"]


class PadRem(commands.Cog):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        self.settings = PadRemSettings("padrem")

        self.pgrem = PgRemWrapper(None, {}, skip_load=True)

    def __unload(self):
        # Manually nulling out database because the GC for cogs seems to be pretty shitty
        self.pgrem = PgRemWrapper(None, {}, skip_load=True)

    async def reload_padrem(self):
        await self.bot.wait_until_ready()
        while self == self.bot.get_cog('PadRem'):
            try:
                await self.refresh_data()
                print('Done refreshing PadRem')
            except Exception as ex:
                print("reload padrem loop caught exception " + str(ex))
                traceback.print_exc()

            await asyncio.sleep(60 * 60 * 1)

    async def refresh_data(self):
        dg_cog = self.bot.get_cog('Dadguide')
        await dg_cog.wait_until_ready()
        database = dg_cog.database
        self.pgrem = PgRemWrapper(database, self.settings.getBoosts())

    @commands.command(name="setboost")
    @checks.is_owner()
    async def _setboost(self, ctx, machine_id: str, boost_rate: int):
        """Sets the boost rate for a specific REM.

        machine_id should be the value in () in the rem list, e.g for
          gf -> Godfest x4 (711) REM (JP) with Aqua Carnival x3 (561)

        Use 711 to set the godfest rate and 561 to set the carnival rate.

        The boost_rate should an integer >= 1.

        You will need to reload the module after changing this.
        """
        self.settings.setBoost(machine_id, boost_rate)
        await ctx.send(box('Done'))

    @commands.command(name="remlist")
    async def _remlist(self, ctx):
        """Lists available rare egg machines that can be rolled"""
        msg = ""

        for server, config in self.pgrem.server_to_config.items():
            msg += "Current REM info for {}:\n".format(server)
            for key, machine in config.machines.items():
                msg += '\t{:7} -> {}\n'.format(key, machine.machine_name)
            msg += '\n'

        await ctx.send(box(msg))

    @commands.command(name="reminfo")
    async def _reminfo(self, ctx, server, rem_name):
        """Displays detailed information on the contents of a REM

        You must specify the server, NA or JP.
        You must specify the rem name. Use 'remlist' to get the full
        set of REMs that can be rolled.
        """
        server = normalizeServer(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, JP")
            return

        config = self.pgrem.server_to_config[server]

        if rem_name not in config.machines:
            await ctx.send(box('Unknown machine name'))
            return

        machine = config.machines[rem_name]

        await self.sayPageOutput(machine.toDescription())

    @commands.command(name="rollrem")
    async def _rollrem(self, ctx, server, rem_name):
        """Rolls a rare egg machine and prints the result

        You must specify the server, NA or JP.
        You must specify the rem name. Use 'remlist' to get the full
        set of REMs that can be rolled.
        """
        server = normalizeServer(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, JP")
            return

        config = self.pgrem.server_to_config[server]

        if rem_name not in config.machines:
            await ctx.send(box('Unknown machine name'))
            return

        machine = config.machines[rem_name]
        monster = machine.pickMonster()

        msg = 'You rolled : #{} {}'.format(monster.monster_no_na, monster.name_na)
        await self.bot.say(box(msg))

    @commands.command(name="rollremfor")
    async def _rollremfor(self, ctx, server: str, rem_name: str, monster_query: str):
        """Rolls a rare egg machine until the selected monster pops out

        You must specify the server, NA or JP.
        You must specify the rem name. Use 'remlist' to get the full
        set of REMs that can be rolled.
        You must specify a monster id present within the egg machine.
        """
        monster_query = monster_query.lower()
        server = normalizeServer(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, JP")
            return

        config = self.pgrem.server_to_config[server]

        if rem_name not in config.machines:
            await ctx.send(box('Unknown machine name'))
            return

        machine = config.machines[rem_name]

        if monster_query.isdigit():
            def check_monster_fn(m):
                return int(monster_query) == m.monster_no_na
        else:
            def check_monster_fn(m):
                return monster_query in m.name_na.lower()

        found = False
        for m in machine.monster_no_to_monster.values():
            if check_monster_fn(m):
                found = True
                break

        if not found:
            await ctx.send(box('That monster is not available in this REM'))
            return

        picks = 0
        roll_stones = machine.stones_per_roll
        stone_price = 3.53 / 5 if server == 'NA' else 2.65 / 5
        while picks < 500:
            monster = machine.pickMonster()
            picks += 1
            if check_monster_fn(monster):
                stones = picks * roll_stones
                price = stones * stone_price
                msg = 'It took {} tries and {} stones (${:.0f}) to pull : #{} {}'.format(
                    picks, stones, price, monster.monster_no_na, monster.name_na)
                await ctx.send(box(msg))
                return

        await ctx.send(box('You failed to roll your monster in 500 tries'))

    async def sayPageOutput(self, msg, format_type=box):
        msg = msg.strip()
        msg = pagify(msg, ["\n"], shorten_by=20)
        for page in msg:
            try:
                await self.bot.say(format_type(page))
            except Exception as e:
                print("page output failed " + str(e))
                print("tried to print: " + page)

    async def whisperPageOutput(self, msg, format_type=box):
        msg = msg.strip()
        msg = pagify(msg, ["\n"], shorten_by=20)
        for page in msg:
            try:
                await ctx.author.send(format_type(page))
            except Exception as e:
                await ctx.send("Page output failed.")
                print("page output failed " + str(e))
                print("tried to print: " + page)


class PadRemSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'machine_id_to_boost': {}
        }
        return config

    def getBoosts(self):
        return self.bot_settings['machine_id_to_boost']

    def setBoost(self, machine_id, boost):
        self.getBoosts()[machine_id] = int(boost)
        self.save_settings()


class RemMonster(object):
    def __init__(self, monster: dadguide.DgMonster):
        self.monster_no = monster.monster_no
        self.monster_no_na = monster.monster_no_na
        self.rarity = monster.rarity
        self.name_na = monster.name_na
        self.on_na = monster.on_na


class PgRemWrapper:
    def __init__(self, database, id_to_boost_map: dict, skip_load=False):
        self.server_to_config = {}
        if skip_load:
            return

        modifier_list = []
        jp_rem_list = []
        na_rem_list = []
        jp_gfe_rem_list = []
        na_gfe_rem_list = []

        gfe_series = database.getSeries(34)
        if gfe_series:
            for m in gfe_series.monsters:
                if m.is_gfe and m.evo_from is None:
                    rm = RemMonster(m)
                    jp_gfe_rem_list.append(rm)
                    if m.on_na:
                        na_gfe_rem_list.append(rm)
        else:
            print('PADREM: GFE Series not found')

        egg_instances = database.all_egg_instances()
        egg_instances.sort(key=lambda x: (
            x.server, x.rem_type.value, x.order, (x.row_type.value * -1)))

        cur_mon_list = None

        for ei in egg_instances:
            rem_monsters = []
            for em in ei.egg_monsters:
                if em.monster is None:
                    print('REM error: egg monster missing')
                else:
                    rem_monsters.append(RemMonster(em.monster))

            boost_rate = id_to_boost_map.get(ei.key())

            if ei.server == '':
                # A blank server means this is the global rem list
                for rm in rem_monsters:
                    if rm.monster_no in PADGUIDE_EXCLUSIVE_MISTAKES:
                        continue
                    jp_rem_list.append(rm)
                    if rm.on_na:
                        na_rem_list.append(rm)
            else:
                # Otherwise this is special rems or carnivals
                if ei.row_type == dadguide.RemRowType.divider:
                    # We started a new machine (always happens for first row)
                    cur_mon_list = []
                    modifier_list.append(EggMachineModifier(ei, cur_mon_list, boost_rate))

                # For new or continued machines, keep adding monsters to the current list
                cur_mon_list.extend(rem_monsters)

        for server in ['NA', 'JP']:
            mods = [emm for emm in modifier_list if emm.server == server]
            rem_list = jp_rem_list if server == 'JP' else na_rem_list
            gfe_rem_list = jp_gfe_rem_list if server == 'JP' else na_gfe_rem_list
            self.server_to_config[server] = PgServerRemConfig(server, rem_list, gfe_rem_list, mods)


class EggMachine:
    def __init__(self):
        self.machine_id = None
        self.machine_name = None

        self.monster_no_to_boost = {}
        self.monster_no_to_monster = {}
        self.monster_entries = list()
        self.stone_count = 5

    def addMonsterAndBoost(self, monster, boost):
        saved_boost = self.monster_no_to_boost.get(monster.monster_no, boost)
        self.monster_no_to_boost[monster.monster_no] = max(boost, saved_boost)
        self.monster_no_to_monster[monster.monster_no] = monster

    def addMonster(self, monster, rate):
        for i in range(0, rate):
            self.monster_entries.append(monster)

    def pickMonster(self):
        if not len(self.monster_entries):
            return None
        return self.monster_entries[random.randrange(len(self.monster_entries))]

    def computeMonsterEntries(self):
        self.monster_entries.clear()
        for monster_no in self.monster_no_to_boost.keys():
            m = self.monster_no_to_monster[monster_no]
            self.addMonster(m, self.pointsForMonster(m))

    def pointsForMonster(self, monster):
        return (9 - monster.rarity) * self.monster_no_to_boost[monster.monster_no]

    def pointsForMonster(self, monster):
        id_monster_rates = self.rem_config['monster_no']
        if monster.monster_no_na in id_monster_rates:
            return id_monster_rates[monster.monster_no]
        else:
            return self.rem_config['rarity'][monster.rarity]

    def chanceOfMonster(self, monster):
        return self.pointsForMonster(monster) / len(self.monster_entries)

    def toDescription(self):
        return 'Egg machine (unknown)'

    def toLongDescription(self, include_monsters, rarity_cutoff, chance_cutoff=.005):
        msg = self.machine_name + '\n'

        cur_rarity = None
        cur_count = None
        cum_chance = None
        cur_msg = None

        for m in sorted(self.monster_no_to_monster.values(), key=lambda m: (m.rarity, m.monster_no), reverse=True):
            if cur_rarity != m.rarity:
                if cur_rarity is not None:
                    msg += '{}* ({} monsters at {:.1%})\n'.format(cur_rarity, cur_count, cum_chance)
                    msg += cur_msg

                cur_rarity = m.rarity
                cur_count = 0
                cum_chance = 0.0
                cur_msg = ''

            chance = self.chanceOfMonster(m)
            cur_count += 1
            cum_chance += chance

            if include_monsters and cur_rarity >= rarity_cutoff and (chance >= chance_cutoff or cur_rarity > 6):
                cur_msg += '\t{: 5.1%} #{:4d} {}\n'.format(chance, m.monster_no_na, m.name_na)

        msg += '{}* ({} monsters at {:.1%})\n'.format(cur_rarity, cur_count, cum_chance)
        msg += cur_msg
        return msg


class RareEggMachine(EggMachine):
    def __init__(self, server, global_rem_list, carnival_modifier):
        super(RareEggMachine, self).__init__()

        self.machine_name = 'REM ({})'.format(server)
        self.rem_config = DEFAULT_MACHINE_CONFIG
        self.stones_per_roll = self.rem_config['stones_per_roll']

        if carnival_modifier:
            self.machine_name += ' with {} x{} ({})'.format(carnival_modifier.name,
                                                            carnival_modifier.boost_rate, carnival_modifier.tet_seq)

        for m in global_rem_list:
            if server == 'NA' and not m.on_na:
                continue
            self.addMonsterAndBoost(m, 1)

        if carnival_modifier is not None:
            for m in carnival_modifier.rem_monsters:
                if m.monster_no_na in PADGUIDE_EXCLUSIVE_MISTAKES:
                    self.addMonsterAndBoost(m, 1)
                else:
                    self.addMonsterAndBoost(m, carnival_modifier.boost_rate)

        self.computeMonsterEntries()

    def toDescription(self):
        return self.toLongDescription(False, 0)


class GfEggMachine(RareEggMachine):
    def __init__(self, server, global_rem_list, gfe_rem_list, carnival_modifier, godfest_modifier):
        super(GfEggMachine, self).__init__(server, global_rem_list, carnival_modifier)

        self.machine_name = '{} Godfest x{} ({}) {}'.format(
            godfest_modifier.open_date_str, godfest_modifier.boost_rate, godfest_modifier.tet_seq, self.machine_name)

        for m in gfe_rem_list:
            self.addMonsterAndBoost(m, 1)

        for m in godfest_modifier.rem_monsters:
            self.addMonsterAndBoost(m, godfest_modifier.boost_rate)

        self.computeMonsterEntries()

    def toDescription(self):
        return self.toLongDescription(True, 6)


class CollabEggMachine(EggMachine):
    def __init__(self, collab_modifier):
        super(CollabEggMachine, self).__init__()

        self.machine_id = int(collab_modifier.tet_seq)
        self.machine_name = '{} ({})'.format(collab_modifier.name, collab_modifier.tet_seq)

        self.rem_config = DEFAULT_COLLAB_CONFIG
        if self.machine_id == 905:
            self.rem_config = IMOUTO_COLLAB_CONFIG
        if self.machine_id == 946:
            self.rem_config = IMOUTO_COLLAB_CONFIG_2
        if self.machine_id == 650:
            self.rem_config = FF_COLLAB_CONFIG
        if self.machine_id == 1066:
            self.rem_config = MH_COLLAB_CONFIG

        self.stones_per_roll = self.rem_config['stones_per_roll']

        for m in collab_modifier.rem_monsters:
            self.addMonsterAndBoost(m, 1)

        self.computeMonsterEntries()

    def toDescription(self):
        return self.toLongDescription(True, 1)


DEFAULT_MACHINE_CONFIG = {
    'stones_per_roll': 5,
    'monster_no': {},
    'rarity': {
        8: 3,
        7: 3,
        6: 6,
        5: 12,
        4: 24,
    },
}

DEFAULT_COLLAB_CONFIG = {
    'stones_per_roll': 5,
    'monster_no': {},
    'rarity': {
        8: 1,
        7: 3,
        6: 4,
        5: 9,
        4: 12,
    },
}

# TODO: make this configurable
IMOUTO_COLLAB_CONFIG = {
    'stones_per_roll': 10,
    'monster_no': {},
    'rarity': {
        8: 0,
        7: 15,
        6: 51,
        5: 145,
    },
}
IMOUTO_COLLAB_CONFIG_2 = {
    'stones_per_roll': 10,
    'monster_no': {
        3274: 30,
        3524: 15,
    },
    'rarity': {
        8: 0,
        7: 0,
        6: 88,
        5: 290,
    },
}

FF_COLLAB_CONFIG = {
    'stones_per_roll': 5,
    'monster_no': {},
    'rarity': {
        8: 0,
        7: 0,
        6: 29,
        5: 40,
        4: 57,
    },
}

MH_COLLAB_CONFIG = {
    'stones_per_roll': 10,
    'monster_no': {},
    'rarity': {
        8: 0,
        7: 8,
        6: 22,
        5: 75,
        4: 0,
    },
}


class EggMachineModifier:
    def __init__(self, egg_instance, rem_monsters, boost_rate):
        """Do not hold onto a ref to egg_instance."""
        self.server = egg_instance.server
        self.tet_seq = egg_instance.tet_seq
        self.order = egg_instance.order
        self.start_datetime = egg_instance.start_datetime
        self.end_datetime = egg_instance.end_datetime
        self.open_date_str = egg_instance.open_date_str

        self.rem_type = egg_instance.rem_type
        self.name = egg_instance.egg_name_us.name if egg_instance.egg_name_us else 'unknown'

        self.rem_monsters = rem_monsters

        self.boost_rate = 1

        if boost_rate is not None:
            self.boost_rate = boost_rate
        elif self.isGodfest():
            self.boost_rate = 4
        elif self.isCarnival():
            self.boost_rate = 3

    def isGodfest(self):
        return self.rem_type == dadguide.RemType.godfest

    def isRare(self):
        return self.rem_type == dadguide.RemType.rare

    def isCarnival(self):
        name = self.name.lower()
        return self.isRare() and ('gala' in name or 'carnival' in name or 'special!' in name)

    def getName(self):
        if self.rem_type == dadguide.RemType.godfest.value:
            return 'Godfest x{}'.format(self.boost_rate)
        else:
            return self.name


class PgServerRemConfig:
    def __init__(self, server, global_rem_list, gfe_rem_list, modifier_list):
        self.godfest_modifiers = list()
        self.collab_modifiers = list()
        self.carnival_modifier = None

        for modifier in modifier_list:
            if modifier.isGodfest():
                self.godfest_modifiers.append(modifier)
            elif modifier.isCarnival():
                self.carnival_modifier = modifier
            else:
                self.collab_modifiers.append(modifier)

        self.base_machine = RareEggMachine(server, global_rem_list, self.carnival_modifier)

        self.godfest_machines = list()
        for godfest_modifier in self.godfest_modifiers:
            self.godfest_machines.append(GfEggMachine(
                server, global_rem_list, gfe_rem_list, self.carnival_modifier, godfest_modifier))

        self.collab_machines = list()
        for collab_modifier in self.collab_modifiers:
            self.collab_machines.append(CollabEggMachine(collab_modifier))

        self.machines = OrderedDict()
        self.machines['rem'] = self.base_machine
        for idx, machine in enumerate(self.godfest_machines):
            suffix = '' if idx == 0 else str(idx + 1)
            self.machines['gf' + suffix] = machine
        for idx, machine in enumerate(self.collab_machines):
            suffix = '' if idx == 0 else str(idx + 1)
            self.machines['collab' + suffix] = machine


PADGUIDE_EXCLUSIVE_MISTAKES = [
    2665,  # Red Gemstone, Silk
    2666,  # Evo'd Silk
    2667,  # Blue Gemstone, Carat
    2668,  # Evo'd Carat
    2669,  # Green Gemstone, Cameo
    2670,  # Evo'd Cameo
    2671,  # Light Gemstone, Facet
    2672,  # Evo'd Facet
    2673,  # Dark Gemstone, Sheen
    2674,  # Evo'd Sheen

    2915,  # Red Hero, Napoleon
    2916,  # Evo'd Napoleon
    2917,  # Blue Hero, Barbarossa
    2918,  # Evo'd Barbarossa
    2919,  # Green Hero, Robin Hood
    2920,  # Evo'd Robin Hood
    2921,  # Light Hero, Yang Guifei
    2922,  # Evo'd Yang Guifei
    2923,  # Dark Hero, Oda Nobunaga
    2924,  # Evo'd Oda Nobunaga
]
