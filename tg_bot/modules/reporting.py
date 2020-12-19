import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User, ParseMode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, Unauthorized
from telegram.ext import CommandHandler, RegexHandler, run_async, Filters,CallbackQueryHandler
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, LOGGER
from tg_bot.modules.helper_funcs.chat_status import user_not_admin, user_admin
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import reporting_sql as sql

REPORT_GROUP = 5

@run_async
@loggable
def solve_callback(bot: Bot, update: Update) -> str:

    query = update.callback_query  # type: Optional[CallbackQuery]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message # type: Optional[Message]
    match = re.match(r"solve_report\((.+?)\)", query.data)

    if match:
        report_id = match.group(1)
        chat = update.effective_chat  # type: Optional[Chat]
        admin_tag = mention_html(user.id, user.first_name)
        user_member = chat.get_member(user_id)
        unwarned_tag = mention_html(user_member.user.id, user_member.user.first_name)
        prev_message = update.effective_message.text_html
        message.edit_text(f"{prev_message}\n\n ~ Report Solved by {admin_tag}",                           parse_mode=ParseMode.HTML)
        query.answer(text="Report Solved!")
        # message.edit_text(prev_message,parse_mode=ParseMode.HTML)
        return f"<b>{html.escape(chat.title)}:</b>" \
               f"\nREPORT SOLVED " \
               f"\n<b>Reported ID:</b> {report_id}"\
               f"\n<b>Admin:</b> {admin_tag}"\
            #    f"\n<b>User:</b> {unwarned_tag} (<code>{user_member.user.id}</code>)"
    else:
        query.answer(text="Sorry,There was an error")
    return ""
@run_async
@user_admin
def report_setting(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    if chat.type == chat.PRIVATE:
        if len(args) >= 1:
            if args[0] in ("yes", "on"):
                sql.set_user_setting(chat.id, True)
                msg.reply_text("Turned on reporting! You'll be notified whenever anyone reports something.")

            elif args[0] in ("no", "off"):
                sql.set_user_setting(chat.id, False)
                msg.reply_text("Turned off reporting! You wont get any reports.")
        else:
            msg.reply_text(f"Your current report preference is: `{sql.user_should_report(chat.id)}`",parse_mode=ParseMode.MARKDOWN)

    else:
        if len(args) >= 1:
            if args[0] in ("yes", "on"):
                sql.set_chat_setting(chat.id, True)
                msg.reply_text("Turned on reporting! Admins who have turned on reports will be notified when /report or @admin are called.")

            elif args[0] in ("no", "off"):
                sql.set_chat_setting(chat.id, False)
                msg.reply_text("Turned off reporting! No admins will be notified on /report or @admin.")
        else:
            msg.reply_text(f"This chat's current setting is: `{sql.chat_should_report(chat.id)}`",parse_mode=ParseMode.MARKDOWN)


@run_async
# @user_not_admin
@loggable
def report(bot: Bot, update: Update) -> str:
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    if chat and message.reply_to_message and sql.chat_should_report(chat.id):
        reported_user = message.reply_to_message.from_user  # type: Optional[User]
        chat_name = chat.title or chat.first or chat.username
        admin_list = chat.get_administrators()
        messages = update.effective_message  # type: Optional[Message]
        reported_tag = mention_html(reported_user.id,reported_user.first_name)
        reporter_tag = mention_html(user.id, user.first_name)
        if chat.username and chat.type == Chat.SUPERGROUP:
            reported = f"{reporter_tag} reported {reported_tag} to the admins!"
            if message.reply_to_message and message.reply_to_message.message_id:
                report_id = f"#{message.reply_to_message.message_id}"
            else:
                report_id = f"#{message.message_id}"
            msg = f"<b>{html.escape(chat.title)}:</b>" \
                  f"\n<b>Report ID:</b> {report_id}"\
                  f"\n<b>Reported user:</b> {reported_tag} (<code>{reported_user.id}</code>)" \
                  f"\n<b>Reported by:</b> {reporter_tag} (<code>{user.id}</code>)"
            link = f"http://telegram.me/c/{chat_tag_id}/{message.message_id}"
            should_forward = False
            buttons = [InlineKeyboardButton(text="Go To Report", url=link),InlineKeyboardButton(text="Solve",callback_data=f"solve_report({report_id})")]
            report_markup =InlineKeyboardMarkup([buttons])
            messages.reply_text(reported, reply_markup=report_markup, parse_mode=ParseMode.HTML)
        else:
            if message.reply_to_message and message.reply_to_message.message_id:
                report_id = f"#C{message.reply_to_message.message_id}"
            else:
                report_id = f"#C{message.message_id}"
            
            reported = f"{reporter_tag} reported {reported_tag} to the admins!"
            msg = f"<b>{html.escape(chat.title)}:</b>" \
                  f"\n<b>Report ID:</b> {report_id}"\
                  f"\n<b>Reported user:</b> {reported_tag} (<code>{reported_user.id}</code>)" \
                  f"\n<b>Reported by:</b> {reporter_tag} (<code>{user.id}</code>)"
            link = f"http://telegram.me/c/{chat_tag_id}/{message.message_id}"
            chat_tag_id = str(chat.id)[4:]
            link = f"http://telegram.me/c/{chat_tag_id}/{message.message_id}"
            should_forward = False if message.reply_to_message.from_user.is_bot else True
            buttons = [InlineKeyboardButton(text="Go To Report", url=link),InlineKeyboardButton(text="Solve",callback_data=f"solve_report({report_id})")]
            report_markup = InlineKeyboardMarkup([buttons])
            messages.reply_text(reported, reply_markup = report_markup, parse_mode=ParseMode.HTML)

        reported_admin_count = 0
        for admin in admin_list:
            if admin.user.is_bot:  # can't message bots
                continue

            if sql.user_should_report(admin.user.id):
                try:
                    bot.send_message(admin.user.id, msg + link, parse_mode=ParseMode.HTML)
                    reported_admin_count += 1
                    if should_forward:
                        # bot.forwardMessage(admin.user.id,chat.id,False,message.message_id)
                        message.reply_to_message.forward(admin.user.id)

                        if len(message.text.split()) > 1:  # If user is giving a reason, send his message too
                            message.forward(admin.user.id)

                except Unauthorized:
                    pass
                except BadRequest as excp:  # TODO: cleanup exceptions
                    LOGGER.exception("Exception while reporting user")
        admin_reported = f"Reported {report_id} to {reported_admin_count} Admins"
        messages.reply_text(reported,quote=False)
        return msg

    return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return f"This chat is setup to send user reports to admins, via /report and @admin: `{sql.chat_should_report(chat_id)}`"


def __user_settings__(user_id):
    return f"You receive reports from chats you're admin in: `{sql.user_should_report(user_id)}`.\nToggle this with /reports in PM."


__mod_name__ = "Reporting"

__help__ = """
 - /report <reason>: reply to a message to report it to admins.
 - @admin: reply to a message to report it to admins.
NOTE: Neither of these will get triggered if used by admins.

*Admin only:*
 - /reports <on/off>: change report setting, or view current status.
   - If done in pm, toggles your status.
   - If in chat, toggles that chat's status.
"""

REPORT_HANDLER = CommandHandler("report", report, filters=Filters.group)
SETTING_HANDLER = CommandHandler("reports", report_setting, pass_args=True)
ADMIN_REPORT_HANDLER = RegexHandler("(?i)@admin(s)?", report)
CALLBACK_QUERY_HANDLER = CallbackQueryHandler(solve_callback, pattern=r"solve_report")

dispatcher.add_handler(REPORT_HANDLER, REPORT_GROUP)
dispatcher.add_handler(ADMIN_REPORT_HANDLER, REPORT_GROUP)
dispatcher.add_handler(SETTING_HANDLER)
