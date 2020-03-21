from .scheduler import *

async def replacement_delete_messages(self, messages):
    message_ids = list(
        {m.id for m in messages if m.__class__.__name__ != "SchedulerMessage"}
    )

    if not message_ids:
        return

    if len(message_ids) == 1:
        await self._state.http.delete_message(self.id, message_ids[0])
        return

    if len(message_ids) > 100:
        raise discord.ClientException(
            "Can only bulk delete messages up to 100 messages"
        )

    await self._state.http.delete_messages(self.id, message_ids)


def setup(bot):
    discord.TextChannel.delete_messages = replacement_delete_messages
    cog = Scheduler(bot)
    bot.add_cog(cog)
    cog.init()
