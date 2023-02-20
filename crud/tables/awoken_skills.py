import json
import os
from datetime import datetime
from typing import Awaitable, Callable, TYPE_CHECKING, Tuple

import aiofiles
from redbot.core import Config, checks
from redbot.core.commands import Context
from tsutils.cog_mixins import CogMixin, mixin_group
from tsutils.user_interaction import send_cancellation_message

if TYPE_CHECKING:
    from dbcog import DBCog

AWOKEN_SKILL_KEYS = {
    "awoken_skill_id": -1,
    "name_ja_official": "Unknown Official Name",
    "name_ko_official": "Unknown Official Name",
    "name_en_official": "Unknown Official Name",
    "desc_ja_official": "Unknown Official Text",
    "desc_ko_official": "Unknown Official Text",
    "desc_en_official": "Unknown Official Text",
    "name_en": 'Untranslated',
    "name_ja": 'Untranslated',
    "name_ko": 'Untranslated',
    "desc_en": 'Untranslated',
    "desc_ja": 'Untranslated',
    "desc_ko": 'Untranslated',
}


class CRUDAwokenSkills(CogMixin):
    def setup_self(self):
        self.awokenskill.setup(self)

    red_get_data_for_user = red_delete_data_for_user = lambda x: None

    config: Config
    json_folder: str

    get_dbcog: Callable[[], Awaitable["DBCog"]]
    execute_read: Callable[[Context, str, Tuple], Awaitable[None]]
    execute_write: Callable[[Context, str, Tuple], Awaitable[None]]
    git_verify: Callable[[Context, str, str], Awaitable[None]]

    @mixin_group('crud', aliases=['awos'])
    async def awokenskill(self, ctx):
        """Awoken skill related commands"""

    @awokenskill.command()
    async def search(self, ctx, *, search_text):
        """Search for a awoken skill via its jp or na name"""
        dbcog = await self.get_dbcog()
        if search_text in dbcog.KNOWN_AWOKEN_SKILL_TOKENS:
            where = f'awoken_skill_id = %s'
            replacements = (dbcog.KNOWN_AWOKEN_SKILL_TOKENS[search_text].value,)
        else:
            where = f"lower(name_en) LIKE %s OR lower(name_ja) LIKE %s"
            replacements = ('%{}%'.format(search_text).lower(),) * 2
        sql = (f'SELECT awoken_skill_id, name_en, name_ja, name_ko, desc_en,'
               f' desc_ja, desc_ko FROM awoken_skills'
               f' WHERE {where}'
               f' ORDER BY awoken_skill_id DESC LIMIT 20')
        await self.execute_read(ctx, sql, replacements)

    @awokenskill.command()
    @checks.is_owner()
    async def add(self, ctx, *elements):
        """Add a new awoken skill.

        Valid element keys are: `name_en`, `name_ko`, `name_ja`, `desc_en`, `desc_ko`, `desc_ja`

        Example Usage:
        [p]crud awokenskill add key1 "Value1" key2 "Value2"
        """
        if not elements:
            return await ctx.send_help()
        if len(elements) % 2 != 0:
            return await send_cancellation_message(ctx, "Imbalanced key-value pairs. Make sure"
                                                        " multi-word values are in quotes")
        elements = {elements[i]: elements[i + 1] for i in range(0, len(elements), 2)}

        if not (elements and all(x in AWOKEN_SKILL_KEYS for x in elements)):
            return await ctx.send_help()

        if "awoken_skill_id" not in elements or not elements["awoken_skill_id"].isdigit():
            return await ctx.send("You must supply an numeric `awoken_skill_id` when adding a new awoken skill.")
        elements["awoken_skill_id"] = int(elements["awoken_skill_id"])

        EXTRAS = {
            'adj_hp': 0,
            'adj_atk': 0,
            'adj_rcv': 0,
            'tstamp': int(datetime.now().timestamp())
        }
        elements = {**AWOKEN_SKILL_KEYS, **EXTRAS, **elements}

        key_infix = ", ".join(elements.keys())
        value_infix = ", ".join("%s" for v in elements.values())
        sql = ('INSERT INTO awoken_skills ({})'
               ' VALUES ({})').format(key_infix, value_infix)

        await self.execute_write(ctx, sql, (*elements.values(),))

        fn = os.path.join(await self.config.pipeline_base(), self.json_folder, 'awoken_skill.json')
        async with aiofiles.open(fn, 'r') as f:
            j = json.loads(await f.read())
        j.append({
            "adj_atk": 0,
            "adj_hp": 0,
            "adj_rcv": 0,
            "desc_ja": elements['desc_ja'],
            "desc_ja_official": elements['desc_ja_official'],
            "desc_ko": elements['desc_ko'],
            "desc_ko_official": elements['desc_ko_official'],
            "desc_en": elements['desc_en'],
            "desc_en_official": elements['desc_en_official'],
            'name_ja': elements['name_ja'],
            "name_ja_official": elements['name_ja_official'],
            'name_en': elements['name_en'],
            "name_ko_official": elements['name_ko_official'],
            'name_ko': elements['name_ko'],
            "name_en_official": elements['name_en_official'],
            "pad_awakening_id": elements['awoken_skill_id'],
        })
        async with aiofiles.open(fn, 'w') as f:
            await f.write(json.dumps(j, indent=2, ensure_ascii=False, sort_keys=True))
        await self.git_verify(ctx, self.json_folder, 'awoken_skill.json')

    @awokenskill.command()
    async def edit(self, ctx, awoken_skill, *elements):
        """Edit an existing awoken skill.

        Valid element keys are: `name_en`, `name_ko`, `name_ja`, `desc_en`, `desc_ko`, `desc_ja`

        Example Usage:
        [p]crud awokenskill edit 100 key1 "Value1" key2 "Value2"
        [p]crud awokenskill edit misc_comboboost key1 "Value1" key2 "Value2"
        """
        dbcog = await self.get_dbcog()
        if awoken_skill in dbcog.KNOWN_AWOKEN_SKILL_TOKENS:
            awoken_skill_id = dbcog.KNOWN_AWOKEN_SKILL_TOKENS[awoken_skill].value
        elif awoken_skill.isdigit():
            awoken_skill_id = int(awoken_skill)
        else:
            return await ctx.send("Invalid awoken skill.")

        awoken_skill_id = int(awoken_skill_id)

        if not elements:
            return await ctx.send_help()
        if len(elements) % 2 != 0:
            return await send_cancellation_message(ctx, "Imbalanced key-value pairs. Make sure"
                                                        " multi-word values are in quotes")
        elements = {elements[i]: elements[i + 1] for i in range(0, len(elements), 2)}

        if not (elements and all(x in AWOKEN_SKILL_KEYS for x in elements)):
            return await ctx.send_help()

        if 'awoken_skill_id' in elements:
            return await ctx.send("`awoken_skill_id` is not a supported key for editing.")

        replacement_infix = ", ".join(["{} = %s".format(k) for k in elements.keys()])
        sql = ('UPDATE awoken_skills'
               ' SET {}'
               ' WHERE awoken_skill_id = %s').format(replacement_infix)

        await self.execute_write(ctx, sql, (*elements.values(), awoken_skill_id))

        fn = os.path.join(await self.config.pipeline_base(), self.json_folder, 'awoken_skill.json')
        async with aiofiles.open(fn, 'r') as f:
            j = json.loads(await f.read())

        for e in j:
            if e['pad_awakening_id'] == awoken_skill_id:
                e.update(elements)
        async with aiofiles.open(fn, 'w') as f:
            await f.write(json.dumps(j, indent=2, ensure_ascii=False, sort_keys=True))
        await self.git_verify(ctx, self.json_folder, 'awoken_skill.json')

    @awokenskill.command()
    @checks.is_owner()
    async def delete(self, ctx, awoken_skill_id: int):
        """Delete an existing awoken skill"""
        sql = ('DELETE FROM awoken_skills'
               ' WHERE awoken_skill_id = %s')

        await self.execute_write(ctx, sql, (awoken_skill_id,))

        fn = os.path.join(await self.config.pipeline_base(), self.json_folder, 'awoken_skill.json')
        async with aiofiles.open(fn, 'r') as f:
            j = json.loads(await f.read())
        for e in j[:]:
            if e['pad_awakening_id'] == awoken_skill_id:
                j.remove(e)
        async with aiofiles.open(fn, 'w') as f:
            await f.write(json.dumps(j, indent=2, ensure_ascii=False, sort_keys=True))
        await self.git_verify(ctx, self.json_folder, 'awoken_skill.json')
