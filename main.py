import asyncio
import json

from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext

from api import get_all_goods, get_orders_by_tg_id, check_auth, get_active_orders, get_discount, finish_order, \
    no_paid_along_time, get_client_by_tg_id, delete_order, get_discounts_info, post_discount, delete_discount, \
    update_ttn, ttn_tracking, get_order_by_ttn, get_order_by_id, add_new_visitor
from aiogram import Bot, Dispatcher, executor, types, filters
from config import *
from engine import manager_notes_builder, id_spliter, ttn_info_builder
from States import NewTTN

admin_list = [575926846, 516842877]
storage = MemoryStorage()

bot = Bot(token=BOT_TOKEN, parse_mode="HTML", )
dp = Dispatcher(bot, storage=storage)


async def check_admin_permission(message):
    if message.chat.id not in admin_list:
        return False
    return True


@dp.message_handler(commands=['start'])
async def start_message(message):
    await add_new_visitor(int(message.chat.id))
    asyncio.create_task(get_no_paid_orders())

    greetings_text = f"Вітаю, {message.chat.first_name}. \nВи можете переглянути та купити товари в магазині 🛒, або переглянути статус ваших замовлень 📦"
    markup_k = types.ReplyKeyboardMarkup(resize_keyboard=True)
    order_status_button = types.KeyboardButton("Статус замовлень 📦")
    contact_info = types.KeyboardButton("Зв‘язок з нами 📞")
    discount_info = types.KeyboardButton("Знижки 💎")

    markup_k.add(order_status_button, contact_info, discount_info)
    if await check_admin_permission(message):
        admin_button = types.KeyboardButton("/admin")
        markup_k.add(admin_button)

    await bot.send_message(message.chat.id, text=greetings_text, reply_markup=markup_k)


@dp.message_handler(commands=['admin'])
async def admin_panel(message):
    if not await check_admin_permission(message):
        return await bot.send_message(message.chat.id, text="Вы не являетесь администратором!")
    markup_i = types.InlineKeyboardMarkup(row_width=1)
    active_orders = types.InlineKeyboardButton("Активні замовлення 📃", callback_data="active_order")
    not_paid_along_time_client = types.InlineKeyboardButton("Довго не сплачували замовлення 📆", callback_data="no_paid")
    discount_edit_button = types.InlineKeyboardButton("Редагувати знижки ⚙", callback_data="edit_discount")
    markup_i.add(active_orders, not_paid_along_time_client, discount_edit_button)
    return await bot.send_message(message.chat.id,
                                  text="Шановний адміністратор. Ви зайшли до меню керування, <b>будьте обачні перш ніж обирати</b>",
                                  reply_markup=markup_i)


async def make_order(telegram_id, chat_id, data, goods, order, client):
    markup_i = types.InlineKeyboardMarkup(row_width=2)

    text = f"<b>Ім'я:</b> {order['name']}\n<b>Прізвище</b>: {order['last_name']}\n<b>Адреса доставки:</b> {order['nova_post_address']} \n"
    if ttn := order['ttn']:
        text += f"<b>Номер ТТН</b>: {ttn}\n"
        check_ttn_button = types.InlineKeyboardButton(f"Відстежити ttn", callback_data=f'check_ttn/{order["ttn"]}')
        markup_i.add(check_ttn_button)

    if order["prepayment"]:
        text += f'<b>Тип платежу:</b> Потребує оплати\n\n'
    else:
        text += f'<b>Тип платежу:</b> Накладений платіж\n\n'
    to_pay = 0

    for obj in data:
        good = find_good(goods, obj['good_id'])
        to_pay += good["price"][PRICE_ID_PROD] * obj['count']
        text += f"<b>Товар:</b> {good['title']} - Кількість: {obj['count']}\n\n"

    discount = await get_discount(client['id'])
    if discount['success']:
        to_pay -= to_pay / 100 * discount['data']['procent']

    text += f"<b>До сплати {to_pay}💳</b>"

    if order['prepayment'] == 1 and order['is_paid'] == 0:
        delete_button = types.InlineKeyboardButton("Видалити замовлення", callback_data=f"delete_order/{order['id']}")
        markup_i.add(delete_button)

    await bot.send_message(telegram_id, text=text, reply_markup=markup_i)

    if order["prepayment"] and not order["is_paid"]:
        await bot.send_invoice(chat_id=telegram_id,
                               title="Сплатити замовлення",
                               description='Шановний клієнт, для завершення потрібно лише сплатити замовлення ',
                               provider_token='632593626:TEST:sandbox_i93395288591',
                               currency="uah",
                               is_flexible=False,
                               prices=[types.LabeledPrice(label='Оплата товаров STOSHOP', amount=(int(to_pay * 100)))],
                               payload="test"
                               )


def find_good(goods, good_id):
    for good in goods:
        if good["id"] == good_id:
            return good


@dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment(message):
    await bot.send_message(message.chat.id, "Успешно!")


@dp.message_handler(filters.Text(contains="статус", ignore_case=True))
async def check_status(message):
    print(message)
    if type(message) == type(types.Message()):
        telegram_id = int(message.chat.id)
        chat_id = message.chat.id
    else:
        chat_id = int(message["message"]['chat']['id'])
        telegram_id = int(message['from']['id'])

    client = await check_auth(telegram_id)

    if not client['success']:
        return await bot.send_message(telegram_id, f"Ви не авторизовані. Увійдіть або зареєструйтесь у додатку")

    orders = await get_orders_by_tg_id(telegram_id)
    active_orders = list(filter(lambda x: x["is_completed"] == False, orders))
    print(active_orders)

    if len(active_orders) == 0:
        return await bot.send_message(telegram_id, f"У вас немає замовлень")

    goods = await get_all_goods()
    await bot.send_message(telegram_id, f"Кількість ваших замовлень: {len(active_orders)}")

    for order in active_orders:
        data = json.loads(order["goods_list"].replace("'", '"'))
        await make_order(telegram_id, chat_id, data, goods["data"], order, client)


@dp.message_handler(filters.Text(contains="Зв‘язок", ignore_case=True))
async def show_info(message):
    markup_i = types.InlineKeyboardMarkup()
    write_to_button = types.InlineKeyboardButton("Написати Адміністратору", url='t.me/fallenreds')
    markup_i.add(write_to_button)
    if type(message) == type(types.Message()):
        return await message.reply(f"<b>ПІБ:</b> Дмитро\n<b>Телефон:</b> +380 99 025 91 52", reply_markup=markup_i)
    else:
        return await bot.send_message(message["from"]["id"], f"<b>ПІБ:</b> Дмитро\n<b>Телефон:</b> +380 99 025 91 52",
                                      reply_markup=markup_i)


@dp.message_handler(filters.Text(contains="знижки", ignore_case=True))
async def check_discount(message: types.Message):
    telegram_id = message.chat.id
    reply_text = ""
    discounts_info = await get_discounts_info()

    client = await get_client_by_tg_id(telegram_id)
    if client['success']:
        client_discount = await get_discount(client['id'])
        client_procent = 0
        print(client_discount)
        if client_discount["success"]:
            client_procent = client_discount['data']["procent"]
            reply_text = f'Доступна вам знижка складає <b>{client_procent}%</b>.\nВаша місячна сума сплаченого товару становить <b>{client_discount["money_spent"]} грн</b>'
        if client_discount["data"] == "No discount":
            reply_text = f'<b>Нажаль, ви поки не маєте знижки</b>.\nВаша місячна сума сплаченого товару становить <b>{client_discount["money_spent"]} грн</b>'

    reply_text += "\nЗараз доступні такі знижки:\n\n"
    for discount in discounts_info:
        reply_text += f"Сума сплаченого товару: <b>{discount['month_payment']} грн</b> — <b>{discount['procent']}%</b>\n"

    await bot.send_message(telegram_id, reply_text)


async def is_discount(text):
    month_payment, procent = text.split("@")
    try:
        int(month_payment)
        int(procent)
        if int(procent) <= 100:
            return True
        raise ValueError
    except ValueError:
        return False


@dp.message_handler(filters.Text(contains="@", ignore_case=True))
async def add_new_discount(message: types.Message):
    telegram_id = message.chat.id
    if await check_admin_permission(message) and await is_discount(message.text):
        month_payment, procent = message.text.split("@")
        response = await post_discount(int(procent), int(month_payment))
        if response['success']:
            await bot.send_message(telegram_id, "Нова знижка успішно створена!")
        else:
            await bot.send_message(telegram_id, "Помилка на сервері, спробуйте пізніше!")


    elif check_admin_permission(message):
        await bot.send_message(telegram_id, "Введите значения в указаном формате.")


async def order_list_builder(bot, orders, admin_id, goods):
    for order in orders:
        notes_info = await manager_notes_builder(order, goods)  # {"text":goods_info, "client": base_client}
        client = notes_info["client"]
        markup_i = types.InlineKeyboardMarkup()
        deactivate_button = types.InlineKeyboardButton("Закрити замовлення",
                                                       callback_data=f"deactivate_order/{order['id']}")
        delete_button = types.InlineKeyboardButton("Видалити замовлення",
                                                   callback_data=f"delete_order/{order['id']}")

        if not order["ttn"]:
            add_ttn_button = types.InlineKeyboardButton(f"Додати ttn", callback_data=f"add_ttn/{order['id']}")
            markup_i.add(add_ttn_button)
        else:
            add_ttn_button = types.InlineKeyboardButton(f"Оновити ttn", callback_data=f"add_ttn/{order['id']}")
            check_ttn_button = types.InlineKeyboardButton(f"Відстежити ttn", callback_data=f'check_ttn/{order["ttn"]}')
            markup_i.add(add_ttn_button, check_ttn_button)

        markup_i.add(deactivate_button, delete_button)
        await bot.send_message(admin_id, text=notes_info["text"], reply_markup=markup_i)


async def edit_discount(telegram_id):
    discounts_info = await get_discounts_info()
    for discount in discounts_info:
        markup_i = types.InlineKeyboardMarkup()
        delete_discount = types.InlineKeyboardButton("Видалити знижку ❌",
                                                     callback_data=f"delete_discount/{discount['id']}")
        markup_i.add(delete_discount)
        await bot.send_message(telegram_id, f"<b>{discount['month_payment']} грн</b> — <b>{discount['procent']}%</b>",
                               reply_markup=markup_i)

    markup_i = types.InlineKeyboardMarkup()
    add_discount = types.InlineKeyboardButton("Додати знижку ➕", callback_data=f"new_discount")
    markup_i.add(add_discount)
    await bot.send_message(telegram_id,
                           f"<b>Або додайте нову знижку у форматі:\nкількість витрачених коштів за місяць-процент.\nНаприклад 1000@2</b>",
                           reply_markup=markup_i)


@dp.callback_query_handler()
async def callback_admin_panel(callback: types.CallbackQuery):
    goods = await get_all_goods()

    admin_id = callback.from_user.id
    if callback.data == "active_order":
        active_orders = await get_active_orders()
        if not active_orders:
            return await bot.send_message(admin_id, text="На данний момент немає активних замовлень")
        await order_list_builder(bot, active_orders, admin_id, goods)

    if "deactivate_order/" in callback.data:
        order_id = await id_spliter(callback.data)
        order = await get_order_by_id(order_id)

        response = await finish_order(order_id)
        print(response)

        if response['success']:
            await bot.send_message(admin_id,
                                   text="Замовлення успішно закрито. Не забудьте змінити статус замовлення на remonline!")
            await bot.send_message(order['telegram_id'], "Ваше замовлення успішно завершене адміністратором. Дякуюємо, що обираєте нас!")
        else:
            await bot.send_message(admin_id, text="Упс. Відбулась невідома помилка. Спробуйте трішки пізніше")

    if "check_ttn/" in callback.data:
        ttn = await id_spliter(callback.data)
        order = await get_order_by_ttn(ttn)

        response = await ttn_tracking(ttn, order['phone'])
        tnn_info_text = await ttn_info_builder(response, order)
        await bot.send_message(callback.message.chat.id, text=tnn_info_text)

    if "change_order_prepayment/" in callback.data:
        order_id = callback.data.rsplit('/')[-1]

    if "delete_order/" in callback.data:
        order_id = await id_spliter(callback.data)
        order = await get_order_by_id(order_id)
        response = await delete_order(order_id)
        markup_i = types.InlineKeyboardMarkup()
        write_to_button = types.InlineKeyboardButton("Написати Адміністратору", url='t.me/fallenreds')
        markup_i.add(write_to_button)
        if response['success']:
            await bot.send_message(admin_id,
                                   text="Замовлення успішно видалено. Якщо тип замовлення накладений платіж, будь ласка, не забудьте видалити його з remonline!")
            await bot.send_message(order['telegram_id'],
                                   "Ваше замовлення видалено адміністратором. Для детальної інформації зверніться до адміністратора.",reply_markup=markup_i)
        else:
            await bot.send_message(admin_id, text="Упс. Відбулась невідома помилка. Спробуйте трішки пізніше")

    if callback.data == "no_paid":
        orders = await no_paid_along_time()
        print(orders)
        if not orders['success']:
            return await bot.send_message(admin_id, text="Наразі немає несплачених замовлень, з передплатою")
        await order_list_builder(bot, orders['data'], admin_id, goods)

    if callback.data == "Зв‘язок":
        await show_info(callback)

    if "add_ttn/" in callback.data:
        order_id = await id_spliter(callback.data)
        ttn_message = await bot.send_message(callback.message.chat.id,
                                             f"Добре, уведіть зараз id замовлення.\n\n<b>Id цього "
                                             f"замовлення {order_id}.</b>")

        await NewTTN.order_id.set()

    if callback.data == "Статус":
        await check_status(callback)

    if callback.data == "edit_discount":
        await edit_discount(callback.message.chat.id)

    if "delete_discount/" in callback.data:
        discount_id = await id_spliter(callback.data)
        response = await delete_discount(discount_id)
        if response['success']:
            await bot.send_message(callback.message.chat.id, text="Знижку було успішно видалено!")
        else:
            await bot.send_message(callback.message.chat.id,
                                   text="Упс. Відбулась невідома помилка. Спробуйте трішки пізніше")




    if callback.data == "new_discount":
        await bot.send_message(callback.message.chat.id, text="Очікую нові дані")


@dp.message_handler(content_types=['text'], state=NewTTN.order_id)
async def order_state(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['order_id'] = message.text

    await message.reply(
        "<b>Дуже добре, зараз напишіть номер TTN. </b>\n\nЗверніть увагу, у разі помилки ви завжди зможете змінити ТTN замовлення")
    await NewTTN.next()


@dp.message_handler(content_types=['text'], state=NewTTN.ttn_state)
async def ttn_state(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['ttn_state'] = message.text

    data = await state.get_data()
    print(data)
    await state.finish()
    response = await update_ttn(data['order_id'], data['ttn_state'])
    print(response)

    if response['success']:
        return await message.reply("Чудово, ви успішно оновили TTN замовлення")
    else:
        await message.reply("Упс. Відбулась невідома помилка. Спробуйте трішки пізніше")


async def get_no_paid_orders():
    while True:
        print("Updating get_no_paid_orders")
        client_notification = """<b>Шановний клієнт, у вас є несплачені замовлення.</b>\nДля оплати натисніть на <b>Статус замовлень 📦</b>.\nАбо натисніть на <b>Зв‘язок з нами 📞</b> .
          """

        orders = await no_paid_along_time()
        if orders['success']:
            for order in orders['data']:
                markup_i_client = types.InlineKeyboardMarkup()
                write_to_button = types.InlineKeyboardButton("Зв‘язок з нами 📞", callback_data="Зв‘язок")
                to_pay_button = types.InlineKeyboardButton("Сплатити 💸", callback_data="Статус")
                markup_i_client.add(write_to_button, to_pay_button)

                telegram_id = order['telegram_id']
                client = await get_client_by_tg_id(telegram_id)
                await bot.send_message(telegram_id, text=client_notification, reply_markup=markup_i_client)
            not_paid_along_time_client = types.InlineKeyboardButton("Так, переглянути несплачені замовлення",
                                                                    callback_data="no_paid")
            markup_i = types.InlineKeyboardMarkup()
            markup_i.add(not_paid_along_time_client)

            for admin in admin_list:
                await bot.send_message(admin, text=f"Наразі є несплачені замовлення у кількості {len(orders['data'])}",
                                       reply_markup=markup_i)
        await asyncio.sleep(3600)


executor.start_polling(dp, skip_updates=True)
