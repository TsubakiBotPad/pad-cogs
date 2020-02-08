import asyncio
from copy import deepcopy
from datetime import datetime
import os
import threading
import time

from dateutil import tz
import discord
from discord.ext import commands
from twython import Twython, TwythonStreamer
from twython.exceptions import TwythonError

from __main__ import user_allowed, send_cmd_help

from .utils import checks
from .utils.chat_formatting import *
from .utils.dataIO import fileIO

TIME_FMT = """%a %b %d %H:%M:%S %Y"""


class TwitterCog2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = fileIO("data/twitter2/config.json", "load")

        config = self.config
        self.twitter_config = (config['akey'], config['asecret'],
                               config['otoken'], config['osecret'])
        print(self.twitter_config)

#         self.channels = list() # channels to push updates to
        self.channel_ids = config['channels'] or dict()
        self.ntweets = 0
        self.stream = None
        self.stream_thread = None
        self.pre = 'TwitterBot: '  # message preamble

    def __unload(self):
        # Stop previous thread, if any
        if self.stream_thread:
            self.stream.disconnect()
            self.stream_thread.join()

    async def connect(self):
        """Called when connected as a Discord client. Sets up the TwitterUserStream
and starts following a user if one was set upon construction."""
        print("Connected twitter bot.")
        # Setup twitter stream
        if self.stream:
            print("skipping connect")
            return
        self.stream = TwitterUserStream(self.twitter_config)
        self.stream.add(self.tweet)
        await self.refollow()
        print("done with on_ready")

    @commands.group(pass_context=True, no_pm=True)
    @checks.is_owner()
    async def twitter2(self, ctx):
        """Manage twitter feed mirroring"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @twitter2.command(name="info", pass_context=True, no_pm=True)
    async def _info(self, ctx):
        await self.bot.say(self.info(ctx.message.channel))

#     @twitter2.command(name="follow", pass_context=True, no_pm=True)
#     @checks.mod_or_permissions(manage_guild=True)
#     async def _follow(self, ctx, command):
#         await self.bot.say("stopping follow on " + self.tuser)
#         tuser = command
#         self.stream.disconnect()
#         await self.bot.say("starting follow on " + tuser)
#         await self.follow(tuser, ctx.message.channel)

    @twitter2.command(name="addchannel", pass_context=True, no_pm=True)
    async def _addchannel(self, ctx, twitter_user):
        twitter_user = twitter_user.lower()
        already_following = twitter_user in self.channel_ids
        if already_following:
            if ctx.message.channel.id in self.channel_ids[twitter_user]:
                await self.bot.say("Channel already active.")
                return
        elif not self.checkTwitterUser(twitter_user):
            await self.bot.say(inline("User seems invalid : " + twitter_user))
            return
        else:
            self.channel_ids[twitter_user] = list()

        self.channel_ids[twitter_user].append(ctx.message.channel.id)
        self.save_config()
        await self.bot.say(inline("Channel now active for user " + twitter_user))

        if not already_following:
            await self.bot.say(inline("New account, restarting twitter connection"))
            await self.refollow()

    @twitter2.command(name="rmchannel", pass_context=True, no_pm=True)
    async def _rmchannel(self, ctx, twitter_user):
        twitter_user = twitter_user.lower()
        channel_id = ctx.message.channel.id
        if twitter_user not in self.channel_ids:
            await self.bot.say(inline("That account is not active for any channels."))
            return
        elif channel_id not in self.channel_ids[twitter_user]:
            await self.bot.say(inline("Channel was not active for that account."))
            return

        self.channel_ids[twitter_user].remove(channel_id)
        await self.bot.say(inline("Channel removed for user " + twitter_user))
        if not len(self.channel_ids[twitter_user]):
            await self.bot.say(inline("Last channel removed for " + twitter_user + ", restarting twitter connection"))
            self.channel_ids.pop(twitter_user)
            await self.refollow(True)

        self.save_config()

    @twitter2.command(name="resend", pass_context=True, no_pm=True)
    async def _resend(self, ctx, idx: int=1):
        last_tweet = self.stream.last(idx)
        if last_tweet:
            print('Resending tweet idx ' + str(idx))
            await self.tweetAsync(last_tweet)
        else:
            await self.bot.say('No tweet to send')

    def checkTwitterUser(self, tuser):
        return self.stream.get_user(tuser) is not None

    async def refollow(self, src_channel=None):
        """Start streaming tweets from the Twitter user by the given name.
Returns False if the user does not exist, True otherwise."""
        if not len(self.channel_ids):
            return

        # Stop previous thread, if any
        if self.stream_thread:
            if src_channel:
                await self.bot.say("Disconnecting from twitter.")
            self.stream.disconnect()
            self.stream_thread.join()

        # Setup new thread to run the twitter stream in background
        if src_channel:
            await self.bot.say("Connecting to twitter.")

        user_string = ",".join(self.channel_ids.keys())
        self.stream_thread = self.stream.follow_thread(user_string)

        if src_channel:
            await self.bot.say("Now following these users: " + user_string + ".")

    def totime(self, data):
        dt = TwitterUserStream.timeof(data)
        utc = dt.replace(tzinfo=tz.tzutc())
        local = utc.astimezone(tz.tzlocal())
        return local.strftime(TIME_FMT)

    def tweet(self, data):
        self.bot.loop.call_soon(asyncio.async, self.tweetAsync(data))

    @twitter2.command(name="testmsg", pass_context=True, no_pm=True)
    async def _testmsg(self, ctx, twitter_user):
        data = {
            'text': 'test msg',
            'id_str': 'idstring',
            'user': {'screen_name': twitter_user}
        }
        await self.bot.say("Sending test msg: " + str(data))
        await self.tweetAsync(data)

    async def tweetAsync(self, data):
        """Display a tweet to the current channel. Increments ntweets."""
        text = data and data.get('text')
        msg_id = data and data.get('id_str')
        user = data and data.get('user')
        user_name = user and user.get('screen_name')

        if not text:
            return False

        self.ntweets += 1
        msg = box("@" + user_name + " tweeted : \n" + text)
        msg += "<https://twitter.com/" + user_name + "/status/" + msg_id + ">"

        entities = data.get('entities')
        if entities:
            media = entities.get('media')
            if media and len(media) > 0:
                for media_item in media:
                    msg += "\n" + media_item.get("media_url_https")

        await self.send_all(msg, user_name)
        return True

    async def send_all(self, message, twitter_user):
        """Send a message to all active channels."""
        twitter_user = twitter_user.lower()
        if twitter_user not in self.channel_ids:
            print("Error! Unexpected user: " + twitter_user)
            return

        for chan_id in self.channel_ids[twitter_user]:
            print("for channel " + chan_id)
            await self.bot.send_message(discord.Object(chan_id), message)
        return True

    def info(self, channel=None):
        """Send the clients some misc info. Only shows channels on the same server
as the given channel. If channel is None, show active channels from all servers."""
        # Get time of last message from following user
        last_time = 'Never'
        if self.stream and self.stream.last():
            last_time = self.totime(self.stream.last())

        # Get the active channels on the same server as the request
        ccount = 0
        cstr = ""
#         for c in self.channels:
#             if channel is None or c.server == channel.server:
#                 ccount += 1
#                 cstr += "#" + c.name + ", "
        if cstr:
            cstr = cstr[:-2]  # strip extra comma

        return ("**TwitterBot**\n" +
                "Currently following: " + ",".join(self.channel_ids.keys()) + "\n" +
                "Tweets streamed: " + str(self.ntweets) + "\n" +
                "Last tweet from user: " + last_time + "\n" +
                "Active channels on server: (" + str(ccount) + ") " + cstr)

    def save_config(self):
        self.config['channels'] = self.channel_ids
        f = "data/twitter2/config.json"
        fileIO(f, "save", self.config)


def check_folder():
    if not os.path.exists("data/twitter2"):
        print("Creating data/twitter2 folder...")
        os.makedirs("data/twitter2")


def check_file():
    config = {
        'akey': '',
        'asecret': '',
        'otoken': '',
        'osecret': '',
        'channels': [],
    }

    f = "data/twitter2/config.json"
    if not fileIO(f, "check"):
        print("Creating default twitter2 config.json...")
        fileIO(f, "save", config)


def setup(bot):
    print('twitter2 bot setup')
    check_folder()
    check_file()
    n = TwitterCog2(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(n.connect())
    bot.add_cog(n)
    print('done adding twitter2 bot')


def _bisect_left(a, x, lo=0, hi=None, key=None, cmp=None):
    """Return the index where to insert item x in list a, assuming a is sorted.

    The return value i is such that all e in a[:i] have e < x, and all e in
    a[i:] have e >= x.  So if x already appears in the list, a.insert(x) will
    insert just before the leftmost x already there.

    Optional args lo (default 0) and hi (default len(a)) bound the
    slice of a to be searched.

    If key is given, use key(x) instead of x, and key(e) for each e in a when
    determining ordering.

    If cmp is given, use cmp(x, y) instead of 'x < y' in the comparison check
    done between every pair of elements x, y in a.
    """
    def ident(x): return x
    if key is None:
        key = ident

    def compare(x, y): return x < y
    if cmp is None:
        cmp = compare

    if lo < 0:
        raise ValueError('lo must be non-negative')
    if hi is None:
        hi = len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if cmp(key(a[mid]), key(x)):
            lo = mid + 1
        else:
            hi = mid
    return lo


class TwitterUserStream(TwythonStreamer):
    """Stream tweets from a user's Twitter feed. Whenever a tweet is
received on the stream, each function in callbacks will be called with the
Twitter response data as the argument.

Note that the Twitter API may deliver messages out of order and may deliver repeat
messages. Use the 'show_dupes' property to control whether duplicate messages are
reported to the callbacks. The 'store' property controls how many of the most
recent messages to store."""

    def __init__(self, twitter_config, user=None, callbacks=[], show_dupes=False, store=10):
        self.twitter_config = twitter_config
        super(TwitterUserStream, self).__init__(*self.twitter_config)
        self.twitter = Twython(*self.twitter_config)

        self.error = ""  # text of last error
        self._errors = 0
        self._max_errors = 5
        self._show_dupes = show_dupes
        self._follow = user
        self._lastn = list()
        self._store = store  # max size of _lastn
        self._callbacks = list()
        self.add_all(callbacks)
        self._follow_users = list()
        self._follow_user_ids = list()

    def __getattr__(self, attr):
        if attr == 'show_dupes':
            return self._show_dupes
        elif attr == 'store':
            return self._store
        raise AttributeError

    def __setattr__(self, attr, value):
        # show_dupes (bool): whether to report duplicate messages to the callbacks
        if attr == 'show_dupes':
            self._show_dupes = bool(value)

        # store (int): how many tweets to store
        elif attr == 'store':
            if isinstance(value, int):
                # clamp to 0
                if value < 0:
                    value = 0
                # truncate stored messages if we are reducing the count
                if value < self._store:
                    self._lastn = self._lastn[:value]
                self._store = value
            else:
                raise TypeError("type of argument 'store' must be integral")
        else:
            super(TwitterUserStream, self).__setattr__(attr, value)

    # Format of the 'created_at' timestamp returned from Twitter
    # E.g. 'Wed Jan 20 06:35:02 +0000 2016'
    TIME_FMT = """%a %b %d %H:%M:%S %z %Y"""

    @staticmethod
    def timeof(tweet):
        """Return the 'created_at' time for the given tween as a datetime object."""
        return datetime.strptime(tweet['created_at'], TwitterUserStream.TIME_FMT)

    def _remember(self, tweet):
        """Remember a new tweet, dropping the oldest one if we have reached our
limit on 'store'. Keeps tweets in chronological order. See latest()."""
        if len(self._lastn) >= self.store:
            self._lastn.pop(0)
        # Maintain chronological sorting on insertion (using binary search)
        i = _bisect_left(self._lastn, tweet, key=self.timeof)
        self._lastn.insert(i, tweet)

    def latest(self):
        """Return the last several tweets by the last-followed user, in order of
actual occurrence time. The number of messages stored is limited by the 'store'
property."""
        return iter(self._lastn)

    def last(self, idx=1):
        """Return the last tweet which was received. Only valid if 'store' is
greater than zero. Otherwise returns an empty dictionary."""
        if len(self._lastn) > 0:
            idx = idx * -1
            return self._lastn[idx]
        else:
            return dict()

    def stored(self):
        """Return the number of tweets currently stored in latest()."""
        return len(self._lastn)

    def follow_thread(self, *args, **kwargs):
        """Convenient wrapper for calling follow() in a background thread.
The Thread object is started and then returned. Passes on args and kwargs to
the follow() method."""
        thread = threading.Thread(target=self.follow, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread

    def get_user(self, user):
        """Return the user ID of a Twitter user as a string given his screen name,
or None if the user is invalid."""
        try:
            result = self.twitter.get("users/show", params={'screen_name': user})
            return result['id_str']
        except TwythonError as e:
            self.on_error(e.error_code, e.msg)
        return None

    def follow(self, users=None, get_last=True):
        """Start streaming tweents from a user. This method will block basically
forever, so running it in a Thread is a good idea.
If user is None, use the user given on construction.
If get_last is True, fetch the user's last tweets before streaming. The number
of tweets prefetched depends on the 'store' property. Note that any registered
callbacks will NOT be called on these pre-existing tweets. Use latest() to see the
prefetched tweets."""
        user_list = users.split(',') or self._follow_users
        if not len(user_list):
            print('No users specified.')
            return False

        # Fetch the ID of the user by screen name
        uids = list()
        for user in user_list:
            uids.append(self.get_user(user))
        print("uids: " + ",".join(uids))

        self._follow_users = user_list
        self._follow_user_ids = uids

        # Fill up the last 'store' tweets if get_last is set
#         if get_last:
#             del self._lastn[:]
#             result = self.twitter.get("statuses/user_timeline",
#                 params={'user_id':uid, 'count':str(self.store)})
#             # Results are returned in reverse-chronological order
#             result.reverse()
#
#             for tweet in result:
#                 if self._filter_tweet(tweet):
#                     safe_print2(tweet)
#                     self._remember(tweet)

        # Follow the given user
        self.statuses.filter(follow=",".join(self._follow_user_ids))
        return True

    def add(self, callback):
        """Register a function to be called when tweets are received.
Returns the TwitterUserStream object.

Example:
  t = TwitterUserStream(...)
  t.add(myfunc).follow("Bob")
"""
        self._callbacks.append(callback)
        return self

    def add_all(self, callbacks):
        """Register several functions to be called when tweets are received.
Returns the TwitterUserStream object.

Example:
  t = TwitterUserStream(...)
  t.add_all([myfunc1, myfunc2]).follow("Bob")
"""
        self._callbacks.extend(callbacks)

    def remove(self, callback):
        """Unregister the function if it is currently a callback.
Returns the TwitterUserStream object."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def remove_all(self, callbacks):
        """Unregister several functions if they are registered.
Returns the TwitterUserStream object."""
        for callback in callbacks:
            self.remove(callback)

    def _filter_tweet(self, data):
        """Return True if the given tweet should be passed on to the callbacks,
False otherwise."""
        # If we don't have an ID, this isn't valid
        if 'id_str' not in data:
            print("filtering tweet due to missing id_str")
            return False

        # Ignore replies, quotes, and retweets
        if (data.get('in_reply_to_status_id_str')
                or data.get('quoted_statis_id_str')
                or data.get('retweeted_status')):
            return False

        # Ignore messages not directly sent by user
        tweet_uid = data.get('user').get('id_str')
        if (tweet_uid not in self._follow_user_ids):
            print("ignoring msg from " + tweet_uid + " expected " + str(self._follow_user_ids))
            return False

        # If show_dupes is off, ignore duplicate tweets
        if not self.show_dupes:
            for tweet in self._lastn:
                if data['id_str'] == tweet['id_str']:
                    print("ignoring dupe")
                    return False

        return True

    def on_success(self, data):
        """Called by TwythonStreamer when a message is received on the
underlying stream. Dispatches the message to all registered callbacks (in the
order they were registered) if the message is not a duplicate or show_dupes is
enabled."""
#         if 'text' in data:
#             print("got tweet")
#             safe_print(data['text'])
#             safe_print(data)

        # Make sure this is a tweet we are interested in
        if not self._filter_tweet(data):
            return

        # Remember this message - if we reach our store limit, pop the oldest
        self._remember(data)

        # Notify callbacks
        for callback in self._callbacks:
            callback(data)

    def on_error(self, code, data):
        """Called when there is an error. Disconnects from the stream after
receiving too many errors. Sets the 'error' attribute to an appropriate error
message."""
        errmsg = ("Twitter Error: [{0}] {1}".format(code, data))
        print(errmsg)
        self.error = errmsg
        self._errors += 1
        if self._errors >= self._max_errors:
            print("Maximum number of errors exceeded, disconnecting...")
            self.disconnect()
