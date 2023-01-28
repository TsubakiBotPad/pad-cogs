import difflib
import json
import logging
from io import BytesIO
from typing import Any

import aiohttp
from redbot.core import checks, commands, Config
from tsutils.helper_functions import repeating_timer
from tsutils.menu.components.config import BotConfig
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.user_interaction import send_cancellation_message

from azurlane.azurlane_view import AzurlaneViewState
from azurlane.menu import AzurlaneMenu, AzurlaneMenuPanes
from azurlane.menu_map import azurlane_menu_map
from azurlane.resources import DATA_URL

logger = logging.getLogger('red.padbot-cogs.azurlane')


class AzurLane(commands.Cog):
    """AzurLane."""

    menu_map = azurlane_menu_map

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.card_data = []

        self.config = Config.get_conf(self, identifier=9401770)

        self.id_to_card = None
        self.names_to_card = None

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        return

    async def register_menu(self):
        await self.bot.wait_until_ready()
        menulistener = self.bot.get_cog("MenuListener")
        if menulistener is None:
            logger.warning("MenuListener is not loaded.")
            return
        await menulistener.register(self)

    async def get_menu_default_data(self, ims):
        data = {
            'alcog': self,
            'user_config': await BotConfig.get_user(self.config, ims['original_author_id']),
        }
        return data

    async def reload_al(self):
        await self.bot.wait_until_ready()
        async for _ in repeating_timer(3600, lambda: self == self.bot.get_cog('AzurLane')):
            async with aiohttp.ClientSession() as session:
                async with session.get(DATA_URL) as resp:
                    raw_resp = await resp.text()
                    self.card_data = json.loads(raw_resp)['items']
            logger.info(f'Done retrieving cards: {len(self.card_data)}')

            self.id_to_card = {c['id']: c for c in self.card_data}
            self.names_to_card = {'{}'.format(c['name_en']).lower(): c for c in self.card_data}

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def alid(self, ctx, *, query: str):
        """Azure Lane query."""
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

        if not c:
            return await send_cancellation_message(ctx, f'No matches for query `{query}`.')
        reaction_list = AzurlaneMenuPanes.get_initial_reaction_list(len(c['images']))
        menu = AzurlaneMenu.menu()
        query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, query)
        state = AzurlaneViewState(ctx.message.author.id, AzurlaneMenu.MENU_TYPE,
                                  query_settings,
                                  c, 0,
                                  reaction_list=reaction_list)

        await menu.create(ctx, state)
