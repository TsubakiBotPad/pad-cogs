from typing import TYPE_CHECKING

from tsutils import EmojiUpdater

from padinfo.core.padinfo_settings import settings

if TYPE_CHECKING:
    from dadguide.database_context import DbContext
    from dadguide.models.monster_model import MonsterModel


class IdEmojiUpdater(EmojiUpdater):
    def __init__(self, ctx, emoji_to_embed, m: "MonsterModel" = None, pad_info=None, selected_emoji=None, bot=None,
                 db_context: "DbContext" = None, **kwargs):
        super().__init__(emoji_to_embed, **kwargs)
        self.ctx = ctx
        self.emoji_dict = emoji_to_embed
        self.m = m
        self.pad_info = pad_info
        self.selected_emoji = selected_emoji
        self.bot = bot
        self.db_context = db_context

        settings.log_emoji("start_" + selected_emoji)

    async def on_update(self, ctx, selected_emoji):
        evo_id = settings.checkEvoID(ctx.author.id)
        settings.log_emoji(selected_emoji)
        if evo_id:
            evos = sorted({*self.db_context.graph.get_alt_ids_by_id(self.m.monster_id)})
            index = evos.index(self.m.monster_id)
            if selected_emoji == self.pad_info.previous_monster_emoji:
                new_id = evos[index - 1]
            elif selected_emoji == self.pad_info.next_monster_emoji:
                if index == len(evos) - 1:
                    new_id = evos[0]
                else:
                    new_id = evos[index + 1]
            else:
                self.selected_emoji = selected_emoji
                return True
            if new_id == self.m.monster_id:
                return False
            self.m = self.db_context.graph.get_monster(new_id)
        else:
            if selected_emoji == self.pad_info.previous_monster_emoji:
                prev_monster = self.db_context.graph.numeric_prev_monster(self.m)
                if prev_monster is None:
                    return False
                self.m = prev_monster
            elif selected_emoji == self.pad_info.next_monster_emoji:
                next_monster = self.db_context.graph.numeric_next_monster(self.m)
                if next_monster is None:
                    return False
                self.m = next_monster
            else:
                self.selected_emoji = selected_emoji
                return True

        self.emoji_dict = await self.pad_info.get_id_emoji_options(self.ctx,
                                                                   m=self.m, scroll=sorted(
                {*self.db_context.graph.get_alt_ids_by_id(self.m.monster_id)}) if evo_id else [], menu_type=1)
        return True


class ScrollEmojiUpdater(EmojiUpdater):
    def __init__(self, ctx, emoji_to_embed, m: "MonsterModel" = None, ms: "list[int]" = None, selected_emoji=None,
                 pad_info=None, bot=None, **kwargs):
        super().__init__(emoji_to_embed, **kwargs)
        self.ctx = ctx
        self.emoji_dict = emoji_to_embed
        self.m = m
        self.ms = ms
        self.pad_info = pad_info
        self.selected_emoji = selected_emoji
        self.bot = bot

    async def on_update(self, ctx, selected_emoji):
        index = self.ms.index(self.m)

        if selected_emoji == self.pad_info.first_monster_emoji:
            self.m = self.ms[0]
        elif selected_emoji == self.pad_info.previous_monster_emoji:
            self.m = self.ms[index - 1]
        elif selected_emoji == self.pad_info.next_monster_emoji:
            if index == len(self.ms) - 1:
                self.m = self.ms[0]
            else:
                self.m = self.ms[index + 1]
        elif selected_emoji == self.pad_info.last_monster_emoji:
            self.m = self.ms[-1]
        else:
            self.selected_emoji = selected_emoji
            return True

        self.emoji_dict = await self.pad_info.get_id_emoji_options(self.ctx, m=self.m, scroll=self.ms)
        return True
