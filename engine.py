import json

from api import get_orders_by_tg_id, get_client_by_tg_id


def find_good(goods, good_id):
    for good in goods:
        if good["id"] == good_id:
            return good


async def base_client_info_builder(client):
    print(client)
    base_client_name = f"{client['name']} {client['last_name']}"
    base_client_phone = f"{client['phone']}"
    return f"<b>Данные клиента remonline:</b>\nФИО:{base_client_name}\nТелефон:{base_client_phone}\n\n"


async def manager_notes_builder(order, goods) -> dict:
    base_client = await get_client_by_tg_id(order['telegram_id'])
    base_client_info = await base_client_info_builder(base_client)

    name = f"{order['name']} {order['last_name']}"
    phone = f"{order['phone']}"
    address = f"{order['nova_post_address']}"
    prepayment = "Передплата" if order["prepayment"] == True else "Накладений платіж"
    goods_list = json.loads(order["goods_list"].replace("'", '"'))

    is_paid = "Нема даних"
    if order["prepayment"]:
        if order["is_paid"]:
            is_paid = "Сплачено"
        is_paid = "Не сплачено"

    goods_info = f"{base_client_info}<b>Дані замовлення:</b>\nФІО: {name}\nТелефон: {phone}\nАдреса: {address}\nТип платежу: {prepayment}\nСтатус оплаты:{is_paid}"

    if ttn := order['ttn']:
        goods_info += f"\nНомер ТТН: {ttn}"

    for obj in goods_list:
        good = find_good(goods["data"], obj['good_id'])
        goods_info += f"\n\nТовар: {good['title']} - Кількість: {obj['count']}"

    return {"text": goods_info, "client": base_client}


async def id_spliter(callback_data: str) -> int:
    """
    :param callback_data: delete_order/45
    :return: 45
    """

    return int(callback_data.rsplit('/')[-1])

async def ttn_info_builder(response: dict, order):
    text = ''
    if response["success"]:
        data = response['data'][0]
        text = f"<b>📮Інформація про посилку за номером: {data['Number']}</b>\n\n"
        print(response)
        text += f"<b>Cтатус: </b> {data['Status']}\n"
        text += f"<b>Фактична вага: </b> {data['FactualWeight']}\n"

        if not data['RecipientFullName']:
            text += f"<b>ПІБ отримувача: </b> {order['last_name']} {order['name']}\n"
        else:
            text += f"<b>ПІБ отримувача: </b> {data['RecipientFullName']}\n"

        text += f"<b>ПІБ відправника: </b> {data['SenderFullNameEW']}\n"
        text += f"<b>Адреса отримувача: </b> {data['CityRecipient']}, {data['WarehouseRecipient']}\n"
        text += f"<b>Адреса відправника: </b> {data['CitySender']}, {data['WarehouseSender']}\n"
        text += f"<b>Очікувана дата доставки: </b> {data['ScheduledDeliveryDate']}\n\n"
        if not data['RecipientDateTime']:
            text += f"<b>Дата отримання: </b> Немає даних\n"
        else:
            text += f"<b>Дата отримання: </b> {data['RecipientDateTime']}\n"
        text += f"<b>Вартість доставки: </b> {data['DocumentCost']}\n"
        text += f"<b>Оголошена вартість: </b> {data['AnnouncedPrice']}\n"
        if data['PaymentMethod'] == 'Cash':
            text += f"<b>Тип платежу: </b> передплата\n"
        else:
            text += f"<b>Тип платежу: </b> Накладний платіж\n"
        text += f"<b>Сума оплати по ЕН: </b> {data['ExpressWaybillAmountToPay']}\n"
        if data['ExpressWaybillPaymentStatus'] == "Payed":
            text += f"<b>Статус по ЕН: </b> Сплачено\n"
        else:
            text += f"<b>Статус по ЕН: </b> Потребує оплати\n"
        return text
    return "ПОМИЛКА"
