import difflib
import json
from _collections import OrderedDict

import aiohttp
from redbot.core import commands
from redbot.core.utils.chat_formatting import *

from rpadutils import Menu, EmojiUpdater, char_to_emoji

FIRST_REQ = 'https://schoolido.lu/api/cards/?page_size=100'


class SchoolIdol(commands.Cog):
    """SchoolIdol."""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.card_data = []
        self.menu = Menu(bot)
        self.regular_emoji = char_to_emoji('r')
        self.idol_emoji = char_to_emoji('i')

    async def reload_sif(self):
        await self.bot.wait_until_ready()

        next_req = FIRST_REQ
        async with aiohttp.ClientSession() as session:
            while next_req:
                print(next_req)
                async with session.get(next_req) as resp:
                    raw_resp = await resp.text()
                    js_resp = json.loads(raw_resp)
                    next_req = js_resp['next']
                    self.card_data.extend(js_resp['results'])
        print('done retrieving cards: {}'.format(len(self.card_data)))

        self.id_to_card = {c['id']: c for c in self.card_data}
        name_to_card = {'{}'.format(c['idol']['name']).lower(): c for c in self.card_data}
        firstname_to_card = {c['idol']['name'].lower().split(' ')[-1]: c for c in self.card_data}
        collection_name_to_card = {'{} {}'.format(
            c['translated_collection'], c['idol']['name']).lower(): c for c in self.card_data}
        collection_firstname_to_card = {'{} {}'.format(
            c['translated_collection'], c['idol']['name'].split(' ')[-1]).lower(): c for c in self.card_data}
        self.names_to_card = {
            **name_to_card,
            **firstname_to_card,
            **collection_name_to_card,
            **collection_firstname_to_card,
        }

    @commands.command()
    async def sifid(self, ctx, *, query: str):
        """SIF query."""
        query = query.lower().strip()
        c = None
        if query.isdigit():
            c = self.id_to_card.get(int(query), None)
        else:
            c = self.names_to_card.get(query, None)
            if c is None:
                matches = difflib.get_close_matches(
                    query, self.names_to_card.keys(), n=1, cutoff=.6)
                if len(matches):
                    c = self.names_to_card[matches[0]]

        if c:
            await self.do_menu(ctx, c)
        else:
            await ctx.send(inline('no matches'))

    async def do_menu(self, ctx, c):
        emoji_to_embed = OrderedDict()
        regular_embed = make_card_embed(c, IMAGE_FIELD)
        if regular_embed:
            emoji_to_embed[self.regular_emoji] = regular_embed
            starting_menu_emoji = self.regular_emoji

        idol_embed = make_card_embed(c, IDOL_IMAGE_FIELD)
        if idol_embed:
            emoji_to_embed[self.idol_emoji] = idol_embed
            starting_menu_emoji = self.idol_emoji

        if starting_menu_emoji is None:
            await ctx.send(inline('no images found'))
            return

        return await self._do_menu(ctx, starting_menu_emoji, emoji_to_embed)

    async def _do_menu(self, ctx, starting_menu_emoji, emoji_to_embed):
        remove_emoji = self.menu.emoji['no']
        emoji_to_embed[remove_emoji] = self.menu.reaction_delete_message

        try:
            result_msg, result_embed = await self.menu.custom_menu(ctx,
                                                                   EmojiUpdater(emoji_to_embed), starting_menu_emoji,
                                                                   timeout=20)
            if result_msg and result_embed:
                # Message is finished but not deleted, clear the footer
                result_embed.set_footer(text=discord.Embed.Empty)
                await self.bot.edit_message(result_msg, embed=result_embed)
        except Exception as ex:
            print('Menu failure', ex)


def make_card_embed(c, url_field):
    cid = c['id']
    image_url = c[url_field]
    if not image_url:
        return None

    base_url = 'https://storage.googleapis.com/mirubot/sifimages/processed/{}_{}.png'

    embed = discord.Embed()
    embed.title = toHeader(c)
    embed.url = get_info_url(c)
    embed.set_image(url=base_url.format(cid, url_field))
    embed.set_footer(text='Requester may click the reactions below to switch tabs')
    return embed


IMAGE_FIELD = 'transparent_image'
IDOL_IMAGE_FIELD = 'transparent_idolized_image'


def toHeader(c):
    cid = c['id']
    collection = c['translated_collection']
    name = c['idol']['name']
    if collection:
        return 'No. {} {} {}'.format(cid, collection, name)
    else:
        return 'No. {} {}'.format(cid, name)


def get_info_url(c):
    return 'https://schoolido.lu/cards/{}/'.format(c['id'])
