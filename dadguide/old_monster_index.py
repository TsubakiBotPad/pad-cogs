import difflib

from collections import defaultdict

from redbot.core.utils import AsyncIter
from discord.utils import find as find_first
import tsutils

from .database_manager import DgMonster
from .database_manager import Attribute
from .database_manager import EvoType
from .database_manager import InternalEvoType
from .database_manager import PotentialMatches
from .database_manager import NamedMonster
from .database_manager import NamedMonsterGroup
from .database_context import DbContext


class MonsterIndex(tsutils.aobject):
    async def __init__(self, monster_database: DbContext, nickname_overrides, basename_overrides,
                       panthname_overrides, accept_filter=None):
        # Important not to hold onto anything except IDs here so we don't leak memory
        self.db_context = monster_database
        base_monster_ids = monster_database.get_base_monster_ids()

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
            136: ['xmas', 'christmas'],
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
            group_basename_overrides = basename_overrides.get(base_id, [])
            evolution_tree = [monster_database.get_monster(m) for m in
                              monster_database.get_evolution_tree_ids(base_id)]
            named_mg = NamedMonsterGroup(evolution_tree, group_basename_overrides)
            for monster in evolution_tree:
                if accept_filter and not accept_filter(monster):
                    continue
                prefixes = self.compute_prefixes(monster, evolution_tree)
                extra_nicknames = monster_id_to_nicknames[monster.monster_id]
                named_monster = NamedMonster(monster, named_mg, prefixes, extra_nicknames,
                                             db_context=self.db_context)
                named_monsters.append(named_monster)

        # Sort the NamedMonsters into the opposite order we want to accept their nicknames in
        # This order is:
        #  1) High priority first
        #  2) Larger group sizes
        #  3) Minimum ID size in the group
        #  4) Monsters with higher ID values
        def named_monsters_sort(nm: NamedMonster):
            return (not nm.is_low_priority, nm.group_size, -1 *
                    nm.base_monster_no_na, nm.monster_no_na)

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
        self.two_word_entries = {}
        for nm in named_monsters:
            self.all_prefixes.update(nm.prefixes)
            for nickname in nm.final_nicknames:
                self.all_entries[nickname] = nm
            for nickname in nm.final_two_word_nicknames:
                self.two_word_entries[nickname] = nm
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

    def init_index(self):
        pass

    def compute_prefixes(self, m: DgMonster, evotree: list):
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

        awoken = lower_name.startswith('awoken') or '覚醒' in lower_name
        revo = lower_name.startswith('reincarnated') or '転生' in lower_name
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
        if m.cur_evo_type == EvoType.Base:
            prefixes.add('base')
        elif m.cur_evo_type == EvoType.Evo:
            prefixes.add('evo')
        elif m.cur_evo_type == EvoType.UvoAwoken and not awoken_or_revo_or_equip_or_mega:
            prefixes.add('uvo')
            prefixes.add('uevo')
        elif m.cur_evo_type == EvoType.UuvoReincarnated and not awoken_or_revo_or_equip_or_mega:
            prefixes.add('uuvo')
            prefixes.add('uuevo')

        # True Evo Type Prefixes
        if m.true_evo_type == InternalEvoType.Reincarnated:
            prefixes.add('revo')
            prefixes.add('reincarnated')

        # Other Prefixes
        if m.farmable:
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
        prefixes.update(self.series_to_prefix_map.get(
            self.db_context.graph.get_monster(m.monster_no).series.series_id, []))

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

        # handle exact nickname match
        if query in self.all_entries:
            return self.all_entries[query], None, "Exact nickname"

        contains_ja = tsutils.containsJa(query)
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
            return self.pickBestMonster(matches), None, "Base ID match, max of 1".format()

        # prefix search for nicknames, space-preceeded, take max id
        for nickname, m in self.all_entries.items():
            if nickname.startswith(query + ' '):
                matches.add(m)
        if len(matches):
            return self.pickBestMonster(matches), None, "Space nickname prefix, max of {}".format(len(matches))

        # prefix search for nicknames, take max id
        for nickname, m in self.all_entries.items():
            if nickname.startswith(query):
                matches.add(m)
        if len(matches):
            all_names = ",".join(map(lambda x: x.name_en, matches))
            return self.pickBestMonster(matches), None, "Nickname prefix, max of {}, matches=({})".format(
                len(matches), all_names)

        # prefix search for full name, take max id
        for nickname, m in self.all_entries.items():
            if (m.name_en.lower().startswith(query) or m.name_ja.lower().startswith(query)):
                matches.add(m)
        if len(matches):
            return self.pickBestMonster(matches), None, "Full name, max of {}".format(len(matches))

        # for nicknames with 2 names, prefix search 2nd word, take max id
        if query in self.two_word_entries:
            return self.two_word_entries[query], None, "Second-word nickname prefix, max of {}".format(len(matches))

        # TODO: refactor 2nd search characteristcs for 2nd word

        # full name contains on nickname, take max id
        for nickname, m in self.all_entries.items():
            if (query in m.name_en.lower() or query in m.name_ja.lower()):
                matches.add(m)
        if len(matches):
            return self.pickBestMonster(matches), None, 'Nickname contains nickname match ({})'.format(
                len(matches))

        # No decent matches. Try near hits on nickname instead
        matches = difflib.get_close_matches(query, self.all_entries.keys(), n=1, cutoff=.8)
        if len(matches):
            match = matches[0]
            return self.all_entries[match], None, 'Close nickname match ({})'.format(match)

        # Still no decent matches. Try near hits on full name instead
        matches = difflib.get_close_matches(
            query, self.all_en_name_to_monsters.keys(), n=1, cutoff=.9)
        if len(matches):
            match = matches[0]
            return self.all_en_name_to_monsters[match], None, 'Close name match ({})'.format(match)

        # About to give up, try matching all words
        matches = set()
        for nickname, m in self.all_entries.items():
            if (all(map(lambda x: x in m.name_en.lower(), query.split())) or
                            all(map(lambda x: x in m.name_ja.lower(), query.split()))):
                matches.add(m)
        if len(matches):
            return self.pickBestMonster(matches), None, 'All word match on full name, max of {}'.format(
                len(matches))

        # couldn't find anything
        return None, "Could not find a match for: " + query, None

    def find_monster2(self, query):
        """Search with alternative method for resolving prefixes.

        Implements the lookup for id2, where you are allowed to specify multiple prefixes for a card.
        All prefixes are required to be exactly matched by the card.
        Follows a similar logic to the regular id but after each check, will remove any potential match that doesn't
        contain every single specified prefix.
        """
        query = tsutils.rmdiacritics(query).lower().strip()
        # id search
        if query.isdigit():
            m = self.monster_no_na_to_named_monster.get(int(query))
            if m is None:
                return None, 'Looks like a monster ID but was not found', None
            else:
                return m, None, "ID lookup"

        # handle exact nickname match
        if query in self.all_entries:
            return self.all_entries[query], None, "Exact nickname"

        contains_ja = tsutils.containsJa(query)
        if len(query) < 2 and contains_ja:
            return None, 'Japanese queries must be at least 2 characters', None
        elif len(query) < 4 and not contains_ja:
            return None, 'Your query must be at least 4 letters', None

        # we want to look up only the main part of the query, and then verify that each result has the prefixes
        # so break up the query into an array of prefixes, and a string (new_query) that will be the lookup
        query_prefixes = []
        parts_of_query = query.split()
        new_query = ''
        for i, part in enumerate(parts_of_query):
            if part in self.all_prefixes:
                query_prefixes.append(part)
            else:
                new_query = ' '.join(parts_of_query[i:])
                break

        # if we don't have any prefixes, then default to using the regular id lookup
        if len(query_prefixes) < 1:
            return self.find_monster(query)

        matches = PotentialMatches()

        # prefix search for ids, take max id
        for nickname, m in self.all_entries.items():
            if query.endswith("base {}".format(m.monster_id)):
                matches.add(
                    find_first(lambda mo: m.base_monster_no == mo.monster_id, self.all_entries.values()))
        matches.remove_potential_matches_without_all_prefixes(query_prefixes)

        # first try to get matches from nicknames
        for nickname, m in self.all_entries.items():
            if new_query in nickname:
                matches.add(m)
        matches.remove_potential_matches_without_all_prefixes(query_prefixes)

        # if we don't have any candidates yet, pick a new method
        if not matches.length():
            # try matching on exact names next
            for nickname, m in self.all_en_name_to_monsters.items():
                if new_query in m.name_en.lower() or new_query in m.name_ja.lower():
                    matches.add(m)
            matches.remove_potential_matches_without_all_prefixes(query_prefixes)

        # check for exact match on pantheon name but only if needed
        if not matches.length():
            for pantheon in self.all_pantheon_nicknames:
                if new_query == pantheon.lower():
                    matches.get_monsters_from_potential_pantheon_match(pantheon, self.pantheon_nick_to_name,
                                                                       self.pantheons)
            matches.remove_potential_matches_without_all_prefixes(query_prefixes)

        # check for any match on pantheon name, again but only if needed
        if not matches.length():
            for pantheon in self.all_pantheon_nicknames:
                if new_query in pantheon.lower():
                    matches.get_monsters_from_potential_pantheon_match(pantheon, self.pantheon_nick_to_name,
                                                                       self.pantheons)
            matches.remove_potential_matches_without_all_prefixes(query_prefixes)

        if matches.length():
            return matches.pick_best_monster(), None, None
        return None, "Could not find a match for: " + query, None

    def pickBestMonster(self, named_monster_list):
        return max(named_monster_list, key=lambda x: (not x.is_low_priority, x.rarity, x.monster_no_na))
