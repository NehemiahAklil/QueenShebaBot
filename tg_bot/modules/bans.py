import html
import random
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User,ParseMode
from telegram.error import BadRequest
from telegram.ext import run_async, CommandHandler, Filters
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, BAN_STICKER, LOGGER, OWNER_ID
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_ban_protected, can_restrict, \
    is_user_admin, is_user_in_chat, can_delete, user_can_ban
from tg_bot.modules.helper_funcs.extraction import extract_user_and_text
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable

betrayal_quotes = [
"<i>“To betray, you must first belong.” and you belonged in our heart</i>\n\n<b>Kim Philby</b>",
"<i>“There is no greater blessing than a family hand that lifts you from a fall; but there is not lower a family hand that strikes you when you're down.” you just did this to me :(</i>\n\n<b>Wes Fessler</b>",
"<i>“There is always a lesson of a lifetime to learn in every betrayal.” I just did never get emotionally attached to members they all leave you in the end :(</i>\n\n<b>Edmond Mbiaka</b>",
"<i>It was a mistake, you said. But the cruel thing was, it felt like the mistake was mine, for trusting you.</i>\n\n<b>David Levithan</b>",
"<i>“One should rather die than be betrayed. There is no deceit in death. It delivers precisely what it has. Betrayal, though ... betrayal is the willful slaughter of hope.” but we won't stop hoping for your return :(</i>\n\n<b>Steven Deitz</b>",
"<i>“You know that you have been stabbed when you feel the deep pain of betrayal.” this just happened right now and it hurts :(</i>\n\n<b>Les Parrott</b>"
] 

@run_async
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def ban(bot: Bot, update: Update, args: List[str]) -> str:
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

    if user_id == int(OWNER_ID):
        message.reply_text("I'm not gonna ban my owner, want me to ban you instead?!")
        return ""

    elif user_id == bot.id:
        message.reply_text("I'm not gonna BAN myself, are you crazy?")
        return ""

    elif is_user_ban_protected(chat, user_id, member):
        message.reply_text("I really wish I could ban admins...")
        return ""

    log = "<b>{}:</b>" \
          "\n#BANNED" \
          "\n<b>Admin:</b> {}" \
          "\n<b>User:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                       mention_html(user.id, user.first_name),
                                                       mention_html(member.user.id, member.user.first_name),
                                                       member.user.id)
    if reason:
        log += "\n<b>Reason:</b> {}".format(reason)

    try:
        chat.kick_member(user_id)
        bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        message.reply_text("Banned!")
        return log

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text('Banned!', quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Well damn, I can't ban that user.")

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def sban(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat # type: Optional[Chat]
    user = update.effective_user # type: Optional[User]
    message = update.effective_message # type: Optional[Message]
    
    user_id, reason = extract_user_and_text(message, args)
    
    if not user_id:
        return ""
        
    try:
        mem = chat.get_member(user_id)
    except BadRequest:
        return ""
        
    if user_id == int(OWNER_ID):
        return ""
        
    elif user_id == bot.id:
        return ""
        
    elif is_user_ban_protected(chat, user_id, mem):
        return ""
        
    log = "<b>{}:</b>" \
          "\n#SBANNED" \
          "\n<b>Admin:</b> {}" \
          "\n<b>User:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                       mention_html(user.id, user.first_name),
                                                       mention_html(mem.user.id, mem.user.first_name),
                                                       mem.user.id)
              
    if reason:
         log += "\n<b>Reason:</b> {}".format(reason)
         
    if can_delete(chat, bot.id):
        try:
            update.effective_message.reply_to_message.delete()
            update.effective_message.delete()
            chat.kick_member(user_id)
            return log
             
        except BadRequest as excp:
            LOGGER.warning(update)
            LOGGER.exception("Error silently banning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
             
    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def temp_ban(bot: Bot, update: Update, args: List[str]) -> str:
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
            message.reply_text("I can't seem to find this user.")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("I really wish I could ban admins..")
        return ""

    if user_id == bot.id:
        message.reply_text("I'm not gonna BAN myself, are you crazy?!")
        return ""

    if not reason:
        message.reply_text("You haven't specified a time to ban this user for!")
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    bantime = extract_time(message, time_val)

    if not bantime:
        return ""

    log = "<b>{}:</b>" \
          "\n#TEMP BANNED" \
          "\n<b>Admin:</b> {}" \
          "\n<b>User:</b> {} (<code>{}</code>)" \
          "\n<b>Time:</b> {}".format(html.escape(chat.title),
                                     mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name),
                                     member.user.id,
                                     time_val)
    if reason:
        log += "\n<b>Reason:</b> {}".format(reason)

    try:
        chat.kick_member(user_id, until_date=bantime)
        bot.send_sticker(chat.id, BAN_STICKER)  #BanHammer Sticker
        message.reply_text("Banned! User will be banned for {}.".format(time_val))
        return log

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text("Banned! User will be banned for {}.".format(time_val), quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Well damn, I can't ban that user.")

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def kick(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("I can't seem to find this user")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id):
        message.reply_text("I really wish I could kick admins...")
        return ""

    if user_id == bot.id:
        message.reply_text("Yeahhh I'm not gonna do that")
        return ""

    res = chat.unban_member(user_id)  # unban on current user = kick
    if res:
        bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        message.reply_text("Kicked!")
        log = "<b>{}:</b>" \
              "\n#KICKED" \
              "\n<b>Admin:</b> {}" \
              "\n<b>User:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                           mention_html(user.id, user.first_name),
                                                           mention_html(member.user.id, member.user.first_name),
                                                           member.user.id)
        if reason:
            log += "\n<b>Reason:</b> {}".format(reason)

        return log

    else:
        message.reply_text("Well damn, I can't kick that user.")

    return ""


@run_async
@bot_admin
@can_restrict
def kickme(bot: Bot, update: Update):
    user_id = update.effective_message.from_user.id
    message = update.effective_message 
    chat = update.effective_chat
    if is_user_admin(update.effective_chat, user_id):
        message.reply_text("I wish I could... but you're an admin.")
        return

    res = chat.unban_member(user_id)  # unban on current user = kick
    if res:
        reply = random.choice(betrayal_quotes)
        message.reply_text(reply,parse_mode=ParseMode.HTML)
    else:
        message.reply_text("Huh? I can't :/")


@run_async
@bot_admin
@can_restrict
def banme(bot: Bot, update: Update):
    user_id = update.effective_message.from_user.id
    chat_id = update.effective_chat.id
    if is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text("I wish I could... but you're an admin.")
        return
    
    try:
        bot.kick_chat_member(chat_id, user_id)
        res = "Get outta here!"
    except:
        res = "Huh... something went wrong. Report this @PhoenixSupport"
    update.effective_message.reply_text(res)


@run_async
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def unban(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("I can't seem to find this user")
            return ""
        else:
            raise

    if user_id == bot.id:
        message.reply_text("How would I unban myself if I wasn't here...?")
        return ""

    if is_user_in_chat(chat, user_id):
        message.reply_text("Why are you trying to unban someone that's already in the chat?")
        return ""

    chat.unban_member(user_id)
    unbanned_member = mention_html(member.user.id,member.user.first_name)
    message.reply_text(f"Yep, {unbanned_member} can join now!",parse_mode=ParseMode.HTML)

    log = "<b>{}:</b>" \
          "\n#UNBANNED" \
          "\n<b>Admin:</b> {}" \
          "\n<b>User:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                       mention_html(user.id, user.first_name),
                                                       mention_html(member.user.id, member.user.first_name),
                                                       member.user.id)
    if reason:
        log += "\n<b>Reason:</b> {}".format(reason)

    return log


__help__ = """
 - /kickme: kicks the user who issues the command.
 - /banme: bans the user who issues the command.

*Admin only:*
 - /ban <userhandle>: bans a user. (via handle, or reply)
 - /tban <userhandle> x(m/h/d): bans a user for x time. (via handle, or reply). m = minutes, h = hours, d = days.
 - /unban <userhandle>: unbans a user. (via handle, or reply)
 - /kick <userhandle>: kicks a user, (via handle, or reply)
"""

__mod_name__ = "Bans"

BAN_HANDLER = CommandHandler("ban", ban, pass_args=True, filters=Filters.group)
SBAN_HANDLER = CommandHandler("sban", sban, pass_args=True, filters=Filters.group)
TEMPBAN_HANDLER = CommandHandler(["tban", "tempban"], temp_ban, pass_args=True, filters=Filters.group)
KICK_HANDLER = CommandHandler("kick", kick, pass_args=True, filters=Filters.group)
UNBAN_HANDLER = CommandHandler("unban", unban, pass_args=True, filters=Filters.group)
KICKME_HANDLER = DisableAbleCommandHandler("kickme", kickme, filters=Filters.group)
BANME_HANDLER = DisableAbleCommandHandler("banme", banme, filters=Filters.group)

dispatcher.add_handler(BAN_HANDLER)
dispatcher.add_handler(SBAN_HANDLER)
dispatcher.add_handler(TEMPBAN_HANDLER)
dispatcher.add_handler(KICK_HANDLER)
dispatcher.add_handler(UNBAN_HANDLER)
dispatcher.add_handler(KICKME_HANDLER)
dispatcher.add_handler(BANME_HANDLER)
