# padbot-cogs

Red v3 Cogs developed originally for Miru Bot, now for Tsubaki Bot.

Code should be PEP 8 formatted with a 120 character line limit.

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

```bash
# Clone your repo, not this one!!!!!!!! You will want to load your own changes!!!!
git clone https://github.com/TsubakiBotPad/padbot-cogs.git
```

## Set up your bot
The installation instructions in Red's official documentation are pretty good. You will need to be prepared to do the following:
* Create a venv
* Install the Red library
* Create a Discord API key, make a bot, and associate it to your installation

Installation instruction links:
* [Windows install instructions](https://docs.discord.red/en/stable/install_windows.html)
* [Linux/Mac install instructions](https://docs.discord.red/en/stable/install_linux_mac.html)

If you are running on a cloud server for the first time and aren't sure what Linux distro to pick, please, please, please, please, please pick Ubuntu. Their docs aren't well-tested on other distros.

## Installing dependencies
First download `requirements.txt` so that you can run it from your Red venv. In Linux this is done by running the following from the directory holding the folder `name-of-bot` that you created during the Red setup process:
```bash
wget https://raw.githubusercontent.com/TsubakiBotPad/padbot-cogs/master/requirements.txt
```
Then run:
```bash
source name-of-bot/bin/activate
pip install -r requirements.txt
deactivate
```
The rest of the guide takes place from inside Discord.  Replace `^` with your prefix.

## Configuring development version
Once the bot is launched, set it to use your repo directory as a cog path. Type this in Discord where the bot is:

```
^addpath path/to/repo/root
```
## Loading cogs

* Some cogs will have cross dependencies on each other.  Use `^traceback 1` if you encounter any errors to see your traceback.
* Common dependencies include:
    * dadguide
    * padinfo

### Emoji
* You probably don't actually need emoji to be working in order to do development for Tsubaki.
* There are over seven emoji servers. River has access to these, talk to her if you think you need access to them.  In-depth development of the `^id` command may be reason to get access to them.
* You will use `^padinfo emojiserver add` with the IDs she gives you.

# Puzzle and Dragons

Most cogs here relate to the mobile game 'Puzzle & Dragons'.

| Cog           | Purpose                                                         |
| ---           | ---                                                             |
| azurelane     | **DISCONTINUED** Azur Lane card lookup                          |
| channelmirror | A better version of the built-in discord announcement channel   |
| crud          | Database editor.  Not useful for bots other than prod Tsubaki   |
| dadguide      | Central cog to host all PAD data                                |
| damagecalc    | Simple attack damage calculator                                 |
| feedback      | A specialized feedback cog for Tsubaki specifically             |
| padboard      | Converts board images to dawnglare board/solved board links     |
| padbuildimg   | Creates images of PAD teams via a special query language        |
| padbuilds     | See user-made builds for dungeons i think??? (nobody uses this) |
| padevents     | A scheduler cog to help players see upcoming daily GH dungeons. |
| padguidedb    | Database editor.  Not offered to Tsubaki clones.                |
| padglobal     | Global PAD info commands                                        |
| padinfo       | Monster lookup and info display                                 |
| padmonitor    | Keeps an eye out for PAD updates                                |      
| padsearch     | Search for monsters with specific attributes                    |
| padrem        | Rare Egg Machine simulation.  I don't think this ever existed   |
| pricecheck    | Lumon's thing.  Something about stamina trade equivalence       |
| profile       | Global user PAD profile storage and lookup                      |
| schoolidol    | **DISCONTINUED** Love Live! School Idol Festival card lookup    |
