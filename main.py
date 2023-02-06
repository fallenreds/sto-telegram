import json
import asyncio
from api import get_all_goods, get_orders_by_tg_id
from aiogram import Bot, Dispatcher, executor, types, filters
# from DB import DBConnection
from config import *

# from RestAPI.RemonlineAPI import RemonlineAPI

# CRM = RemonlineAPI(REMONLINE_API_KEY_PROD)
# warehouse = CRM.get_main_warehouse_id()
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)






@dp.message_handler(commands=['start'])
async def start_message(message):
    greetings_text = f"Здравствуйте, {message.chat.first_name}. \nВы можете просмотреть и купить товары в магазине 🛒, или же просмотреть статус ваших заказов 📦"

    markup_k = types.ReplyKeyboardMarkup(resize_keyboard=True)
    order_status_button = types.KeyboardButton("Статус заказов 📦")
    markup_k.add(order_status_button)
    await bot.send_message(message.chat.id, text=greetings_text, reply_markup=markup_k)


async def make_order(message, data, goods, order):
    text = f'<b>Имя:</b> {order["name"]}\n<b>Фамилия</b>: {order["last_name"]}\n<b>Адрес доставки:</b> {order["nova_post_address"]} \n'
    if order["prepayment"]:
        text += f'<b>Тип платежа:</b> Нуждается в оплате\n\n'
    else:
        text += f'<b>Тип платежа:</b> Наложенный платеж\n\n'
    to_pay = 0

    for obj in data:
        good = find_good(goods, obj['good_id'])
        to_pay += good["price"][PRICE_ID_PROD] * obj['count']
        text += f"<b>Товар:</b> {good['title']} - Количество: {obj['count']}\n\n"
    text += f"<b>К оплате {to_pay}💳</b>"
    await bot.send_message(message.chat.id, text=text)

    if order["prepayment"] and not order["is_paid"]:
        await bot.send_invoice(message.chat.id,
                               title="Оплатить заказ",
                               description='Для успешного оформления заказа осталось лишь его оплатить',
                               provider_token='5322214758:TEST:4eb03c3b-916d-436b-aba8-3b70b54c711e',
                               currency="uah",
                               is_flexible=False,
                               prices=[types.LabeledPrice(label='Настоящая Машина Времени', amount=int(to_pay) * 100)],
                               payload="test"

                               )


def find_good(goods, good_id):
    for good in goods:
        if good["id"] == good_id:
            return good

@dp.message_handler(filters.Text(contains="статус", ignore_case=True))
async def check_status(message: types.Message):

    orders = await get_orders_by_tg_id(int(message.chat.id))
    if len(orders) == 0:
        return await message.reply(f"У вас нет заказов")

    goods = await get_all_goods()
    await message.reply(f"У вас {len(orders)} заказов:")

    for order in orders:
        data = json.loads(order["goods_list"].replace("'", '"'))
        await make_order(message, data, goods["data"], order)


executor.start_polling(dp, skip_updates=True)
