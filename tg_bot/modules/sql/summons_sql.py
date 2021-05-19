import threading

from sqlalchemy import Integer, Column, String, ARRAY, UnicodeText, func, distinct, Boolean

from tg_bot.modules.sql import BASE, SESSION


class Summons(BASE):
    __tablename__ = "summons"

    user_id = Column(Integer, primary_key=True)
    chat_id = Column(String(14), primary_key=True)
    custom_name = Column(UnicodeText)
    stop_summoning = Column(Boolean)

    def __init__(self, user_id, chat_id, custom_name="", stop_summoning=False):
        self.user_id = user_id
        self.chat_id = str(chat_id)
        self.custom_name = custom_name
        self.stop_summoning = stop_summoning

    def __repr__(self):
        return f"{self.user_id} wants be summoned in {self.chat_id} is set to {not self.stop_summoning}"


class SummonsSettings(BASE):
    __tablename__ = "summon_settings"
    chat_id = Column(String(14), primary_key=True)
    should_summon = Column(Boolean, default=True)

    def __init__(self, chat_id, should_summon=False):
        self.chat_id = str(chat_id)
        self.should_summon = should_summon

    def __repr__(self):
        return "<Summoning in {} is set to {}.>".format(self.chat_id, self.should_summon)


Summons.__table__.create(checkfirst=True)
SummonsSettings.__table__.create(checkfirst=True)
SUMMONS_INSERTION_LOCK = threading.RLock()
SUMMONS_SETTINGS_INSERTION_LOCK = threading.RLock()


def should_summon(chat_id):
    try:
        setting = SESSION.query(SummonsSettings).get(str(chat_id))
        if setting:
            return setting.should_summon
        else:
            return False
    finally:
        SESSION.close()


def can_summon_user(user_id, chat_id):
    with SUMMONS_INSERTION_LOCK:
        curr = SESSION.query(Summons).get((user_id, str(chat_id)))
        if curr and curr.stop_summoning:
            return False
        return True


def add_summoned_user(user_id, chat_id, custom_name=None, should_tag=None):
    with SUMMONS_INSERTION_LOCK:
        curr = SESSION.query(Summons).get((user_id, str(chat_id)))
        if not curr:
            curr = Summons(user_id, str(chat_id))
        if custom_name:
            curr.custom_name = custom_name
        if should_tag:
            curr.stop_summoning = False
        name = curr.custom_name
        SESSION.add(curr)
        SESSION.commit()
        return name, user_id


def get_chat_summons(chat_id):
    try:
        return SESSION.query(Summons).filter(Summons.chat_id == str(chat_id), Summons.stop_summoning == False).all()
    finally:
        SESSION.close()


def remove_chat_summons(chat_id):
    try:
        curr_summons = SESSION.query(Summons).filter(Summons.chat_id == str(chat_id)).all()
        for curr in curr_summons:
            SESSION.delete(curr)
            SESSION.commit()
    finally:
        SESSION.close()


def stop_user_summon(user_id, chat_id):
    with SUMMONS_INSERTION_LOCK:
        removed = False
        curr = SESSION.query(Summons).get((user_id, str(chat_id)))
        if curr:
            curr.stop_summoning = True
            SESSION.add(curr)
            SESSION.commit()
            removed = True

        SESSION.close()
        return removed


def set_summons_setting(chat_id, shall_summon):
    with SUMMONS_SETTINGS_INSERTION_LOCK:
        curr_setting = SESSION.query(SummonsSettings).get(str(chat_id))
        if not curr_setting:
            curr_setting = SummonsSettings(chat_id)
        curr_setting.should_summon = shall_summon
        SESSION.add(curr_setting)
        SESSION.commit()


def get_summons_setting(chat_id):
    try:
        setting = SESSION.query(SummonsSettings).get(str(chat_id))
        if setting:
            return setting.should_summon
        else:
            return False

    finally:
        SESSION.close()
