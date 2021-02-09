import difflib
from collections import defaultdict

import tsutils
from discord.utils import find as find_first
from redbot.core.utils import AsyncIter

from dadguide.models.enum_types import Attribute, MonsterType
from dadguide.models.monster_model import MonsterModel
from dadguide.models.series_model import SeriesModel
from .database_context import DbContext
from .models.enum_types import EvoType
from .models.enum_types import InternalEvoType


class MonsterIndex(tsutils.aobject):
    async def __ainit__(self, monster_database: DbContext, nickname_overrides, treename_overrides,
                        panthname_overrides, accept_filter=None):
        # Important not to hold onto anything except IDs here so we don't leak memory
        self.db_context = monster_database
        base_monster_ids = monster_database.get_monsters_where(monster_database.graph.monster_is_base)

        self.attr_short_prefix_map = {
            Attribute.Fire: ['r'],
            Attribute.Water: ['b'],
            Attribute.Wood: ['g'],
            Attribute.Light: ['l'],
            Attribute.Dark: ['d'],
            Attribute.Unknown: ['h'],
            Attribute.Nil: ['x'],
        }
        self.attr_long_prefix_map = {
            Attribute.Fire: ['red', 'fire'],
            Attribute.Water: ['blue', 'water'],
            Attribute.Wood: ['green', 'wood'],
            Attribute.Light: ['light'],
            Attribute.Dark: ['dark'],
            Attribute.Unknown: ['unknown'],
            Attribute.Nil: ['null', 'none'],
        }

        self.series_to_prefix_map = {
            130: ['halloween', 'hw', 'h'],
            136: ['xmas', 'christmas', 'x'],
            125: ['summer', 'beach'],
            114: ['school', 'academy', 'gakuen'],
            139: ['new years', 'ny'],
            149: ['wedding', 'bride'],
            154: ['padr'],
            175: ['valentines', 'vday', 'v'],
            183: ['gh', 'gungho'],
            117: ['gh', 'gungho'],
        }

        monster_id_to_nicknames = defaultdict(set)
        for monster_id, nicknames in nickname_overrides.items():
            monster_id_to_nicknames[monster_id] = nicknames

        named_monsters = []
        async for base_mon in AsyncIter(base_monster_ids):
            base_id = base_mon.monster_id
            base_monster = monster_database.graph.get_monster(base_id)
            series = base_monster.series
            group_treename_overrides = treename_overrides.get(base_id, [])
            evolution_tree = monster_database.graph.get_alt_monsters_by_id(base_id)
            named_mg = NamedMonsterGroup(evolution_tree, group_treename_overrides)
            named_evolution_tree = []
            for monster in evolution_tree:
                if accept_filter and not accept_filter(monster):
                    continue
                prefixes = self.compute_prefixes(monster, evolution_tree)
                extra_nicknames = monster_id_to_nicknames[monster.monster_id]

                # The query mis-handles transforms so we have to fetch base monsters
                # from the graph properly ourselves instead of just listening to whatever
                # the query says the base monster is above
                named_monster = NamedMonster(
                    monster, named_mg, prefixes, extra_nicknames, series,
                    base_monster=monster_database.graph.get_base_monster(monster))
                named_monsters.append(named_monster)
                named_evolution_tree.append(named_monster)
            for named_monster in named_evolution_tree:
                named_monster.set_evolution_tree(named_evolution_tree)

        # Sort the NamedMonsters into the opposite order we want to accept their nicknames in
        # This order is:
        #  1) High priority first
        #  2) Larger group sizes
        #  3) Minimum ID size in the group
        #  4) Monsters with higher ID values
        def named_monsters_sort(named_mon: NamedMonster):
            return (not named_mon.is_low_priority, named_mon.group_size, -1 *
                    named_mon.base_monster_no_na, named_mon.monster_no_na)

        named_monsters.sort(key=named_monsters_sort)

        # set up a set of all pantheon names, a set of all pantheon nicknames, and a dictionary of nickname -> full name
        # later we will set up a dictionary of pantheon full name -> monsters
        self.all_pantheon_names = set()
        self.all_pantheon_names.update(panthname_overrides.values())

        self.pantheon_nick_to_name = panthname_overrides
        self.pantheon_nick_to_name.update(panthname_overrides)

        self.all_pantheon_nicknames = set()
        self.all_pantheon_nicknames.update(panthname_overrides.keys())

        self.all_prefixes = set()
        self.pantheons = defaultdict(set)
        self.all_entries = {}
        self.bad_entries = {}
        self.two_word_entries = {}
        for nm in named_monsters:
            self.all_prefixes.update(nm.prefixes)
            for nickname in nm.final_nicknames:
                self.all_entries[nickname] = nm
            for nickname in nm.final_two_word_nicknames:
                self.two_word_entries[nickname] = nm
            for nickname in nm.bad_nicknames:
                self.bad_entries[nickname] = nm.bad_nicknames[nickname]
            if nm.series:
                for pantheon in self.all_pantheon_names:
                    if pantheon.lower() == nm.series.lower():
                        self.pantheons[pantheon.lower()].add(nm)

        self.all_monsters = named_monsters
        self.all_en_name_to_monsters = {m.name_en.lower(): m for m in named_monsters}
        self.monster_no_na_to_named_monster = {m.monster_no_na: m for m in named_monsters}
        self.monster_id_to_named_monster = {m.monster_id: m for m in named_monsters}

        for monster_id, nicknames in nickname_overrides.items():
            nm = self.monster_id_to_named_monster.get(monster_id)
            if nm:
                for nickname in nicknames:
                    self.all_entries[nickname] = nm

    __init__ = __ainit__

    def init_index(self):
        pass

    def compute_prefixes(self, m: MonsterModel, evotree: list):
        prefixes = set()

        attr1_short_prefixes = self.attr_short_prefix_map[m.attr1]
        attr1_long_prefixes = self.attr_long_prefix_map[m.attr1]
        prefixes.update(attr1_short_prefixes)
        prefixes.update(attr1_long_prefixes)

        # If no 2nd attribute, use x so we can look those monsters up easier
        attr2_short_prefixes = self.attr_short_prefix_map.get(m.attr2, ['x'])
        for a1 in attr1_short_prefixes:
            for a2 in attr2_short_prefixes:
                prefixes.add(a1 + a2)
                prefixes.add(a1 + '/' + a2)

        # TODO: add prefixes based on type

        # Chibi monsters have the same NA name, except lowercased
        lower_name = m.name_en.lower()
        if m.name_en != m.name_ja:
            if lower_name == m.name_en:
                prefixes.add('chibi')
        elif 'ミニ' in m.name_ja:
            # Guarding this separately to prevent 'gemini' from triggering (e.g. 2645)
            prefixes.add('chibi')

        if 'chibi' in lower_name:
            prefixes.add('chibi')

        true_evo_type = self.db_context.graph.true_evo_type_by_monster(m)
        awoken = lower_name.startswith('awoken') or '覚醒' in lower_name
        revo = true_evo_type == InternalEvoType.Reincarnated
        srevo = lower_name.startswith('super reincarnated') or '超転生' in lower_name
        mega = lower_name.startswith('mega awoken') or '極醒' in lower_name
        awoken_or_revo_or_equip_or_mega = awoken or revo or m.is_equip or mega

        # These clauses need to be separate to handle things like 'Awoken Thoth' which are
        # actually Evos but have awoken in the name
        if awoken:
            prefixes.add('a')
            prefixes.add('awoken')

        if revo:
            prefixes.add('revo')
            prefixes.add('reincarnated')

        if mega:
            prefixes.add('mega')
            prefixes.add('mega awoken')
            prefixes.add('awoken')
            prefixes.add('ma')

        if srevo:
            prefixes.add('srevo')
            prefixes.add('super reincarnated')

        # Prefixes for evo type
        cur_evo_type = self.db_context.graph.cur_evo_type_by_monster(m)
        if cur_evo_type == EvoType.Base:
            prefixes.add('base')
        elif cur_evo_type == EvoType.Evo:
            prefixes.add('evo')
        elif cur_evo_type == EvoType.UvoAwoken and not awoken_or_revo_or_equip_or_mega:
            prefixes.add('uvo')
            prefixes.add('uevo')
        elif cur_evo_type == EvoType.UuvoReincarnated and not awoken_or_revo_or_equip_or_mega:
            prefixes.add('uuvo')
            prefixes.add('uuevo')

        # Other Prefixes
        if self.db_context.graph.monster_is_farmable_evo(m):
            prefixes.add('farmable')

        # If any monster in the group is a pixel, add 'nonpixel' to all the versions
        # without pixel in the name. Add 'pixel' as a prefix to the ones with pixel in the name.
        def is_pixel(n):
            n = n.name_en.lower()
            return n.startswith('pixel') or n.startswith('ドット')

        for gm in evotree:
            if is_pixel(gm):
                prefixes.update(['pixel'] if is_pixel(m) else ['np', 'nonpixel'])
                break

        if m.is_equip:
            prefixes.add('assist')
            prefixes.add('equip')

        # Collab prefixes
        prefixes.update(self.series_to_prefix_map.get(m.series.series_id, []))

        return prefixes

    def find_monster(self, query):
        query = tsutils.rmdiacritics(query).lower().strip()

        # id search
        if query.isdigit():
            m = self.monster_no_na_to_named_monster.get(int(query))
            if m is None:
                return None, 'Looks like a monster ID but was not found', None
            else:
                return m, None, "ID lookup"
            # special handling for na/jp

        # TODO: need to handle na_only?

        err = None
        if query in self.bad_entries:
            err = ("It looks like this query won't be supported soon!"
                   f" Please start using `^id {self.bad_entries[query]}` instead, with a space."
                   " For more information, check out:"
                   " <https://github.com/TsubakiBotPad/pad-cogs/wiki/%5Eid-user-guide>"
                   " or join the Tsubaki server (<https://discord.gg/QCRxNtC>).")

        # handle exact nickname match
        if query in self.all_entries:
            return self.all_entries[query], err, "Exact nickname"

        contains_ja = tsutils.contains_ja(query)
        if len(query) < 2 and contains_ja:
            return None, 'Japanese queries must be at least 2 characters', None
        elif len(query) < 4 and not contains_ja:
            return None, 'Your query must be at least 4 letters', None

        # TODO: this should be a length-limited priority queue
        matches = set()

        # prefix search for ids, take max id
        for nickname, m in self.all_entries.items():
            if query.endswith("base {}".format(m.monster_id)):
                matches.add(
                    find_first(lambda mo: m.base_monster_no == mo.monster_id, self.all_entries.values()))
        if len(matches):
            return self.pick_best_monster(matches), None, "Base ID match, max of 1".format()

        # prefix search for nicknames, space-preceeded, take max id
        for nickname, m in self.all_entries.items():
            if nickname.startswith(query + ' '):
                matches.add(m)
        if len(matches):
            return self.pick_best_monster(matches), err, "Space nickname prefix, max of {}".format(len(matches))

        # prefix search for nicknames, take max id
        for nickname, m in self.all_entries.items():
            if nickname.startswith(query):
                matches.add(m)
        if len(matches):
            all_names = ",".join(map(lambda x: x.name_en, matches))
            return self.pick_best_monster(matches), err, "Nickname prefix, max of {}, matches=({})".format(
                len(matches), all_names)

        # prefix search for full name, take max id
        for nickname, m in self.all_entries.items():
            if m.name_en.lower().startswith(query) or m.name_ja.lower().startswith(query):
                matches.add(m)
        if len(matches):
            return self.pick_best_monster(matches), err, "Full name, max of {}".format(len(matches))

        # for nicknames with 2 names, prefix search 2nd word, take max id
        if query in self.two_word_entries:
            return self.two_word_entries[query], err, "Second-word nickname prefix, max of {}".format(len(matches))

        # TODO: refactor 2nd search characteristcs for 2nd word

        # full name contains on nickname, take max id
        for nickname, m in self.all_entries.items():
            if query in m.name_en.lower() or query in m.name_ja.lower():
                matches.add(m)
        if len(matches):
            return self.pick_best_monster(matches), err, 'Nickname contains nickname match ({})'.format(
                len(matches))

        # No decent matches. Try near hits on nickname instead
        matches = difflib.get_close_matches(query, self.all_entries.keys(), n=1, cutoff=.8)
        if len(matches):
            match = matches[0]
            return self.all_entries[match], err, 'Close nickname match ({})'.format(match)

        # Still no decent matches. Try near hits on full name instead
        matches = difflib.get_close_matches(
            query, self.all_en_name_to_monsters.keys(), n=1, cutoff=.9)
        if len(matches):
            match = matches[0]
            return self.all_en_name_to_monsters[match], err, 'Close name match ({})'.format(match)

        # About to give up, try matching all words
        matches = set()
        for nickname, m in self.all_entries.items():
            if (all(map(lambda x: x in m.name_en.lower(), query.split())) or
                    all(map(lambda x: x in m.name_ja.lower(), query.split()))):
                matches.add(m)
        if len(matches):
            return self.pick_best_monster(matches), err, 'All word match on full name, max of {}'.format(
                len(matches))

        # couldn't find anything
        return None, "Could not find a match for: " + query, None

    @staticmethod
    def pick_best_monster(named_monster_list):
        return max(named_monster_list, key=lambda x: (not x.is_low_priority, x.rarity, x.monster_no_na))


class NamedMonsterGroup(object):
    def __init__(self, evolution_tree: list, treename_overrides: list):
        base_monster = min(evolution_tree, key=lambda m: m.monster_id)

        self.is_low_priority = (
                self._is_low_priority_monster(base_monster)
                or self._is_low_priority_group(evolution_tree))

        self.group_size = len(evolution_tree)
        self.base_monster_no = base_monster.monster_id
        self.base_monster_no_na = base_monster.monster_no_na

        self.monster_no_to_treename = {
            m.monster_id: self._compute_monster_treename(m) for m in evolution_tree
        }

        self.computed_treename = self._compute_group_treename(evolution_tree)
        self.computed_treenames = {self.computed_treename}
        if '-' in self.computed_treename:
            self.computed_treenames.add(self.computed_treename.replace('-', ' '))

        self.treenames = treename_overrides or self.computed_treenames

    @staticmethod
    def _compute_monster_treename(m: MonsterModel):
        treename = m.name_en.lower()
        if ',' in treename:
            name_parts = treename.split(',')
            if name_parts[1].strip().startswith('the '):
                # handle names like 'xxx, the yyy' where xxx is the name
                treename = name_parts[0]
            else:
                # otherwise, grab the chunk after the last comma
                treename = name_parts[-1]

        for x in ['awoken', 'reincarnated']:
            if treename.startswith(x):
                treename = treename.replace(x, '')

        # Fix for DC collab garbage
        treename = treename.replace('(comics)', '')
        treename = treename.replace('(film)', '')

        return treename.strip()

    def _compute_group_treename(self, monsters):
        """Computes the treename for a group of monsters.

        Prefer a treename with the largest count across the group. If all the
        groups have equal size, prefer the lowest monster number treename.
        This monster in general has better names, particularly when all the
        names are unique, e.g. for male/female hunters."""

        def count_and_id():
            return [0, 0]

        treename_to_info = defaultdict(count_and_id)

        for m in monsters:
            treename = self.monster_no_to_treename[m.monster_id]
            entry = treename_to_info[treename]
            entry[0] += 1
            entry[1] = max(entry[1], m.monster_id)

        entries = [[count_id[0], -1 * count_id[1], bn] for bn, count_id in treename_to_info.items()]
        return max(entries)[2]

    @staticmethod
    def _is_low_priority_monster(m: MonsterModel):
        lp_types = [MonsterType.Evolve, MonsterType.Enhance, MonsterType.Awoken, MonsterType.Vendor]
        lp_substrings = ['tamadra']
        lp_min_rarity = 2
        name = m.name_en.lower()

        failed_type = m.type1 in lp_types
        failed_ss = any([x in name for x in lp_substrings])
        failed_rarity = m.rarity < lp_min_rarity
        failed_chibi = name == m.name_en and m.name_en != m.name_ja
        failed_equip = m.is_equip
        return failed_type or failed_ss or failed_rarity or failed_chibi or failed_equip

    @staticmethod
    def _is_low_priority_group(mg: list):
        lp_grp_min_rarity = 5
        max_rarity = max(m.rarity for m in mg)
        failed_max_rarity = max_rarity < lp_grp_min_rarity
        return failed_max_rarity


class NamedMonster(object):
    def __init__(self, monster: MonsterModel, monster_group: NamedMonsterGroup, prefixes: set, extra_nicknames: set,
                 series: SeriesModel, base_monster: MonsterModel = None):

        self.evolution_tree = None

        # Hold on to the IDs instead
        self.monster_id = monster.monster_id
        self.monster_no_na = monster.monster_no_na
        self.monster_no_jp = monster.monster_no_jp

        # ID of the root of the tree for this monster
        self.base_monster_no = base_monster.monster_id
        self.base_monster_no_na = base_monster.monster_no_na

        # This stuff is important for nickname generation
        self.group_treenames = monster_group.treenames
        self.prefixes = prefixes

        # Pantheon
        series = series
        self.series = series.name if series else None

        # Data used to determine how to rank the nicknames
        self.is_low_priority = monster_group.is_low_priority or monster.is_equip
        self.group_size = monster_group.group_size
        self.rarity = monster.rarity
        self.sell_mp = monster.sell_mp

        # Used in fallback searches
        self.name_en = monster.name_en
        self.name_ja = monster.name_ja

        # These are just extra metadata
        self.monster_treename = monster_group.monster_no_to_treename[self.monster_id]
        self.group_computed_treename = monster_group.computed_treename
        self.extra_nicknames = extra_nicknames

        # Compute any extra prefixes
        if self.monster_treename in ('ana', 'ace'):
            self.prefixes.add(self.monster_treename)

        # Compute extra treenames by checking for two-word treenames and using the second half
        self.two_word_treenames = set()
        for treename in self.group_treenames:
            treename_words = treename.split(' ')
            if len(treename_words) == 2:
                self.two_word_treenames.add(treename_words[1])

        # The primary result nicknames
        self.final_nicknames = set()
        # Set the configured override nicknames
        self.final_nicknames.update(self.extra_nicknames)
        # Set the roma subname for JP monsters
        if monster.roma_subname:
            self.final_nicknames.add(monster.roma_subname)

        self.bad_nicknames = dict()

        # For each treename, add nicknames
        for treename in self.group_treenames:
            # Add the treename directly
            self.final_nicknames.add(treename)
            # Add the prefix plus treename, and the prefix with a space between treename
            for prefix in self.prefixes:
                self.final_nicknames.add(prefix + treename)
                self.final_nicknames.add(prefix + ' ' + treename)
                self.bad_nicknames[prefix + treename] = prefix + ' ' + treename

        self.final_two_word_nicknames = set()

        # Slightly different process for two-word treenames. Does this make sense? Who knows.
        for treename in self.two_word_treenames:
            self.final_two_word_nicknames.add(treename)
            # Add the prefix plus treename, and the prefix with a space between treename
            for prefix in self.prefixes:
                self.final_two_word_nicknames.add(prefix + treename)
                self.final_two_word_nicknames.add(prefix + ' ' + treename)
                self.bad_nicknames[prefix + treename] = prefix + ' ' + treename

    def set_evolution_tree(self, evolution_tree):
        """
        Set the evolution tree to a list of NamedMonsters so that we can have
        nice things like prefix lookups on the entire tree in id2 and not cry
        about Diablos equip
        """
        self.evolution_tree = evolution_tree
