import random
import re
from datetime import datetime

import tsutils
from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import box, pagify

from padinfo.core.find_monster import findMonster3


class IdTest:
    bot = None
    get_dgcog = None

    def __init__(self):
        self.config = Config.get_conf(self, identifier=-1)

    @commands.group()
    # @checks.is_owner()
    async def idtest(self, ctx):
        """ID Test suite subcommands"""

    @idtest.command(name="add")
    async def idt_add(self, ctx, id: int, *, query):
        """Add a test for the id3 test suite (Append `| reason` to add a reason)"""
        query, *reason = query.split("|")
        query = query.strip()
        if await self.config.user(ctx.author).lastaction() != 'id3' and \
                not await tsutils.confirm_message(ctx, "Are you sure you want to add to the id3 test suite?"):
            return
        await self.config.user(ctx.author).lastaction.set('id3')

        async with self.config.test_suite() as suite:
            oldd = suite.get(query, {})
            if oldd.get('result') == id:
                await ctx.send(f"This test case already exists with id `{sorted(suite).index(query)}`.")
                return
            suite[query] = {
                'result': id,
                'ts': datetime.now().timestamp(),
                'reason': reason[0].strip() if reason else ''
            }

            if await tsutils.get_reaction(ctx, f"Added test case `{id} - {query}`"
                                               f" with ref `{sorted(suite).index(query)}`",
                                          "\N{LEFTWARDS ARROW WITH HOOK}", timeout=5):
                if oldd:
                    suite[query] = oldd
                else:
                    del suite[query]
                await ctx.react_quietly("\N{CROSS MARK}")
            else:
                await ctx.send(f"Successfully added test case `{id} - {query}` with ref `{sorted(suite).index(query)}`")
                await ctx.tick()

    @idtest.group(name="name")
    async def idt_name(self, ctx):
        """Name subcommands"""

    @idtest.group(name="fluff")
    async def idt_fluff(self, ctx):
        """Fluff subcommands"""

    @idt_name.command(name="add")
    async def idtn_add(self, ctx, id: int, token, *, reason=""):
        """Add a name token test to the id3 test suite"""
        await self.norf_add(ctx, id, token, reason, False)

    @idt_fluff.command(name="add")
    async def idtf_add(self, ctx, id: int, token, *, reason=""):
        """Add a fluff token test to the id3 test suite"""
        await self.norf_add(ctx, id, token, reason, True)

    async def norf_add(self, ctx, id: int, token, reason, fluffy):
        reason = reason.lstrip("| ")
        if await self.config.user(ctx.author).lastaction() != 'name' and \
                not await tsutils.confirm_message(ctx,
                                                  "Are you sure you want to add to the fluff/name test suite?"):
            return
        await self.config.user(ctx.author).lastaction.set('name')

        async with self.config.fluff_suite() as suite:
            if any(t['id'] == id and t['token'] == token and t['fluff'] == fluffy for t in suite):
                await ctx.send("This test already exists.")
                return

            old = None
            if any(t['id'] == id and t['token'] == token for t in suite):
                old = [t for t in suite if t['id'] == id and t['token'] == token][0]
                if not await tsutils.confirm_message(ctx, f"Are you sure you want to change"
                                                          f" the type of test case #{suite.index(old)}"
                                                          f" `{id} - {token}` from "
                                                          f" **{'fluff' if fluffy else 'name'}** to"
                                                          f" **{'name' if fluffy else 'fluff'}**?"):
                    await ctx.react_quietly("\N{CROSS MARK}")
                    return
                suite.remove(old)

            case = {
                'id': id,
                'token': token,
                'fluff': fluffy,
                'reason': reason,
                'ts': datetime.now().timestamp()
            }

            suite.append(case)
            suite.sort(key=lambda v: (v['id'], v['token'], v['fluff']))

            if await tsutils.get_reaction(ctx, f"Added {'fluff' if fluffy else 'name'} "
                                               f"case `{id} - {token}` with ref `{suite.index(case)}`",
                                          "\N{LEFTWARDS ARROW WITH HOOK}", timeout=5):
                suite.pop()
                if old:
                    suite.append(old)
                await ctx.react_quietly("\N{CROSS MARK}")
            else:
                m = await ctx.send(f"Successfully added {'fluff' if fluffy else 'name'} "
                                   f"case `{id} - {token}` with ref `{suite.index(case)}`")
                await m.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    @idtest.command(name="import")
    async def idt_import(self, ctx, *, queries):
        """Import id3 tests"""
        if await self.config.user(ctx.author).lastaction() != 'id3' and \
                not await tsutils.confirm_message(ctx, "Are you sure you want to edit **query**?"):
            return
        await self.config.user(ctx.author).lastaction.set('id3')

        cases = re.findall(r'\s*(?:\d+. )?(.+?) + - (\d+) *(.*)', queries)
        async with self.config.test_suite() as suite:
            for query, result, reason in cases:
                suite[query] = {'result': int(result), 'reason': reason, 'ts': datetime.now().timestamp()}
        await ctx.tick()

    @idt_name.command(name="import")
    async def idtn_import(self, ctx, *, queries):
        """Import name/fluff tests"""
        await self.norf_import(ctx, queries)

    @idt_fluff.command(name="import")
    async def idtf_import(self, ctx, *, queries):
        """Import name/fluff tests"""
        await self.norf_import(ctx, queries)

    async def norf_import(self, ctx, queries):
        if await self.config.user(ctx.author).lastaction() != 'name' and \
                not await tsutils.confirm_message(ctx, "Are you sure you want to edit **name/fluff**?"):
            return
        await self.config.user(ctx.author).lastaction.set('name')

        cases = re.findall(r'\s*(?:\d+. )?(.+?) + - (\d+)\s+(\w*) *(.*)', queries)
        async with self.config.fluff_suite() as suite:
            for query, result, fluff, reason in cases:
                # print(query, result, fluff, reason)
                if not any(c['id'] == int(result) and c['token'] == query for c in suite):
                    suite.append({
                        'id': int(result),
                        'token': query,
                        'fluff': fluff == 'fluff',
                        'reason': reason,
                        'ts': datetime.now().timestamp()})
        await ctx.tick()

    @idtest.command(name="remove", aliases=["delete", "rm"])
    async def idt_remove(self, ctx, *, item):
        """Remove an id3 test"""
        if await self.config.user(ctx.author).lastaction() != 'id3' and \
                not await tsutils.confirm_message(ctx, "Are you sure you want to edit **query**?"):
            return
        await self.config.user(ctx.author).lastaction.set('id3')

        async with self.config.test_suite() as suite:
            if item in suite:
                del suite[item]
            elif item.isdigit() and int(item) < len(suite):
                del suite[sorted(suite)[int(item)]]
            else:
                await ctx.react_quietly("\N{CROSS MARK}")
                return
        await ctx.tick()

    @idt_name.command(name="remove")
    async def idtn_remove(self, ctx, *, item: int):
        """Remove a name/fluff test"""
        await self.norf_remove(ctx, item)

    @idt_fluff.command(name="remove")
    async def idtf_remove(self, ctx, *, item: int):
        """Remove a name/fluff test"""
        await self.norf_remove(ctx, item)

    async def norf_remove(self, ctx, item):
        if await self.config.user(ctx.author).lastaction() != 'name' and \
                not await tsutils.confirm_message(ctx, "Are you sure you want to edit **name/fluff**?"):
            return
        await self.config.user(ctx.author).lastaction.set('name')

        async with self.config.fluff_suite() as suite:
            if item >= len(suite):
                await ctx.send("There are not that many items.")
                return
            suite.remove(sorted(suite, key=lambda v: (v['id'], v['token'], v['fluff']))[item])
        await ctx.tick()

    @idtest.command(name="setreason", aliases=["addreason"])
    async def idt_setreason(self, ctx, number: int, *, reason):
        """Set a reason for an id3 test case"""
        if reason == '""':
            reason = ""
        if await self.config.user(ctx.author).lastaction() != 'id3' and \
                not await tsutils.confirm_message(ctx, "Are you sure you want to edit **query**?"):
            return
        await self.config.user(ctx.author).lastaction.set('id3')

        async with self.config.test_suite() as suite:
            if number >= len(suite):
                await ctx.react_quietly("\N{CROSS MARK}")
                return
            suite[sorted(suite)[number]]['reason'] = reason
        await ctx.tick()

    @idt_name.command(name="setreason")
    async def idtn_setreason(self, ctx, number: int, *, reason):
        """Set a reason for an name/fluff test case"""
        await self.norf_setreason(ctx, number, reason)

    @idt_fluff.command(name="setreason")
    async def idtf_setreason(self, ctx, number: int, *, reason):
        """Set a reason for an name/fluff test case"""
        await self.norf_setreason(ctx, number, reason)

    async def norf_setreason(self, ctx, number, reason):
        if reason == '""':
            reason = ""
        if await self.config.user(ctx.author).lastaction() != 'name' and \
                not await tsutils.confirm_message(ctx, "Are you sure you want to edit **name/fluff**?"):
            return
        await self.config.user(ctx.author).lastaction.set('name')

        async with self.config.fluff_suite() as suite:
            if number >= len(suite):
                await ctx.react_quietly("\N{CROSS MARK}")
                return
            # noinspection PyTypeChecker
            sorted(suite, key=lambda v: (v['id'], v['token'], v['fluff']))[number]['reason'] = reason
        await ctx.tick()

    @idtest.command(name="list")
    async def idt_list(self, ctx):
        """List id3 tests"""
        await self.config.user(ctx.author).lastaction.set('id3')

        suite = await self.config.test_suite()
        o = ""
        ml = len(max(suite, key=len))
        for c, kv in enumerate(sorted(suite.items())):
            o += f"{str(c).rjust(3)}. {kv[0].ljust(ml)} - {str(kv[1]['result']).ljust(4)}\t{kv[1].get('reason') or ''}\n"
        if not o:
            await ctx.send("There are no test cases.")
        for page in pagify(o):
            await ctx.send(box(page))

    @idt_name.command(name="list")
    async def idtn_list(self, ctx, inclusive: bool = False):
        """List name tests"""
        await self.norf_list(ctx, False, inclusive)

    @idt_fluff.command(name="list")
    async def idtf_list(self, ctx, inclusive: bool = False):
        """List fluff tests"""
        await self.norf_list(ctx, True, inclusive)

    async def norf_list(self, ctx, fluff, inclusive):
        await self.config.user(ctx.author).lastaction.set('name')

        suite = await self.config.fluff_suite()
        o = ""
        for c, v in enumerate(sorted(suite, key=lambda v: (v['id'], v['token'], v['fluff']))):
            if inclusive or v['fluff'] == fluff:
                o += f"{str(c).rjust(3)}. {v['token'].ljust(10)} - {str(v['id']).ljust(4)}" \
                     f"\t{'fluff' if v['fluff'] else 'name '}\t{v.get('reason', '')}\n"
        if not o:
            await ctx.send("There are no test cases.")
        for page in pagify(o):
            await ctx.send(box(page))

    @idtest.command(name="listnoreason")
    async def idt_listnoreason(self, ctx):
        """List id3 tests with no reasons"""
        await self.config.user(ctx.author).lastaction.set('id3')

        suite = await self.config.test_suite()
        o = ""
        ml = len(max(suite, key=len))
        for c, kv in enumerate(sorted(suite.items())):
            if not kv[1].get('reason'):
                o += f"{str(c).rjust(3)}. {kv[0].ljust(ml)} - {str(kv[1]['result']).ljust(4)}\t{kv[1].get('reason') or ''}\n"
        if not o:
            await ctx.send("There are no test cases.")
        for page in pagify(o):
            await ctx.send(box(page))

    @idt_name.command(name="listnoreason")
    async def idtn_listnoreason(self, ctx, inclusive: bool = False):
        """List name tests with no reasons"""
        await self.norf_listnoreason(ctx, False, inclusive)

    @idt_fluff.command(name="listnoreason")
    async def idtf_lisnoreasont(self, ctx, inclusive: bool = False):
        """List fluff tests with no reasons"""
        await self.norf_listnoreason(ctx, True, inclusive)

    async def norf_listnoreason(self, ctx, fluff, inclusive):
        await self.config.user(ctx.author).lastaction.set('name')

        suite = await self.config.fluff_suite()
        o = ""
        for c, v in enumerate(sorted(suite, key=lambda v: (v['id'], v['token'], v['fluff']))):
            if inclusive or v['fluff'] == fluff and not v['reason']:
                o += f"{str(c).rjust(3)}. {v['token'].ljust(10)} - {str(v['id']).ljust(4)}" \
                     f"\t{'fluff' if v['fluff'] else 'name '}\t{v.get('reason', '')}\n"
        if not o:
            await ctx.send("There are no test cases.")
        for page in pagify(o):
            await ctx.send(box(page))

    @idtest.command(name="listrecent")
    async def idt_listrecent(self, ctx, count: int = 0):
        """List recent id3 tests"""
        suite = await self.config.test_suite()
        if count == 0:
            count = len(suite)
        o = ""
        ml = len(max(suite, key=len))
        for c, kv in enumerate(sorted(suite.items(), key=lambda kv: kv[1].get('ts', 0), reverse=True)[:count]):
            o += f"{kv[0].ljust(ml)} - {str(kv[1]['result']).ljust(4)}\t{kv[1].get('reason') or ''}\n"
        if not o:
            await ctx.send("There are no test cases.")
        for page in pagify(o):
            await ctx.send(box(page))

    @idtest.command(name="run", aliases=["test"])
    async def idt_run(self, ctx):
        """Run all id3 tests"""
        suite = await self.config.test_suite()
        dgcog = await self.get_dgcog()
        await self.config.user(ctx.author).lastaction.set('id3')
        c = 0
        o = ""
        ml = len(max(suite, key=len)) + 2
        rcircle = '\N{LARGE RED CIRCLE}'
        async with ctx.typing():
            for q, r in suite.items():
                m = await findMonster3(dgcog, q)
                mid = m and m.monster_id
                if m is not None and m.monster_id != r['result'] or m is None and r['result'] >= 0:
                    reason = '   Reason: ' + r.get('reason') if 'reason' in r else ''
                    q = '"' + q + '"'
                    o += f"{q.ljust(ml)} - {rcircle} Ex: {r['result']}, Ac: {mid}{reason}\n"
                else:
                    c += 1
        if c != len(suite):
            o += f"\n\nTests complete.  {c}/{len(suite)} succeeded."
        else:
            o += "\n\n\N{LARGE GREEN CIRCLE} All tests succeeded" + random.choice('.....!!!!!?')
        for page in pagify(o):
            await ctx.send(box(page))

    @idt_name.command(name="run")
    async def idtn_run(self, ctx):
        """Run all name/fluff tests"""
        await self.norf_run(ctx)

    @idt_fluff.command(name="run")
    async def idtf_run(self, ctx):
        """Run all name/fluff tests"""
        await self.norf_run(ctx)

    async def norf_run(self, ctx):
        """Run all name/fluff tests"""
        suite = await self.config.fluff_suite()
        await self.config.user(ctx.author).lastaction.set('name')
        c = 0
        o = ""
        rcircle, ycircle = '\N{LARGE RED CIRCLE}', '\N{LARGE YELLOW CIRCLE}'
        async with ctx.typing():
            for v in suite:
                fluff = v['id'] in [m.monster_id for m in self.bot.get_cog("Dadguide").index2.fluff_tokens[v['token']]]
                name = v['id'] in [m.monster_id for m in self.bot.get_cog("Dadguide").index2.name_tokens[v['token']]]

                if (v['fluff'] and not fluff) or (not v['fluff'] and not name):
                    q = '"{}"'.format(v['token'])
                    o += f"{str(v['id']).ljust(4)} {q.ljust(10)} - " \
                         f"{ycircle if name or fluff else rcircle} " \
                         f"Not {'Fluff' if name else 'Name' if fluff else 'A'} Token\n"
                else:
                    c += 1
        if c != len(suite):
            o += f"\n\nTests complete.  {c}/{len(suite)} succeeded."
        else:
            o += "\n\n\N{LARGE GREEN CIRCLE} All tests succeeded."
        for page in pagify(o):
            await ctx.send(box(page))

    @idtest.command(name="runall")
    async def idt_runall(self, ctx):
        """Run all tests"""
        rcircle, ycircle = '\N{LARGE RED CIRCLE}', '\N{LARGE YELLOW CIRCLE}'
        dgcog = await self.get_dgcog()
        qsuite = await self.config.test_suite()
        qo = ""
        qc = 0
        ml = len(max(qsuite, key=len)) + 2
        async with ctx.typing():
            for c, q in enumerate(sorted(qsuite)):
                m = await findMonster3(dgcog, q)
                mid = m and m.monster_id
                if m is not None and m.monster_id != qsuite[q]['result'] or m is None and qsuite[q]['result'] >= 0:
                    reason = '   Reason: ' + qsuite[q].get('reason') if qsuite[q].get('reason') else ''
                    q = '"' + q + '"'
                    qo += f"{str(c).rjust(4)}. {q.ljust(ml)} - {rcircle} Ex: {qsuite[q]['result']}, Ac: {mid}{reason}\n"
                else:
                    qc += 1

        fsuite = await self.config.fluff_suite()
        fo = ""
        fc = 0
        async with ctx.typing():
            for c, v in enumerate(fsuite):
                fluff = v['id'] in [m.monster_id for m in self.bot.get_cog("Dadguide").index2.fluff_tokens[v['token']]]
                name = v['id'] in [m.monster_id for m in self.bot.get_cog("Dadguide").index2.name_tokens[v['token']]]

                if (v['fluff'] and not fluff) or (not v['fluff'] and not name):
                    q = '"{}"'.format(v['token'])
                    fo += f"{str(c).rjust(4)}. {str(v['id']).ljust(4)} {q.ljust(ml - 5)} - " \
                          f"{ycircle if name or fluff else rcircle} " \
                          f"Not {'Fluff' if name else 'Name' if fluff else 'A'} Token\n"
                else:
                    fc += 1

        o = ""
        if fo:
            o += "[Failed Token Tests]\n" + fo
        if qo:
            o += "\n[Failed Query Tests]\n" + qo

        if qc + fc != len(fsuite) + len(qsuite):
            o += f"\n\nTests complete.  {qc + fc}/{len(fsuite) + len(qsuite)} succeeded."
        else:
            o += "\n\n\N{LARGE GREEN CIRCLE} \N{LARGE GREEN CIRCLE} All tests succeeded" \
                 + random.choice(['.'] * 5 + ['!!'] * 5 + ['???'])
        for page in pagify(o):
            await ctx.send(box(page))
