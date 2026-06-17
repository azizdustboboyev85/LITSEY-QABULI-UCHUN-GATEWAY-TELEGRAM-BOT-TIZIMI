from aiogram.fsm.state import StatesGroup, State

class Registration(StatesGroup):
    """O'quvchining ro'yxatdan o'tish jarayoni uchun FSM (Finite State Machine) holatlari."""
    name = State()       # O'quvchi to'liq ismi (F.I.Sh)
    phone = State()      # Telefon raqami
    documents = State()  # Hujjatlar yuklash bosqichi
