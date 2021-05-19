# Simple dictionary module by @TheRealPhoenix
import requests

from telegram import Bot, Message, Update, ParseMode
from telegram.ext import CommandHandler, run_async

from tg_bot import dispatcher


# @run_async
# def define(bot: Bot, update: Update, args):
#     msg = update.effective_message
#     word = " ".join(args)
#     res = requests.get(f"https://googledictionaryapi.eu-gb.mybluemix.net/?define={word}")
#     if res.status_code == 200:
#         info = res.json()[0].get("meaning")
#         if info:
#             meaning = ""
#             for count, (key, value) in enumerate(info.items(), start=1):
#                 meaning += f"<b>{count}. {word}</b> <i>({key})</i>\n"
#                 for i in value:
#                     defs = i.get("definition")
#                     meaning += f"• <i>{defs}</i>\n"
#             msg.reply_text(meaning, parse_mode=ParseMode.HTML)
#         else:
#             return
#     else:
#         msg.reply_text("No results found!")
#
@run_async
def define(bot: Bot, update: Update, args):
    msg = update.effective_message
    word = " ".join(args)
    res = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
    print(res)
    if res.status_code != 200:
        msg.reply_text("No results found!")
    info = res.json()[0]['meanings']
    phonetics = res.json()[0]['phonetics']
    query_word = res.json()[0]['word']
    pronounction = []
    if phonetics:
        for phonetic in phonetics:
            pronounction.append(phonetic.get('text'))
    print(info)
    if info:
        if len(pronounction):
            meaning = f"{query_word} {' or '.join(pronounction)}\n"
        else:
            meaning = f"{query_word}\n"
        count = 1
        for partOfSpeecch in info:
            meaning += f"<b>{partOfSpeecch.get('partOfSpeech').capitalize()}</b>\n"
            definitions = partOfSpeecch.get("definitions")

            for definition in definitions:
                for cnt, (key, value) in enumerate(definition.items()):
                    if not cnt:
                        meaning += f"<b>{count}.</b> {value}\n"
                    elif key == 'synonyms':
                        meaning += f"  <b>{key}</b> <i>{', '.join(value)}</i>\n"
                    else:
                        meaning += f"<b>  {key}</b> <i>{value}</i>\n"
                count += 1
            meaning += "\n"
        msg.reply_text(meaning, parse_mode=ParseMode.HTML)
    else:
        return


__help__ = """
Ever stumbled upon a word that you didn't know of and wanted to look it up?
With this module, you can find the definitions of words without having to leave the app!

*Available commands:*
 - /define(df) <word>: returns the definition of the word.
 """

__mod_name__ = "Dictionary"

DEFINE_HANDLER = CommandHandler(["define", "df"], define, pass_args=True)

dispatcher.add_handler(DEFINE_HANDLER)
