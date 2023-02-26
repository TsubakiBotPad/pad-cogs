import csv
import math
import os
import re
import urllib
from io import BytesIO
from shutil import rmtree

import aiohttp
import discord
from PIL import Image, ImageChops, ImageDraw, ImageFont
from ply import lex
from redbot.core import checks, commands
from redbot.core.utils.chat_formatting import box, inline
from tsutils.cog_settings import CogSettings
from tsutils.tsubaki.links import CLOUDFRONT_URL
from tsutils.user_interaction import send_cancellation_message, send_confirmation_message

HELP_MSG = """
^buildimg <build_shorthand>

Generates an image representing a team based on a string.

Format:
    card name(assist)[latent,latent]*repeat|Stats
    Card name must be first, otherwise the order does not matter
    Separate each card with /
    Separate each team with ;
    To use / in card name, put quote around the entire team slot (e.g. "g/l medjed(g/x zela)"/...)
    sdr is a special card name for dummy assists/skill delay buffers
Latent Acronyms:
    Separate each latent with a ,
    Killers: bak(balanced), phk(physical), hek(healer), drk(dragon), gok(god), aak(attacker, dek(devil), mak(machine)
             evk(evo mat), rek(redeemable), awk(awoken mat), enk(enhance)
    Stats (+ for 2 slot): hp, atk, rcv, all(all stat), hp+, atk+, rcv+
    Resists (+ for 2 slot): rres, bres, gres, lres, dres, rres+, bres+, gres+, lres+, dres+
    AA4: ls(leader swap), jsf(jammer skyfall), psf(poison skyfall), attr(attribute absorb res), vdp(void damage penatration)
    Awakening restricted: unm(unmatchable clear), spn(spinner clear), abs(void damage absorb)
    Others: sdr, ah(autoheal)
Repeat:
    *# defines number of times to repeat this particular card
    e.g. whaledor(plutus)*3/whaledor(carat)*2 creates a team of 3 whaledor(plutus) followed by 2 whaledor(carat)
    Latents can also be repeated, e.g. whaledor[sdr*5] for 5 sdr latents
Stats Format:
    | LV### SLV## AW# SA# +H## +A## +R## +(0 or 297)
    | indicates end of card name and start of stats
    LV: level, 1 to 120
    SLV: skill level, 1 to 99 or MAX
    AW: awakenings, 0 to 9
    SA: super awakening, 0 to 9
    +H: HP plus, 0 to 99
    +A: ATK plus, 0 to 99
    +R: RCV plus, 0 to 99
    +: total plus (+0 or +297 only)
    Case insensitive, order does not matter
"""
EXAMPLE_MSG = "Examples:\n1P{}\n2P{}\n3P{}\nLatent Validation{}\nStats Validation{}".format(
    box("bj(weld)lv120/baldin[gok *3](gilgamesh)/youyu(assist reeche)/mel(chocolate)/isis(koenma)/bj(rathian)"),
    box("amen/dios(sdr) * 3/whaledor; mnoah(assist jack frost) *3/tengu/tengu[sdr,sdr,sdr,sdr,sdr,sdr](durandalf)"),
    box("zela(assist amen) *3/base raizer * 2/zela; zela(assist amen) *4/base valeria/zela; zela * 6"),
    box("eir[drk,drk,sdr]/eir[bak,bak,sdr]/eir[sdr *4, dek]/eir[sdr *8, dek]"),
    box("dmeta(uruka|lv120+297slvmax)|+h33+a66+r99lv120slv15/    hmyne(buruka|lv120+297slv1)|+h99+a99+r99lv120slv15")
)

"""
Examples:
1P:
    bj(weld)lv120/baldin[gok, gok, gok](gilgamesh)/youyu(assist reeche)/mel(chocolate)/isis(koenma)/bj(rathian)
2P:
    amen/dios(sdr) * 3/whaledor; mnoah(assist jack frost) *3/tengu/tengu[sdr,sdr,sdr,sdr,sdr,sdr](durandalf)
3P:
    zela(assist amen) *3/base raizer * 2/zela; zela(assist amen) *4/base valeria/zela; zela * 6
Latent Validation:
    eir[drk,drk,sdr]/eir[bak,bak,sdr]
Stats Validation:
    dmeta(uruka|lv120+297slvmax)|+h33+a66+r99lv120slv15/    hmyne(buruka|lv120+297slv1)|+h99+a99+r99lv120slv15

"""

MAX_LATENTS = 8
LATENTS_MAP = {
    # NOT APPLICABLE
    1: 'emp',
    2: 'nemp',

    # ONE SLOT
    101: 'hp',
    102: 'atk',
    103: 'rcv',
    104: 'rres',
    105: 'bres',
    106: 'gres',
    107: 'lres',
    108: 'dres',
    109: 'ah',
    110: 'sdr',
    111: 'te',

    # TWO SLOTS
    201: 'bak',
    202: 'phk',
    203: 'hek',
    204: 'drk',
    205: 'gok',
    206: 'aak',
    207: 'dek',
    208: 'mak',
    209: 'evk',
    210: 'rek',
    211: 'awk',
    212: 'enk',
    213: 'all',
    214: 'hp+',
    215: 'atk+',
    216: 'rcv+',
    217: 'rres+',
    218: 'bres+',
    219: 'gres+',
    220: 'lres+',
    221: 'dres+',
    222: 'te+',

    # SIX SLOTS
    601: 'psf',
    602: 'jsf',
    603: 'ls',
    604: 'vdp',
    605: 'attr',
    606: 'unm',
    607: 'spn',
    608: 'abs',
}
AWO_RES_LATENT_TO_AWO_MAP = {
    606: 27,
    607: 20,
    608: 62,
}
LATENTS_MAP.update({-k: 'n' + LATENTS_MAP[k] for k in AWO_RES_LATENT_TO_AWO_MAP})
REVERSE_LATENTS_MAP = {v: k for k, v in LATENTS_MAP.items()}
TYPE_TO_KILLERS_MAP = {
    'God': [207],  # devil
    'Devil': [205],  # god
    'Machine': [205, 201],  # god balanced
    'Dragon': [208, 203],  # machine healer
    'Physical': [208, 203],  # machine healer
    'Attacker': [207, 202],  # devil physical
    'Healer': [204, 206],  # dragon attacker
    'Balanced': [201, 202, 203, 204, 205, 206, 207, 208]
}

AWK_CIRCLE = 'circle'
AWK_STAR = 'star'
DELAY_BUFFER = 'delay_buffer'
REMOTE_ASSET_URL = 'https://raw.githubusercontent.com/TsubakiBotPad/padbot-cogs/master/padbuildimg/assets/'
REMOTE_AWK_URL = CLOUDFRONT_URL + '/media/awakenings/{0:03d}.png'


# REMOTE_LAT_URL = 'https://pad.protic.site/wp-content/uploads/pad-latents/'

class DictWithAttributeAccess(dict):
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value


class PadBuildImgSettings(CogSettings):
    def make_default_build_img_params(self):
        build_img_params = DictWithAttributeAccess({
            'ASSETS_DIR': './assets/',
            'PORTRAIT_DIR': CLOUDFRONT_URL + '/media/icons/{monster_id:05d}.png',
            # 'OUTPUT_DIR': './data/padbuildimg/output/',
            'PORTRAIT_WIDTH': 100,
            'PADDING': 10,
            'LATENTS_WIDTH': 25,
            'FONT_NAME': './assets/OpenSans-ExtraBold.ttf'
        })
        if not os.path.exists(build_img_params.ASSETS_DIR):
            os.mkdir(build_img_params.ASSETS_DIR)
        # if not os.path.exists(build_img_params.OUTPUT_DIR):
        #     os.mkdir(build_img_params.OUTPUT_DIR)
        return build_img_params

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        return

    def buildImgParams(self):
        if 'build_img_params' not in self.bot_settings:
            self.bot_settings['build_img_params'] = self.make_default_build_img_params()
            self.save_settings()
        return DictWithAttributeAccess(self.bot_settings['build_img_params'])

    def setBuildImgParamsByKey(self, key, value):
        if 'build_img_params' not in self.bot_settings:
            self.bot_settings['build_img_params'] = self.make_default_build_img_params()
        if key in self.bot_settings['build_img_params']:
            self.bot_settings['build_img_params'][key] = value
        self.save_settings()

    async def downloadAssets(self, source, target):
        async with aiohttp.ClientSession() as session:
            async with session.get(source) as resp:
                data = await resp.read()
                with open(target, "wb") as f:
                    f.write(data)

    async def downloadAllAssets(self, awk_ids):
        params = self.buildImgParams()
        if os.path.exists(params.ASSETS_DIR):
            rmtree(params.ASSETS_DIR)
        os.mkdir(params.ASSETS_DIR)
        os.mkdir(params.ASSETS_DIR + 'lat/')
        os.mkdir(params.ASSETS_DIR + 'awk/')
        for lat in LATENTS_MAP.values():
            await self.downloadAssets(REMOTE_ASSET_URL + 'lat/' + lat + '.png',
                                      params.ASSETS_DIR + 'lat/' + lat + '.png')
        for awk in awk_ids:
            await self.downloadAssets(REMOTE_AWK_URL.format(awk), params.ASSETS_DIR + 'awk/' + str(awk) + '.png')
        await self.downloadAssets(REMOTE_ASSET_URL + AWK_CIRCLE + '.png', params.ASSETS_DIR + AWK_CIRCLE + '.png')
        await self.downloadAssets(REMOTE_ASSET_URL + AWK_STAR + '.png', params.ASSETS_DIR + AWK_STAR + '.png')
        await self.downloadAssets(REMOTE_ASSET_URL + DELAY_BUFFER + '.png', params.ASSETS_DIR + DELAY_BUFFER + '.png')
        font_name = os.path.basename(params.FONT_NAME)
        await self.downloadAssets(REMOTE_ASSET_URL + font_name, params.ASSETS_DIR + font_name)

    def dmOnly(self, server_id):
        if 'dm_only' not in self.bot_settings:
            self.bot_settings['dm_only'] = []
            self.save_settings()
        return server_id in self.bot_settings['dm_only']

    def toggleDmOnly(self, server_id):
        if 'dm_only' not in self.bot_settings:
            self.bot_settings['dm_only'] = []
        else:
            if server_id in self.bot_settings['dm_only']:
                self.bot_settings['dm_only'].remove(server_id)
            else:
                self.bot_settings['dm_only'].append(server_id)
        self.save_settings()


def lstripalpha(s):
    while s and not s[0].isdigit():
        s = s[1:]
    return s


class PaDTeamLexer:
    tokens = [
        'ID',
        'ASSIST',
        'LATENT',
        'STATS',
        'SPACES',
        'LV',
        'SLV',
        'AWAKE',
        'SUPER',
        'P_HP',
        'P_ATK',
        'P_RCV',
        'P_ALL',
        'REPEAT',
    ]

    def t_ID(self, t):
        r'^.+?(?=[\(\|\[\*])|^(?!.*[\(\|\[\*].*).+'
        # first word before ( or [ or | or * entire word if those characters are not in string
        t.value = t.value.strip()
        return t

    def t_ASSIST(self, t):
        r'\(.*?\)'
        # words in ()
        t.value = t.value.strip('()')
        return t

    def t_LATENT(self, t):
        r'\[.+?\]'
        # words in []
        t.value = [lat.strip().lower() for lat in t.value.strip('[]').split(',')]
        for v in t.value.copy():
            if '*' not in v:
                continue
            tmp = [lat.strip() for lat in v.split('*')]
            if len(tmp[0]) == 1 and tmp[0].isdigit():
                count = int(tmp[0])
                latent = tmp[1]
            elif len(tmp[1]) == 1 and tmp[1].isdigit():
                count = int(tmp[1])
                latent = tmp[0]
            else:
                continue
            idx = t.value.index(v)
            t.value.remove(v)
            for i in range(count):
                t.value.insert(idx, latent)
        t.value = t.value[0:MAX_LATENTS]
        t.value = [REVERSE_LATENTS_MAP[lat] for lat in t.value if lat in REVERSE_LATENTS_MAP]
        return t

    def t_STATS(self, t):
        r'\|'
        pass

    def t_SPACES(self, t):
        r'\s'
        # spaces must be checked after ID
        pass

    def t_LV(self, t):
        r'[lL][vV][lL]?\s?\d{1,3}'
        # LV followed by 1~3 digit number
        t.value = int(lstripalpha(t.value[2:]))
        return t

    def t_SLV(self, t):
        r'[sS][lL][vV]\s?(\d{1,2}|[mM][aA][xX])'
        # SL followed by 1~2 digit number or max
        t.value = t.value[3:]
        if t.value.isdigit():
            t.value = int(t.value)
        else:
            t.value = 99
        return t

    def t_AWAKE(self, t):
        r'[aA][wW]\s?\d'
        # AW followed by 1 digit number
        t.value = int(t.value[2:])
        return t

    def t_SUPER(self, t):
        r'[sS][aA]\s?\d'
        # SA followed by 1 digit number
        t.value = int(t.value[2:])
        return t

    def t_P_ALL(self, t):
        r'\+\s?\d{1,3}'
        # + followed by 0 or 297
        t.value = min(int(t.value[1:]), 297)
        return t

    def t_P_HP(self, t):
        r'\+[hH]\s?\d{1,2}'
        # +H followed by 1~2 digit number
        t.value = int(t.value[2:])
        return t

    def t_P_ATK(self, t):
        r'\+[aA]\s?\d{1,2}'
        # +A followed by 1~2 digit number
        t.value = int(t.value[2:])
        return t

    def t_P_RCV(self, t):
        r'\+[rR]\s?\d{1,2}'
        # +R followed by 1~2 digit number
        t.value = int(t.value[2:])
        return t

    def t_REPEAT(self, t):
        r'\*\s?\d'
        # * followed by a number
        t.value = min(int(t.value[1:]), MAX_LATENTS)
        return t

    t_ignore = '\t\n'

    def t_error(self, t):
        raise commands.UserFeedbackCheckFailure(
            "Parse Error: Unknown text '{}' at position {}".format(t.value, t.lexpos))

    def __init__(self):
        self.lexer = None

    def build(self, **kwargs):
        # pass debug=1 to enable verbose output
        self.lexer = lex.lex(module=self)
        return self.lexer


def validate_latents(card_dict, card, ass_card):
    latents = card_dict['LATENT']
    card_types = [t.name for t in card.types]
    awos = {a.awoken_skill_id for a in card.awakenings[:-card.superawakening_count]}
    if card_dict['SUPER'] and card.superawakening_count:
        awos.add(card.awakenings[-card.superawakening_count + card_dict['SUPER'] - 1].awoken_skill_id)
    if ass_card and ass_card.is_equip:
        awos |= {a.awoken_skill_id for a in ass_card.awakenings}
    if latents is None:
        return None
    for idx, l in enumerate(latents):
        if 200 < l < 209:
            if not any([l in TYPE_TO_KILLERS_MAP[t] for t in card_types if t is not None]):
                latents[idx] = None
        if l in AWO_RES_LATENT_TO_AWO_MAP and AWO_RES_LATENT_TO_AWO_MAP[l] not in awos:
            latents[idx] = -latents[idx]
    latents = [lat for lat in latents if lat is not None]
    return latents if len(latents) > 0 else None


def outline_text(draw, x, y, font, text_color, text, thickness=1):
    shadow_color = 'black'
    draw.text((x - thickness, y - thickness), text, font=font, fill=shadow_color)
    draw.text((x + thickness, y - thickness), text, font=font, fill=shadow_color)
    draw.text((x - thickness, y + thickness), text, font=font, fill=shadow_color)
    draw.text((x + thickness, y + thickness), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=text_color)


def trim(im):
    bg = Image.new(im.mode, im.size, (255, 255, 255, 0))
    diff = ImageChops.difference(im, bg)
    diff = ImageChops.add(diff, diff, 2.0, -100)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)


def text_center_pad(font_size, line_height):
    return math.floor((line_height - font_size) / 3)


def idx_to_xy(idx):
    return idx // 2, - (idx % 2)


class PadBuildImageGenerator(object):
    def __init__(self, params, ctx, build_name='pad_build'):
        self.params = params
        self.ctx = ctx
        self.dbcog = ctx.bot.get_cog("DBCog")
        self.lexer = PaDTeamLexer().build()
        self.build = {
            'NAME': build_name,
            'TEAM': [],
            'INSTRUCTION': None
        }
        self.build_img = None

    async def process_build(self, input_str):
        team_strings = [row for row in csv.reader(re.split('[;\n]', input_str), delimiter='/') if len(row) > 0]
        if len(team_strings) > 3:
            team_strings = team_strings[0:3]
        for team in team_strings:
            team_sublist = []
            for slot in team:
                try:
                    team_sublist.extend(await self.process_card(slot))
                except Exception as ex:
                    self.build['TEAM'] = []
                    raise ex
            self.build['TEAM'].append(team_sublist)

    async def process_card(self, card_str, is_assist=False):
        if not is_assist:
            result_card = {
                '+ATK': 99,
                '+HP': 99,
                '+RCV': 99,
                'AWAKE': 9,
                'SUPER': 0,
                'MAX_AWAKE': 9,
                'GOLD_STAR': True,
                'ID': 0,
                'LATENT': None,
                'LV': 99,
                'SLV': 0,
                'ON_COLOR': True,
                'EXTRA_SLOTS': False
            }
        else:
            result_card = {
                '+ATK': 0,
                '+HP': 0,
                '+RCV': 0,
                'AWAKE': 0,
                'SUPER': 0,
                'MAX_AWAKE': 0,
                'GOLD_STAR': True,
                'ID': 0,
                'LATENT': None,
                'LV': 1,
                'SLV': 0,
                'MAX_SLV': 0,
                'ON_COLOR': False,
                'EXTRA_SLOTS': False
            }
        if len(card_str) == 0:
            if is_assist:
                result_card['ID'] = DELAY_BUFFER
                return result_card, None
            else:
                return []
        self.lexer.input(card_str)
        assist_str = None
        ass_card = None
        card = None
        repeat = 1
        for tok in iter(self.lexer.token, None):
            if tok.type == 'ASSIST':
                assist_str = tok.value
                ass_card = await self.dbcog.find_monster(tok.value, self.ctx.author.id)
                if ass_card is None:
                    raise commands.UserFeedbackCheckFailure(f'Lookup Error: Could not find a monster to match:'
                                                            f' {tok.value}.')
            elif tok.type == 'REPEAT':
                repeat = min(tok.value, MAX_LATENTS)
            elif tok.type == 'ID':
                if tok.value.lower() == 'sdr':
                    result_card['ID'] = DELAY_BUFFER
                    card = DELAY_BUFFER
                else:
                    card = await self.dbcog.find_monster(tok.value, self.ctx.author.id)
                    if card is None:
                        raise commands.UserFeedbackCheckFailure(f'Lookup Error: Could not find a monster to match:'
                                                                f' {tok.value}.')
                    if not card.is_inheritable:
                        if is_assist:
                            return None, None
                        else:
                            result_card['GOLD_STAR'] = False
                    result_card[
                        'MNO'] = card.monster_no_na if card.monster_no_na != card.monster_id else card.monster_no_jp
                    result_card['ID'] = card.monster_id
            elif tok.type == 'P_ALL':
                if tok.value >= 297:
                    result_card['+HP'] = 99
                    result_card['+ATK'] = 99
                    result_card['+RCV'] = 99
                else:
                    result_card['+HP'] = 0
                    result_card['+ATK'] = 0
                    result_card['+RCV'] = 0
            elif tok.type != 'STATS':
                result_card[tok.type.replace('P_', '+')] = tok.value
        card_att = None
        if card is None:
            return []
        elif card != DELAY_BUFFER:
            result_card['LATENT'] = validate_latents(
                result_card,
                card,
                ass_card
            )
            result_card['LV'] = min(
                result_card['LV'],
                120 if card.limit_mult is not None and card.limit_mult > 1 else card.level
            )
            if card.active_skill:
                result_card['MAX_SLV'] = card.active_skill.cooldown_turns_max - card.active_skill.cooldown_turns_min + 1
            else:
                result_card['MAX_SLV'] = 0
            result_card['MAX_AWAKE'] = len(card.awakenings) - card.superawakening_count
            if is_assist:
                result_card['MAX_AWAKE'] = result_card['MAX_AWAKE'] if result_card['AWAKE'] > 0 else 0
                result_card['AWAKE'] = result_card['MAX_AWAKE']
                result_card['SUPER'] = 0
            else:
                result_card['SUPER'] = min(result_card['SUPER'], card.superawakening_count)
                if result_card['SUPER'] > 0:
                    super_awakes = [x.awoken_skill_id for x in card.awakenings[-card.superawakening_count:]]
                    result_card['SUPER'] = super_awakes[result_card['SUPER'] - 1]
                    result_card['LV'] = max(100, result_card['LV'])
            card_att = card.attr1
        if is_assist:
            return result_card, card_att
        else:
            parsed_cards = [result_card]
            if isinstance(assist_str, str):
                assist_card, assist_att = await self.process_card(assist_str, is_assist=True)
                if card_att is not None and assist_att is not None:
                    assist_card['ON_COLOR'] = card_att == assist_att
                parsed_cards.append(assist_card)
            else:
                parsed_cards.append(None)
            parsed_cards = parsed_cards * repeat
            return parsed_cards

    def combine_latents(self, card):
        latents = card['LATENT']
        if not latents:
            return False
        if len(latents) > MAX_LATENTS:
            latents = latents[0:MAX_LATENTS]
        latents_bar = Image.new('RGBA',
                                (self.params.PORTRAIT_WIDTH, self.params.LATENTS_WIDTH * 2),
                                (255, 255, 255, 0))
        x_offset = 0
        y_offset = 0
        row_count = 0
        one_slot, two_slot, six_slot = [], [], []
        for lat in latents:
            if 100 <= lat < 200:
                one_slot.append(lat)
            elif 200 <= lat < 300:
                two_slot.append(lat)
            elif 600 <= lat < 700:
                six_slot.append(lat)
                six_slot.append(1)
            elif -700 < lat <= -600:
                six_slot.append(lat)
                six_slot.append(2)
        sorted_latents = []
        if len(one_slot) > len(two_slot):
            sorted_latents.extend(six_slot)
            sorted_latents.extend(one_slot)
            sorted_latents.extend(two_slot)
        else:
            sorted_latents.extend(six_slot)
            sorted_latents.extend(two_slot)
            sorted_latents.extend(one_slot)
        last_height = 0
        for lat in sorted_latents:
            latent_icon = Image.open(self.params.ASSETS_DIR + 'lat/' + LATENTS_MAP[lat] + '.png')
            if x_offset + latent_icon.size[0] > self.params.PORTRAIT_WIDTH:
                row_count += 1
                x_offset = 0
                y_offset += last_height
            if row_count >= MAX_LATENTS // 4 and x_offset + latent_icon.size[0] >= self.params.LATENTS_WIDTH * (
                    MAX_LATENTS % 4):
                break
            latents_bar.paste(latent_icon, (x_offset, y_offset))
            last_height = latent_icon.size[1]
            x_offset += latent_icon.size[0]

        return latents_bar

    def combine_portrait(self, card, show_stats=True, show_supers=False):
        if card['ID'] == DELAY_BUFFER:
            return Image.open(self.params.ASSETS_DIR + DELAY_BUFFER + '.png')
        if 'http' in self.params.PORTRAIT_DIR:
            portrait = Image.open(urllib.request.urlopen(self.params.PORTRAIT_DIR.format(monster_id=card['ID'])))
        else:
            portrait = Image.open(self.params.PORTRAIT_DIR.format(monster_id=card['ID']))
        draw = ImageDraw.Draw(portrait)
        slv_offset = 80
        if show_stats:
            # + eggsinclude_instructions
            sum_plus = card['+HP'] + card['+ATK'] + card['+RCV']
            if 0 < sum_plus:
                if sum_plus < 297:
                    font = ImageFont.truetype(self.params.FONT_NAME, 14)
                    outline_text(draw, 5, 2, font, 'yellow', '+{:d} HP'.format(card['+HP']))
                    outline_text(draw, 5, 14, font, 'yellow', '+{:d} ATK'.format(card['+ATK']))
                    outline_text(draw, 5, 26, font, 'yellow', '+{:d} RCV'.format(card['+RCV']))
                else:
                    font = ImageFont.truetype(self.params.FONT_NAME, 18)
                    outline_text(draw, 5, 0, font, 'yellow', '+297')
            # level
            if card['LV'] > 0:
                outline_text(draw, 5, 75, ImageFont.truetype(self.params.FONT_NAME, 18),
                             'white', 'Lv.{:d}'.format(card['LV']))
                slv_offset = 65
        # skill level
        if card['MAX_SLV'] > 0 and card['SLV'] > 0:
            slv_txt = 'SLv.max' if card['SLV'] >= card['MAX_SLV'] else 'SLv.{:d}'.format(card['SLV'])
            outline_text(draw, 5, slv_offset,
                         ImageFont.truetype(self.params.FONT_NAME, 12), 'pink', slv_txt)
        # ID
        outline_text(draw, 67, 82, ImageFont.truetype(self.params.FONT_NAME, 12), 'lightblue', str(card['MNO']))
        del draw
        if card['MAX_AWAKE'] > 0:
            # awakening
            if card['AWAKE'] >= card['MAX_AWAKE']:
                awake = Image.open(self.params.ASSETS_DIR + AWK_STAR + '.png')
            else:
                awake = Image.open(self.params.ASSETS_DIR + AWK_CIRCLE + '.png')
                draw = ImageDraw.Draw(awake)
                draw.text((8, -2), str(card['AWAKE']),
                          font=ImageFont.truetype(self.params.FONT_NAME, 18), fill='yellow')
                del draw
            portrait.paste(awake, (self.params.PORTRAIT_WIDTH - awake.size[0] - 5, 5), awake)
            awake.close()
        if show_supers and card['SUPER'] > 0:
            # SA
            awake = Image.open(self.params.ASSETS_DIR + 'awk/' + str(card['SUPER']) + '.png')
            portrait.paste(awake,
                           (self.params.PORTRAIT_WIDTH - awake.size[0] - 5,
                            (self.params.PORTRAIT_WIDTH - awake.size[0]) // 2),
                           awake)
            awake.close()
        return portrait

    def generate_build_image(self, include_instructions=False):
        if self.build is None:
            return
        team_size = max([len(x) for x in self.build['TEAM']])
        p_w = self.params.PORTRAIT_WIDTH * math.ceil(team_size / 2) + \
              self.params.PADDING * math.ceil(team_size / 10)
        p_h = (self.params.PORTRAIT_WIDTH + self.params.LATENTS_WIDTH + self.params.PADDING) * \
              2 * len(self.build['TEAM'])
        include_instructions &= self.build['INSTRUCTION'] is not None
        if include_instructions:
            p_h += len(self.build['INSTRUCTION']) * (self.params.PORTRAIT_WIDTH // 2 + self.params.PADDING)
        self.build_img = Image.new('RGBA',
                                   (p_w, p_h),
                                   (255, 255, 255, 0))
        y_offset = 0
        for team in self.build['TEAM']:
            has_assist = any([card is not None for idx, card in enumerate(team) if idx % 2 == 1])
            has_latents = any([card['LATENT'] is not None for idx, card in enumerate(team)
                               if idx % 2 == 0 and card is not None])
            if has_assist:
                y_offset += self.params.PORTRAIT_WIDTH
            for idx, card in enumerate(team):
                if idx > 11 or idx > 9 and len(self.build['TEAM']) % 2 == 0:
                    break
                if card is not None:
                    x, y = idx_to_xy(idx)
                    portrait = self.combine_portrait(
                        card,
                        show_stats=card['ON_COLOR'],
                        show_supers=len(self.build['TEAM']) != 2)
                    if portrait is None:
                        continue
                    x_offset = self.params.PADDING * math.ceil(x / 4)
                    self.build_img.paste(
                        portrait,
                        (x_offset + x * self.params.PORTRAIT_WIDTH,
                         y_offset + y * self.params.PORTRAIT_WIDTH))
                    if has_latents and idx % 2 == 0 and card['LATENT'] is not None:
                        latents = self.combine_latents(card)
                        self.build_img.paste(
                            latents,
                            (x_offset + x * self.params.PORTRAIT_WIDTH,
                             y_offset + (y + 1) * self.params.PORTRAIT_WIDTH))
                        latents.close()
                    portrait.close()
            y_offset += self.params.PORTRAIT_WIDTH + self.params.PADDING * 2
            if has_latents:
                y_offset += self.params.LATENTS_WIDTH * 2

        if include_instructions:
            y_offset -= self.params.PADDING * 2
            draw = ImageDraw.Draw(self.build_img)
            font = ImageFont.truetype(self.params.FONT_NAME, 24)
            text_padding = text_center_pad(25, self.params.PORTRAIT_WIDTH // 2)
            for step in self.build['INSTRUCTION']:
                x_offset = self.params.PADDING
                outline_text(draw, x_offset, y_offset + text_padding,
                             font, 'white', 'F{:d} - P{:d} '.format(step['FLOOR'], step['PLAYER'] + 1))
                x_offset += self.params.PORTRAIT_WIDTH
                if step['ACTIVE'] is not None:
                    actives_used = [self.build['TEAM'][idx][ids]
                                    for idx, side in enumerate(step['ACTIVE'])
                                    for ids in side]
                    for card in actives_used:
                        if 'http' in self.params.PORTRAIT_DIR:
                            p_small = Image.open(
                                urllib.request.urlopen(self.params.PORTRAIT_DIR.format(monster_id=card['ID']))).resize(
                                (self.params.PORTRAIT_WIDTH // 2, self.params.PORTRAIT_WIDTH // 2), Image.LINEAR)
                        else:
                            p_small = Image.open(self.params.PORTRAIT_DIR.format(monster_id=card['ID'])).resize(
                                (self.params.PORTRAIT_WIDTH // 2, self.params.PORTRAIT_WIDTH // 2), Image.LINEAR)
                        self.build_img.paste(p_small, (x_offset, y_offset))
                        x_offset += self.params.PORTRAIT_WIDTH // 2
                    x_offset += self.params.PADDING
                outline_text(draw, x_offset, y_offset + text_padding, font, 'white', step['ACTION'])
                y_offset += self.params.PORTRAIT_WIDTH // 2
            del draw

        self.build_img = trim(self.build_img)


class PadBuildImage(commands.Cog):
    """PAD Build Image Generator."""

    def __init__(self, bot):
        self.bot = bot
        self.settings = PadBuildImgSettings("padbuildimg")

    async def get_dbcog(self):
        dbcog = self.bot.get_cog("DBCog")
        if dbcog is None:
            raise ValueError("DBCog cog is not loaded")
        await dbcog.wait_until_ready()
        return dbcog

    @commands.command()
    async def helpbuildimg(self, ctx):
        """Help info for the buildimage command."""
        await ctx.author.send(box(HELP_MSG))
        if checks.admin_or_permissions(manage_guild=True):
            await ctx.author.send(box('For Server Admins: Output location can be changed between current channel and '
                                      'direct messages via ^togglebuildimgoutput'))
        await ctx.author.send(EXAMPLE_MSG)

    @commands.command(aliases=['buildimg', 'pdchu'])
    async def padbuildimg(self, ctx, *, build_str: str):
        """Create a build image based on input.
        Use ^helpbuildimg for more info.
        """

        async with ctx.typing():
            params = self.settings.buildImgParams()
            try:
                pbg = PadBuildImageGenerator(params, ctx)
                await pbg.process_build(build_str)
                pbg.generate_build_image()
            except commands.UserFeedbackCheckFailure as ex:
                await ctx.send(box(str(ex) + '\nSee ^helpbuildimg for syntax'))
                return -1

        if pbg.build_img is not None:
            with BytesIO() as build_io:
                pbg.build_img.save(build_io, format='PNG')
                build_io.seek(0)
                if ctx.guild and self.settings.dmOnly(ctx.guild.id):
                    try:
                        await ctx.author.send(file=discord.File(build_io, 'pad_build.png'))
                        await ctx.send('Sent build to {}'.format(ctx.author))
                    except discord.errors.Forbidden as ex:
                        await send_cancellation_message(ctx, 'Failed to send build to {}'.format(ctx.author))
                else:
                    try:
                        await ctx.send(file=discord.File(build_io, 'pad_build.png'))
                    except discord.errors.Forbidden as ex:
                        await send_cancellation_message(ctx, "Failed to send build. (Insufficient Permissions)")
        else:
            await ctx.send(box('Invalid build, see ^helpbuildimg'))
        return 0

    @commands.command()
    @checks.is_owner()
    async def configbuildimg(self, ctx, param_key: str, param_value: str):
        """
        Configure PadBuildImageGenerator parameters:
            ASSETS_DIR - directory for storing assets (use ^refreshassets to update)
            PORTRAIT_DIR - path pattern to where portraits are stored, {monster_id} must be present
            PORTRAIT_WIDTH - width of portraits, default 100
            PADDING - padding between various things, default 10
            LATENTS_WIDTH - width of 1 slot latent, default 25
            FONT_NAME - path to font
        """
        if param_key in ['ASSETS_DIR', 'PORTRAIT_DIR', 'PORTRAIT_WIDTH', 'PADDING', 'LATENTS_WIDTH', 'FONT_NAME']:
            if param_key in ['PORTRAIT_WIDTH', 'PADDING', 'LATENTS_WIDTH']:
                param_value = int(param_value)
            if param_key in ['ASSETS_DIR'] and param_value[-1] not in ['/', '\\']:
                param_value += '/'
            self.settings.setBuildImgParamsByKey(param_key, param_value)
            await ctx.send(box('Set {} to {}'.format(param_key, param_value)))
        else:
            await ctx.send(box('Invalid parameter {}'.format(param_key)))

    @commands.command()
    @checks.is_owner()
    async def refreshassets(self, ctx):
        """
        Refresh assets folder
        """
        async with ctx.typing():
            await send_confirmation_message(ctx, 'Downloading assets to {}'.format(self.settings.buildImgParams().ASSETS_DIR))
            dbcog = await self.get_dbcog()
            awk_ids = dbcog.database.awoken_skill_map.keys()
            await self.settings.downloadAllAssets(awk_ids)
            await ctx.tick()

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def togglebuildimgoutput(self, ctx):
        """
        Toggles between sending result to server vs sending result to direct message
        """
        self.settings.toggleDmOnly(ctx.guild.id)
        if self.settings.dmOnly(ctx.guild.id):
            await ctx.send('Response mode set to direct message')
        else:
            await ctx.send('Response mode set to current channel')
