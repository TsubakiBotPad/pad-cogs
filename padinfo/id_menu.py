import discord
import prettytable

import tsutils
import urllib.parse

from redbot.core.utils.chat_formatting import box, inline

from .leader_skills import createMultiplierText
from .leader_skills import createSingleMultiplierText

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dadguide.database_context import DbContext
    from dadguide.models.monster_model import MonsterModel

INFO_PDX_TEMPLATE = 'http://www.puzzledragonx.com/en/monster.asp?n={}'

MEDIA_PATH = 'https://d1kpnpud0qoyxf.cloudfront.net/media/'
RPAD_PIC_TEMPLATE = MEDIA_PATH + 'portraits/{0:05d}.png?cachebuster=2'
RPAD_PORTRAIT_TEMPLATE = MEDIA_PATH + 'icons/{0:05d}.png'
VIDEO_TEMPLATE = MEDIA_PATH + 'animated_portraits/{0:05d}.mp4'
GIF_TEMPLATE = MEDIA_PATH + 'animated_portraits/{0:05d}.gif'
ORB_SKIN_TEMPLATE = MEDIA_PATH + 'orb_skins/jp/{0:03d}.png'
ORB_SKIN_CB_TEMPLATE = MEDIA_PATH + 'orb_skins/jp/{0:03d}cb.png'

YT_SEARCH_TEMPLATE = 'https://www.youtube.com/results?search_query={}'
SKYOZORA_TEMPLATE = 'http://pad.skyozora.com/pets/{}'
ILMINA_TEMPLATE = 'https://ilmina.com/#/CARD/{}'


def get_pdx_url(m: "MonsterModel"):
    return INFO_PDX_TEMPLATE.format(tsutils.get_pdx_id(m))


def get_portrait_url(m: "MonsterModel"):
    return RPAD_PORTRAIT_TEMPLATE.format(m.monster_id)


def get_pic_url(m: "MonsterModel"):
    return RPAD_PIC_TEMPLATE.format(m.monster_id)


class IdMenu(object):
    def __init__(self, db_context: "DbContext" = None, allowed_emojis: list = None):
        self.db_context = db_context
        self.allowed_emojis = allowed_emojis

    def match_emoji(self, name):
        for e in self.allowed_emojis:
            if e.name == name:
                return e
        return name

    @staticmethod
    def monsterToHeader(m: "MonsterModel", link=False):
        # type_emojis = '{} '.format(''.join(
        #     [str(self.match_emoji('mons_type_{}'.format(t.name.lower()))) for t in m.types])) if show_types else ''
        type_emojis = ''
        msg = '[{}] {}{}'.format(m.monster_no_na, type_emojis, m.name_en)
        return '[{}]({})'.format(msg, get_pdx_url(m)) if link else msg

    @staticmethod
    def monsterToJaSuffix(m: "MonsterModel", subname_on_override=True):
        suffix = ""
        if m.roma_subname and (subname_on_override or m.name_en_override is None):
            suffix += ' [{}]'.format(m.roma_subname)
        if not m.on_na:
            suffix += ' (JP only)'
        return suffix

    def monsterToLongHeader(self, m: "MonsterModel", link=False):
        msg = self.monsterToHeader(m) + self.monsterToJaSuffix(m)
        return '[{}]({})'.format(msg, get_pdx_url(m)) if link else msg

    def monsterToEvoHeader(self, m: "MonsterModel", link=True):
        prefix = f" {self.monster_attr_emoji(m)} "
        msg = f"{m.monster_no_na} - {m.name_en}"
        suffix = self.monsterToJaSuffix(m, False)
        return prefix + ("[{}]({})".format(msg, get_pdx_url(m)) if link else msg) + suffix

    @staticmethod
    def monsterToThumbnailUrl(m: "MonsterModel"):
        return get_portrait_url(m)

    def monsterToBaseEmbed(self, m: "MonsterModel"):
        header = self.monsterToLongHeader(m)
        embed = discord.Embed()
        embed.set_thumbnail(url=self.monsterToThumbnailUrl(m))
        embed.title = header
        embed.url = get_pdx_url(m)
        embed.set_footer(text='Requester may click the reactions below to switch tabs')
        return embed

    def addEvoListFields(self, monsters, current_monster):
        if not len(monsters):
            return
        field_data = ''
        field_values = []
        for ae in sorted(monsters, key=lambda x: int(x.monster_id)):
            monster_header = self.monsterToEvoHeader(
                ae, link=ae.monster_id != current_monster.monster_id) + '\n'
            if len(field_data + monster_header) > 1024:
                field_values.append(field_data)
                field_data = ""
            field_data += monster_header
        field_values.append(field_data)
        return field_values

    def monster_attr_emoji(self, monster: "MonsterModel"):
        attr1 = monster.attr1.name.lower()
        attr2 = monster.attr2.name.lower()
        emoji = "{}_{}".format(attr1, attr2) if attr1 != attr2 else 'orb_{}'.format(attr1)
        return self.match_emoji(emoji)

    def monsterToEvoEmbed(self, m: "MonsterModel"):
        embed = self.monsterToBaseEmbed(m)
        alt_versions = self.db_context.graph.get_alt_monsters_by_id(m.monster_no)
        gem_versions = list(filter(None, map(self.db_context.graph.evo_gem_monster, alt_versions)))

        if not len(alt_versions):
            embed.description = 'No alternate evos or evo gem'
            return embed

        evos = self.addEvoListFields(alt_versions, m)
        if not gem_versions:
            embed.add_field(name="{} alternate evo(s)".format(len(alt_versions)), value=evos[0], inline=False)
            for f in evos[1:]:
                embed.add_field(name="\u200b", value=f)
            return embed
        gems = self.addEvoListFields(gem_versions, m)

        embed.add_field(name="{} alternate evo(s)".format(len(alt_versions)), value=evos[0], inline=False)
        for e in evos[1:]:
            embed.add_field(name="\u200b", value=e, inline=False)

        embed.add_field(name="{} evolve gem(s)".format(len(gem_versions)), value=gems[0], inline=False)
        for e in gems[1:]:
            embed.add_field(name="\u200b", value=e, inline=False)

        return embed

    def addMonsterEvoOfList(self, monster_id_list, embed, field_name):
        if not len(monster_id_list):
            return
        field_data = ''
        if len(monster_id_list) > 5:
            field_data = '{} monsters'.format(len(monster_id_list))
        else:
            item_count = min(len(monster_id_list), 5)
            monster_list = [self.db_context.graph.get_monster(m) for m in monster_id_list]
            for ae in sorted(monster_list, key=lambda x: x.monster_no_na, reverse=True)[:item_count]:
                field_data += "{}\n".format(self.monsterToLongHeader(ae, link=True))
        embed.add_field(name=field_name, value=field_data)

    def monsterToEvoMatsEmbed(self, m: "MonsterModel"):
        embed = self.monsterToBaseEmbed(m)

        mats_for_evo = self.db_context.graph.evo_mats_by_monster(m)

        field_name = 'Evo materials'
        field_data = ''
        if len(mats_for_evo) > 0:
            for ae in mats_for_evo:
                field_data += "{}\n".format(self.monsterToLongHeader(ae, link=True))
        else:
            field_data = 'None'
        embed.add_field(name=field_name, value=field_data)

        self.addMonsterEvoOfList(self.db_context.graph.material_of_ids(m), embed, 'Material for')
        evo_gem = self.db_context.graph.evo_gem_monster(m)
        if not evo_gem:
            return embed
        self.addMonsterEvoOfList(self.db_context.graph.material_of_ids(evo_gem), embed, "Evo gem is mat for")
        return embed

    def monsterToPantheonEmbed(self, m: "MonsterModel"):
        full_pantheon = self.db_context.get_monsters_by_series(m.series_id)
        pantheon_list = list(filter(lambda x: self.db_context.graph.monster_is_base(x), full_pantheon))
        if len(pantheon_list) == 0 or len(pantheon_list) > 6:
            return None

        embed = self.monsterToBaseEmbed(m)

        field_name = 'Pantheon: ' + self.db_context.graph.get_monster(m.monster_no).series.name
        field_data = ''
        for monster in sorted(pantheon_list, key=lambda x: x.monster_no_na):
            field_data += '\n' + self.monsterToHeader(monster, link=True)
        embed.add_field(name=field_name, value=field_data)

        return embed

    def monsterToSkillupsEmbed(self, m: "MonsterModel"):
        if m.active_skill is None:
            return None
        possible_skillups_list = self.db_context.get_monsters_by_active(m.active_skill.active_skill_id)
        skillups_list = list(filter(
            lambda x: self.db_context.graph.monster_is_farmable_evo(x), possible_skillups_list))

        if len(skillups_list) == 0:
            return None

        embed = self.monsterToBaseEmbed(m)

        field_name = 'Skillups'
        field_data = ''

        # Prevent huge skillup lists
        if len(skillups_list) > 8:
            field_data = '({} skillups omitted)'.format(len(skillups_list) - 8)
            skillups_list = skillups_list[0:8]

        for monster in sorted(skillups_list, key=lambda x: x.monster_no_na):
            field_data += '\n' + self.monsterToHeader(monster, link=True)

        if len(field_data.strip()):
            embed.add_field(name=field_name, value=field_data)

        return embed

    @staticmethod
    def monsterToPicUrl(m: "MonsterModel"):
        return get_pic_url(m)

    def monsterToPicEmbed(self, m: "MonsterModel", animated=False):
        embed = self.monsterToBaseEmbed(m)
        url = self.monsterToPicUrl(m)
        embed.set_image(url=url)
        # Clear the thumbnail, don't need it on pic
        embed.set_thumbnail(url='')
        extra_links = []
        if animated:
            extra_links.append('Animation: {} -- {}'.format(self.monsterToVideoUrl(m), self.monsterToGifUrl(m)))
        if m.orb_skin_id is not None:
            extra_links.append('Orb Skin: {} -- {}'.format(self.monsterToOrbSkinUrl(m), self.monsterToOrbSkinCBUrl(m)))
        if len(extra_links) > 0:
            embed.add_field(name='Extra Links', value='\n'.join(extra_links))

        return embed

    @staticmethod
    def monsterToVideoUrl(m: "MonsterModel", link_text='(MP4)'):
        return '[{}]({})'.format(link_text, VIDEO_TEMPLATE.format(m.monster_no_jp))

    @staticmethod
    def monsterToGifUrl(m: "MonsterModel", link_text='(GIF)'):
        return '[{}]({})'.format(link_text, GIF_TEMPLATE.format(m.monster_no_jp))

    @staticmethod
    def monsterToOrbSkinUrl(m: "MonsterModel", link_text='Regular'):
        return '[{}]({})'.format(link_text, ORB_SKIN_TEMPLATE.format(m.orb_skin_id))

    @staticmethod
    def monsterToOrbSkinCBUrl(m: "MonsterModel", link_text='Color Blind'):
        return '[{}]({})'.format(link_text, ORB_SKIN_CB_TEMPLATE.format(m.orb_skin_id))

    def monstersToLsEmbed(self, left_m: "MonsterModel", right_m: "MonsterModel"):
        lls = left_m.leader_skill
        rls = right_m.leader_skill

        multiplier_text = createMultiplierText(lls, rls)

        embed = discord.Embed()
        embed.title = '{}\n\n'.format(multiplier_text)
        description = ''
        description += '\n**{}**\n{}'.format(
            self.monsterToHeader(left_m, link=True),
            lls.desc if lls else 'None')
        description += '\n**{}**\n{}'.format(
            self.monsterToHeader(right_m, link=True),
            rls.desc if rls else 'None')
        embed.description = description

        return embed

    def monsterToHeaderEmbed(self, m: "MonsterModel"):
        header = self.monsterToLongHeader(m, link=True)
        embed = discord.Embed()
        embed.description = header
        return embed

    def monsterToAcquireString(self, m: "MonsterModel"):
        acquire_text = None
        if self.db_context.graph.monster_is_farmable(m) and not self.db_context.graph.monster_is_mp_evo(m):
            # Some MP shop monsters 'drop' in PADR
            acquire_text = 'Farmable'
        elif self.db_context.graph.monster_is_farmable_evo(m) and not self.db_context.graph.monster_is_mp_evo(m):
            acquire_text = 'Farmable Evo'
        elif m.in_pem:
            acquire_text = 'In PEM'
        elif self.db_context.graph.monster_is_pem_evo(m):
            acquire_text = 'PEM Evo'
        elif m.in_rem:
            acquire_text = 'In REM'
        elif self.db_context.graph.monster_is_rem_evo(m):
            acquire_text = 'REM Evo'
        elif m.in_mpshop:
            acquire_text = 'MP Shop'
        elif self.db_context.graph.monster_is_mp_evo(m):
            acquire_text = 'MP Shop Evo'
        return acquire_text

    def monsterToEmbed(self, m: "MonsterModel"):
        embed = self.monsterToBaseEmbed(m)

        # in case we want to readd the type emojis later
        # types_row = ' '.join(['{} {}'.format(str(match_emoji(allowed_emojis, 'mons_type_{}'.format(t.name.lower()))), t.name) for t in m.types])
        types_row = '/'.join(['{}'.format(t.name) for t in m.types])

        awakenings_row = ''
        for idx, a in enumerate(m.awakenings):
            as_id = a.awoken_skill_id
            as_name = a.name
            mapped_awakening = AWAKENING_MAP.get(as_id, as_name)
            mapped_awakening = self.match_emoji(mapped_awakening)

            # Wrap superawakenings to the next line
            if len(m.awakenings) - idx == m.superawakening_count:
                awakenings_row += '\n{}'.format(self.match_emoji('sa_questionmark'))
                awakenings_row += ' {}'.format(mapped_awakening)
            else:
                awakenings_row += ' {}'.format(mapped_awakening)

        is_transform_base = self.db_context.graph.monster_is_transform_base(m)
        transform_base = self.db_context.graph.get_transform_base_by_id(m.monster_id) if not is_transform_base else None

        awakenings_row = awakenings_row.strip()

        if not len(awakenings_row):
            awakenings_row = 'No Awakenings'

        if is_transform_base:

            killers_row = '**Available killers:** [{} slots] {}'.format(m.latent_slots,
                                                                        self.get_killers_text(m))
        else:
            killers_row = '**Avail. killers (pre-transform):** [{} slots] {}'.format(
                transform_base.latent_slots,
                self.get_killers_text(transform_base))

        embed.add_field(name=types_row, value='{}\n{}'.format(awakenings_row, killers_row), inline=False)

        info_row_1 = 'Inheritable' if m.is_inheritable else 'Not inheritable'
        acquire_text = self.monsterToAcquireString(m)
        tet_text = self.db_context.graph.true_evo_type_by_monster(m).value

        orb_skin = "" if m.orb_skin_id is None else " (Orb Skin)"

        info_row_2 = '**Rarity** {} (**Base** {}){}\n**Cost** {}'.format(
            m.rarity,
            self.db_context.graph.get_base_monster_by_id(m.monster_no).rarity,
            orb_skin,
            m.cost
        )

        if acquire_text:
            info_row_2 += '\n**{}**'.format(acquire_text)
        if tet_text in ("Reincarnated", "Assist", "Pixel", "Super Reincarnated"):
            info_row_2 += '\n**{}**'.format(tet_text)

        embed.add_field(name=info_row_1, value=info_row_2)

        hp, atk, rcv, weighted = m.stats()
        if m.limit_mult > 0:
            lb_hp, lb_atk, lb_rcv, lb_weighted = m.stats(lv=110)
            stats_row_1 = 'Stats (LB, +{}%)'.format(m.limit_mult)
            stats_row_2 = '**HP** {} ({})\n**ATK** {} ({})\n**RCV** {} ({})'.format(
                hp, lb_hp, atk, lb_atk, rcv, lb_rcv)
        else:
            stats_row_1 = 'Stats'
            stats_row_2 = '**HP** {}\n**ATK** {}\n**RCV** {}'.format(hp, atk, rcv)
        if any(x if x.name == 'Enhance' else None for x in m.types):
            stats_row_2 += '\n**Fodder EXP** {:,}'.format(m.fodder_exp)
        embed.add_field(name=stats_row_1, value=stats_row_2)

        active_header = 'Active Skill'
        active_body = 'None'
        active_skill = m.active_skill
        if active_skill:
            active_header = 'Active Skill ({} -> {})'.format(active_skill.turn_max,
                                                             active_skill.turn_min)
            active_body = active_skill.desc
        embed.add_field(name=active_header, value=active_body, inline=False)

        leader_skill = m.leader_skill
        ls_row = m.leader_skill.desc if leader_skill else 'None'
        ls_header = 'Leader Skill'
        if leader_skill:
            multiplier_text = createMultiplierText(leader_skill)
            ls_header += " {}".format(multiplier_text)
        embed.add_field(name=ls_header, value=ls_row, inline=False)

        evos_header = "Alternate Evos"
        evos_body = ", ".join(f"**{m2.monster_id}**"
                              if m2.monster_id == m.monster_id
                              else f"[{m2.monster_id}]({get_pdx_url(m2)})"
                              for m2 in
                              sorted({*self.db_context.graph.get_alt_monsters_by_id(m.monster_no)},
                                     key=lambda x: x.monster_id))
        embed.add_field(name=evos_header, value=evos_body, inline=False)

        return embed

    def get_killers_text(self, m: "MonsterModel"):
        if 'Any' in m.killers:
            return 'Any'
        return ' '.join([str(self.match_emoji('latent_killer_{}'.format(k.lower()))) for k in m.killers])

    def monsterToOtherInfoEmbed(self, m: "MonsterModel"):
        embed = self.monsterToBaseEmbed(m)
        # Clear the thumbnail, takes up too much space
        embed.set_thumbnail(url='')

        body_text = '\n'
        stat_cols = ['', 'HP', 'ATK', 'RCV']
        for plus in (0, 297):
            body_text += '**Stats at +{}:**'.format(plus)
            tbl = prettytable.PrettyTable(stat_cols)
            tbl.hrules = prettytable.NONE
            tbl.vrules = prettytable.NONE
            tbl.align = "l"
            levels = (m.level, 110) if m.limit_mult > 0 else (m.level,)
            for lv in levels:
                for inh in (False, True):
                    hp, atk, rcv, _ = m.stats(lv, plus=plus, inherit=inh)
                    row_name = 'Lv{}'.format(lv)
                    if inh:
                        row_name = '(Inh)'
                    tbl.add_row([row_name.format(plus), hp, atk, rcv])
            body_text += box(tbl.get_string())

        body_text += "\n**JP Name**: {}".format(m.name_ja)
        body_text += "\n[YouTube]({}) | [Skyozora]({}) | [PDX]({}) | [Ilimina]({})".format(
            YT_SEARCH_TEMPLATE.format(urllib.parse.quote(m.name_ja)),
            SKYOZORA_TEMPLATE.format(m.monster_no_jp),
            INFO_PDX_TEMPLATE.format(m.monster_no_jp),
            ILMINA_TEMPLATE.format(m.monster_no_jp))

        if m.history_us:
            body_text += '\n**History:** {}'.format(m.history_us)

        body_text += '\n**Series:** {}'.format(self.db_context.graph.get_monster(m.monster_no).series.name)
        body_text += '\n**Sell MP:** {:,}'.format(m.sell_mp)
        if m.buy_mp is not None:
            body_text += "  **Buy MP:** {:,}".format(m.buy_mp)

        if m.exp < 1000000:
            xp_text = '{:,}'.format(m.exp)
        else:
            xp_text = '{:.1f}'.format(m.exp / 1000000).rstrip('0').rstrip('.') + 'M'
        body_text += '\n**XP to Max:** {}'.format(xp_text)
        body_text += '  **Max Level:**: {}'.format(m.level)

        # weighted stat calculation & display
        hp, atk, rcv, weighted = m.stats()
        body_text += '\n**Weighted stats:** {}'.format(weighted)
        if m.limit_mult > 0:
            lb_hp, lb_atk, lb_rcv, lb_weighted = m.stats(lv=110)
            body_text += ' | LB {} (+{}%)'.format(lb_weighted, m.limit_mult)

        body_text += '\n**Fodder EXP:** {:,}'.format(m.fodder_exp)
        body_text += '\n**Rarity:** {} **Cost:** {}'.format(m.rarity, m.cost)

        embed.description = body_text

        return embed

    def monstersToLssEmbed(self, m: "MonsterModel"):
        multiplier_text = createSingleMultiplierText(m.leader_skill)

        embed = discord.Embed()
        embed.title = '{}\n\n'.format(multiplier_text)
        description = ''
        description += '\n**{}**\n{}'.format(
            self.monsterToHeader(m, link=True),
            m.leader_skill.desc if m.leader_skill else 'None')
        embed.description = description

        return embed


AWAKENING_MAP = {
    1: 'boost_hp',
    2: 'boost_atk',
    3: 'boost_rcv',
    4: 'reduce_fire',
    5: 'reduce_water',
    6: 'reduce_wood',
    7: 'reduce_light',
    8: 'reduce_dark',
    9: 'misc_autoheal',
    10: 'res_bind',
    11: 'res_blind',
    12: 'res_jammer',
    13: 'res_poison',
    14: 'oe_fire',
    15: 'oe_water',
    16: 'oe_wood',
    17: 'oe_light',
    18: 'oe_dark',
    19: 'misc_te',
    20: 'misc_bindclear',
    21: 'misc_sb',
    22: 'row_fire',
    23: 'row_water',
    24: 'row_wood',
    25: 'row_light',
    26: 'row_dark',
    27: 'misc_tpa',
    28: 'res_skillbind',
    29: 'oe_heart',
    30: 'misc_multiboost',
    31: 'killer_dragon',
    32: 'killer_god',
    33: 'killer_devil',
    34: 'killer_machine',
    35: 'killer_balance',
    36: 'killer_attacker',
    37: 'killer_physical',
    38: 'killer_healer',
    39: 'killer_evomat',
    40: 'killer_awoken',
    41: 'killer_enhancemat',
    42: 'killer_vendor',
    43: 'misc_comboboost',
    44: 'misc_guardbreak',
    45: 'misc_extraattack',
    46: 'teamboost_hp',
    47: 'teamboost_rcv',
    48: 'misc_voidshield',
    49: 'misc_assist',
    50: 'misc_super_extraattack',
    51: 'misc_skillcharge',
    52: 'res_bind_super',
    53: 'misc_te_super',
    54: 'res_cloud',
    55: 'res_seal',
    56: 'misc_sb_super',
    57: 'attack_boost_high',
    58: 'attack_boost_low',
    59: 'l_shield',
    60: 'l_attack',
    61: 'misc_super_comboboost',
    62: 'orb_combo',
    63: 'misc_voice',
    64: 'misc_dungeonbonus',
    65: 'reduce_hp',
    66: 'reduce_atk',
    67: 'reduce_rcv',
    68: 'res_blind_super',
    69: 'res_jammer_super',
    70: 'res_poison_super',
    71: 'misc_jammerboost',
    72: 'misc_poisonboost',
}
