"""
Utilities for managing moderator notes about users.
"""

import discord
from discord.ext import commands

from __main__ import send_cmd_help
from __main__ import settings

from . import rpadutils
from .rpadutils import CogSettings
from .utils import checks
from .utils.chat_formatting import *


class ModNotes:
    def __init__(self, bot):
        self.bot = bot
        self.settings = ModNotesSettings("modnotes")

    @commands.group(pass_context=True, no_pm=True, aliases=["usernote"])
    @checks.mod_or_permissions(manage_server=True)
    async def usernotes(self, context):
        """Moderator notes for users.

        This module allows you to create notes to share between moderators.
        """
        if context.invoked_subcommand is None:
            await send_cmd_help(context)

    @usernotes.command(name="print", pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_server=True)
    async def _print(self, ctx, user: discord.User):
        """Print the notes for a user."""
        notes = self.settings.getNotesForUser(ctx.message.server.id, user.id)
        if not notes:
            await self.bot.say(box('No notes for {}'.format(user.name)))
            return

        for idx, note in enumerate(notes):
            await self.bot.say(inline('Note {} of {}:'.format(idx + 1, len(notes))))
            await self.bot.say(box(note))

    @usernotes.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_server=True)
    async def add(self, ctx, user: discord.User, *, note_text: str):
        """Add a note to a user."""
        timestamp = str(ctx.message.timestamp)[:-7]
        msg = 'Added by {} ({}): {}'.format(ctx.message.author.name, timestamp, note_text)
        server_id = ctx.message.server.id
        notes = self.settings.addNoteForUser(server_id, user.id, msg)
        await self.bot.say(inline('Done. User {} now has {} notes'.format(user.name, len(notes))))

    @usernotes.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_server=True)
    async def delete(self, ctx, user: discord.User, note_num: int):
        """Delete a specific note for a user."""
        notes = self.settings.getNotesForUser(ctx.message.server.id, user.id)
        if len(notes) < note_num:
            await self.bot.say(box('Note not found for {}'.format(user.name)))
            return

        note = notes[note_num - 1]
        notes.remove(note)
        self.settings.setNotesForUser(ctx.message.server.id, user.id, notes)
        await self.bot.say(inline('Removed note {}. User has {} remaining.'.format(note_num, len(notes))))
        await self.bot.say(box(note))

    @usernotes.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_server=True)
    async def list(self, ctx):
        """Lists all users and note counts for the server."""
        user_notes = self.settings.getUserNotes(ctx.message.server.id)
        msg = 'Notes for {} users'.format(len(user_notes))
        for user_id, notes in user_notes.items():
            user = ctx.message.server.get_member(user_id)
            user_text = '{} ({})'.format(user.name, user.id) if user else user_id
            msg += '\n\t{} : {}'.format(len(notes), user_text)

        for page in pagify(msg):
            await self.bot.say(box(page))


def setup(bot):
    n = ModNotes(bot)
    bot.add_cog(n)


class ModNotesSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'servers': {}
        }
        return config

    def servers(self):
        return self.bot_settings['servers']

    def getServer(self, server_id):
        servers = self.servers()
        if server_id not in servers:
            servers[server_id] = {}
        return servers[server_id]

    def getUserNotes(self, server_id):
        server = self.getServer(server_id)
        key = 'user_notes'
        if key not in server:
            server[key] = {}
        return server[key]

    def getNotesForUser(self, server_id, user_id):
        user_notes = self.getUserNotes(server_id)
        return user_notes.get(user_id, [])

    def setNotesForUser(self, server_id, user_id, notes):
        user_notes = self.getUserNotes(server_id)

        if notes:
            user_notes[user_id] = notes
        else:
            user_notes.pop(user_id, None)
        self.save_settings()
        return notes

    def addNoteForUser(self, server_id, user_id, note: str):
        notes = self.getNotesForUser(server_id, user_id)
        notes.append(note)
        self.setNotesForUser(server_id, user_id, notes)
        return notes
