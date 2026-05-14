from aiogram.fsm.state import State, StatesGroup


class SubscribeStates(StatesGroup):
    waiting_time = State()
    waiting_tz = State()


class ThinkingPattern(StatesGroup):
    irritation = State()
    excitement = State()
    sensation = State()
    feeling = State()
    feeling_custom = State()
    emotion = State()
    emotion_custom = State()
    impression = State()
    meaning = State()
    idea = State()


class HistoryStates(StatesGroup):
    waiting_date = State()
