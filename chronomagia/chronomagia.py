import asyncio
import csv
import difflib
import os
import traceback
import urllib.parse
from collections import OrderedDict

import discord
from redbot.core import commands, data_manager
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import inline

import rpadutils
from rpadutils import Menu, EmojiUpdater


def _data_file(file_name: str) -> str:
    return os.path.join(str(data_manager.cog_data_path(raw_name='padglobal')), file_name)


SUMMARY_SHEET = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vQsO9Xi9cKaUQWPvDjjIKpHotZ036LCTN66PuNoQwvb8qZi4LmEUEOYmHDyqUJUzghI28aPrQHfRSYd/pub?gid=1488138129&single=true&output=csv'
PIC_URL = 'https://storage.googleapis.com/mirubot-chronomagia/cards/{}.png'


class CmCard(object):
    def __init__(self, csv_row):
        row = [x.strip() for x in csv_row]
        self.name = row[0]
        self.name_clean = clean_name_for_query(self.name)
        self.expansion = row[12]
        self.rarity = row[1]
        self.monspell = row[2]
        self.cost = row[3]
        self.type1 = row[4]
        self.type2 = row[5]
        self.atk = row[6]
        self.defn = row[7]
        self.atkeff = row[9]
        self.cardeff = row[11]


class ChronoMagia(commands.Cog):
    """ChronoMagia."""

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.card_data = []
        self.menu = Menu(bot)
        self.id_emoji = '\N{INFORMATION SOURCE}'
        self.pic_emoji = '\N{FRAME WITH PICTURE}'

    async def reload_cm_task(self):
        await self.bot.wait_until_ready()
        while self == self.bot.get_cog('ChronoMagia'):
            try:
                await self.refresh_data()
                print('Done refreshing ChronoMagia')
            except Exception as ex:
                print("reload CM loop caught exception " + str(ex))
                traceback.print_exc()
            await asyncio.sleep(60 * 60 * 1)

    async def refresh_data(self):
        await self.bot.wait_until_ready()

        standard_expiry_secs = 2 * 60 * 60
        summary_text = await rpadutils.makeAsyncCachedPlainRequest(
            _data_file('summary.csv'), SUMMARY_SHEET, standard_expiry_secs)
        file_reader = csv.reader(summary_text.splitlines(), delimiter=',')
        next(file_reader, None)  # skip header
        self.card_data.clear()
        for row in file_reader:
            if not row or not row[0].strip():
                # Ignore empty rows
                continue
            if len(row) < 11:
                print('bad row: ', row)
            self.card_data.append(CmCard(row))

    @commands.command()
    async def cmid(self, ctx, *, query: str):
        """ChronoMagia query."""
        query = clean_name_for_query(query)
        if len(query) < 3:
            await ctx.send(inline('query must be at least 3 characters'))
            return

        names_to_card = {x.name_clean: x for x in self.card_data}

        # Check if the card name starts with the query
        matches = list(filter(lambda x: x.startswith(query), names_to_card.keys()))

        # Find a card that closely matches the query
        if not matches:
            matches = difflib.get_close_matches(query, names_to_card.keys(), n=1, cutoff=.6)

        # Find a card that contains the query text
        if not matches:
            matches = list(filter(lambda x: query in x, names_to_card.keys()))

        if matches:
            await self.do_menu(ctx, names_to_card[matches[0]])
        else:
            await ctx.send(inline('no matches'))

    async def do_menu(self, ctx, c):
        emoji_to_embed = OrderedDict()
        emoji_to_embed[self.id_emoji] = make_embed(c)
        emoji_to_embed[self.pic_emoji] = make_img_embed(c)
        return await self._do_menu(ctx, self.id_emoji, emoji_to_embed)

    async def _do_menu(self, ctx, starting_menu_emoji, emoji_to_embed):
        remove_emoji = self.menu.emoji['no']
        emoji_to_embed[remove_emoji] = self.menu.reaction_delete_message

        try:
            result_msg, result_embed = await self.menu.custom_menu(ctx, EmojiUpdater(emoji_to_embed),
                                                                   starting_menu_emoji, timeout=20)
            if result_msg and result_embed:
                # Message is finished but not deleted, clear the footer
                result_embed.set_footer(text=discord.Embed.Empty)
                await result_msg.edit(embed=result_embed)
        except Exception as ex:
            print('Menu failure', ex)


def make_base_embed(c: CmCard):
    embed = discord.Embed()
    embed.title = c.name
    embed.set_footer(text='Requester may click the reactions below to switch tabs')
    return embed


def make_embed(c: CmCard):
    embed = make_base_embed(c)

    embed.add_field(
        name=c.monspell, value='{}\nCost {}'.format(c.rarity, c.cost), inline=True)
    if c.monspell == 'Monster':
        mtype = '\n{}/{} '.format(c.type1, c.type2) if c.type2 else '{} '.format(c.type1)
        embed.add_field(name=mtype, value='Atk {}\nDef {}'.format(c.atk, c.defn), inline=True)
        if c.expansion:
            embed.add_field(name='Expansion', value=c.expansion, inline=False)

        if c.atkeff:
            embed.add_field(name='Attack Effect', value=c.atkeff, inline=False)

        if c.cardeff:
            embed.add_field(name='Card Effect', value=c.cardeff, inline=False)
    else:
        embed.add_field(name='Card Effect', value=c.cardeff, inline=True)

    return embed


def make_img_embed(c: CmCard):
    embed = make_base_embed(c)
    url = PIC_URL.format(urllib.parse.quote(c.name))
    print(url)
    embed.set_image(url=url)
    return embed


def clean_name_for_query(name: str):
    return name.strip().lower().replace(',', '')
