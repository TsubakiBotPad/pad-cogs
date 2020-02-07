# THIS IS LEGACY DOCUMENTATION AND HAS NOT BEEN UPDATED YET

# rpad-cogs

Cogs developed for Miru Bot.

Code should be pep8 formatted with a 100 character line limit.

# Setting up your own Miru instance for contributing code

## Installing Tools
* Install Git (see the Red install link below if you need help doing this, or read any tutorial)
* Install Python (see the Red install link below if you need help doing this, or read any tutorial)
* Familiarize yourself with how to use a command prompt and Git Bash (if you can't do this you will have a baaaaaaad time) (though in Git all you have to do is git clone so you don't actually need to know everything)

## Installing Miru Dependencies
* For Romanji/Kana conversion you will use Romkan. This is a bit tricky to install so we'll go over it first.
    * If you want to skip this, you can locally comment out all calls to it, but this might be annoying when syncing your code if you're editing files that import it, so you should probably just do it. But if figuring this out is a barrier to entry to start actually coding, feel free to skip at least at the start.
    * git clone [this repo](https://github.com/soimort/python-romkan) into any folder you want.
    * Open setup.py in the text editor or IDE of your choice. Make the following replacement (basically add `encoding='utf8'` in 3 places):
    ```python
    here = os.path.abspath(os.path.dirname(__file__))
    proj_info = json.loads(open(os.path.join(here, PROJ_METADATA), encoding='utf8').read())
    README = open(os.path.join(here, 'README.rst'), encoding='utf8').read()
    CHANGELOG = open(os.path.join(here, 'CHANGELOG.rst'), encoding='utf8').read()
    VERSION = imp.load_source('version', os.path.join(here, 'src/%s/version.py' % PACKAGE_NAME)).__version__
    ```
    * Open a command line in this same directory and run `py setup.py install`
* You may have to install some or all of the following libraries, just use `pip install` or `py -m pip install` in a command prompt for these (note this may be an incomplete list still):
    * python-dateutil
    * pytz
    * twython
    * feedparser
    * tabulate
    * pypng
    * padtools
    * opencv-python
    * Pillow
    * setuptools
    * google-cloud
    * google-api
    * backoff
    * dill
    * prettytable
    * ply
    * aiohttp
    * discord
* Or you can do this via `pip install -r requirements.txt`
## Setting up the bot
* Install Red - [Windows Install](https://twentysix26.github.io/Red-Docs/red_install_windows/) (or switch to whichever OS you want)
* Create your bot account & have it join a private server with just you and the bot, for testing. Probably don't name it Miru to avoid confusion. This step is also explained in the above instructions.
* By now I'm assuming you have a running bot in a server.
* If you ever need to restart the bot, press Ctrl+C in the command prompt where she is running from, and then you can restart it if needed.
* Fork this repo (you are probably already on the page, but if not [go here](https://github.com/nachoapps/rpad-cogs). You will need a GitHub account to do this. Click the button that says "Fork" in the upper-right-hand corner of the page.
* Install Miru cogs - [Link to instructions](https://twentysix26.github.io/Red-Docs/red_getting_started/#community-cogs). Install your fork of it, not the original!
* All cogs must be directly in the folder `Red-DiscordBot\cogs`, so if you aren't on Linux you will likely have to copy-paste the Python files into your fork manually any time you want to commit / make a pull request.
* If you forgot one of the dependencies covered above then you may have to restart the bot after fixing it, if the error doesn't go away immediately.
* Some cogs will have cross dependencies on each other. Check the command prompt that Miru is running from if you encounter any errors.
* Common dependencies include:
    * rpadutils
    * dadguide
    * padinfo
* Note that when you edit cogs with dependencies, you might need to do multiple reloads. For example, if updating dadguide, you will need to reload padinfo as well.
* After you have done all of this, restart the bot again. Hopefully by now `^id ` should work!

## Other

### Emoji
* If you want emojis in `^id` commands, and you are setting this up for DEV PURPOSES ONLY, you can talk to tactical_retreat about getting your bot invited to the emoji servers. If you want to make your own separate Miru instance though, you're on your own for that.
* Give t_r your bot's invite link & ask him for the server IDs
* Then use `^padinfo setemojiservers` with the IDs he gives you. The main Miru server is one of them, you can get that ID yourself.

# Puzzle and Dragons

Most cogs here relate to the mobile game 'Puzzle and Dragons'. Data is sourced from the
DadGuide mobile app.

| Cog        | Purpose                                                         |
| ---        | ---                                                             |
| damagecalc | Simple attack damage calculator                                 |
| padboard   | Converts board images to dawnglare board/solved board links     |
| padglobal  | Global PAD info commands                                        |
| dadguide   | Utility classes relating to DadGuide data                       |
| padinfo    | Monster lookup and info display                                 |
| padrem     | Rare Egg Machine simulation                                     |
| padvision  | Utilities relating to PAD image scanning                        |
| profile    | Global user PAD profile storage and lookup                      |


# Admin/util cogs

Cogs that make server administration easier, do miscellaneous useful things, or
contain utility libraries.

| Cog            | Purpose                                                     |
| ---            | ---                                                         |
| baduser        | Tracks misbehaving users, other misc user tracking          |   
| calculator     | Replacement for the calculator cog that doesnt suck         |  
| fancysay       | Make the bot say special things                             |
| memes          | CustomCommands except role-limited                          |    
| rpadutils      | Utility library shared by many other libraries              |    
| sqlactivitylog | Archives messages in sqlite, allows for lookup              |    
| timecog        | Convert/print time in different timezones                   | 
| trutils        | Misc utilities intended for my usage only                   |
| twitter2       | Mirrors a twitter feed to a channel                         |


# Other/deprecated cogs

Cogs not intended for normal use, or superceded.

| Cog            | Purpose                                                     |
| ---            | ---                                                         |
| adminlog       | In-memory storage of user messages and lookup               |
| donations      | Tracks users who have donated for hosting fees              |
| supermod       | April fools joke, random moderator selection                |

