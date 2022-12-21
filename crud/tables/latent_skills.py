import json
import os
from datetime import datetime
from json import JSONDecodeError
from typing import Awaitable, Callable, TYPE_CHECKING, Tuple

import aiofiles
from redbot.core import Config, checks
from redbot.core.commands import Context
from tsutils.cog_mixins import CogMixin, mixin_group
from tsutils.user_interaction import send_cancellation_message

if TYPE_CHECKING:
    from dbcog import DBCog

LATENT_SKILL_KEYS = {
    "latent_skill_id": -1,
    "name_ja": 'Untranslated',
    "name_en": 'Untranslated',
    "name_ko": 'Untranslated',
    "desc_ja": 'Untranslated',
    "desc_en": 'Untranslated',
    "desc_ko": 'Untranslated',
    "name_ja_official": 'Unknown',
    "name_en_official": 'Unknown',
    "name_ko_official": 'Unknown',
    "desc_ja_official": 'Unknown',
    "desc_en_official": 'Unknown',
    "desc_ko_official": 'Unknown',
    "monster_id": None,
    "slots": None,
    "required_awakening": None,
    "required_types": None,
    "required_level": None,
    "has_120_boost": 0,
}


class CRUDLatentSkills(CogMixin):
    def setup_self(self):
        self.latentskill.setup(self)

    red_get_data_for_user = red_delete_data_for_user = lambda x: None

    config: Config
    json_folder: str

    get_dbcog: Callable[[], Awaitable["DBCog"]]
    execute_read: Callable[[Context, str, Tuple], Awaitable[None]]
    execute_write: Callable[[Context, str, Tuple], Awaitable[None]]
    git_verify: Callable[[Context, str, str], Awaitable[None]]

    @mixin_group('crud', aliases=['lats'])
    async def latentskill(self, ctx):
        """Awoken skill related commands"""

    @latentskill.command()
    async def search(self, ctx, *, search_text):
        """Search for a latent skill via its jp or na name"""
        sql = (f'SELECT latent_skill_id, name_en, name_ja, name_ko, desc_en,'
               f' desc_ja, desc_ko FROM latent_skills'
               f' WHERE lower(name_en_official) LIKE %s OR lower(name_ja_official) LIKE %s'
               f' ORDER BY latent_skill_id DESC LIMIT 20')
        replacements = ('%{}%'.format(search_text).lower(),) * 2
        await self.execute_read(ctx, sql, replacements)

    @latentskill.command()
    @checks.is_owner()
    async def add(self, ctx, *elements):
        """Add a new latent skill.

        Valid element keys are: `name_ja`, `name_en`, `name_ko`, `desc_ja`, `desc_en`, `desc_ko`,\
         `name_ja_official`, `name_en_official`, `name_ko_official`, `desc_ja_official`, `desc_en_official`,\
         `desc_ko_official`, `slots`, `monster_id`, `required_awakening`, `required_types`, `required_level`,\
         `has_120_boost`, `latent_skill_id`

        Example Usage:
        [p]crud latentskill add latent_skill_id 1 name_en "Improved HP" slots 1
        """
        if not elements:
            return await ctx.send_help()
        if len(elements) % 2 != 0:
            return await send_cancellation_message(ctx, "Imbalanced key-value pairs. Make sure"
                                                        " multi-word values are in quotes")
        elements = {elements[i]: elements[i + 1] for i in range(0, len(elements), 2)}

        if not (elements and all(x in LATENT_SKILL_KEYS for x in elements)):
            return await ctx.send_help()

        required_vals = ('latent_skill_id', 'monster_id', 'slots')
        for rval in required_vals:
            if rval not in elements:
                return await ctx.send(f"You must supply `{rval}` when adding a new latent skill.")

        numeric_vals = ('latent_skill_id', 'monster_id', 'slots', 'required_awakening', 'required_level')
        for nval in numeric_vals:
            if nval in elements:
                if not elements[nval].isdigit():
                    return await ctx.send(f"`{nval}` must be numeric.")
                elements[nval] = int(elements[nval])

        bool_vals = ('has_120_boost',)
        for bval in bool_vals:
            if bval in elements:
                if not elements[bval] in ('0', '1'):
                    return await ctx.send(f"`{bval}` must be 0 or 1.")
                elements[bval] = int(elements[bval])

        json_vals = ('required_types',)
        for jval in json_vals:
            if jval in elements:
                try:
                    json.loads(elements[jval])
                except JSONDecodeError:
                    return await ctx.send(f"`{jval}` must be valid JSON.")

        elements = {**LATENT_SKILL_KEYS, **elements}

        key_infix = ", ".join(elements.keys())
        value_infix = ", ".join("%s" for v in elements.values())
        sql = ('INSERT INTO latent_skills ({})'
               ' VALUES ({})').format(key_infix, value_infix)
        await self.execute_write(ctx, sql, (*elements.values(),))

    @latentskill.command(name="edit")
    async def edit(self, ctx, latent_skill_id: int, *elements):
        """Edit an existing latent skill.

        Valid element keys are: `name_ja`, `name_en`, `name_ko`, `desc_ja`, `desc_en`, `desc_ko`,\
         `name_ja_official`, `name_en_official`, `name_ko_official`, `desc_ja_official`, `desc_en_official`,\
         `desc_ko_official`, `slots`, `monster_id`, `required_awakening`, `required_types`, `required_level`,\
         `has_120_boost`

        Example Usage:
        [p]crud latentskill edit 1 key1 "Value1" key2 "Value2"
        """
        dbcog = await self.get_dbcog()

        if not elements:
            return await ctx.send_help()
        if len(elements) % 2 != 0:
            return await send_cancellation_message(ctx, "Imbalanced key-value pairs. Make sure"
                                                        " multi-word values are in quotes")
        elements = {elements[i]: elements[i + 1] for i in range(0, len(elements), 2)}

        if not (elements and all(x in LATENT_SKILL_KEYS for x in elements)):
            return await ctx.send_help()

        if 'latent_skill_id' in elements:
            return await ctx.send("`latent_skill_id` is not a supported key for editing.")

        numeric_vals = ('latent_skill_id', 'monster_id', 'slots', 'required_awakening', 'required_level')
        for nval in numeric_vals:
            if nval in elements:
                if not elements[nval].isdigit():
                    return await ctx.send(f"`{nval}` must be numeric.")
                elements[nval] = int(elements[nval])

        bool_vals = ('has_120_boost',)
        for bval in bool_vals:
            if bval in elements:
                if not elements[bval] in ('0', '1'):
                    return await ctx.send(f"`{bval}` must be 0 or 1.")
                elements[bval] = int(elements[bval])

        json_vals = ('required_types',)
        for jval in json_vals:
            if jval in elements:
                try:
                    json.loads(elements[jval])
                except JSONDecodeError:
                    return await ctx.send(f"`{jval}` must be valid JSON.")

        replacement_infix = ", ".join(["{} = %s".format(k) for k in elements.keys()])
        sql = ('UPDATE latent_skills'
               ' SET {}'
               ' WHERE latent_skill_id = %s').format(replacement_infix)
        await self.execute_write(ctx, sql, (*elements.values(), latent_skill_id))

    @latentskill.command()
    @checks.is_owner()
    async def delete(self, ctx, latent_skill_id: int):
        """Delete an existing latent skill"""
        sql = ('DELETE FROM latent_skills'
               ' WHERE latent_skill_id = %s')

        await self.execute_write(ctx, sql, (latent_skill_id,))
