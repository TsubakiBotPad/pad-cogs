import math

import discord
from discord.ext import commands
from ply import lex, yacc

from __main__ import user_allowed, send_cmd_help


class PadLexer(object):

    tokens = [
        'ROWS',
        'TPAS',
        'ATK',
        'OE',
#         'ID',
        'MULT',

#         'RESIST',
#         'DEFENCE',

        'ROW',
        'TPA',
        'ORB',
        'COMBO',
    ]

    def t_ROWS(self, t):
        r'rows\(\d+\)'
        t.value = t.value.strip('rows(').strip(')')
        t.value = int(t.value)
        return t

    def t_OE(self, t):
        r'oe\(\d+\)'
        t.value = t.value.strip('oe(').strip(')')
        t.value = int(t.value)
        return t

    def t_TPAS(self, t):
        r'tpas\(\d+\)'
        t.value = t.value.strip('tpas(').strip(')')
        t.value = int(t.value)
        return t

    def t_ATK(self, t):
        r'atk\(\d+\)'
        t.value = t.value.strip('atk(').strip(')')
        t.value = int(t.value)
        return t

    def t_ID(self, t):
        r'id\(\w+\)'
        t.value = t.value.strip('id(').strip(')')
        return t

    def t_MULT(self, t):
        r'multi?\([0-9.]+\)'
        t.value = t.value.strip('mult').strip('i').strip('(').strip(')')
        t.value = float(t.value)
        return t

    def t_ROW(self, t):
        r'row(\(\d*\))?'
        t.value = t.value.strip('row').strip('(').strip(')')
        t.value = int(t.value) if t.value else 6
        if t.value < 6 or t.value > 30:
            raise Exception('row must have 6-30 orbs, got ' + t.value)

        return t

    def t_TPA(self, t):
        r'tpa(\(\))?'
        t.value = 4
        return t

    def t_ORB(self, t):
        r'orbs?(\([0-9]*\))?'
        t.value = t.value.strip('orb').strip('s').strip('(').strip(')')
        t.value = int(t.value) if t.value else 3
        if t.value < 3 or t.value > 30:
            raise Exception('match must have 3-30 orbs, got ' + t.value)
        return t

    def t_COMBO(self, t):
        r'combos?\(\d+\)'
        t.value = t.value.strip('combo').strip('s').strip('(').strip(')')
        t.value = int(t.value)
        return t

    t_ignore = ' \t\n'

    def t_error(self, t):
        raise TypeError("Unknown text '%s'" % (t.value,))

    def build(self, **kwargs):
        # pass debug=1 to enable verbose output
        self.lexer = lex.lex(module=self)
        return self.lexer

class DamageConfig(object):

    def __init__(self, lexer):
        self.rows = None
        self.oe = None
        self.tpas = None
        self.atk = None
        self.id = None
        self.mult = None

        self.row_matches = list()
        self.tpa_matches = list()
        self.orb_matches = list()
        self.combos = None

        for tok in iter(lexer.token, None):
            type = tok.type
            value = tok.value
            self.rows = self.setIfType('ROWS', type, self.rows, value)
            self.oe = self.setIfType('OE', type, self.oe, value)
            self.tpas = self.setIfType('TPAS', type, self.tpas, value)
            self.atk = self.setIfType('ATK', type, self.atk, value)
            self.id = self.setIfType('ID', type, self.id, value)
            self.mult = self.setIfType('MULT', type, self.mult, value)

            if type == 'ROW':
                self.row_matches.append(value)
            if type == 'TPA':
                self.tpa_matches.append(value)
            if type == 'ORB':
                if value == 4:
                    self.tpa_matches.append(value)
                elif value == 30:
                    self.row_matches.append(value)
                else:
                    self.orb_matches.append(value)

            self.combos = self.setIfType('COMBOS', type, self.combos, value)

        if self.rows is None:
            self.rows = 0
        if self.oe is None:
            self.oe = 0
        if self.tpas is None:
            self.tpas = 0
        if self.atk is None:
            self.atk = 1
        if self.mult is None:
            self.mult = 1
        if self.combos is None:
            self.combos = 0

        if (len(self.row_matches) + len(self.tpa_matches) + len(self.orb_matches)) == 0:
            raise Exception('You need to specify at least one attack match (orb, tpa, row)')

    def setIfType(self, expected_type, given_type, current_value, new_value):
        if expected_type != given_type:
            return current_value
        if current_value is not None:
            raise Exception('You set {} more than once'.format(given_type))
        return new_value

    def updateWithMonster(self, monster):
        # set tpas
        # set attack
        # set mult
        pass

    def calculateMatchDamage(self, match, all_enhanced):
        orb_damage = (1 + (match - 3) * .25)
        oe_damage = (1 + .06 * match) * (1 + .05 * self.oe) if all_enhanced else 1
        tpa_damage = math.pow(1.5, self.tpas) if match == 4 else 1
        return self.atk * orb_damage * oe_damage * tpa_damage

    def calculate(self, all_enhanced):
        base_damage = 0
        for match in (self.row_matches + self.tpa_matches + self.orb_matches):
            base_damage += self.calculateMatchDamage(match, all_enhanced)

        combo_count = len(self.row_matches) + len(self.tpa_matches) + len(self.orb_matches) + self.combos
        combo_mult = 1 + (combo_count - 1) * .25
        row_mult = 1 + self.rows / 10 * len(self.row_matches)

        final_damage = base_damage * combo_mult * row_mult * self.mult

        return int(final_damage)


class DamageCalc:
    """Damage calculator."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def helpdamage(self, ctx):
        """Help info for the damage command

        ^damage <specification string>

        The specification string consists of:
            1) Optional card modifiers
            2) Orb matches (minimum 1)

        ---------------------------
        Card Modifiers

        * atk(n)  : Attack value for the card
        * mult(n) : The full (leader x leader) multiplier to use
        * rows(n) : Number of row enhances on team
        * oe(n)   : Number of orb enhances on team
        * tpas(n) : Number of tpas on card

        If unspecified, modifiers default to 1 or zero as appropriate.

        ---------------------------
        Orb Matches

        * row(n)   : A row of n (default 6) orbs [row, row(), row(n)]
        * orb(n)   : A non-row match of n (default 3) orbs [orb, orb(), orb(n)]
        * tpa      : An alias for orb(4) [tpa, tpa()]
        * combo(n) : Off-color combos that increase multiplier

        ---------------------------
        Examples

        ^damage atk(100) orb() tpa
        3-orb match and a 4-orb match with 100 attack, no tpas/row enhance, no multiplier

        ^damage atk(100) mult(2.5) rows(1) tpas(2) row row() row(8) tpa tpa() orb orb() orb(5) combo(2)
        100 attack, 2.5x,  1 row enhance, 2 tpas
        2x 6-orb rows
        8-orb row
        2x tpa
        2x 3-orb matches
        5-orb match
        2 off-color combos

        Resistance, defense, loading by monster id, killers, etc coming soon
        """
        await send_cmd_help(ctx)

    @commands.command(pass_context=True)
    async def damage(self, ctx, *, damage_spec):
        """Computes damage for the provided damage_spec

        The specification string consists of a series of optional modifiers, followed by
        a minimum of at least one orb match.

        Use ^helpdamage for more info
        """

        lexer = PadLexer().build()
        lexer.input(damage_spec)
        config = DamageConfig(lexer)
        damage = config.calculate(all_enhanced=False)
        enhanced_damage = config.calculate(all_enhanced=True)
        await self.bot.say("```Damage (no enhanced) :  {}\nDamage (all enhanced) : {}```".format(damage, enhanced_damage))


def setup(bot):
    n = DamageCalc(bot)
    bot.add_cog(n)
