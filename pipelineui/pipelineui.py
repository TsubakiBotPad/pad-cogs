import asyncio
import json
import logging
from io import BytesIO

import discord
import pymysql
from redbot.core import checks, commands
from redbot.core.utils.chat_formatting import box, inline, pagify
from tsutils.cog_settings import CogSettings
from tsutils.user_interaction import send_repeated_consecutive_messages, send_cancellation_message, \
    send_confirmation_message

logger = logging.getLogger('red.padbot-cogs.pipelineui')


def is_padguidedb_admin_check(ctx):
    is_owner = ctx.author.id in ctx.bot.owner_ids
    return is_owner or ctx.bot.get_cog("PipelineUI").settings.checkAdmin(ctx.author.id)


def is_padguidedb_admin():
    return commands.check(is_padguidedb_admin_check)


class PipelineUI(commands.Cog):
    """UI to the Tsubaki database"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.settings = PadGuideDbSettings("padguidedb")

        self.queue_size = 0
        self.pipeline_lock = asyncio.Lock()
        self.dungeon_lock = asyncio.Lock()
        self.extract_images_lock = asyncio.Lock()
        self.dungeon_load_lock = asyncio.Lock()

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

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

    @commands.group(aliases=['pdb', 'pui'])
    @is_padguidedb_admin()
    async def pipelineui(self, context):
        """PadGuide database manipulation."""

    @pipelineui.command()
    @checks.is_owner()
    async def addadmin(self, ctx, user: discord.Member):
        """Adds a user to the padguide db admin"""
        self.settings.addAdmin(user.id)
        await ctx.tick()

    @pipelineui.command()
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
                await send_cancellation_message(ctx, "Invalid user id.")
                return
        await ctx.tick()

    @pipelineui.command()
    @checks.is_owner()
    async def setconfigfile(self, ctx, *, config_file):
        """Set the database config file."""
        self.settings.setConfigFile(config_file)
        await ctx.tick()

    @pipelineui.command()
    async def searchdungeon(self, ctx, *, search_text):
        """Search for a dungeon via its jp or na name"""
        search_text = '%{}%'.format(search_text)
        with self.get_cursor() as cursor:
            sql = ('SELECT dungeon_id, name_en, name_ja, visible FROM dungeons'
                   ' WHERE LOWER(name_en) LIKE %s OR LOWER(name_ja) LIKE %s'
                   ' ORDER BY dungeon_id DESC LIMIT 20')
            cursor.execute(sql, [search_text, search_text])
            results = list(cursor.fetchall())
            msg = 'Results\n' + json.dumps(results, indent=2, ensure_ascii=False)
            await ctx.send(inline(sql))
            for page in pagify(msg):
                await ctx.send(box(page))

    @pipelineui.command()
    async def subdungeonlist(self, ctx, dungeon_id):
        """Show the subdungeon ids of a dungeon"""
        with self.get_cursor() as cursor:
            cursor.execute('SELECT name_en FROM dungeons'
                           ' WHERE dungeon_id = %s', (dungeon_id,))
            dg_name = next(iter(cursor.fetchall()), {'name_en': None})['name_en']
            if dg_name is None:
                return await ctx.send(f"No dungeon found with id {dungeon_id}")

            cursor.execute('SELECT sub_dungeon_id, name_en FROM sub_dungeons'
                           ' WHERE dungeon_id = %s'
                           ' ORDER BY sub_dungeon_id', (dungeon_id,))
            results = list(cursor.fetchall())
            msg = f'{dg_name}: {dungeon_id}\n\t' + '\n\t'.join(f"{row['name_en']}: {row['sub_dungeon_id']}"
                                                               for row in results)
            for page in pagify(msg):
                await ctx.send(box(page))

    @pipelineui.command()
    async def searchsubdungeons(self, ctx, *, search_text):
        """Show the subdungeon ids of all matching dungeons"""
        search_text = f"%{search_text}%"
        with self.get_cursor() as cursor:
            cursor.execute('SELECT dungeon_id, name_en FROM dungeons'
                           ' WHERE LOWER(name_en) LIKE %s OR LOWER(name_ja) LIKE %s'
                           ' ORDER BY dungeon_id LIMIT 20', (search_text, search_text))
            dgs = cursor.fetchall()
            if not dgs:
                return await ctx.send(f"No dungeons found")

            msg = []
            for dg in dgs:
                cursor.execute('SELECT sub_dungeon_id, name_en FROM sub_dungeons'
                               ' WHERE dungeon_id = %s'
                               ' ORDER BY sub_dungeon_id', (dg['dungeon_id'],))
                results = list(cursor.fetchall())
                msg.append(f"{dg['name_en']} - {dg['dungeon_id']}\n\t"
                           + '\n\t'.join(f"{row['name_en']} - {row['sub_dungeon_id']}"
                                         for row in results))
            await ctx.send_interactive(map(box, pagify('\n\n'.join(msg), delims=['\n\n'])))

    @pipelineui.command()
    @is_padguidedb_admin()
    async def loaddungeon(self, ctx, server: str, dungeon_id: int, dungeon_floor_id: int, queues: int = 1):
        if queues > 5:
            await send_cancellation_message(ctx, "You must send less than 5 queues.")
            return
        elif self.queue_size + queues > 60:
            await send_cancellation_message(ctx, "The size of the queue cannot exceed 60.  It is currently {}.".format(
                                                    self.queue_size))
            return
        elif not self.settings.hasUserInfo(server):
            await send_cancellation_message(ctx, "There is no account associated with server '{}'.".format(
                                                    server.upper()))
            return

        self.queue_size += queues
        if queues == 1:
            await send_confirmation_message(ctx, 'Queueing load in slot {}'.format(self.queue_size))
        else:
            await send_confirmation_message(ctx, 'Queueing loads in slots {}-{}'.format(self.queue_size - queues + 1,
                                                                                   self.queue_size))

        event_loop = asyncio.get_event_loop()
        for queue in range(queues):
            event_loop.create_task(self.do_dungeon_load(ctx, server.upper(), dungeon_id, dungeon_floor_id))

    async def do_dungeon_load(self, ctx, server, dungeon_id, dungeon_floor_id):
        async with self.dungeon_load_lock:
            process = await asyncio.create_subprocess_exec(
                self.settings.pythonExecutable(),
                self.settings.dungeonScriptFile(),
                '--db_config={}'.format(self.settings.configFile()),
                '--server={}'.format(server),
                '--dungeon_id={}'.format(dungeon_id),
                '--floor_id={}'.format(dungeon_floor_id),
                '--user_uuid={}'.format(self.settings.userUuidFor(server)),
                '--user_intid={}'.format(self.settings.userIntidFor(server)),
                '--stream_safe',

                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if b"Traceback" in stderr:
                logger.error("Dungeon Load Error:\n{}\n\n{}".format(stdout.decode(), stderr.decode()))
                await send_repeated_consecutive_messages(ctx, inline(
                    'Load for {} {} {} failed'.format(server, dungeon_id, dungeon_floor_id)))
            else:
                await send_repeated_consecutive_messages(ctx,
                    'Load for {} {} {} finished'.format(server, dungeon_id, dungeon_floor_id))
            self.queue_size -= 1

    @pipelineui.command()
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

    @pipelineui.command()
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
                msg += ','.join(map(str, row.values())) + "\n"
            msg += '\n\nfloor_id,monster_id,count\n'
            for row in results2:
                msg += ','.join(map(str, row.values())) + "\n"

            for page in pagify(msg):
                await ctx.send(box(page))

    @pipelineui.command()
    @checks.is_owner()
    async def cleardungeon(self, ctx, dungeon_id: int):
        with self.get_cursor() as cursor:
            sql = "DELETE FROM wave_data WHERE dungeon_id = {}".format(int(dungeon_id))
            cursor.execute(sql)
        await ctx.tick()

    @pipelineui.group()
    @is_padguidedb_admin()
    async def pipeline(self, context):
        """PadGuide pipeline utilities."""

    @pipeline.command()
    @is_padguidedb_admin()
    async def fulletl(self, ctx, server='COMBINED'):
        """Runs a job which downloads pad data, and updates the padguide database."""
        await self.runetl(ctx, '--server=' + server)

    @pipeline.command()
    @is_padguidedb_admin()
    async def savechanges(self, ctx):
        """Runs a job which saves changes made by CRUD."""
        await self.runetl(ctx, '--skipdownload', '--processors=Monsters')

    async def runetl(self, ctx, *args):
        if self.pipeline_lock.locked():
            await send_cancellation_message(ctx, 'Manual pipeline already running')
            return

        async with self.pipeline_lock:
            await ctx.send('Running pipeline: this could take a while')
            process = await asyncio.create_subprocess_exec(
                'bash',
                self.settings.fullETLFile(),
                *args,

                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

        if b"Pipeline completed successfully!" not in stderr:
            logger.error("Pipeline Error:\n" + stderr.decode())
            await send_cancellation_message(ctx,'Pipeline failed')
        else:
            await send_confirmation_message(ctx, 'Pipeline finished')

    @pipeline.command()
    @is_padguidedb_admin()
    async def processdungeon(self, ctx):
        """Runs the dungeon processor script."""
        if self.dungeon_lock.locked():
            await send_cancellation_message(ctx, 'Dungeon processor already running')
            return

        async with self.dungeon_lock:
            await ctx.send('Running dungeon processor: this could take a while')
            process = await asyncio.create_subprocess_exec(
                'bash',
                self.settings.dungeonProcessorFile(),

                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            for page in pagify(str(stderr)):
                await ctx.send(box(page))
        await send_confirmation_message(ctx, 'Dungeon processing finished')

    @pipeline.command()
    @is_padguidedb_admin()
    async def extractimages(self, ctx):
        """Runs a job which downloads image updates, generates full images, and portraits."""
        if self.extract_images_lock.locked():
            await send_cancellation_message(ctx, 'Extract images already running')
            return

        async with self.extract_images_lock:
            await ctx.send('Running image extract pipeline: this could take a while')
            process = await asyncio.create_subprocess_exec(
                'bash',
                self.settings.imageUpdateFile(),

                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if stderr:
                logger.error("Image Extract Error:\n" + stderr.decode())
                await send_cancellation_message(ctx, 'Image extract failed')
                return
        await send_confirmation_message(ctx, 'Image extract finished')

    @pipelineui.command()
    @checks.is_owner()
    async def setdungeonscriptfile(self, ctx, *, dungeon_script_file):
        """Set the dungeon script file."""
        self.settings.setDungeonScriptFile(dungeon_script_file)
        await ctx.tick()

    @pipelineui.command()
    @checks.is_owner()
    async def setfulletlfile(self, ctx, *, full_etl_file):
        """Set the full ETL file."""
        self.settings.setFullETLFile(full_etl_file)
        await ctx.tick()

    @pipelineui.command()
    @checks.is_owner()
    async def setdungeonprocessorfile(self, ctx, *, full_etl_file):
        """Set the full ETL file."""
        self.settings.setDungeonProcessorFile(full_etl_file)
        await ctx.tick()

    @pipelineui.command()
    @checks.is_owner()
    async def setimageupdatefile(self, ctx, *, image_update_file):
        """Set the image update file."""
        self.settings.setImageUpdateFile(image_update_file)
        await ctx.tick()

    @pipelineui.command()
    @checks.is_owner()
    async def setpythonexecutable(self, ctx, *, python_executable):
        """Set the python executable file."""
        self.settings.setPythonExecutable(python_executable)
        await ctx.tick()

    @pipelineui.command()
    @checks.is_owner()
    async def setuserinfo(self, ctx, server: str, user_uuid: str, user_intid: str):
        """Set the dungeon script."""
        self.settings.setUserInfo(server, user_uuid, user_intid)
        await ctx.tick()


class PadGuideDbSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'admins': [],
            'config_file': '',
            'dungeon_script_file': '',
            'full_etl_file': '',
            'dungeon_processor_file': '',
            'update_image_file': '',
            'python_executable': '/usr/bin/python3',
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
        return self.bot_settings.get('full_etl_file', '')

    def setFullETLFile(self, full_etl_file):
        self.bot_settings['full_etl_file'] = full_etl_file
        self.save_settings()

    def dungeonProcessorFile(self):
        return self.bot_settings.get('dungeon_processor_file', '')

    def setDungeonProcessorFile(self, dungeon_processor_file):
        self.bot_settings['dungeon_processor_file'] = dungeon_processor_file
        self.save_settings()

    def imageUpdateFile(self):
        return self.bot_settings.get('update_image_file', '')

    def setImageUpdateFile(self, update_image_file):
        self.bot_settings['update_image_file'] = update_image_file
        self.save_settings()

    def pythonExecutable(self):
        return self.bot_settings.get('python_executable', '/usr/bin/python3')

    def setPythonExecutable(self, python_executable):
        self.bot_settings['python_executable'] = python_executable
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
