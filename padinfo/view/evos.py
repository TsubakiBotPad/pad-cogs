from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedThumbnail, EmbedFooter, EmbedMain, EmbedField
from discordmenu.embed.menu import EmbedView
from discordmenu.embed.text import Text, LinkedText
from discordmenu.emoji_cache import emoji_cache

from padinfo.common.emoji_map import get_emoji, format_emoji
from padinfo.common.padx import monster_url
from padinfo.view.components.base import pad_info_footer
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class EvosView:
    @staticmethod
    def _get_monster_attr_emoji(monster: "MonsterModel"):
        attr1 = monster.attr1.name.lower()
        attr2 = monster.attr2.name.lower()
        emoji = "{}_{}".format(attr1, attr2) if attr1 != attr2 else 'orb_{}'.format(attr1)
        return get_emoji(emoji)

    @staticmethod
    def _evo_line(m: "MonsterModel", link=True):
        msg = f"{m.monster_no_na} - {m.name_en}"
        return Box(
            Text(format_emoji(EvosView._get_monster_attr_emoji(m))),
            LinkedText(msg, monster_url(m)) if link else Text(msg),
            Text(MonsterHeader.ja_suffix(m, False)),
            delimiter=' '
        )

    @staticmethod
    def _evo_lines(monsters, current_monster):
        if not len(monsters):
            return []
        return [
            EvosView._evo_line(ae, link=ae.monster_id != current_monster.monster_id)
            for ae in sorted(monsters, key=lambda x: int(x.monster_id))
        ]

    @staticmethod
    def embed(m: "MonsterModel", alt_versions, gem_versions, color):
        fields = [
            EmbedField(
                ("{} evolution" if len(alt_versions) == 1 else "{} evolutions").format(len(alt_versions)),
                Box(*EvosView._evo_lines(alt_versions, m)))]

        if gem_versions:
            fields.append(
                EmbedField(
                    ("{} evolve gem" if len(gem_versions) == 1 else "{} evolve gems").format(len(gem_versions)),
                    Box(*EvosView._evo_lines(gem_versions, m))))

        return EmbedView(
            EmbedMain(
                color=color,
                title=MonsterHeader.long_v2(m).to_markdown(),
                url=monster_url(m)),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(m)),
            embed_footer=pad_info_footer(),
            embed_fields=fields)
