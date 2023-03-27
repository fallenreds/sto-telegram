import asyncio
import json

from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext

from UpdateTask import order_updates, get_no_paid_orders

from api import *
from aiogram import Bot, Dispatcher, executor, filters

from buttons import *
from config import *
from engine import manager_notes_builder, id_spliter, ttn_info_builder, send_error_log, make_order
from States import NewTTN, NewPost, NewClientDiscount, NewPaymentData, NewProps, NewTextPost
from handlers.client_handler import show_clients
from labels import AdminLabels
from notifications import *

admin_list = [516842877, 5783466675]
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
        return await bot.send_message(message.chat.id, text=AdminLabels.notAdmin.value)
    markup_i = types.InlineKeyboardMarkup(row_width=1)

    markup_i.add(
        get_active_orders_button(),
        get_not_paid_along_time_button(),
        get_edit_discount_button(),
        get_all_clients_button(),
        get_make_post(),
        get_set_props(),
        get_props_info_button()
    )
    return await bot.send_message(message.chat.id, text=AdminLabels.enter_notifications.value, reply_markup=markup_i)


# async def make_order(bot, telegram_id, data, goods, order, client):
#     markup_i = types.InlineKeyboardMarkup(row_width=2)
#
#     text = f"<b>Номер замовлення</b> {order['id']}\n<b>Ім'я:</b> {order['name']}\n<b>Прізвище</b>: {order['last_name']}\n<b>Адреса доставки:</b> {order['nova_post_address']} \n"
#     if ttn := order['ttn']:
#         text += f"<b>Номер ТТН</b>: {ttn}\n"
#         check_ttn_button = get_check_ttn_button(order['ttn'])
#         markup_i.add(check_ttn_button)
#
#     if order["prepayment"]:
#         text += f'<b>Тип платежу:</b> Передплата\n'
#         if order['is_paid'] == 1:
#             text += f'<b>Статус оплати:</b> Оплачено\n\n'
#         else:
#             text += f'<b>Статус оплати:</b> Потребує оплати\n\n'
#     else:
#         text += f'<b>Тип платежу:</b> Накладений платіж\n\n'
#     to_pay = 0
#
#
#     for obj in data:
#         good = find_good(goods, obj['good_id'])
#         to_pay += good["price"][PRICE_ID_PROD] * obj['count']
#         text += f"<b>Товар:</b> {good['title']} - Кількість: {obj['count']}\n\n"
#
#     discount = await get_discount(client['id'])
#     if discount['success']:
#         to_pay -= to_pay / 100 * discount['data']['procent']
#
#     if not order['is_paid']:
#         text += f"<b>До сплати {to_pay}💳</b>"
#
#     if order['prepayment'] == 1 and order['is_paid'] == 0:
#         delete_button = get_delete_order_button(order['id'])
#         markup_i.add(delete_button)
#
#     if order["prepayment"] and not order["is_paid"]:
#         props: dict
#         with open('props.json', "r", encoding='utf-8') as f:
#             props = json.load(f)
#         text += "\n\nДля того щоб отримати реквізити натисніть на кнопку <b>Переглянути реквізити👇</b>" \
#                 "\nПісля сплати замовлення натисніть кнопку <b>Відправити фото з оплатою</b>"
#         markup_i.add(get_props_info_button())
#         markup_i.add(get_send_payment_photo_button(order['id']))
#     await bot.send_message(telegram_id, text=text, reply_markup=markup_i)

    # Оплата рабочая, ждет пока он не сделает ФОП
    # if order["prepayment"] and not order["is_paid"]:
    #     await bot.send_invoice(chat_id=telegram_id,
    #                            title=f"Сплатити замовлення №{order['id']}",
    #                            description=f'Шановний клієнт, для завершення потрібно лише сплатити замовлення #{order["id"]}',
    #                            provider_token='632593626:TEST:sandbox_i93395288591',
    #                            currency="uah",
    #                            is_flexible=False,
    #                            prices=[types.LabeledPrice(label='Оплата послуг Airbag AutoDelivery',
    #                                                       amount=(int(to_pay * 100)))],
    #                            payload=order['id']
    #                            )


async def get_props_info():
    with open('props.json', "r", encoding='utf-8') as f:
        props = json.load(f)
    return f"<b>Натисніть на номер картки щоб скопіювати</b>\n" \
           f"\n<b>ФІО</b>: {props['full_name']}\n<b>Номер картки</b>: <code>{props['card']}</code>\n"


def find_good(goods, good_id):
    for good in goods:
        if good["id"] == good_id:
            return good


async def pre_checkout_payment(pre_checkout_query):
    order = await get_order_by_id(int(pre_checkout_query.invoice_payload))
    print(order)
    order_goods_list = json.loads(order["goods_list"].replace("'", '"'))
    goods = await get_all_goods()
    goods = goods['data']

    if order:
        telegram_id = order['telegram_id']
        for order_good in order_goods_list:

            real_good = find_good(goods, order_good['good_id'])
            if int(real_good['residue']) < int(order_good['count']):
                error_message = f"\nШановний клієнт, ми вибачаємось за незручності, проте товару {real_good['title']} " \
                                f"зараз недостатньо для виконання замовлення. " \
                                f"\n\nЙого кількість зараз {int(real_good['residue'])}" \
                                f"\n\nБудь ласка, створіть ваше замовлення знов." \
                                f"Це замовлення буде видалено. Дякуємо за розуміння"
                await bot.send_message(telegram_id, text=error_message)
                await delete_order(order['id'])
                return await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False, error_message=error_message)
            return await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True,
                                                       error_message="Все добре", )
    else:

        return await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False,
                                                   error_message="Помилка, замовлення не знайдено")


@dp.pre_checkout_query_handler(lambda query: True)
async def checkout(pre_checkout_query):
    try:
        await pre_checkout_payment(pre_checkout_query)
    except Exception as error:
        return await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False,
                                                   error_message="Невідома помилка, спробуйте пізніше")


@dp.message_handler(content_types=['successful_payment'])
async def got_payment(message: types.message.Message):
    await make_pay_order(int(message.successful_payment.invoice_payload))
    await bot.send_message(message.chat.id,
                           f"Дякую, ви успішно оплатили замовлення №{message.successful_payment.invoice_payload}!")


@dp.message_handler(filters.Text(contains="статус", ignore_case=True))
async def check_status(message):
    try:
        if type(message) == type(types.Message()):
            telegram_id = int(message.chat.id)
            #chat_id = message.chat.id
        else:
            #chat_id = int(message["message"]['chat']['id'])
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
            await make_order(bot, telegram_id, data, goods["data"], order, client)
    except TypeError as error:
        await send_error_log(bot, 516842877, error)
        await no_connection_with_server_notification(bot, message)

@dp.message_handler(filters.Text(contains="Зв‘язок", ignore_case=True))
async def show_info(message):
    markup_i = types.InlineKeyboardMarkup()
    write_to_button = types.InlineKeyboardButton("Написати", url='https://t.me/airbagsale')
    to_call_button = types.InlineKeyboardButton("Позвонити", callback_data="to_call")
    markup_i.add(write_to_button, to_call_button)
    if type(message) == type(types.Message()):
        await bot.send_contact(message.chat.id, phone_number="+380989989828", first_name='AIRBAG "DELIVERY AUTO"',
                               reply_markup=markup_i)
    else:
        await bot.send_contact(message["from"]["id"], phone_number="+380989989828", first_name='AIRBAG "DELIVERY AUTO"',
                               reply_markup=markup_i)


@dp.message_handler(filters.Text(contains="знижки", ignore_case=True))
async def check_discount(message: types.Message):
    try:
        telegram_id = message.chat.id
        reply_text = "В магазині <b>Airbag “AutoDelivery”</b> діють накопичувальні знижки для гуртових покупців.\n\n"
        discounts_info = await get_discounts_info()

        client = await get_client_by_tg_id(telegram_id)
        print(client)
        if client['success']:
            client_money_spend = await get_money_spend_cur_month(client['id'])
            client_discount = await get_discount(client['id'])
            print(client_discount)
            client_procent = 0
            if client_discount["success"]:
                client_procent = client_discount['data']["procent"]
                reply_text += f'Наразі Вам доступна знижка <b>{client_procent}%</b>.\nЗагальна сума замовлень у цьому місяці <b>{client_money_spend} грн</b>\n\n'

            else:
                reply_text += f'<b>Нажаль, ви поки не маєте знижки</b>.\nЗагальна сума замовлень у цьому місяці <b>{client_money_spend} грн</b>\n\n '

        reply_text += "В залежності від суми замовлення в минулому місяці, надається знижка на всі замовлення у поточному місяці:\n"

        for n in range(len(discounts_info)):
            if n != len(discounts_info) - 1:
                reply_text += f"⚪ Від <b>{discounts_info[n]['month_payment']}</b> до <b>{discounts_info[n + 1]['month_payment']}</b> грн  — <b>{discounts_info[n]['procent']}%</b>\n"
            else:
                reply_text += f"⚪ Від <b>{discounts_info[n]['month_payment']}</b> грн  — <b>{discounts_info[n]['procent']}%</b>\n"

        reply_text += "\n<b>Порядок нарахування:</b>"
        reply_text += "\n⚪ Розрахунок знижки проводиться <b>щомісяця</b>;"
        reply_text += "\n⚪ Знижка розповсюджується <b>на весь товар</b> у каталозі;"

        reply_text += "\n\n<b>Сподіваємось, що накопичувальна знижка дозволить зробити нашу співпрацю ще більш успішною.</b>"
        await bot.send_message(telegram_id, reply_text)
    except TypeError as error:
        await send_error_log(bot, 516842877, error)
        await no_connection_with_server_notification(bot, message)


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
        if not response:
            return None
        if response['success']:
            await bot.send_message(telegram_id, "Нова знижка успішно створена!")
        else:
            await unknown_error_notifications(bot, telegram_id)


    elif check_admin_permission(message):
        await bot.send_message(telegram_id, "Введите значения в указаном формате.")


async def order_list_builder(bot, orders, admin_id, goods):
    for order in orders:
        notes_info = await manager_notes_builder(order, goods)  # {"text":goods_info, "client": base_client}

        markup_i = types.InlineKeyboardMarkup()
        deactivate_button = get_deactive_order_button(order['id'])
        delete_button = get_delete_order_button(order['id'])

        if not order["ttn"]:
            add_ttn_button = types.InlineKeyboardButton(f"Додати ttn", callback_data=f"add_ttn/{order['id']}")
            markup_i.add(add_ttn_button)
        else:
            add_ttn_button = types.InlineKeyboardButton(f"Оновити ttn", callback_data=f"add_ttn/{order['id']}")
            check_ttn_button = get_check_ttn_button(order['ttn'])
            markup_i.add(add_ttn_button, check_ttn_button)
        if order['prepayment']:
            if order['is_paid'] == 0:
                to_not_prepayment_button = get_to_not_prepayment_button(order['id'])
                markup_i.add(to_not_prepayment_button)
                markup_i.add(get_make_paid_button(order['id']))

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
    try:


        goods = await get_all_goods()

        admin_id = callback.from_user.id
        if callback.data == "active_order":
            active_orders = await get_active_orders()
            if not active_orders:
                return await bot.send_message(admin_id, text="На данний момент немає активних замовлень")
            await order_list_builder(bot, active_orders, admin_id, goods)

        if callback.data == "show_all_clients":
            await show_clients(callback.message, bot)

        if "check_order/" in callback.data:
            order_id = await id_spliter(callback.data)
            order = [await get_order_by_id(order_id)]
            print(order)
            await order_list_builder(bot, order, callback.message.chat.id, goods)

        if callback.data == "discount_info":
            await check_discount(callback.message)

        if "make_paid/" in callback.data:
            order_id = await id_spliter(callback.data)
            order = await get_order_by_id(order_id)
            admin_text = f"Чудово, тепер перевірте замовлення в remonline №{order_id}!"
            client_text = f"Дякую, ви успішно оплатили замовлення №{order_id}!"
            await make_pay_order(int(order_id))
            await bot.send_message(order['telegram_id'], client_text)
            await bot.send_message(callback.message.chat.id, admin_text)

        if callback.data == "change_props" and callback.message.chat.id in admin_list:
            await NewProps.full_name.set()
            await bot.send_message(callback.message.chat.id,
                                   "Будь ласка, напишіть ФІО в реквізитах.\nДля відміни операції натисніть /stop")

        if "deactivate_order/" in callback.data:
            order_id = await id_spliter(callback.data)
            order = await get_order_by_id(order_id)

            response = await finish_order(order_id)
            if not response:
                return None
            if response['success']:
                client_text = f"Дякуємо за замовлення <b>№{order['id']}</b>!\nДо нових зустрічей у AirBag “AutoDelivery” 💛💙"
                await bot.send_message(admin_id,
                                       text="Замовлення успішно закрито. Не забудьте змінити статус замовлення на remonline!")
                await bot.send_message(order['telegram_id'], client_text)
            else:
                await unknown_error_notifications(bot, admin_id)

        if "to_not_prepayment/" in callback.data:
            order_id = await id_spliter(callback.data)
            order = await get_order_by_id(order_id)
            await change_to_not_prepayment(order_id)
            await change_to_not_prepayment_notifications(bot, order_id, callback.message.chat.id)
            await change_to_not_prepayment_notifications(bot, order_id, order['telegram_id'])
        if "check_ttn/" in callback.data:
            ttn = await id_spliter(callback.data)
            order = await get_order_by_ttn(ttn)

            response = await ttn_tracking(ttn, order['phone'])
            tnn_info_text = await ttn_info_builder(response, order)
            await bot.send_message(callback.message.chat.id, text=tnn_info_text)

        # if "change_order_prepayment/" in callback.data:
        #     order_id = callback.data.rsplit('/')[-1]

        if "send_payment_photo" in callback.data:
            order_id = callback.data.rsplit('/')[-1]
            await NewPaymentData.order_id.set()
            await bot.send_message(callback.message.chat.id,
                                   f'Будь ласка, напишіть ваш номер замовлення, за яке ви хочете відправити фото оплати. Номер цього замовлення {order_id}.\nДля відміни операції натисніть /stop')

        if callback.data == "to_call":
            await bot.send_message(callback.message.chat.id, text="Номер телефону: \n+380989989828")

        if "delete_order/" in callback.data:
            order_id = await id_spliter(callback.data)
            order = await get_order_by_id(order_id)
            response = await delete_order(order_id)
            markup_i = types.InlineKeyboardMarkup().add(get_our_contact_button())
            if not response:
                return None
            if response['success']:
                client_text = f"<b>На жаль, ми не дочекалися підтвердження Вашого замовлення №{order_id} 😟</b>" \
                              f"\nЗамовлення видалено, чекаємо на Ваше повернення! 😀"
                if callback.message.chat.id in admin_list:
                    await bot.send_message(admin_id, text=f"Замовлення №{order_id} успішно видалено. Якщо тип замовлення накладений платіж, будь ласка, не забудьте видалити його з remonline!")
                await bot.send_message(order['telegram_id'], client_text, reply_markup=markup_i)
            else:
                await unknown_error_notifications(bot, admin_id)

        if callback.data == "no_paid":
            orders = await no_paid_along_time()
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
        if callback.data == "get_props_info":
            await bot.send_message(callback.message.chat.id, await get_props_info())

        if callback.data == "edit_discount":
            await edit_discount(callback.message.chat.id)

        if "delete_discount/" in callback.data:
            discount_id = await id_spliter(callback.data)
            response = await delete_discount(discount_id)
            if not response:
                return None
            if response['success']:
                await bot.send_message(callback.message.chat.id, text="Знижку було успішно видалено!")
            else:
                await unknown_error_notifications(bot, callback.message.chat.id)

        if callback.data == "new_discount":
            await bot.send_message(callback.message.chat.id, text="Очікую нові дані")

        if callback.data == "make_post" and callback.message.chat.id in admin_list:
            markup_i = types.InlineKeyboardMarkup().add(get_make_post_only_text_button(),
                                                        get_make_post_text_with_image_button())
            await bot.send_message(callback.message.chat.id,
                                   text="Оберіть: оголошення з фотографією чи без?\nДля відміни операції натисніть /stop",
                                   reply_markup=markup_i)

        if callback.data == "make_post_with_image":
            await bot.send_message(callback.message.chat.id, text="Добре, чекаю від вас текст оголошення")
            await NewPost.text.set()

        if callback.data == "make_post_no_image":
            await bot.send_message(callback.message.chat.id, text="Добре, чекаю від вас текст оголошення")
            await NewTextPost.text.set()

        if callback.data == "show_client_info":
            message = callback.message
            await show_clients(message, bot)

        if "add_client_monthpayment/" in callback.data:
            client_id = await id_spliter(callback.data)
            await bot.send_message(callback.message.chat.id,
                                   f"Добре, пришліть мені ID клієнта. ID цього клієнта: {client_id}")
            await NewClientDiscount.client_id.set()

    except TypeError as error:
        await no_connection_with_server_notification(bot, callback.message)
    except Exception as error:
        await send_error_log(bot, 516842877, error)


@dp.message_handler(commands=['stop'], state='*')
async def cmd_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
    await message.reply('Ви успішно зупинили операцію.')

@dp.message_handler(content_types=['text'], state=NewProps.full_name)
async def new_props_fullname_state(message: types.Message, state: FSMContext):
    try:
        async with state.proxy() as data:
            data['full_name'] = message.text
        await bot.send_message(message.chat.id, "Чудово, тепер напишіть номер картки")
        await NewProps.next()
    except Exception as error:
        await bot.send_message(message.chat.id, "Нажаль, чомусь сталась помилка.")


@dp.message_handler(content_types=['text'], state=NewProps.card)
async def new_props_card_state(message: types.Message, state: FSMContext):
    try:
        async with state.proxy() as data:
            data['card'] = message.text

        data = await state.get_data()
        with open('props.json', 'w') as file:
            file.write(json.dumps(data, indent=4))

        await bot.send_message(message.chat.id, "Ваші реквізити успішно змінено")


    except Exception as error:
        await bot.send_message(message.chat.id, "Нажаль, чомусь сталась помилка.")
    finally:
        await state.finish()


@dp.message_handler(content_types=['text'], state=NewPaymentData.order_id)
async def new_payment_order_id_state(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['order_id'] = message.text
    await bot.send_message(message.chat.id, "Чудово, тепер відправте фото з оплатою замовлення")
    await NewPaymentData.next()


@dp.message_handler(content_types=["photo"], state=NewPaymentData.photo)
async def new_payment_photo_state(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if message.photo[0]:
            data['photo'] = message.photo[0].file_id

    data = await state.get_data()

    markup_i = types.InlineKeyboardMarkup()
    markup_i.add(get_order_info_button(data['order_id']))
    admin_text = f"Шановний адміністратор, створена оплата за замовлення №{data['order_id']}, показати його?"
    for admin in admin_list:
        await bot.send_photo(admin, photo=data['photo'], caption=admin_text, reply_markup=markup_i)
    await bot.send_message(message.chat.id, "Дякую. Очікуйте повідомлення про підтвердження замовлення")
    await state.finish()


@dp.message_handler(content_types=['text'], state=NewClientDiscount.client_id)
async def new_client_discount_state(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['client_id'] = message.text

    await bot.send_message(message.chat.id, "Тепер уведіть кількість")
    await NewClientDiscount.next()


@dp.message_handler(content_types=['text'], state=NewClientDiscount.count)
async def new_client_discount_state(message: types.Message, state: FSMContext):
    try:
        async with state.proxy() as data:
            data['count'] = message.text
        data = await state.get_data()
        response = await add_bonus_client_discount(client_id=data['client_id'], count=data['count'])
        if not response:
            return None
        if response["success"]:
            await bot.send_message(message.chat.id, f"Клієнту №{data['client_id']} було надано {data['count']} бонусів")
            await client_added_bonus_notifications(bot, data['client_id'])
        else:
            await bot.send_message(message.chat.id, response['error'])
    except Exception as error:
        await send_error_log(bot, 516842877, error)
    finally:
        await state.finish()



@dp.message_handler(content_types=['text'], state=NewTextPost.text)
async def new_no_phono_post(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text

    data = await state.get_data()
    await bot.send_message(message.chat.id, text="Ваше оголошення незабаром буде усім користувачам боту")
    visitors = await get_visitors()
    if visitors:
        for visitor in visitors:
            try:
                await bot.send_message(visitor['telegram_id'], data['text'])
            except Exception as error:
                await send_error_log(bot, 516842877, error)
    await state.finish()

@dp.message_handler(content_types=['text'], state=NewPost.text)
async def new_post_text_state(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
    await bot.send_message(message.chat.id, "А теперь пришліть фото оголошення")
    await NewPost.next()


@dp.message_handler(content_types=["photo"], state=NewPost.photo)
async def new_post_photo_state(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['photo'] = message.photo[0].file_id
    data = await state.get_data()
    await bot.send_message(message.chat.id, text="Ваше оголошення незабаром буде усім користувачам боту")
    visitors = await get_visitors()
    if visitors:
        for visitor in visitors:
            try:
                await bot.send_photo(chat_id=visitor['telegram_id'], photo=data['photo'], caption=data['text'])
            except Exception as error:
                await send_error_log(bot, 516842877, error)
    await state.finish()




@dp.message_handler(content_types=['text'], state=NewTTN.order_id)
async def order_state(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['order_id'] = message.text

    await message.reply(
        "<b>Дуже добре, зараз напишіть номер TTN. </b>\n\nЗверніть увагу, у разі помилки ви завжди зможете змінити ТTN замовлення")
    await NewTTN.next()


@dp.message_handler(content_types=['text'], state=NewTTN.ttn_state)
async def ttn_state(message: types.Message, state: FSMContext):
    try:
        async with state.proxy() as data:
            data['ttn_state'] = message.text

        data = await state.get_data()
        await state.finish()
        response = await update_ttn(data['order_id'], data['ttn_state'])
        if not response:
            return None
        if response['success']:
            order = await get_order_by_id(data['order_id'])
            await ttn_update_notification(bot, order)
            return await message.reply("Чудово, ви успішно оновили TTN замовлення")

        else:
            return await unknown_error_notifications(bot, message.chat.id)
    except Exception as error:
        await send_error_log(bot, 516842877, error)


async def update(_):
    asyncio.create_task(get_no_paid_orders(bot, admin_list))
    asyncio.create_task(order_updates(bot, admin_list))


executor.start_polling(dp, skip_updates=True, on_startup=update)
