import aiohttp
import config

baseurl = "http://127.0.0.1:8000/"




async def get_all_goods():
    async with aiohttp.ClientSession() as session:
        async with session.get('http://127.0.0.1:8000/api/v1/goods') as resp:
            if resp.status == 200:
                return await resp.json()


async def get_orders_by_tg_id(telegram_id):
    async with aiohttp.ClientSession() as session:
        async with session.get(f'http://127.0.0.1:8000/api/v1/getorder/{telegram_id}') as resp:
            if resp.status == 200:
                return await resp.json()


