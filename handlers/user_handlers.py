import re
import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
import requests

from lexicon.lexicon import LEXICON_RU


# Настройка логера
logger = logging.getLogger(__name__)
handler = logging.FileHandler('logs', encoding='utf8')
formatter = logging.Formatter('[%(asctime)s] #%(levelname)-8s %(filename)s: %(lineno)d - %(name)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Инициализируем роутер уровня модуля
router = Router()


# Cоздаем класс, наследуемый от StatesGroup, для группы состояний нашей FSM
class ChoiceCityCurrency(StatesGroup):
    # Создаем экземпляр класса State
    waiting_currency = State()


@router.message(CommandStart())
async def process_start_command(message: Message):
    text = f'Привет {message.from_user.first_name}, {LEXICON_RU["start"]}'
    await message.answer(text)
    logger.info(f'Бот запущен пользователем {message.from_user.id}')


@router.message(Command(commands='help'))
async def process_help_command(message: Message):
    await message.answer(text=f'{LEXICON_RU["help"]}')


@router.message(Command(commands='convert'), StateFilter(default_state))
async def process_convert_command(message: Message, state: FSMContext):
    await message.answer(text=f'{LEXICON_RU["convert"]}')
    await state.set_state(ChoiceCityCurrency.waiting_currency)


@router.message(StateFilter(ChoiceCityCurrency.waiting_currency))
async def process_convert(message: Message, state: FSMContext):
    # Получаем текст сообщения
    text = message.text.strip()
    # Проверяем валидность строки с помощью регулярного выражения
    pattern = r'^(\d+(\.\d+)?)\s+(\w+)\s+to\s+(\w+)$'
    match = re.match(pattern, text)
    if match:
        # Извлекаем значения из строки
        amount = int(match.group(1))
        from_currency = match.group(3)
        to_currency = match.group(4)

        exchange_rates = requests.get('https://www.cbr-xml-daily.ru/daily_json.js').json()
        # Проверяем что искомые валюты присутствуют, в проивном случае отправляем сообщение
        try:
            exchange_rates["Valute"][from_currency]["Value"]
        except KeyError:
            await message.answer(text=f'Валюта {from_currency} не найдена.Попробуйте ещё /convert')
            await state.clear()
            logger.warning(f'Валюта {from_currency} не найдена')
        try:
            exchange_rates["Valute"][to_currency]["Value"]
        except KeyError:
            await message.answer(text=f'Валюта {to_currency} не найдена..Попробуйте ещё /convert')
            await state.clear()
            logger.warning(f'Валюта {to_currency} не найдена')

        response_user = exchange_rates["Valute"][from_currency]["Value"] *\
            amount / exchange_rates["Valute"][to_currency]["Value"]
        await message.answer(text=f'Составляет: {response_user} {to_currency}')
        await state.clear()
        logger.info('Конвертация выполнена успешно')


@router.message()
async def process_hello_command(message: Message):
    text = message.text.lower()

    if re.search(r'\b(привет|доброе утро|здравствуй)\b', text):
        await message.answer(text=LEXICON_RU['hello'])
        logger.info('Отправлен ответ на приветствие')
    elif re.search(r'\b(пока|всего доброго|до свидания)\b', text):
        await message.answer(text=LEXICON_RU['good_bay'])
        logger.info('Отправлен ответ на прощание')
    else:
        await message.answer(text=LEXICON_RU['unknow'])
        logger.warning('Получена неизвестная команда')
