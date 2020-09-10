import asyncio
import csv
import io
import json

import discord
import pymysql
from redbot.core import checks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import inline, box, pagify

from rpadutils import CogSettings, rpadutils

PADGUIDEDB_COG = None


def is_padguidedb_admin_check(ctx):
    is_owner = ctx.author.id in PADGUIDEDB_COG.bot.owner_ids
    return is_owner or PADGUIDEDB_COG.settings.checkAdmin(ctx.author.id)


def is_padguidedb_admin():
    return commands.check(is_padguidedb_admin_check)


class PadGuideDb(commands.Cog):
    """PadGuide Database manipulator"""

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.settings = PadGuideDbSettings("padguidedb")

        self.queue_size = 0
        self.full_etl_lock = asyncio.Lock()
        self.extract_images_lock = asyncio.Lock()
        self.dungeon_load_lock = asyncio.Lock()
        global PADGUIDEDB_COG
        PADGUIDEDB_COG = self

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO("data".encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        return

    def get_cursor(self):
        with open(self.settings.configFile(), 'r') as db_config:
            return self.connect(json.load(db_config)).cursor()

    def connect(self, db_config):
        return pymysql.connect(host=db_config['host'],
                               user=db_config['user'],
                               password=db_config['password'],
                               db=db_config['db'],
                               charset=db_config['charset'],
                               cursorclass=pymysql.cursors.DictCursor,
                               autocommit=True)

    @commands.group(aliases=['pdb'])
    @is_padguidedb_admin()
    async def padguidedb(self, context):
        """PadGuide database manipulation."""

    @padguidedb.command()
    @checks.is_owner()
    async def addadmin(self, ctx, user: discord.Member):
        """Adds a user to the padguide db admin"""
        self.settings.addAdmin(user.id)
        await ctx.send("done")

    @padguidedb.command()
    @checks.is_owner()
    async def rmadmin(self, ctx, user):
        """Removes a user from the padguide db admin"""
        try:
            u = await commands.MemberConverter().convert(ctx, user)
            self.settings.rmAdmin(u.id)
        except commands.BadArgument as e:
            try:
                u = int(user)
                self.settings.rmAdmin(u)
            except ValueError:
                await ctx.send(inline("Invalid user id."))
                return
        await ctx.send("done")

    @padguidedb.command()
    @checks.is_owner()
    async def setconfigfile(self, ctx, *, config_file):
        """Set the database config file."""
        self.settings.setConfigFile(config_file)
        await ctx.send(inline('Done'))

    @padguidedb.command()
    @is_padguidedb_admin()
    async def searchdungeon(self, ctx, *, search_text):
        """Search"""
        search_text = '%{}%'.format(search_text)
        with self.get_cursor() as cursor:
            sql = ('select dungeon_id, name_na, name_jp, visible from dungeons'
                   ' where lower(name_na) like %s or lower(name_jp) like %s'
                   ' order by dungeon_id desc limit 20')
            cursor.execute(sql, [search_text, search_text])
            results = list(cursor.fetchall())
            msg = 'Results\n' + json.dumps(results, indent=2, ensure_ascii=False)
            await ctx.send(inline(sql))
            for page in pagify(msg):
                await ctx.send(box(page))

    @padguidedb.command()
    @checks.is_owner()
    async def setdungeonscriptfile(self, ctx, *, dungeon_script_file):
        """Set the dungeon script file."""
        self.settings.setDungeonScriptFile(dungeon_script_file)
        await ctx.send(inline('Done'))

    @padguidedb.command()
    @checks.is_owner()
    async def setfulletlfile(self, ctx, *, full_etl_file):
        """Set the full ETL file."""
        self.settings.setFullETLFile(full_etl_file)
        await ctx.send(inline('Done'))

    @padguidedb.command()
    @checks.is_owner()
    async def setimageupdatefile(self, ctx, *, image_update_file):
        """Set the image update file."""
        self.settings.setImageUpdateFile(image_update_file)
        await ctx.send(inline('Done'))

    @padguidedb.command()
    @checks.is_owner()
    async def setuserinfo(self, ctx, server: str, user_uuid: str, user_intid: str):
        """Set the dungeon script."""
        self.settings.setUserInfo(server, user_uuid, user_intid)
        await ctx.send(inline('Done'))

    @padguidedb.command()
    @is_padguidedb_admin()
    async def loaddungeon(self, ctx, server: str, dungeon_id: int, dungeon_floor_id: int, queues: int = 1):
        if queues > 5:
            await ctx.send("You must send less than 5 queues.")
            return
        elif self.queue_size + queues > 60:
            await ctx.send("The size of the queue cannot exceed 60.  It is currently {}.".format(self.queue_size))
            return
        elif not self.settings.hasUserInfo(server):
            await ctx.send("There is no account associated with server '{}'.".format(server.upper()))
            return

        self.queue_size += queues
        if queues == 1:
            await ctx.send(inline('Queueing load in slot {}'.format(self.queue_size)))
        else:
            await ctx.send(
                inline('Queueing loads in slots {}-{}'.format(self.queue_size - queues + 1, self.queue_size)))

        event_loop = asyncio.get_event_loop()
        for queue in range(queues):
            event_loop.create_task(self.do_dungeon_load(ctx, server.upper(), dungeon_id, dungeon_floor_id))

    async def do_dungeon_load(self, ctx, server, dungeon_id, dungeon_floor_id):
        async with self.dungeon_load_lock:
            process = await asyncio.create_subprocess_exec(
                '/usr/bin/python3',
                self.settings.dungeonScriptFile(),
                '--db_config={}'.format(self.settings.configFile()),
                '--server={}'.format(server),
                '--dungeon_id={}'.format(dungeon_id),
                '--floor_id={}'.format(dungeon_floor_id),
                '--user_uuid={}'.format(self.settings.userUuidFor(server)),
                '--user_intid={}'.format(self.settings.userIntidFor(server)),

                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if stderr:
                print("Dungeon Load Error:\n" + stderr.decode())
                await rpadutils.doubleup(ctx, inline(
                    'Load for {} {} {} failed'.format(server, dungeon_id, dungeon_floor_id)))
            else:
                await rpadutils.doubleup(ctx, inline(
                    'Load for {} {} {} finished'.format(server, dungeon_id, dungeon_floor_id)))
            self.queue_size -= 1

    @padguidedb.command()
    @is_padguidedb_admin()
    async def olddungeondrops(self, ctx, dungeon_id: int, dungeon_floor_id: int):
        with self.get_cursor() as cursor:
            sql = ("SELECT stage, drop_monster_id, COUNT(*) AS count"
                   " FROM wave_data"
                   " WHERE dungeon_id = {} AND floor_id = {}"
                   " GROUP BY 1, 2"
                   " ORDER BY 1, 2").format(int(dungeon_id), int(dungeon_floor_id))
            cursor.execute(sql)
            results = list(cursor.fetchall())
            msg = 'stage,drop_monster_id,count'
            for row in results:
                msg += '\n{},{},{}'.format(row['stage'], row['drop_monster_id'], row['count'])
            for page in pagify(msg):
                await ctx.send(box(page))

    @padguidedb.command()
    @is_padguidedb_admin()
    async def dungeondrops(self, ctx, dungeon_id: int):
        with self.get_cursor() as cursor:
            sql = ("SELECT `floor_id`, COUNT(DISTINCT `entry_id`)"
                   " FROM `dadguide`.`wave_data`"
                   " WHERE `dungeon_id` = {}"
                   " GROUP BY `floor_id`"
                   " ORDER BY `wave_data`.`floor_id`  DESC;").format(dungeon_id)
            cursor.execute(sql)
            results1 = list(cursor.fetchall())

            sql = ("SELECT `floor_id`, `drop_monster_id`, COUNT(id)"
                   " FROM `dadguide`.`wave_data`"
                   " WHERE `dungeon_id` = {} AND `drop_monster_id` != 9900 AND `drop_monster_id` != 0"
                   " GROUP BY `floor_id`, `drop_monster_id`"
                   " ORDER BY `wave_data`.`floor_id`  DESC;").format(dungeon_id)
            cursor.execute(sql)
            results2 = list(cursor.fetchall())

            msg = 'floor_id,count\n'
            for row in results1:
                print(row)
                msg += ','.join(map(str,row.values()))+"\n"
            msg += '\n\nfloor_id,monster_id,count\n'
            for row in results2:
                print(row)
                msg += ','.join(map(str,row.values()))+"\n"

            for page in pagify(msg):
                await ctx.send(box(page))

    @padguidedb.command()
    @checks.is_owner()
    async def cleardungeon(self, ctx, dungeon_id: int):
        with self.get_cursor() as cursor:
            sql = "DELETE FROM wave_data WHERE dungeon_id = {}".format(int(dungeon_id))
            cursor.execute(sql)
        await ctx.send(inline("Done"))

    # @padguidedb.command()
    @is_padguidedb_admin()
    async def dungeondata(self, ctx, dungeon_id: int):
        with self.get_cursor() as cursor:
            sql = "SELECT * FROM wave_data WHERE dungeon_id = {}".format(int(dungeon_id))
            cursor.execute(sql)
            results = list(cursor.fetchall())
            order = sorted(results[0])
            rows = [list(map(lambda x: row[x], order)) for row in results]
            fauxfile = io.StringIO()
            writer = csv.writer(fauxfile)
            writer.writerow(order)
            writer.writerows(rows)
            fauxfile.seek(0)
            m = await ctx.send(file=discord.File(fauxfile, filename="dungeondata.csv"))
        await asyncio.sleep(10)
        await m.delete()

    @padguidedb.group()
    @is_padguidedb_admin()
    async def pipeline(self, context):
        """PadGuide pipeline utilities."""

    @pipeline.command()
    @is_padguidedb_admin()
    async def fulletl(self, ctx):
        """Runs a job which downloads pad data, and updates the padguide database."""
        if self.full_etl_lock.locked():
            await ctx.send(inline('Full ETL already running'))
            return

        async with self.full_etl_lock:
            await ctx.send(inline('Running full ETL pipeline: this could take a while'))
            process = await asyncio.create_subprocess_exec(
                'bash',
                self.settings.fullETLFile(),

                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if stderr:
                print("Full ETL Error:\n" + stderr.decode())
                await ctx.send(inline('Full ETL failed'))
                return
        await ctx.send(inline('Full ETL finished'))

    @pipeline.command()
    @is_padguidedb_admin()
    async def extractimages(self, ctx):
        """Runs a job which downloads image updates, generates full images, and portraits."""
        if self.extract_images_lock.locked():
            await ctx.send(inline('Extract images already running'))
            return

        async with self.extract_images_lock:
            await ctx.send(inline('Running image extract pipeline: this could take a while'))
            process = await asyncio.create_subprocess_exec(
                'bash',
                self.settings.imageUpdateFile(),

                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if stderr:
                print("Image Extract Error:\n" + stderr.decode())
                await ctx.send(inline('Image extract failed'))
                return
        await ctx.send(inline('Image extract finished'))


class PadGuideDbSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'admins': [],
            'config_file': '',
            'dungeon_script_file': '',
            'full_etl_file': '',
            'update_image_file': '',
            'users': {},
        }
        return config

    def admins(self):
        return self.bot_settings['admins']

    def checkAdmin(self, user_id):
        admins = self.admins()
        return user_id in admins

    def addAdmin(self, user_id):
        admins = self.admins()
        if user_id not in admins:
            admins.append(user_id)
            self.save_settings()

    def rmAdmin(self, user_id):
        admins = self.admins()
        if user_id in admins:
            admins.remove(user_id)
            self.save_settings()

    def configFile(self):
        return self.bot_settings.get('config_file', '')

    def setConfigFile(self, config_file):
        self.bot_settings['config_file'] = config_file
        self.save_settings()

    def dungeonScriptFile(self):
        return self.bot_settings.get('dungeon_script_file', '')

    def setDungeonScriptFile(self, dungeon_script_file):
        self.bot_settings['dungeon_script_file'] = dungeon_script_file
        self.save_settings()

    def fullETLFile(self):
        return self.bot_settings.get('dungeon_script_file', '')

    def setFullETLFile(self, full_etl_file):
        self.bot_settings['full_etl_file'] = full_etl_file
        self.save_settings()

    def updateImageFile(self):
        return self.bot_settings.get('dungeon_script_file', '')

    def setUpdateImageFile(self, update_image_file):
        self.bot_settings['update_image_file'] = update_image_file
        self.save_settings()

    def setUserInfo(self, server, user_uuid, user_intid):
        self.bot_settings['users'][server.upper()] = [user_uuid, user_intid]
        self.save_settings()

    def hasUserInfo(self, server):
        return server.upper() in self.bot_settings['users']

    def userUuidFor(self, server):
        return self.bot_settings['users'][server.upper()][0]

    def userIntidFor(self, server):
        return self.bot_settings['users'][server.upper()][1]
