import html
import re
from typing import Optional, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, User, CallbackQuery
from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters, CallbackQueryHandler
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, LOGGER
from tg_bot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_admin,user_admin_no_reply, can_restrict
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable


@run_async
@bot_admin
@user_admin
@loggable
def mute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("You'll need to either give me a username to mute, or reply to someone to be muted.")
        return ""

    if user_id == bot.id:
        message.reply_text("I'm not muting myself!")
        return ""

    member = chat.get_member(int(user_id))

    if member:
        if is_user_admin(chat, user_id, member=member):
            message.reply_text("Afraid I can't stop an admin from talking!")

        elif member.can_send_messages is None or member.can_send_messages:
            bot.restrict_chat_member(chat.id, user_id, can_send_messages=False)
            # message.reply_text("Muted!")
            muter_tag = mention_html(user.id, user.first_name)
            keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Unmute ✅", callback_data="unmute({})".format(member.user.id))]])
            reply = "{} has been muted by {}!".format(mention_html(member.user.id, member.user.first_name), muter_tag)
            message.reply_text(reply,reply_markup=keyboard,parse_mode=ParseMode.HTML)
            return "<b>{}:</b>" \
                   "\n#MUTE" \
                   "\n<b>Admin:</b> {}" \
                   "\n<b>User:</b> {}".format(html.escape(chat.title),
                                              mention_html(user.id, user.first_name),
                                              mention_html(member.user.id, member.user.first_name))

        else:
            message.reply_text("This user is already muted!")
    else:
        message.reply_text("This user isn't in the chat!")

    return ""

@run_async
@user_admin_no_reply
@bot_admin
@loggable
def unmute_button(bot: Bot, update: Update) -> str:
    query = update.callback_query  # type: Optional[CallbackQuery]
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    match = re.match(r"unmute\((.+?)\)", query.data)
    if match:
        user_id = match.group(1)
        member = chat.get_member(int(user_id))
        if member:
            if member.status != 'kicked' and member.status != 'left':
                prev_message = update.effective_message.text_html
                if member.status == "member":
                    update.effective_message.edit_text(f"{prev_message}\n\n <b>~ User already unmuted.</b>",parse_mode=ParseMode.HTML)
                    return ""
                elif member.status == "restricted":
                    bot.restrict_chat_member(chat.id, int(user_id),
                                            can_send_messages=True,
                                            can_send_media_messages=True,
                                            can_send_other_messages=True,
                                            can_add_web_page_previews=True)
                    unmuter_tag  = mention_html(user.id, user.first_name)
                    update.effective_message.edit_text(f"{prev_message}\n\n <b>~ User unmuted by {unmuter_tag}</b>",parse_mode=ParseMode.HTML)
                    return "<b>{}:</b>" \
                        "\n#UNMUTE" \
                        "\n<b>Admin:</b> {}" \
                        "\n<b>User:</b> {}".format(html.escape(chat.title),
                                                    mention_html(user.id, user.first_name),
                                                    mention_html(member.user.id, member.user.first_name))
        else:
            update.effective_message.edit_text("This user isn't even in the chat, unmuting them won't make them talk more than they already do!")
    else:
        update.effective_message.edit_text(
            "User {} is already unmuted.".format(
                mention_html(user.id, user.first_name)),
            parse_mode=ParseMode.HTML)

    return ""





@run_async
@bot_admin
@user_admin
@loggable
def unmute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("You'll need to either give me a username to unmute, or reply to someone to be unmuted.")
        return ""

    # member = chat.get_member(int(user_id))
    member = bot.getChatMember(chat.id,int(user_id))

    if member:
        print(member.status)
        if is_user_admin(chat, user_id, member=member):
            message.reply_text("This is an admin, what do you expect me to do?")
            return ""

        elif member.status != 'kicked' and member.status != 'left':
            if member.status == "member":
                message.reply_text("This user already has the right to speak.")
                return ""
            elif member.status == "restricted":
                bot.restrict_chat_member(chat.id, int(user_id),
                                         can_send_messages=True,
                                         can_send_media_messages=True,
                                         can_send_other_messages=True,
                                         can_add_web_page_previews=True)
                unmuter_tag = mention_html(user.id, user.first_name)
                muted_tag = mention_html(member.user.id, member.user.first_name)
                reply = "{} has been unmuted by {}!".format(muted_tag, unmuter_tag)
                message.reply_text(reply,parse_mode=ParseMode.HTML)
                return "<b>{}:</b>" \
                       "\n#UNMUTE" \
                       "\n<b>Admin:</b> {}" \
                       "\n<b>User:</b> {}".format(html.escape(chat.title),
                                                  mention_html(user.id, user.first_name),
                                                  mention_html(member.user.id, member.user.first_name))
    else:
        message.reply_text("This user isn't even in the chat, unmuting them won't make them talk more than they already do!")

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def temp_mute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("You don't seem to be referring to a user.")
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("I can't seem to find this user")
            return ""
        else:
            raise

    if is_user_admin(chat, user_id, member):
        message.reply_text("I really wish I could mute admins...")
        return ""

    if user_id == bot.id:
        message.reply_text("I'm not gonna MUTE myself, are you crazy?")
        return ""

    if not reason:
        message.reply_text("You haven't specified a time to mute this user for!")
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    mutetime = extract_time(message, time_val)

    if not mutetime:
        return ""

    log = "<b>{}:</b>" \
          "\n#TEMP MUTED" \
          "\n<b>Admin:</b> {}" \
          "\n<b>User:</b> {}" \
          "\n<b>Time:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name), time_val)
    if reason:
        log += "\n<b>Reason:</b> {}".format(reason)

    try:
        if member.can_send_messages is None or member.can_send_messages:
            bot.restrict_chat_member(chat.id, user_id, until_date=mutetime, can_send_messages=False)
            message.reply_text("Muted for {}!".format(time_val))
            return log
        else:
            message.reply_text("This user is already muted.")

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text("Muted for {}!".format(time_val), quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR muting user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Well damn, I can't mute that user.")

    return ""


__help__ = """
*Admin only:*
 - /mute <userhandle>: silences a user. Can also be used as a reply, muting the replied to user.
 - /tmute <userhandle> x(m/h/d): mutes a user for x time. (via handle, or reply). m = minutes, h = hours, d = days.
 - /unmute <userhandle>: unmutes a user. Can also be used as a reply, muting the replied to user.
"""

__mod_name__ = "Muting"

MUTE_HANDLER = CommandHandler(["stfu", "mute"], mute, pass_args=True, filters=Filters.group)
UNMUTE_HANDLER = CommandHandler("unmute", unmute, pass_args=True, filters=Filters.group)
CALLBACK_QUERY_HANDLER = CallbackQueryHandler(unmute_button, pattern=r"unmute")
TEMPMUTE_HANDLER = CommandHandler(["tmute", "tempmute"], temp_mute, pass_args=True, filters=Filters.group)

dispatcher.add_handler(MUTE_HANDLER)
dispatcher.add_handler(UNMUTE_HANDLER)
dispatcher.add_handler(TEMPMUTE_HANDLER)
dispatcher.add_handler(CALLBACK_QUERY_HANDLER)
