import logging
import re
from collections import defaultdict
from typing import Callable, Coroutine, Iterable, List, Literal, Sequence, Set, TYPE_CHECKING, Tuple, TypeVar

from aiomysql import Cursor
from discord.ext.commands import BadArgument, Converter
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import commands
from tsutils.enums import Server
from tsutils.errors import ClientInlineTextException
from tsutils.tsubaki.monster_header import MonsterHeader
from tsutils.user_interaction import get_user_confirmation

if TYPE_CHECKING:
    from dbcog import DBCog
    from dbcog.models.monster_model import MonsterModel

logger = logging.getLogger('red.padbot-cogs.crud.editseries')
T = TypeVar("T")

if not TYPE_CHECKING:
    class AliasedKeywordConverter(Converter):
        def __init__(self, aliases):
            self.aliases = aliases

        async def convert(self, ctx, argument) -> str:
            for kw, aliases in self.aliases.items():
                if argument == kw or (aliases is not None and argument in aliases):
                    return kw
            raise BadArgument(f"Bad keyword `{argument}`."
                              f" Valid keywords are `{'`, `'.join(self.aliases)}`.")


    EditSeriesCommand = AliasedKeywordConverter({
        'add': None,
        'remove': ('rm', 'delete', 'del'),
        'promote': None,
    })
    EditSeriesTarget = AliasedKeywordConverter({
        'monster': ('monsters'),
        'tree': None,
        'group': None,
    })
else:
    EditSeriesCommand = Literal['add', 'remove', 'promote']
    EditSeriesTarget = Literal['monster', 'tree', 'group']


def disjoint_sets(superset: Iterable[T], f: Callable[[T], bool]) -> Tuple[Set[T], Set[T]]:
    a, b = set(), set()
    for e in superset:
        (a if f(e) else b).add(e)
    return a, b


class EditSeries:
    config: Config
    bot: Red
    get_cursor: Callable[[], Coroutine[None, None, Cursor]]
    get_dbcog: Callable[[], Coroutine[None, None, "DBCog"]]

    async def es_execute_write(self, ctx, sql: str, replacements: Sequence = ()) -> int:
        async with await self.get_cursor() as cursor:
            affected = 0
            if sql.strip():
                affected = await cursor.execute(sql, replacements)
                printable = re.sub(r'\n[ \t]+', r'\n', sql % replacements)
                printable = re.sub(r'\n', r'\n\t', printable).strip()
                logger.info(f"{ctx.author} executed the following query via {ctx.message.content}:"
                            f"\n{printable}"
                            f"\nwhich affected {affected} row(s).")
        await ctx.send("{} row(s) affected.".format(affected))
        return affected

    @commands.command()
    async def editseries(self, ctx, command: EditSeriesCommand, series_id: int,
                         target: EditSeriesTarget, *, target_str):
        """Affect the series of a target.

        Commands:
            add - Add a series. If this is the only series, add as a primary series
            remove - Remove a series. If this is the primary series, randomly choose another to take its place
            promote - Add a series as primary, possibly demoting an existing primary in the process

        Targets:
            monster/monsters - One or more monsters specified by id
            tree - A monster tree specified by a monster id of any monster in the tree
            group - A GH group specified by a group id

        Examples:
           [p]editseries add 91 monsters 1319, 1825
           [p]editseries rm 7 tree 1
           [p]editseries promote 28 group 112
        """

        async def tryint(arg):
            if not arg.isnumeric():
                await ctx.send_help()
                raise ClientInlineTextException()

        monsters = None
        if target == 'monster':
            monsters = [int(mid) for mid in re.split(r'\D+', target_str)]
        elif target == 'tree':
            dbcog = await self.get_dbcog()
            monsters = dbcog.database.graph.get_alt_monsters(dbcog.get_monster(int(target_str)))
        elif target == 'group':
            dbcog = await self.get_dbcog()
            monsters = dbcog.database.get_monsters_where(lambda m: m.group_id == int(target_str),
                                                         server=Server.COMBINED)

        if command == 'add':
            await self.es_add(ctx, series_id, monsters)
        elif command == 'remove':
            await self.es_remove(ctx, series_id, monsters)
        elif command == 'promote':
            await self.es_promote(ctx, series_id, monsters)

    async def es_add(self, ctx, series_id: int, monsters: List["MonsterModel"]):
        monsters_str = "(" + ",".join(str(m.monster_id) for m in monsters) + ")"
        async with await self.get_cursor() as cursor:
            await cursor.execute(f"""
                SELECT
                monster_id, series_id
                FROM monster_series
                WHERE monster_id IN {monsters_str} AND series_id <> {series_id}""", ())
            rows = await cursor.fetchall()
            sids = defaultdict(set)
            for row in rows:
                sids[row['monster_id']].add(row['series_id'])
            secondary, primary = disjoint_sets(monsters, lambda m: m.monster_id in sids)
            seen, secondary = map(lambda ms: sorted(ms, key=lambda m: m.monster_id),
                                  disjoint_sets(monsters, lambda m: series_id in sids[m.monster_id]))
            await cursor.execute("SELECT name_en FROM series WHERE series_id = %s", (series_id,))
            rows = await cursor.fetchall()
            if not rows:
                return await ctx.send(f"There is no series with id {series_id}")
            new_series = next(iter(rows))['name_en']
        sql = ""
        for monster in monsters:
            if monster in seen:
                continue
            mid = monster.monster_id
            sql += f"""
                INSERT INTO monster_series
                (monster_series_id, monster_id, series_id, priority, tstamp)
                VALUES
                ({series_id * 100000 + mid}, {mid}, {series_id}, {int(mid in sids)}, UNIX_TIMESTAMP()); 
            """
        confirmation = [f"You are adding series `{new_series}`."]
        if primary:
            confirmation.append(f"The following monsters will have the series added as a primary series:"
                                f" {', '.join(map(MonsterHeader.text_with_emoji, primary))}.")
        if secondary:
            confirmation.append(f"The following monsters will have the series added as a secondary series:"
                                f" {', '.join(map(MonsterHeader.text_with_emoji, secondary))}.")
        if seen:
            confirmation.append(f"The following monsters will not be changed as they already have the series:"
                                f" {', '.join(map(MonsterHeader.text_with_emoji, seen))}.")
        if not await get_user_confirmation(ctx, '\n'.join(confirmation),
                                           timeout=30, force_delete=False):
            return
        await self.es_execute_write(ctx, sql)

    async def es_remove(self, ctx, series_id: int, monsters: List["MonsterModel"]):
        monsters_str = "(" + ",".join(str(m.monster_id) for m in monsters) + ")"
        async with await self.get_cursor() as cursor:
            await cursor.execute(f"""
                SELECT
                monster_id, series_id, priority
                FROM monster_series
                WHERE monster_id IN {monsters_str}""", ())
            rows = await cursor.fetchall()
            sids = defaultdict(set)
            for row in rows:
                sids[row['monster_id']].add(row['series_id'])
            primaries = {}
            for row in rows:
                if row['priority']:
                    primaries[row['monster_id']] = row['series_id']
            await cursor.execute("SELECT name_en FROM series WHERE series_id = %s", (series_id,))
            rows = await cursor.fetchall()
            was_primary, wasnt_primary = disjoint_sets(monsters, lambda m: primaries[m.monster_id] == series_id)
            unadded, wasnt_primary = map(lambda ms: sorted(ms, key=lambda m: m.monster_id),
                                         disjoint_sets(wasnt_primary, lambda m: series_id not in sids[m.monster_id]))
            if not rows:
                return await ctx.send(f"There is no series with id {series_id}")
            new_series = next(iter(rows))['name_en']
        sql = ""
        for monster in monsters:
            if monster in unadded:
                continue
            mid = monster.monster_id
            sql += f"""
                DELETE FROM monster_series
                WHERE monster_id = {mid} AND series_id = {series_id};
            """
            if monster in was_primary:
                sql += f"""UPDATE monster_series
                           SET priority = 1
                           WHERE monster_id = {mid}
                           LIMIT 1;
                """
        confirmation = [f"You are removing series `{new_series}`."]
        if was_primary:
            confirmation.append(f"The following monsters will have their primary series removed:"
                                f" {', '.join(map(MonsterHeader.text_with_emoji, was_primary))}.")
        if wasnt_primary:
            confirmation.append(f"The following monsters will have their secondary series removed:"
                                f" {', '.join(map(MonsterHeader.text_with_emoji, wasnt_primary))}.")
        if unadded:
            confirmation.append(f"The following monsters will continue to not have the series:"
                                f" {', '.join(map(MonsterHeader.text_with_emoji, unadded))}.")
        if not await get_user_confirmation(ctx, '\n'.join(confirmation),
                                           timeout=30, force_delete=False):
            return
        await self.es_execute_write(ctx, sql)

    async def es_promote(self, ctx, series_id: int, monsters: List["MonsterModel"]):
        monsters_str = "(" + ",".join(str(m.monster_id) for m in monsters) + ")"
        async with await self.get_cursor() as cursor:
            await cursor.execute(f"""
                SELECT
                monster_id, series_id
                FROM monster_series
                WHERE monster_id IN {monsters_str}""", ())
            rows = await cursor.fetchall()
            await cursor.execute("SELECT name_en FROM series WHERE series_id = %s", (series_id,))
            mids = [row['monster_id'] for row in rows]
            sids = defaultdict(set)
            for row in rows:
                sids[row['monster_id']].add(row['series_id'])
            rows = await cursor.fetchall()
            if not rows:
                return await ctx.send(f"There is no series with id {series_id}")
            new_series = next(iter(rows))['name_en']
        sql = ""
        has_series, no_series = disjoint_sets(monsters, lambda m: m.monster_id in mids)
        in_series, not_in_series = map(lambda ms: sorted(ms, key=lambda m: m.monster_id),
                                       disjoint_sets(has_series, lambda m: series_id in sids[m.monster_id]))
        for monster in monsters:
            mid = monster.monster_id
            sql += f"""
                DELETE FROM monster_series
                WHERE monster_id = {mid} AND series_id = {series_id};
                UPDATE monster_series
                SET priority = 0
                WHERE monster_id = {mid};
                INSERT INTO monster_series
                (monster_series_id, monster_id, series_id, priority, tstamp)
                VALUES
                ({series_id * 100000 + mid}, {mid}, {series_id}, 1, UNIX_TIMESTAMP()); 
            """
        confirmation = [f"You are promoting series `{new_series}`."]
        if has_series:
            confirmation.append(f"The following monsters will have this primary series added:"
                                f" {', '.join(map(MonsterHeader.text_with_emoji, has_series))}.")
        if no_series:
            confirmation.append(f"The following monsters will no longer be unsorted:"
                                f" {', '.join(map(MonsterHeader.text_with_emoji, no_series))}.")
        if not await get_user_confirmation(ctx, '\n'.join(confirmation),
                                           timeout=30, force_delete=False):
            return
        await self.es_execute_write(ctx, sql)
