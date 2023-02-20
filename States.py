from aiogram.dispatcher.filters.state import StatesGroup, State

class NewTTN(StatesGroup):
    order_id = State()
    ttn_state = State()