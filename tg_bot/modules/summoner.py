import html
import json
import random
import time
from datetime import datetime
from typing import Optional, List
from subprocess import Popen, PIPE
import speedtest

import requests
from telegram import Message, Chat, Update, Bot, MessageEntity
from telegram import ParseMode, ReplyKeyboardRemove
from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import escape_markdown, mention_html
from telegram.error import BadRequest, Unauthorized, TelegramError

from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, WHITELIST_USERS, BAN_STICKER
from tg_bot.modules.sql.blacklistusers_sql import BLACKLIST_USERS
from tg_bot.__main__ import GDPR
from tg_bot.__main__ import STATS, USER_INFO
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import user_admin
from tg_bot.modules.helper_funcs.extraction import extract_user
from tg_bot.modules.helper_funcs.filters import CustomFilters


@run_async
def summon_all(bot: Bot, update: Update):
    update.effective_message.reply_text("Summoning all member")

@run_async
def summon_me(bot: Bot, update: Update):
    update.effective_message.reply_text("Adding you to the summons list")

@run_async
def stop_summons(bot: Bot, update: Update):
    update.effective_message.reply_text("Disabling summon all comands for admin use only")

@run_async
@user_admin
def remove_summons(bot: Bot, update: Update):
    update.effective_message.reply_text("Deleting groups current summons list")

@run_async
def rally_all(bot: Bot, update: Update):
    update.effective_message.reply_text("Rally members to arms by sending them pm")

@run_async
def depreciate_ping_time(bot: Bot, update: Update):
    update.effective_message.reply_text("Whattt you're still hang up on pinging try to be a summoner instead use /summonall or page your freinds with /pageall")

@run_async
def depreciate_ping_me(bot: Bot, update: Update):
    update.effective_message.reply_text("Your not a bot so its better your summoned for once instead use /summonme or /pageme to be paged by your buddies")
    



# /ip is for private use
__help__ = """
 - /summonall <reason>: To summon group members who are in the summons list also can add a reason to be displayed with the summon message.
 - /summonme: adds you to the summons list so you can be summoned.
 - /stopsummons: to disable summonall command but to allow for admins only.
 - /removesummons: for admins only to delete all summons list.
 - /rallyall: for admins only will summon everyon on the summon list but will also pm them.
"""

__mod_name__ = "Summoner"

SUMMON_ALL_HANDLER = DisableAbleCommandHandler(["summonall","pageall"], summon_all,filters=Filters.group)
SUMMON_ME_HANDLER = DisableAbleCommandHandler(["summonme","pageme"], summon_me,filters=Filters.group)
DEPRECIATED_PING_HANDLER = CommandHandler(["pingtime,pingall"],depreciate_ping_time,filters=Filters.group)
DEPRECIATED_PING_ME_HANDLER = CommandHandler("pingme",depreciate_ping_me,filters=Filters.group)
STOP_SUMMONS_HANDLER = DisableAbleCommandHandler("stopsummons", stop_summons, filters=Filters.group)
REMOVE_SUMMONS_HANDLER = DisableAbleCommandHandler("removesummons", remove_summons, filters=Filters.group)
RALLY_ALL_HANDLER = DisableAbleCommandHandler("rallyall", rally_all, filters=Filters.group)


dispatcher.add_handler(SUMMON_ALL_HANDLER)
dispatcher.add_handler(SUMMON_ME_HANDLER)
dispatcher.add_handler(DEPRECIATED_PING_HANDLER)
dispatcher.add_handler(DEPRECIATED_PING_ME_HANDLER)
dispatcher.add_handler(STOP_SUMMONS_HANDLER)
dispatcher.add_handler(REMOVE_SUMMONS_HANDLER)
dispatcher.add_handler(RALLY_ALL_HANDLER)

