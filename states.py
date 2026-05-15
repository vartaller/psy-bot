from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    waiting_tz = State()


class SubscribeStates(StatesGroup):
    waiting_time = State()


class ProfileStates(StatesGroup):
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


class EditAnswer(StatesGroup):
    editing = State()    # waiting for text input (text fields or custom choice)


class IndividualityCards(StatesGroup):
    q1 = State()
    q1_custom = State()
    q2 = State()
    q2_custom = State()
    q3 = State()
    q3_custom = State()
