import json
import os
from datetime import datetime
from typing import Awaitable, Callable, TYPE_CHECKING, Tuple

import aiofiles
from aiomysql import Cursor
from redbot.core import Config, checks
from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import inline
from tsutils.cog_mixins import CogMixin, mixin_group
from tsutils.user_interaction import send_cancellation_message

if TYPE_CHECKING:
    from dbcog import DBCog

SERIES_KEYS = {
    "name_en": 'Untranslated',
    "name_ja": 'Untranslated',
    "name_ko": 'Untranslated',
    "series_type": None,
}

SERIES_TYPES = [
    "regular",
    "event",
    "seasonal",
    "ghcollab",
    "collab",
    "lowpriority",
]


class CRUDSeries(CogMixin):
    def setup_self(self):
        self.series.setup(self)

    red_get_data_for_user = red_delete_data_for_user = lambda x: None

    config: Config
    json_folder: str

    get_dbcog: Callable[[], Awaitable["DBCog"]]
    execute_read: Callable[[Context, str, Tuple], Awaitable[None]]
    execute_write: Callable[[Context, str, Tuple], Awaitable[None]]
    git_verify: Callable[[Context, str, str], Awaitable[None]]
    get_cursor: Callable[[], Awaitable[Cursor]]

    @mixin_group('crud')
    async def series(self, ctx):
        """Series related commands"""

    @series.command()
    async def search(self, ctx, *, search_text):
        """Search for a series via its jp or na name"""
        search_text = '%{}%'.format(search_text).lower()
        sql = ('SELECT series_id, name_en, name_ja, name_ko FROM series'
               ' WHERE lower(name_en) LIKE %s OR lower(name_ja) LIKE %s'
               ' ORDER BY series_id DESC LIMIT 20')
        await self.execute_read(ctx, sql, (search_text, search_text))

    @series.command()
    async def add(self, ctx, *elements):
        """Add a new series.

        Valid element keys are: `name_en`, `name_ko`, `name_ja`, `series_type`

        Example Usage:
        [p]crud series add key1 "Value1" key2 "Value2"
        """
        if not elements:
            return await ctx.send_help()
        if len(elements) % 2 != 0:
            return await send_cancellation_message(ctx, "Imbalanced key-value pairs. Make sure"
                                                        " multi-word values are in quotes")
        elements = {elements[i]: elements[i + 1] for i in range(0, len(elements), 2)}

        if not (elements and all(x in SERIES_KEYS for x in elements)):
            return await send_cancellation_message(ctx, f"Valid keys are {', '.join(map(inline, SERIES_KEYS))}")

        if "series_type" in elements and elements['series_type'] not in SERIES_TYPES:
            return await send_cancellation_message(ctx, "`series_type` must be one of: " + ", ".join(SERIES_TYPES))

        EXTRAS = {}
        async with await self.get_cursor() as cursor:
            await cursor.execute("SELECT MAX(series_id) AS max_id FROM series")
            max_val = (await cursor.fetchall())[0]['max_id']
            EXTRAS['series_id'] = max_val + 1
        EXTRAS['tstamp'] = int(datetime.now().timestamp())
        elements = {**SERIES_KEYS, **EXTRAS, **elements}

        key_infix = ", ".join(elements.keys())
        value_infix = ", ".join("%s" for v in elements.values())
        sql = ('INSERT INTO series ({})'
               ' VALUES ({})').format(key_infix, value_infix)

        await self.execute_write(ctx, sql, (*elements.values(),))

        fn = os.path.join(await self.config.pipeline_base(), self.json_folder, 'series.json')
        async with aiofiles.open(fn, 'r') as f:
            j = json.loads(await f.read())
        j.append({
            'name_ja': elements['name_ja'],
            'name_en': elements['name_en'],
            'name_ko': elements['name_ko'],
            'series_id': elements['series_id'],
            'series_type': elements['series_type']
        })
        async with aiofiles.open(fn, 'w') as f:
            await f.write(json.dumps(j, indent=2, ensure_ascii=False, sort_keys=True))
        await self.git_verify(ctx, self.json_folder, 'series.json')

    @series.command()
    async def edit(self, ctx, series_id: int, *elements):
        """Edit an existing series.

        Valid element keys are: `name_en`, `name_ko`, `name_ja`, `series_type`

        Example Usage:
        [p]crud series edit 100 key1 "Value1" key2 "Value2"
        """
        if not elements:
            return await ctx.send_help()
        if len(elements) % 2 != 0:
            return await send_cancellation_message(ctx, "Imbalanced key-value pairs. Make sure"
                                                        " multi-word values are in quotes")
        elements = {elements[i]: elements[i + 1] for i in range(0, len(elements), 2)}

        if not (elements and all(x in SERIES_KEYS for x in elements)):
            return await ctx.send_help()

        if "series_type" in elements and elements['series_type'] not in SERIES_TYPES:
            return await ctx.send("`series_type` must be one of: " + ", ".join(SERIES_TYPES))

        replacement_infix = ", ".join(["{} = %s".format(k) for k in elements.keys()])
        sql = ('UPDATE series'
               ' SET {}'
               ' WHERE series_id = %s').format(replacement_infix)

        await self.execute_write(ctx, sql, (*elements.values(), series_id))

        fn = os.path.join(await self.config.pipeline_base(), self.json_folder, 'series.json')
        async with aiofiles.open(fn, 'r') as f:
            j = json.loads(await f.read())
        for e in j:
            if e['series_id'] == series_id:
                e.update(elements)
        async with aiofiles.open(fn, 'w') as f:
            await f.write(json.dumps(j, indent=2, ensure_ascii=False, sort_keys=True))
        await self.git_verify(ctx, self.json_folder, 'series.json')

    @series.command()
    @checks.is_owner()
    async def delete(self, ctx, series_id: int):
        """Delete an existing series"""
        sql = ('DELETE FROM series'
               ' WHERE series_id = %s')

        await self.execute_write(ctx, sql, (series_id,))

        fn = os.path.join(await self.config.pipeline_base(), self.json_folder, 'series.json')
        async with aiofiles.open(fn, 'r') as f:
            j = json.loads(await f.read())
        for e in j[:]:
            if e['series_id'] == series_id:
                j.remove(e)
        async with aiofiles.open(fn, 'w') as f:
            await f.write(json.dumps(j, indent=2, ensure_ascii=False, sort_keys=True))
        await self.git_verify(ctx, self.json_folder, 'series.json')
