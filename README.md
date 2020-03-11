# miru-v3cogs

Red v3 Cogs developed for Miru Bot.

Code should be pep8 formatted with a 100 character line limit.

# Cog status

### Completed and tested

```

```

### First pass completed

```
automod2
azurelane
baduser
calculator
channelmod
chronomagia
dadguide
damagecalc
donations
fancysay
memes
modnotes
padboard
padbuilds
padevents
padglobal
padguidedb
padinfo
padmonitor
padrem
padsearch
padvision
profile
rpadutils
schoolidol
seniority
sqlactivitylog
stickers
streamcopy
timecog
translate
trutils
voicerole
```

```
# annoying
speech
```






# Setting up your own Miru instance for contributing code

## Installing Tools

* Install Git (see the Red install link below if you need help doing this, or read any tutorial)
* Install Python 3.8 (see the Red install link below if you need help doing this, or read any tutorial)
* Familiarize yourself with how to use a command prompt and Git Bash (if you can't do this you will have a bad time)


## Check out the repo

Fork this repo (you are probably already on the page, but if not [go here](https://github.com/nachoapps/miru-v3cogs). 
You will need a GitHub account to do this. Click the button that says "Fork" in the upper-right-hand corner of the page.

I suggest using [PyCharm Community](https://www.jetbrains.com/pycharm/download) for development. Change into the
`PycharmProjects` directory and clone your fork of the repo:

```shell script
# Clone your repo, not this one.
git clone https://github.com/nachoapps/miru-v3cogs.git

# If you're just setting up a production bot, no need to do this. But you should create a directory and do:
wget https://raw.githubusercontent.com/nachoapps/miru-v3cogs/master/requirements.txt
```

## Set up a virtualenv

One way to install python 3.8:

```shell script
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.8
```

Then set up your 3.8 venv:

```shell script
# Get inside your cloned repo.
cd miru-v3cogs

# Set up the venv.
virtualenv --python=/usr/bin/python3.8 venv

# Atlernatively, install python3.8-venv (possibly python3.8-distutils) and do:
python3.8 -m venv venv

# Activate your venv
source venv/bin/activate

# Install python deps, including Red.
pip install -r requirements.txt
```

## Set up Red Bot

```
# You will use the output from pwd in the next steps, so copy it
pwd

# Initial setup of bot
redbot-setup

# Use whatever you like below, this is my example
bot name> miru_bot_test 

# Replace current_dir with output from pwd
data location> (current_dir)/bot_data

# Pick json for now
storage backend> 1

# Now start the bot, replace the bot name below
redbot miru_bot_test

# Follow the directions to get your bot token
# If copying from a v2 bot, the token is in data/red/settings.json
bot token>  MjQxdzM53TE3MAM2NzA3NTg2.Xc4VVA.RIcv2Ndkxb<truncated>

# Pick whatever you want but consider not overlapping with miru which uses ^
prefix> !
```

Once the bot is launched, set it to use your repo directory as a cog path. Type this in Discord where the bot is:

```
!addpath (pwd output)
```









## TODOs

fork romkan and fix this so people don't keep having to do this

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

## Setting up the bot

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
| donations      | Tracks users who have donated for hosting fees              |

