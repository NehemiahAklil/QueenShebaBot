from typing import List
from malclient import Client
from malclient.exceptions import APIException

from telegram import Bot, Update, Message, InlineKeyboardMarkup, InlineKeyboardButton,ParseMode
from telegram.ext import run_async
from tg_bot import OWNER_ID, MAL_CLIENT_ID, MAL_ACCESS_TOKEN, MAL_CLIENT_SECRET,MAL_REFRESH_TOKEN, dispatcher
from tg_bot.modules.disable import DisableAbleCommandHandler


client = Client()
client.init(access_token=MAL_ACCESS_TOKEN)


def refresh_token(bot:Bot,msg: Message, error: APIException) -> None:
    if str(error.response) == "<Response [401]>":
        client.refresh_bearer_token(
            client_id=MAL_CLIENT_ID,
            refresh_token=MAL_REFRESH_TOKEN,
            client_secret=MAL_CLIENT_SECRET
        )
        new_access_token = client.bearer_token
        new_refresh_token = client.refresh_token
        MSG_TEXT = f"Your MAL access token has expired.\n"\
                   f"*New Access Token*: `{new_access_token}`\n"\
                   f"*New Refresh Token*: `{new_refresh_token}`"
        bot.send_message(OWNER_ID, MSG_TEXT, parse_mode = ParseMode.MARKDOWN)
    else:
        msg.reply_text(f"An error occurred:\n`{error}`", parse_mode = ParseMode.MARKDOWN)


@run_async
def search_anime(bot: Bot, update: Update, args: List[str]) -> None:
    msg = update.effective_message
    query = " ".join(args)
    if not query:
        msg.reply_text("I can't search for nothing...")
        return
    try:
        anime = client.search_anime(query)
    except APIException as e:
        refresh_token(bot,msg, e)
    if not anime:
        msg.reply_text("Not found!")
        return
    anime_id = anime[0].id
    res = client.get_anime_details(anime_id)
    if res.status == "finished_airing":
        status = "Finished Airing"
        episodes = res.num_episodes
    else:
        episodes = None
    genres_list = []
    for i in res.genres:
        genres_list.append(i.name)
    genres = ", ".join(genres_list)
    studio_list = []
    for i in res.studios:
        studio_list.append(i.name)
    studios = ", ".join(studio_list)
    if res.status == "currently_airing":
        status = "Currently Airing"
    if res.start_season:
        premier = res.start_season
    premiered = f"{premier.year} {premier.season.capitalize()}"
    image = res.main_picture.large
    text = f"<b>{res.title} ({res.alternative_titles.ja})</b>\n"\
           f"<b>Type</b>: <code>{res.media_type.upper()}</code>\n"\
           f"<b>Source</b>: <code>{res.source.replace('_', ' ').capitalize()}</code>\n"\
           f"<b>Status</b>: <code>{status}</code>\n"\
           f"<b>Genres</b>: <code>{genres}</code>\n"
    if episodes:
        text += f"<b>Episodes</b>: <code>{episodes}</code>\n"
    text += f"<b>Score</b>: <code>{res.mean}</code>\n"\
            f"<b>Ranked</b>: <code>#{res.rank}</code>\n"\
            f"<b>Studio(s)</b>: <code>{studios}</code>\n"\
            f"<b>Premiered</b>: <code>{premiered}</code>\n\n"\
            f"<a href='{image}'>\u200c</a>"\
            f"{res.synopsis}"
    more_keyboard = [
        [InlineKeyboardButton("More Information", url=f"https://myanimelist.net/anime/{anime_id}")]
    ]
    
    msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(more_keyboard))


@run_async
def search_manga(bot: Bot, update: Update, args: List[str]) -> None:
    msg = update.effective_message
    query = " ".join(args)
    if not query:
        msg.reply_text("I can't search for nothing...")
        return
    try:
        manga = client.search_manga(query)
    except APIException as e:
        refresh_token(msg, e)
    if not manga:
        msg.reply_text("Not found!")
        return
    manga_id = manga[0].id
    res = client.get_manga_details(manga_id)
    genres_list = []
    for i in res.genres:
        genres_list.append(i.name)
    genres = ", ".join(genres_list)
    image = res.main_picture.large
    
    text = f"<b>{res.title} ({res.alternative_titles.ja})</b>\n"\
           f"<b>Type</b>: <code>{res.media_type.capitalize()}</code>\n"\
           f"<b>Status</b>: <code>{res.status.replace('_', ' ').capitalize()}</code>\n"\
           f"<b>Genres</b>: <code>{genres}</code>\n"\
           f"<b>Score</b>: <code>{res.mean}</code>\n"\
           f"<b>Ranked</b>: <code>#{res.rank}</code>\n"
    if res.num_volumes:
        text += f"<b>Volumes</b>: <code>{res.num_volumes}</code>\n"
    if res.num_chapters:
        text += f"<b>Chapters</b>: <code>{res.num_chapters}</code>\n"
    text += f"<a href='{image}'>\u200c</a>"\
            f"\n{res.synopsis}"
    more_keyboard = [
        [InlineKeyboardButton("More Information", url=f"https://myanimelist.net/manga/{manga_id}")]
    ]
    
    msg.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(more_keyboard))


__help__ = """
Get information about anime and manga with the help of this module! All data is fetched from [MyAnimeList](https://myanimelist.net).
*Available commands:*
 - /anime <anime>: returns information about the anime.
 - /manga <manga>: returns information about the manga.
 """


__mod_name__ = "MyAnimeList"


ANIME_HANDLER = DisableAbleCommandHandler("anime", search_anime, pass_args=True)
MANGA_HANDLER = DisableAbleCommandHandler("manga", search_manga, pass_args=True)

dispatcher.add_handler(ANIME_HANDLER)
dispatcher.add_handler(MANGA_HANDLER)
