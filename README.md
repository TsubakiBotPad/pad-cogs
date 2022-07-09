# pad-cogs

**Important: You must use Python 3.8 for the setup!!** If you use an earlier or later version, things WILL break. It's not just convenient to be on the same version as us, it's mandatory.

# Setting up your own Tsubaki instance

## Prerequisites / Tools

- Install Git
- Install Python 3.8
- Familiarize yourself with how to use a command prompt and Git Bash (if you can't do this you will have a bad time)

[Red's Installation Guide](https://docs.discord.red/en/stable/install_guides/index.html) is a useful resource if you're a first timer.

I suggest using [PyCharm Community](https://www.jetbrains.com/pycharm/download) for development. Change into the
`PycharmProjects` directory and clone your fork of the repo:

## Check out the repo

Fork this repo (you are probably already on the page, but if not [go here](https://github.com/TsubakiBotPad/pad-cogs)).

> Note: If you are developing a cog that is in the [misc-cogs repo](https://github.com/TsubakiBotPad/misc-cogs), you may need to complete some steps for both pad-cogs AND misc-cogs.

You will need a GitHub account to do this. Click the button that says "Fork" in the upper-right-hand corner of the page.

Git clone your forked repository.

## Create a Discord Bot

If you don't have one already, follow the instructions to create a bot in Red's official documentation:

[Creating a bot account](https://docs.discord.red/en/stable/bot_application_guide.html#creating-a-bot-account)

Keep the bot `token` that you get from Discord at the end of the instructions handy - you will need it to set up the bot later.

## Installation

1. Clone this repo (fork if you're contributing)
1. Create a python 3 venv. `virtualenv -p python3 <envname>`
1. Activate the venv.
1. `pip install -r requirements.txt`

The above steps install Red automatically. You can now follow the Red instructions to startup the bot:

[Setting Up and Running Red (macOS)](https://docs.discord.red/en/stable/install_guides/mac.html#setting-up-and-running-red)

In command line:

- `redbot-setup`
- `redbot <bot_name>`

## Configure Your Bot

The rest of the guide takes place from inside Discord. Replace `^` with your prefix to talk to your bot.

### Tell your bot where to find the code

Once the bot is launched, set it to use your repo directory as a cog path. Type this in Discord where the bot is:

```
^addpath path/to/repo/root
```

e.g

```
^addpath /Users/Tsubaki/src/pad-cogs
```

> Note: you may have to do this for `pad-cogs`, `core-cogs`, and `misc-cogs`. If you have forked and cloned core & misc cogs, this process is the same! However, if you are only developing in `pad-cogs`, and installing `core-cogs` & `misc-cogs` from remote repos then:
> 
> 1. `^load downloader` (this cog is always installed by default)
> 2. `^repo install misc https://github.com/TsubakiBotPad/misc-cogs`
> 3. `^repo install core https://github.com/TsubakiBotPad/core-cogs`
> 4. Now you can install, for example, the `menulistener` cog with `^repo install core menulistener`. The `menulistener` cog is what makes the `^id` menus interactive instead of single-panel static screens with unusable emoji below them.

### Load cogs

Load relevant cogs (whichever cogs you are developing, `dbcog`, and `padinfo`) using the `^load` command.

> Node: We suggest you load `dbcog` and `padinfo` so that you will have something to test that your bot installation correctly installed; however, if your development does not involve dbcog as a dependency, you may want to keep it unloaded (`^unload dbcog`, get it back with `^load dbcog` at any time), simply because it is very slow for the bot to initialize dbcog on startup, and you will be restarting your bot a lot during development.

```
Syntax: ^load <cog 1> ... <cog n>

e.g
^load dbcog padinfo
```

You can see which cogs you have loaded using the `^cogs` command.

### Test a simple command

You should now be able to run basic commands like `^id`

```
^id tsubaki
```

Should return something like:

<img width="597" alt="image" src="https://user-images.githubusercontent.com/880610/173267597-3cbee890-8411-4ac4-b99e-200b273f63ec.png" />

Happy developing!

## Appendix

### Debugging

- Use `^traceback 1` if you encounter any errors to display them in discord.

### Emoji

You may have noticed that emojis are replaced with placeholders in some commands. This is because the bot does not have access to the specific emojis.

- If you are doing in-depth development of the `^id` command, your bot will need to be invited to the emoji servers. Talk to River to get access to these servers.

- Once you and your bot have joined the servers, use `^padinfo emojiserver add <server_id_1> ... <server_id_n> ` with the IDs she gives you.

### Cog list

Most cogs here relate to the mobile game 'Puzzle & Dragons'.

| Cog           | Purpose                                                         |
| ------------- | --------------------------------------------------------------- |
| azurlane      | Azur Lane card lookup                                           |
| crowddata     | Crowdsourced data collection                                    |
| crud          | Database editor. Not useful for bots other than prod Tsubaki    |
| dbcog         | Central cog to host all PAD data                                |
| dungeoncog    | A cog to search and get info for dungeons                       |
| damagecalc    | Simple attack damage calculator                                 |
| feedback      | A specialized feedback cog for Tsubaki specifically             |
| monidlistener | A listener to give info for monster ids                         |
| padboard      | Converts board images to dawnglare board/solved board links     |
| padbuildimg   | Creates images of PAD teams via a special query language        |
| padbuilds     | See user-made builds for dungeons i think??? (nobody uses this) |
| padevents     | A scheduler cog to help players see upcoming daily GH dungeons. |
| padglobal     | Global PAD info commands                                        |
| padle         | A wordle-inspired monster guessing game                         |
| padinfo       | Monster lookup and info display                                 |
| padmonitor    | Keeps an eye out for PAD updates                                |
| pipelineui    | Interface for running the pipeline (Tsubaki-only)               |
| pricecheck    | Lumon's thing. Something about stamina trade equivalence        |
| profile       | Global user PAD profile storage and lookup                      |
