import discord
import datetime
import os
import asyncio
import re

from redbot.core import checks, commands, Config
from redbot.core.utils.chat_formatting import box, pagify, escape
from random import choice


class TriggerError(Exception):
    pass


class Unauthorized(TriggerError):
    pass


class NotFound(TriggerError):
    pass


class AlreadyExists(TriggerError):
    pass


class Trigger(commands.Cog):
    """Custom triggers"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=7173306)
        self.config.register_global(triggers=[])

        self.triggers = []

    @commands.group()
    @commands.guild_only()
    async def trigger(self, ctx):
        """Trigger creation commands"""

    @trigger.command()
    @checks.admin_or_permissions(administrator=True)
    async def create(self, ctx, trigger_name : str, *, triggered_by : str):
        """Creates a trigger"""
        try:
            self.create_trigger(trigger_name, triggered_by, ctx)
        except AlreadyExists:
            await ctx.send("A trigger with that name already exists.")
        else:
            await self.save_triggers()
            await ctx.send("Trigger created. Entering interactive "
                           "add mode...".format(ctx.prefix))
            trigger = self.get_trigger_by_name(trigger_name)
            await self.interactive_add_mode(trigger, ctx)
            await self.save_triggers()

    @trigger.command()
    @checks.admin_or_permissions(administrator=True)
    async def delete(self, ctx, trigger_name : str):
        """Deletes a trigger"""
        try:
            self.delete_trigger(trigger_name, ctx)
            await self.save_triggers()
        except Unauthorized:
            await ctx.send("You're not authorized to delete that trigger.")
        except NotFound:
            await ctx.send("That trigger doesn't exist.")
        else:
            await ctx.send("Trigger deleted.")

    @trigger.command()
    @checks.admin_or_permissions(administrator=True)
    async def add(self, ctx, trigger_name : str, *, response : str=None):
        """Adds a response to a trigger

        Leaving the response argument empty will enable interactive mode

        Owner only:
        Adding a response as 'file: filename.jpg' will send that file as
        response if present in data/trigger/files"""
        trigger = self.get_trigger_by_name(trigger_name)

        if trigger is None:
            await ctx.send("That trigger doesn't exist.")
            return
        if not trigger.can_edit(ctx.author):
            await ctx.send("You're not allowed to edit that trigger.")
            return

        if response is not None:
            trigger.responses.append(response)
            await ctx.send("Response added.")
        else: # Interactive mode
            await self.interactive_add_mode(trigger, ctx)
        await self.save_triggers()

    @trigger.command()
    @checks.admin_or_permissions(administrator=True)
    async def remove(self, ctx, trigger_name : str):
        """Lets you choose a response to remove"""
        trigger = self.get_trigger_by_name(trigger_name)

        if trigger is None:
            await ctx.send("That trigger doesn't exist.")
            return
        if trigger.responses == []:
            await ctx.send("That trigger has no responses to delete.")
            return
        if not trigger.can_edit(ctx.author):
            await ctx.send("You're not allowed to do that.")
            return

        msg = None
        current_list = None
        past_messages = []
        quit_msg = "\nType 'exit' to quit removal mode."

        while self.get_n_trigger_responses(trigger) is not None:
            r_list = self.get_n_trigger_responses(trigger, truncate=100)
            if current_list is None:
                current_list = await ctx.send(r_list + quit_msg)
            else:
                if r_list != current_list.content:
                    await current_list.edit(content=r_list + quit_msg)
            msg = await self.bot.wait_for("message", timeout=15.0, check=lambda m:m.author==ctx.author)
            if msg is None:
                await ctx.send("Nothing else to remove I guess.")
                break
            elif msg.content.lower().strip() == "exit":
                past_messages.append(msg)
                await ctx.send("Removal mode quit.")
                break
            try:
                i = int(msg.content)
                del trigger.responses[i]
            except:
                pass
            past_messages.append(msg)

        if not trigger.responses:
            await ctx.send("No more responses to delete.")

        past_messages.append(current_list)
        await self.attempt_cleanup(past_messages)

    async def attempt_cleanup(self, messages):
        try:
            for message in messages:
                await message.delete()
        except:
            pass

    @trigger.command()
    async def info(self, ctx, trigger_name : str):
        """Shows a trigger's info"""
        trigger = self.get_trigger_by_name(trigger_name)
        if trigger:
            msg = "Name: {}\n".format(trigger.name)
            owner_name = discord.utils.get(self.bot.get_all_members(), id=trigger.owner)
            owner_name = owner_name if owner_name is not None else "not found"
            msg += "Owner: {} ({})\n".format(owner_name, trigger.owner)
            trigger_type = "all responses" if trigger.type == "all" else "random response"
            msg += "Type: {}\n".format(trigger_type)
            influence = "server" if trigger.server is not None else "global"
            msg += "Influence: {}\n".format(influence)
            cs = "yes" if trigger.case_sensitive else "no"
            msg += "Case Sensitive: {}\n".format(cs)
            regex = "yes" if trigger.regex else "no"
            msg += "Regex: {}\n".format(regex)
            msg += "Cooldown: {} seconds\n".format(trigger.cooldown)
            msg += "Triggered By: \"{}\"\n".format(trigger.triggered_by.replace("`", "\\`"))
            msg += "Payload: {} responses\n".format(len(trigger.responses))
            msg += "Triggered: {} times\n".format(trigger.triggered)
            await ctx.send(box(msg, lang="xl"))
        else:
            await ctx.send("There is no trigger with that name.")

    @trigger.command()
    async def show(self, ctx, trigger_name : str):
        """Shows all responses of a trigger"""
        trigger = self.get_trigger_by_name(trigger_name)
        if trigger:
            payload = self.elaborate_payload(trigger.responses, truncate=9999)
            if payload:
                payload = "\n\n".join(payload)
                if len(payload) > 2000:
                    for page in pagify(payload, delims=[" "]):
                        await ctx.author.send(page)
                else:
                    await ctx.send(payload)
            else:
                await ctx.send("That trigger has no responses.")
        else:
            await ctx.send("That trigger doesn't exist.")

    @trigger.command(name="list")
    async def _list(self, ctx, trigger_type="local"):
        """Lists local / global triggers

        Defaults to local"""
        server = ctx.guild
        results = []
        if trigger_type == "local":
            for trigger in self.triggers:
                if trigger.server == server.id:
                    results.append(trigger)
        elif trigger_type == "global":
            for trigger in self.triggers:
                if trigger.server is None:
                    results.append(trigger)
        else:
            await ctx.send("Invalid type.")
            return
        if results:
            results = ", ".join([r.name for r in results])
            for page in pagify(results, delims=[" ", "\n"]):
                await ctx.send("```\n{}\n```".format(page.lstrip(" "), results))
        else:
            await ctx.send("I couldn't find any trigger of that type.")

    @trigger.command()
    async def search(self, ctx, *, search_terms : str):
        """Returns triggers matching the search terms"""
        result = self.search_triggers(search_terms.lower())
        if result:
            result = ", ".join(sorted([t.name for t in result]))
            await ctx.send("Triggers found:\n\n{}".format(result))
        else:
            await ctx.send("No triggers matching your search.")

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def triggerset(self, ctx):
        """Edits the settings of a trigger"""

    @triggerset.command()
    async def cooldown(self, ctx, trigger_name : str, seconds : int):
        """Sets the trigger's cooldown"""
        trigger = self.get_trigger_by_name(trigger_name)
        if not await self.settings_check(ctx, trigger, ctx.author):
            return
        if seconds < 1:
            seconds = 1
        trigger.cooldown = seconds
        await self.save_triggers()
        await ctx.send("Cooldown set to {} seconds.".format(seconds))

    @triggerset.command()
    async def phrase(self, ctx, trigger_name : str, *, triggered_by : str):
        """Sets the word/phrase by which the trigger is activated by"""
        trigger = self.get_trigger_by_name(trigger_name)
        if not await self.settings_check(ctx, trigger, ctx.author):
            return
        if not triggered_by:
            await ctx.send("Invalid setting.")
            return
        trigger.triggered_by = triggered_by
        await self.save_triggers()
        await ctx.send("The trigger will be activated by `{}`.".format(triggered_by))

    @triggerset.command()
    async def response(self, ctx, trigger_name : str, _type : str):
        """Sets the response type for the trigger.

        Available types: all, random

        All will show all responses in order
        Random will pick one at random"""
        trigger = self.get_trigger_by_name(trigger_name)
        if not await self.settings_check(ctx, trigger, ctx.author):
            return
        _type = _type.lower()
        if _type not in ("all", "random"):
            await ctx.send("Invalid type.")
            return
        trigger.type = _type
        await self.save_triggers()
        await ctx.send("Response type set to {}.".format(_type))

    @triggerset.command()
    @checks.is_owner()
    async def influence(self, ctx, trigger_name : str, _type : str):
        """Sets the influence of the trigger.

        Available types: server, global"""
        trigger = self.get_trigger_by_name(trigger_name)
        if not await self.settings_check(ctx, trigger, ctx.author):
            return
        _type = _type.lower()
        if _type not in ("server", "global"):
            await ctx.send("Invalid type.")
            return
        trigger.server = ctx.guild.id if _type == "server" else None
        await self.save_triggers()
        await ctx.send("Influence set to {}.".format(_type))

    @triggerset.command()
    async def channels(self, ctx, trigger_name : str, *channels : discord.TextChannel):
        """Sets the channel(s) in which the trigger will be active

        Not entering any channel will revert the trigger to server-wide"""
        trigger = self.get_trigger_by_name(trigger_name)
        if not await self.settings_check(ctx, trigger, ctx.author):
            return
        if channels:
            channels = [c.id for c in channels]
            trigger.channels[ctx.guild.id] = list(channels)
            await self.save_triggers()
            if trigger.server is not None:
                await ctx.send("The trigger will be enabled only on "
                                   "those channels.")
            else:
                await ctx.send("In this server the trigger will be "
                                   "enabled only on those channels")
        else:
            trigger.channels[ctx.guild.id] = []
            await self.save_triggers()
            await ctx.send("The trigger will be active in all channels.")

    @triggerset.command()
    async def casesensitive(self, ctx, trigger_name : str,
                            true_or_false : bool):
        """Toggles the trigger's case sensitivity.

        Can be true or false"""
        trigger = self.get_trigger_by_name(trigger_name)
        if not await self.settings_check(ctx, trigger, ctx.author):
            return
        trigger.case_sensitive = true_or_false
        await self.save_triggers()
        await ctx.send("Case sensitivity set to {}.".format(true_or_false))

    @triggerset.command()
    async def regex(self, ctx, trigger_name : str, true_or_false : bool):
        """Toggles the trigger's case capabilities.

        Can be true or false"""
        trigger = self.get_trigger_by_name(trigger_name)
        if not await self.settings_check(ctx, trigger, ctx.author):
            return
        trigger.regex = true_or_false
        await self.save_triggers()
        await ctx.send("Regex set to {}.".format(true_or_false))

    @triggerset.command()
    async def active(self, ctx, trigger_name : str, true_or_false : bool):
        """Toggles the trigger on/off.

        Can be true or false"""
        trigger = self.get_trigger_by_name(trigger_name)
        if not await self.settings_check(ctx, trigger, ctx.author):
            return
        trigger.active = true_or_false
        await self.save_triggers()
        await ctx.send("Trigger active: {}.".format(true_or_false))

    async def settings_check(ctx, self, trigger, author):
        if not trigger:
            await ctx.send("That trigger doesn't exist.")
            return False
        if not trigger.can_edit(author):
            await ctx.send("You're not authorized to edit that triggers' "
                           "settings.")
            return False
        return True

    def get_trigger_by_name(self, name):
        for trigger in self.triggers:
            if trigger.name.lower() == name.lower():
                return trigger
        return None

    def search_triggers(self, search_terms):
        results = []
        for trigger in self.triggers:
            if search_terms in trigger.name.lower():
                results.append(trigger)
                continue
            for payload in trigger.responses:
                if search_terms in payload.lower():
                    results.append(trigger)
                    break
            else:
                if search_terms in trigger.triggered_by.lower():
                    results.append(trigger)
        return results

    def create_trigger(self, name, triggered_by, ctx):
        trigger = self.get_trigger_by_name(name)
        if not trigger:
            trigger = TriggerObj(bot=self.bot,
                                 name=name,
                                 triggered_by=triggered_by,
                                 owner=ctx.author.id,
                                 server=ctx.guild.id
                                )
            self.triggers.append(trigger)
        else:
            raise AlreadyExists()

    def delete_trigger(self, name, ctx):
        trigger = self.get_trigger_by_name(name)
        if trigger:
            if not trigger.can_edit(ctx.author):
                raise Unauthorized()
            self.triggers.remove(trigger)
        else:
            raise NotFound()

    def elaborate_payload(self, payload, truncate=50, escape=True):
        shortened = []
        for p in payload:
            if escape:
                p = escape(p)
            if len(p) < truncate:
                shortened.append(p)
            else:
                shortened.append(p[:truncate] + "...")
        return shortened

    async def interactive_add_mode(self, trigger, ctx):
        msg = ""
        await ctx.send("Everything you type will be added as response "
                       "to the trigger. Type 'exit' to quit.")
        while msg is not None:
            msg = await self.bot.wait_for("message", timeout=60.0, check=lambda m:m.author==ctx.author)
            if msg is None:
                await ctx.send("No more responses then. "
                               "Your changes have been saved.")
                break
            if msg.content.lower().strip() == "exit":
                await ctx.send("Your changes have been saved.")
                break
            trigger.responses.append(msg.content)

    def get_n_trigger_responses(self, trigger, *, truncate=2000):
        msg = ""
        responses = trigger.responses
        i = 0
        for r in responses:
            if len(r) > truncate:
                r = r[:truncate] + "..."
            r = r.replace("`", "\\`").replace("*", "\\*").replace("_", "\\_")
            msg += "{}. {}\n".format(i, r)
            i += 1
        if msg != "":
            return box(msg, lang="py")
        else:
            return None

    async def is_command(self, msg):
        prefixes = await self.bot.get_prefix(msg)
        if not isinstance(prefixes, list):
            prefixes = [prefixes]
        for p in prefixes:
            if msg.content.startswith(p):
                return True
        return False

    def elaborate_response(self, trigger, r):
        is_owner = trigger.owner in self.bot.owner_ids
        if not is_owner:
            return "text", r
        if not r.startswith("file:"):
            return "text", r
        else:
            path = r.replace("file:", "").strip()
        path = os.path.join("data", "trigger", "files", path)
        if os.path.isfile(path):
            return "file", path
        else:
            return "text", r

    @commands.Cog.listener('on_message')
    async def on_message(self, message):
        channel = message.channel
        author = message.author

        if message.guild is None:
            return

        if author == self.bot.user:
            return

        if await self.is_command(message):
            return

        for trigger in self.triggers:
            if not trigger.check(message):
                continue
            payload = trigger.payload()
            for p in payload:
                resp_type, resp = self.elaborate_response(trigger, p)
                if resp_type == "text":
                    await channel.send(resp)
                elif resp_type == "file":
                    await channel.send(file=resp)

    async def save_stats(self):
        """Saves triggers every 10 minutes to preserve stats"""
        await self.bot.wait_until_ready()
        try:
            await asyncio.sleep(60)
            while True:
                await self.save_triggers()
                await asyncio.sleep(60 * 10)
        except asyncio.CancelledError:
            pass

    async def load_triggers(self):
        triggers = await self.config.triggers()
        for trigger in triggers:
            trigger["bot"] = self.bot
            self.triggers.append(TriggerObj(**trigger))

    async def save_triggers(self):
        triggers = [t.export() for t in self.triggers]
        await self.config.triggers.set(triggers)


class TriggerObj:
    def __init__(self, **kwargs):
        self.bot = kwargs.get("bot")
        self.name = kwargs.get("name")
        self.owner = kwargs.get("owner")
        self.triggered_by = kwargs.get("triggered_by")
        self.responses = kwargs.get("responses", [])
        self.server = kwargs.get("server") # if it's None, the trigger will be implicitly global
        self.channels = kwargs.get("channels", {})
        self.type = kwargs.get("type", "all") # Type of payload. Types: all, random
        self.case_sensitive = kwargs.get("case_sensitive", False)
        self.regex = kwargs.get("regex", False)
        self.cooldown = kwargs.get("cooldown", 1) # Seconds
        self.triggered = kwargs.get("triggered", 0) # Counter
        self.last_triggered = datetime.datetime(1970, 2, 6) # Initialized
        self.active = kwargs.get("active", True)

    def export(self):
        data = self.__dict__.copy()
        del data["bot"]
        del data["last_triggered"]
        return data

    def check(self, msg):
        if not self.active:
            return False

        channels = self.channels.get(msg.guild.id, [])
        if channels:
            if msg.channel.id not in channels:
                return False

        content = msg.content
        triggered_by = self.triggered_by

        if (self.server == msg.guild.id or self.server is None) is False:
            return False

        if not self.case_sensitive:
            triggered_by = triggered_by.lower()
            content = content.lower()

        if not self.regex:
            if triggered_by not in content:
                return False
        else:
            found = re.search(triggered_by, content)
            if not found:
                return False

        timestamp = datetime.datetime.now()
        passed = (timestamp - self.last_triggered).seconds
        if passed > self.cooldown:
            self.last_triggered = timestamp
            return True
        else:
            return False

    def payload(self):
        if self.responses:
            self.triggered += 1
        if self.type == "all":
            return self.responses
        elif self.type == "random":
            if self.responses:
                return [choice(self.responses)]
            else:
                return []
        else:
            raise RuntimeError("Invalid trigger type.")

    def can_edit(self, user):
        server = user.guild
        # Using the is_owner_check would be better but I don't always have
        # context here, nor I feel like mocking it
        is_owner = user.id in self.bot.owner_ids
        is_admin = user.guild.permissions_for(user).administrator
        is_trigger_owner = user.id == self.owner
        trigger_is_global = self.server is None
        if trigger_is_global:
            return is_trigger_owner or is_owner
        else:
            return is_trigger_owner or is_owner or is_admin
