from time import sleep
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import ParseMode
from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import mention_html
from telegram.error import BadRequest, Unauthorized, TelegramError

from tg_bot import dispatcher
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.sql import summons_sql as sql
from tg_bot.modules.helper_funcs.chat_status import user_admin, is_user_admin
from tg_bot.modules.helper_funcs.extraction import extract_user_and_text, extract_args


def divide_chunks(l, n):
    # looping till length l
    for i in range(0, len(l), n):
        yield l[i:i + n]


@run_async
def summon_all(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    # if message.reply_to_message:
    # print(message.reply_to_message.reply_markup)
    should_summon = sql.should_summon(chat.id)
    if not should_summon and not is_user_admin(chat, user.id):
        message.reply_text('Summoning is curretnly disabled in this group')
        return ""

    summons_list = sql.get_chat_summons(chat.id)
    if not summons_list:
        message.reply_text('No one to be summoned')
        return ""
    text = []

    for summonee in summons_list:
        if summonee.custom_name:
            text.append(mention_html(summonee.user_id, summonee.custom_name))
        else:
            try:
                member = chat.get_member(summonee.user_id)
                text.append(mention_html(member.user.id, member.user.first_name))
            except BadRequest:
                continue

    summons_msgs = divide_chunks(text, 6)
    print(summons_msgs)
    reason = extract_args(args)
    # message.reply_text("Summoning member")
    for summon_msg in summons_msgs:
        message.reply_text(reason + ', '.join(summon_msg), parse_mode=ParseMode.HTML, quote=False)


@run_async
def summon_me(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    tag_name = extract_args(args)
    can_tag = sql.can_summon_user(user.id, chat.id)
    if can_tag and not tag_name:
        message.reply_text("You're already on the summons list dummy")
    elif not can_tag:
        sql.add_summoned_user(user.id, chat.id, tag_name, True)
        message.reply_text(f"Welcome back to the summons list {tag_name or user.first_name}")
    else:
        sql.add_summoned_user(user.id, chat.id, tag_name, True)
        message.reply_text("Added you to the summons list")
    return ""


@run_async
def unsummon_me(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    stopped_summoning = sql.stop_user_summon(user.id, chat.id)
    if stopped_summoning:
        message.reply_text("Removed you from the summons list")
    else:
        message.reply_text("You aren't even in this group's summons list to begin with?")


@user_admin
@run_async
def summon_thy(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    user_id, reason = extract_user_and_text(message, args)
    member = chat.get_member(user_id)
    print(member.status)
    if member.status == "left":
        message.reply_text(f"{member.user.first_name} can't be summoned cause they're no longer in this group")
        return ""
    else:
        can_summon = sql.can_summon_user(member.user.id, chat.id)
        if not can_summon:
            message.reply_text(f"{member.user.first_name} doesn't want to be summoned and I respect their decision")
            return ""
        sql.add_summoned_user(member.user.id, chat.id, reason)
        message.reply_text(f"Added {member.user.first_name} to the summons list")
        return ""


@run_async
def stop_summons(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]

    sql.set_summons_setting(chat.id, False)
    return message.reply_text("Disabled summon all comand only admins can use it now")


@run_async
def allow_summons(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]

    sql.set_summons_setting(chat.id, True)
    return message.reply_text("Enabled summon all comand everyone can use it now")


@run_async
@user_admin
def remove_summons(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]

    sql.remove_chat_summons(chat.id)
    message.reply_text("Deleted groups current summons list")


@user_admin
@run_async
def rally_all(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    # if message.reply_to_message:
    # print(message.reply_to_message.reply_markup)

    summons_list = sql.get_chat_summons(chat.id)
    if not summons_list:
        message.reply_text('No one to be rallied')
        return ""
    reason = f'with <b>{extract_args(args)}</b>' if extract_args(args) else ""
    rallied_count = 0
    for summonee in summons_list:
        if summonee.user_id == user.id:
            continue
        chat_mention = mention_html(chat.id, chat.title)
        admin_mention = mention_html(user.id, user.first_name)

        if chat.username:
            link = f"http://telegram.me/{chat.username}/{message.message_id}"
        else:
            chat_tag_id = str(chat.id)[4:]
            link = f"http://telegram.me/c/{chat_tag_id}/{message.message_id}"

        member = chat.get_member(summonee.user_id)
        member_mention = mention_html(member.user.id, member.user.first_name)
        rally_markup = InlineKeyboardMarkup([[InlineKeyboardButton(text="Go To Rally", url=link)]])
        if member.status == "left":
            message.reply_text(f"{member.user.first_name} can't be summoned cause they're no longer in this group")
            continue
        sleep(0.3)
        try:
            bot.sendMessage(summonee.user_id, f"Admin {admin_mention} just rallyed you in {chat_mention} {reason}",
                            parse_mode=ParseMode.HTML, reply_markup=rally_markup, timeout=60)
            rallied_count += 1
        except Unauthorized:
            message.reply_text(f"Apparently {member_mention } thought it would be a good idea to block me? "
                               f"haters gonna hate I guess.",parse_mode=ParseMode.HTML)

    message.reply_text(f'Rallied {rallied_count} to your cause')
    return ""


@run_async
def depreciate_ping_time(bot: Bot, update: Update):
    update.effective_message.reply_text(
        "Whattt you're still hang up on pinging try to be a summoner instead use /summonall or be a pager with "
        "/pageall")


@run_async
def depreciate_ping_me(bot: Bot, update: Update):
    update.effective_message.reply_text(
        "You're not a bot that gets pinged. Its better you're summoned for once use /summonme or /pageme to be paged "
        "by your buddies")


__help__ = """
 - /summonall(pageall) <reason>: To summon group members who are in the summons list also can add a reason to be \
 displayed with the summon message.
 - /summonme(pageme): adds you to the summons list so you can be summoned.
 - /unsummonme(unpageme): removes you from the summons list so you won't be summoned again.
 
 *Admin only:*
 - /summonthy <userhandle>: admin only command adds you the summons list so you can be summoned. Can also be used as a \
 reply.
 - /stopsummons(stpsummons): to disable summonall command but to allow for admins only.
 - /allowsummons(alwsummons): to disable summonall command but to allow for admins only.
 - /rmsummons(delsummons): to delete the groups current summons list.
 - /rallyall: to summon everyone on the summon list but will also pm them.
"""

__mod_name__ = "Summoner"

SUMMON_ALL_HANDLER = DisableAbleCommandHandler(["summonall", "pageall"], summon_all, pass_args=True,
                                               filters=Filters.group)
SUMMON_ME_HANDLER = DisableAbleCommandHandler(["summonme", "pageme"], summon_me, pass_args=True, filters=Filters.group)
SUMMON_THY_ME_HANDLER = CommandHandler("summonthy", summon_thy, pass_args=True, filters=Filters.group)
UNSUMMON_ME_HANDLER = CommandHandler(["unsummonme", "unpageme"], unsummon_me, filters=Filters.group)
DEPRECIATED_PING_HANDLER = CommandHandler(["pingtime", "pingall"], depreciate_ping_time, filters=Filters.group)
DEPRECIATED_PING_ME_HANDLER = CommandHandler("pingme", depreciate_ping_me, filters=Filters.group)
STOP_SUMMONS_HANDLER = CommandHandler(["stopsummons", "stpsummons"], stop_summons, filters=Filters.group)
ALLOW_SUMMONS_HANDLER = CommandHandler(["allowsummons", "alwsummons"], allow_summons, filters=Filters.group)
REMOVE_SUMMONS_HANDLER = CommandHandler(["removesummons", "delsummons", 'delsummons'], remove_summons,
                                        filters=Filters.group)
RALLY_ALL_HANDLER = DisableAbleCommandHandler("rallyall", rally_all, pass_args=True, filters=Filters.group)

dispatcher.add_handler(SUMMON_ALL_HANDLER)
dispatcher.add_handler(SUMMON_ME_HANDLER)
dispatcher.add_handler(SUMMON_THY_ME_HANDLER)
dispatcher.add_handler(UNSUMMON_ME_HANDLER)
dispatcher.add_handler(DEPRECIATED_PING_HANDLER)
dispatcher.add_handler(DEPRECIATED_PING_ME_HANDLER)
dispatcher.add_handler(STOP_SUMMONS_HANDLER)
dispatcher.add_handler(ALLOW_SUMMONS_HANDLER)
dispatcher.add_handler(REMOVE_SUMMONS_HANDLER)
dispatcher.add_handler(RALLY_ALL_HANDLER)
