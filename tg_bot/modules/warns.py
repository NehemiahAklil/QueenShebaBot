import html
import re
from typing import Optional, List

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, User, CallbackQuery
from telegram import Message, Chat, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async, DispatcherHandlerStop, MessageHandler, Filters, CallbackQueryHandler
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, BAN_STICKER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import is_user_admin, bot_admin, user_admin_no_reply, user_admin, can_restrict
from tg_bot.modules.helper_funcs.extraction import extract_text, extract_user_and_text, extract_user
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.misc import split_message
from tg_bot.modules.helper_funcs.string_handling import split_quotes
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import warns_sql as sql

WARN_HANDLER_GROUP = 9
CURRENT_WARNING_FILTER_STRING = "<b>Current warning filters in this chat:</b>\n"


# Not async
def warn(user: User, chat: Chat, reason: str, message: Message, warner: User = None,is_warn_kick = False) -> str:
    if is_user_admin(chat, user.id):
        message.reply_text("Damn admins, can't even be warned!")
        return ""

    if warner:
        warner_tag = mention_html(warner.id, warner.first_name)
    else:
        warner_tag = "Automated warn filter."

    limit, soft_warn = sql.get_warn_setting(chat.id)
    num_warns, reasons = sql.warn_user(user.id, chat.id, reason)
    warned_tag = mention_html(user.id, user.first_name) 
    if num_warns >= limit:
        sql.reset_warns(user.id, chat.id)
        if soft_warn:  # kick
            chat.unban_member(user.id)
            reply = f"{limit} warnings, {warned_tag} has been kicked!"
        else:  # ban
            chat.kick_member(user.id)
            reply = f"{limit} warnings, {warned_tag} has been banned!"
        for warn_reason in reasons:
            reply += f"\n - {html.escape(warn_reason)}"

        # banhammer marie sticker
        message.bot.send_sticker(chat.id, BAN_STICKER)
        keyboard = []
        log_reason = f"<b>{html.escape(chat.title)}:</b>" \
                     f"\n#WARN_BAN" \
                     f"\n<b>Admin:</b> {warner_tag}" \
                     f"\n<b>User:</b> {warned_tag} (<code>{user.id}</code>)" \
                     f"\n<b>Reason:</b> {reason}"\
                     f"\n<b>Counts:</b> <code>{num_warns}/{limit}</code>"
    else:
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Remove warn", callback_data=f"rm_warn({user.id})")
                    ]
            ]
        )
        if is_warn_kick:
            reply = f"{warned_tag} has been warned and kicked by {warner_tag}. {num_warns} of {limit} warnings given!"
        else:
            reply = f"{warned_tag} has been warned by {warner_tag}. {num_warns} of {limit} warnings given!"
        if reason:
            reply += f"\nReason: <b>{html.escape(reason)}</b>"

        log_reason = f"<b>{html.escape(chat.title)}:</b>" \
                     f"\n#WARN" \
                     f"\n<b>Admin:</b> {warner_tag}" \
                     f"\n<b>User:</b> {mention_html(user.id, user.first_name)} (<code>{user.id}</code>)" \
                     f"\n<b>Reason:</b> {reason}"\
                     f"\n<b>Counts:</b> <code>{num_warns}/{limit}</code>"

    try:
        if warner:
            return reply,keyboard
        else:
            message.reply_text(reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text(reply, reply_markup=keyboard,parse_mode=ParseMode.HTML, quote=False)
        else:
            raise
    return log_reason


@run_async
@user_admin_no_reply
@bot_admin
@loggable
def button(bot: Bot, update: Update) -> str:
    query = update.callback_query  # type: Optional[CallbackQuery]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message # type: Optional[Message]
    match = re.match(r"rm_warn\((.+?)\)", query.data)

    if match:
        user_id = match.group(1)
        chat = update.effective_chat  # type: Optional[Chat]
        res = sql.remove_warn(user_id, chat.id)
        if res:
            admin_tag = mention_html(user.id, user.first_name)
            user_member = chat.get_member(user_id)
            unwarned_tag = mention_html(user_member.user.id, user_member.user.first_name)
            prev_message = update.effective_message.text_html
            message.edit_text(f"{prev_message}\n\n ~ Warning removed by {admin_tag}",parse_mode=ParseMode.HTML)
            # message.edit_text(prev_message,parse_mode=ParseMode.HTML)
            return f"<b>{html.escape(chat.title)}:</b>" \
                   f"\n#UNWARN" \
                   f"\n<b>Admin:</b> {admin_tag}" \
                   f"\n<b>User:</b> {unwarned_tag} (<code>{user_member.user.id}</code>)"
        else:
            message.edit_text("User already has no warns.")

    return ""


@run_async
@user_admin
@can_restrict
@loggable
def warn_user(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    warner = update.effective_user  # type: Optional[User]

    user_id, reason = extract_user_and_text(message, args)

    if user_id:
        if message.reply_to_message and message.reply_to_message.from_user.id == user_id:
            reply,keyboard = warn(message.reply_to_message.from_user, chat, reason, message, warner)
        else:
            reply,keyboard = warn(chat.get_member(user_id).user, chat, reason, message, warner)
        try:
            message.reply_text(reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        except BadRequest as excp:
            if excp.message == "Reply message not found":
                # Do not reply
                message.reply_text(reply, reply_markup=keyboard,parse_mode=ParseMode.HTML, quote=False)
            else:
                raise
    else:
        message.reply_text("No user was designated!")
    return ""

@run_async
@user_admin
@can_restrict
@loggable
def silent_warn_user(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    warner = update.effective_user  # type: Optional[User]
    user_id, reason = extract_user_and_text(message, args)
    if user_id:
        if message.reply_to_message and message.reply_to_message.from_user.id == user_id:
            warn(message.reply_to_message.from_user, chat, reason, message, warner)
        else:
            warn(chat.get_member(user_id).user, chat, reason, message, warner)
        return message.delete()
    else:
        message.reply_text("No user was designated!")
    return ""

@run_async
@user_admin
@can_restrict
@loggable
def delete_warn_user(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    warner = update.effective_user  # type: Optional[User]
    user_id, reason = extract_user_and_text(message, args)

    if user_id:
        if message.reply_to_message and message.reply_to_message.from_user.id == user_id:
            reply,keyboard  = warn(message.reply_to_message.from_user, chat, reason,message, warner)
        else:
            reply,keyboard  = warn(chat.get_member(user_id).user, chat, reason, message, warner)
        try:
            message.reply_text(reply, reply_markup=keyboard,parse_mode=ParseMode.HTML)
            if message.reply_to_message:
                message.reply_to_message.delete()
        except BadRequest as excp:
            if excp.message == "Reply message not found":
                # Do not reply
                message.reply_text(reply, reply_markup=keyboard,parse_mode=ParseMode.HTML, quote=False)
    else:
        message.reply_text("No user was designated!")
    return ""

@run_async
@user_admin
@can_restrict
@loggable
def warn_kick_user(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    warner = update.effective_user  # type: Optional[User]

    user_id, reason = extract_user_and_text(message, args)

    if user_id:
        if message.reply_to_message and message.reply_to_message.from_user.id == user_id:
            user = message.reply_to_message.from_user
        else:
            user = chat.get_member(user_id).user
        reply,keyboard = warn(user, chat, reason, message, warner,True)
        try:
            chat.unban_member(user.id)
            message.reply_text(reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        except BadRequest as excp:
            if excp.message == "Reply message not found":
                # Do not reply
                message.reply_text(reply, reply_markup=keyboard,parse_mode=ParseMode.HTML, quote=False)
            else:
                raise
    else:
        message.reply_text("No user was designated!")
    return ""


@run_async
@user_admin
@bot_admin
@loggable
def remove_warn(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    user_id = extract_user(message, args)

    if user_id:
        sql.remove_warn(user_id, chat.id)
        warned = chat.get_member(user_id).user
        unwarned_tag = mention_html(user_id,warned.first_name) 
        warner_tag = mention_html(user.id,user.first_name)
        message.reply_text(f"{warner_tag} removed a warning for {unwarned_tag}",parse_mode=ParseMode.HTML)
        return f"<b>{html.escape(chat.title)}:</b>" \
               f"\n#UNWARN" \
               f"\n<b>• Admin:</b> {mention_html(user.id, user.first_name)}" \
               f"\n<b>• User:</b> {mention_html(warned.id, warned.first_name)}" \
               f"\n<b>• ID:</b> <code>{warned.id}</code>"
    else:
        message.reply_text("No user has been designated!")
    return ""


@run_async
@user_admin
@bot_admin
@loggable
def reset_warns(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    user_id = extract_user(message, args)

    if user_id:
        sql.reset_warns(user_id, chat.id)
        message.reply_text("Warnings have been reset!")
        warned = chat.get_member(user_id).user
        return f"<b>{html.escape(chat.title)}:</b>" \
               f"\n#RESETWARNS" \
               f"\n<b>Admin:</b> {mention_html(user.id, user.first_name)}" \
               f"\n<b>User:</b> {mention_html(warned.id, warned.first_name)} (<code>{warned.id}</code>)"
    else:
        message.reply_text("No user has been designated!")
    return ""


@run_async
def warns(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user_id = extract_user(message, args) or update.effective_user.id
    result = sql.get_warns(user_id, chat.id)

    if result and result[0] != 0:
        num_warns, reasons = result
        limit, soft_warn = sql.get_warn_setting(chat.id)

        if reasons:
            text = f"User has {num_warns} out of {limit} warnings, for the following reasons:"
            for reason in reasons:
                text += f"\n - {reason}".capitalize()
            msgs = split_message(text)
            for msg in msgs:
                update.effective_message.reply_text(msg)
        else:
            update.effective_message.reply_text(
                f"User has {num_warns} out of {limit} warnings, but no reasons for any of them.")
    else:
        update.effective_message.reply_text("This user currently doesn't have any warnings!")


# Dispatcher handler stop - do not async
@user_admin
def add_warn_filter(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]

    # use python's maxsplit to separate Cmd, keyword, and reply_text
    args = message.text.split(None, 1)

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])

    if len(extracted) >= 2:
        # set trigger -> lower, so as to avoid adding duplicate filters with different cases
        keyword = extracted[0].lower()
        content = extracted[1]

    else:
        return

    # Note: perhaps handlers can be removed somehow using sql.get_chat_filters
    for handler in dispatcher.handlers.get(WARN_HANDLER_GROUP, []):
        if handler.filters == (keyword, chat.id):
            dispatcher.remove_handler(handler, WARN_HANDLER_GROUP)

    sql.add_warn_filter(chat.id, keyword, content)

    message.reply_text(f"Warn handler added for '{keyword}'!")
    raise DispatcherHandlerStop


@user_admin
def remove_warn_filter(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    # use python's maxsplit to separate Cmd, keyword, and reply_text
    args = msg.text.split(None, 1)

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])

    if len(extracted) < 1:
        return

    to_remove = extracted[0]

    chat_filters = sql.get_chat_warn_triggers(chat.id)

    if not chat_filters:
        msg.reply_text("No warning filters are active here!")
        return

    for filt in chat_filters:
        if filt == to_remove:
            sql.remove_warn_filter(chat.id, to_remove)
            msg.reply_text("Yep, I'll stop warning people for that.")
            raise DispatcherHandlerStop

    msg.reply_text(
        "That's not a current warning filter - run /warnlist for all active warning filters.")


@run_async
def list_warn_filters(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_chat  # type: Optional[Message]
    all_handlers = sql.get_chat_warn_triggers(chat.id)

    if not all_handlers:
        message.reply_text("No warning filters are active here!")
        return

    filter_list = CURRENT_WARNING_FILTER_STRING
    for keyword in all_handlers:
        entry = f" - {html.escape(keyword)}\n"
        if len(entry) + len(filter_list) > telegram.MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(filter_list, parse_mode=ParseMode.HTML)
            filter_list = entry
        else:
            filter_list += entry

    if not filter_list == CURRENT_WARNING_FILTER_STRING:
        message.reply_text(filter_list, parse_mode=ParseMode.HTML)


@run_async
@loggable
def reply_filter(bot: Bot, update: Update) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]

    chat_warn_filters = sql.get_chat_warn_triggers(chat.id)
    to_match = extract_text(message)
    if not to_match:
        return ""

    for keyword in chat_warn_filters:
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            user = update.effective_user  # type: Optional[User]
            warn_filter = sql.get_warn_filter(chat.id, keyword)
            return warn(user, chat, warn_filter.reply, message)
    return ""


@run_async
@user_admin
@loggable
def set_warn_limit(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    if args:
        if args[0].isdigit():
            if int(args[0]) < 3:
                message.reply_text("The minimum warn limit is 3!")
            else:
                sql.set_warn_limit(chat.id, int(args[0]))
                message.reply_text(f"Updated the warn limit to {args[0]}")
                return f"<b>{html.escape(chat.title)}:</b>" \
                       f"\n#SET_WARN_LIMIT" \
                       f"\n<b>Admin:</b> {mention_html(user.id, user.first_name)}" \
                       f"\nSet the warn limit to <code>{args[0]}</code>"
        else:
            message.reply_text("Give me a number as an argument!")
    else:
        limit, soft_warn = sql.get_warn_setting(chat.id)

        message.reply_text(f"The current warn limit is {limit}")
    return ""


@run_async
@user_admin
def set_warn_strength(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    if args:
        chat_title = html.escape(chat.title)
        admin_tag = mention_html(user.id, user.first_name)
        if args[0].lower() in ("on", "yes"):
            sql.set_warn_strength(chat.id, False)
            message.reply_text("Too many warns will now result in a ban!")
            return f"<b>{chat_title}:</b>\n" \
                   f"<b>Admin:</b> {admin_tag}\n" \
                   f"Has enabled strong warns. Users will be banned."
        elif args[0].lower() in ("off", "no"):
            sql.set_warn_strength(chat.id, True)
            message.reply_text("Too many warns will now result in a kick! Users will be able to join again after.")
            return f"<b>{chat_title}:</b>\n" \
                   f"<b>Admin:</b> {admin_tag}\n" \
                   f"Has disabled strong warns. Users will only be kicked."
        else:
            msg.reply_text("I only understand on/yes/no/off!")
    else:
        limit, soft_warn = sql.get_warn_setting(chat.id)
        if soft_warn:
            msg.reply_text("Warns are currently set to *kick* users when they exceed the limits.",
                           parse_mode=ParseMode.MARKDOWN)
        else:
            msg.reply_text("Warns are currently set to *ban* users when they exceed the limits.",
                           parse_mode=ParseMode.MARKDOWN)
    return ""


def __stats__():
    return f"{sql.num_warns()} overall warns, across {sql.num_warn_chats()} chats.\n" \
           f"{sql.num_warn_filters()} warn filters, across {sql.num_warn_filter_chats()} chats."


def __import_data__(chat_id, data):
    for user_id, count in data.get('warns', {}).items():
        for x in range(int(count)):
            sql.warn_user(user_id, chat_id)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    num_warn_filters = sql.num_warn_chat_filters(chat_id)
    limit, soft_warn = sql.get_warn_setting(chat_id)
    limit_action = "kicked" if soft_warn else "banned"
    return f"This chat has `{num_warn_filters}` warn filters. It takes `{limit}` warns " \
           f"before the user gets *{limit_action}*."


__help__ = """
 - /warns <userhandle>: get a user's number, and reason, of warnings.
 - /warnlist: list of all current warning filters

*Admin only:*
 - /warn <userhandle/reply>: warn a user. After 3 warns, the user will be banned from the group.
 - /swarn or /silwarn <userhandle/reply>: warns a user silently by deleted your message after warn.
 - /dwarn or /delwarn <userhandle/reply>: warns a user and also deletes their message.
 - /kwarn or /warnkick <userhandle/reply>: warns a user and kicks them out of the group(only kick not ban).
 - /unwarn or /rmwarn <userhandle>: remove the last warning of the user. Can also be used as a reply.
 - /resetwarn <userhandle>: reset the warnings for a user. Can also be used as a reply.
 - /addwarn <keyword> <reply message>: set a warning filter on a certain keyword. If you want your keyword to \
be a sentence, encompass it with quotes, as such: `/addwarn "very angry" This is an angry user`. 
 - /nowarn <keyword>: stop a warning filter
 - /warnlimit <num>: set the warning limit
 - /strongwarn <on/yes/off/no>: If set to on, exceeding the warn limit will result in a ban. Else, will just kick.
"""

__mod_name__ = "Warnings"

WARN_HANDLER = CommandHandler(
    "warn", warn_user, pass_args=True, filters=Filters.group)
SILENT_WARN_HANDLER = CommandHandler(
    ["swarn","silwarn","silentwarn"], silent_warn_user, pass_args=True, filters=Filters.group)
DELETE_WARN_HANDLER = CommandHandler(
    ["dwarn", "delwarn","deletewarn"], delete_warn_user, pass_args=True, filters=Filters.group)
KICK_WARN_HANDLER = CommandHandler(
    ["kwarn","warnkick"], warn_kick_user, pass_args=True, filters=Filters.group)
UNWARN_HANDLER = CommandHandler(
    ["unwarn", "rmwarn"], remove_warn, pass_args=True, filters=Filters.group)
RESET_WARN_HANDLER = CommandHandler(
    ["resetwarn", "resetwarns"], reset_warns, pass_args=True, filters=Filters.group)
CALLBACK_QUERY_HANDLER = CallbackQueryHandler(button, pattern=r"rm_warn")
MYWARNS_HANDLER = DisableAbleCommandHandler(
    "warns", warns, pass_args=True, filters=Filters.group)
ADD_WARN_HANDLER = CommandHandler(
    "addwarn", add_warn_filter, filters=Filters.group)
RM_WARN_HANDLER = CommandHandler(
    ["nowarn", "stopwarn"], remove_warn_filter, filters=Filters.group)
LIST_WARN_HANDLER = DisableAbleCommandHandler(
    ["warnlist", "warnfilters"], list_warn_filters, filters=Filters.group, admin_ok=True)
WARN_FILTER_HANDLER = MessageHandler(
    CustomFilters.has_text & Filters.group, reply_filter)
WARN_LIMIT_HANDLER = CommandHandler(
    "warnlimit", set_warn_limit, pass_args=True, filters=Filters.group)
WARN_STRENGTH_HANDLER = CommandHandler(
    "strongwarn", set_warn_strength, pass_args=True, filters=Filters.group)

dispatcher.add_handler(WARN_HANDLER)
dispatcher.add_handler(SILENT_WARN_HANDLER)
dispatcher.add_handler(DELETE_WARN_HANDLER)
dispatcher.add_handler(KICK_WARN_HANDLER)
dispatcher.add_handler(UNWARN_HANDLER)
dispatcher.add_handler(CALLBACK_QUERY_HANDLER)
dispatcher.add_handler(RESET_WARN_HANDLER)
dispatcher.add_handler(MYWARNS_HANDLER)
dispatcher.add_handler(ADD_WARN_HANDLER)
dispatcher.add_handler(RM_WARN_HANDLER)
dispatcher.add_handler(LIST_WARN_HANDLER)
dispatcher.add_handler(WARN_LIMIT_HANDLER)
dispatcher.add_handler(WARN_STRENGTH_HANDLER)
dispatcher.add_handler(WARN_FILTER_HANDLER, WARN_HANDLER_GROUP)
