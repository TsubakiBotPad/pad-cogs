# padbot-cogs

Red v3 Cogs developed originally for Miru Bot, now for Tsubaki Bot.

Code should be pep8 formatted with a 100 character line limit.

# Setting up your own Tsubaki instance for contributing code

## Installing Tools

* Install Git (see the Red install link below if you need help doing this, or read any tutorial)
* Install Python 3.8 (see the Red install link below if you need help doing this, or read any tutorial)
* Familiarize yourself with how to use a command prompt and Git Bash (if you can't do this you will have a bad time)


## Check out the repo

Fork this repo (you are probably already on the page, but if not [go here](https://github.com/TsubakiBotPad/padbot-cogs).
You will need a GitHub account to do this. Click the button that says "Fork" in the upper-right-hand corner of the page.

I suggest using [PyCharm Community](https://www.jetbrains.com/pycharm/download) for development. Change into the
`PycharmProjects` directory and clone your fork of the repo:

```shell script
# Clone your repo, not this one.
git clone https://github.com/TsubakiBotPad/padbot-cogs.git

# If you're just setting up a production bot, no need to do this. But you should create a directory and do:
wget https://raw.githubusercontent.com/TsubakiBotPad/padbot-cogs/master/requirements.txt
```

## Set up your bot
The installation instructions in Red's official documentation are pretty good. You will need to be prepared to do the following:
* Create a venv
* Install the Red library
* Create a Discord API key, make a bot, and associate it to your installation

Installation instruction links:
* [Windows install instructions](https://docs.discord.red/en/stable/install_windows.html)
* [Linux/Mac install instructions](https://docs.discord.red/en/stable/install_linux_mac.html)


## Installing additional dependencies
* For Romanji/Kana conversion we use a library called Romkan. There are some problems with the version in PyPI, so it's commented from `requirements.txt`. Instead use pip *inside your venv* to install it separately:
```shell script
pip install git+git://github.com/tejstead/python-romkan
```

The rest of the guide takes place from inside Discord.

## Configuring development version
Once the bot is launched, set it to use your repo directory as a cog path. Type this in Discord where the bot is:

```
!addpath (pwd output)
```

## Loading cogs

* Some cogs will have cross dependencies on each other. Check the command prompt that Miru is running from if you encounter any errors.
* Common dependencies include:
    * rpadutils
    * dadguide
    * padinfo
* Note that when you edit cogs with dependencies, you might need to do multiple reloads. For example, if updating dadguide, you will need to reload padinfo as well.
* After you have done all of this, restart the bot again. Hopefully by now `^id ` should work!

### Emoji
* If you want emojis in `^id` commands, and you are setting this up for DEV PURPOSES ONLY, you can talk to River about getting your bot invited to the emoji servers. If you want to make your own separate Miru instance though, you're on your own for that.
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
