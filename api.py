import aiohttp
import config

base_url = config.TEST_URL


async def get_all_goods():
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(f'{base_url}api/v1/goods', ssl=False) as resp:
            if resp.status == 200:
                return await resp.json()


async def get_orders_by_tg_id(telegram_id) -> list:
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(f'{base_url}api/v1/getorder/{telegram_id}', ssl=False) as resp:
            if resp.status == 200:
                return await resp.json()


async def get_order_by_id(order_id):
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(f'{base_url}api/v1/getorderbyid/{order_id}', ssl=False) as resp:
            if resp.status == 200:
                return await resp.json()


async def get_active_orders() -> list:
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(f'{base_url}api/v1/activeorders', ssl=False) as resp:
            if resp.status == 200:
                return await resp.json()


async def get_visitors() -> list:
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(f'{base_url}api/v1/visitors', ssl=False) as resp:
            if resp.status == 200:
                return await resp.json()


async def add_new_visitor(telegram_id) -> dict:
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.post(f'{base_url}api/v1/AddNewVisitor/{telegram_id}', json={"telegram_id": telegram_id,}, ssl=False) as resp:
            print(telegram_id)
            if resp.status == 200:
                return await resp.json()


async def check_auth(telegram_id):
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(f'{base_url}api/v1/isauthendicated/{telegram_id}', ssl=False) as resp:
            if resp.status == 200:
                return await resp.json()


async def get_discount(client_id):
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(f'{base_url}api/v1/monthdiscount/{client_id}', ssl=False) as resp:
            if resp.status == 200:
                return await resp.json()


async def get_discounts_info():
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(f'{base_url}api/v1/alldiscounts/', ssl=False) as resp:
            if resp.status == 200:
                return await resp.json()


async def post_discount(procent, month_payment):
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.post(f'{base_url}api/v1/discount/',
                                json={"procent": procent, "month_payment": month_payment}, ssl=False) as resp:
            if resp.status == 200:
                return await resp.json()


async def delete_order(order_id):
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.delete(f'{base_url}api/v1/deleteorder/{order_id}', ssl=False) as resp:
            if resp.status == 200:
                return await resp.json()


async def delete_discount(discount_id):
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.delete(f'{base_url}api/v1/discount/{discount_id}', ssl=False) as resp:
            if resp.status == 200:
                return await resp.json()


async def update_ttn(order_id, ttn):
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.patch(f'{base_url}api/v1/updatettn/',
                                 json={"order_id": order_id, "ttn": ttn}, ssl=False) as resp:
            if resp.status == 200:
                return await resp.json()


async def finish_order(order_id):
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.patch(f'{base_url}api/v1/disactiveorder/{order_id}', ssl=False) as resp:
            if resp.status == 200:
                return await resp.json()


async def no_paid_along_time():
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(f'{base_url}api/v1/no-paid-along-time/', ssl=False) as resp:
            if resp.status == 200:
                return await resp.json()


async def get_order_by_ttn(ttn):
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(f'{base_url}api/v1/orderbyttn/{ttn}', ssl=False) as resp:
            if resp.status == 200:
                return await resp.json()


async def ttn_tracking(ttn, recipient_phone):
    async with aiohttp.ClientSession(trust_env=True) as session:
        request = {
            "apiKey": config.NOVA_POST_API_KEY,
            "modelName": "TrackingDocument",
            "calledMethod": "getStatusDocuments",
            "methodProperties": {
                "Documents": [
                    {
                        "DocumentNumber": ttn,
                        "Phone": recipient_phone
                    }
                ]
            }
        }

        async with session.post('https://api.novaposhta.ua/v2.0/json/', json=request, ssl=False) as resp:
            if resp.status == 200:
                return await resp.json()


async def get_client_by_tg_id(telegram_id):
    return await check_auth(telegram_id)
