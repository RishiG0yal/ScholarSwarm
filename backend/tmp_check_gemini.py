import asyncio
import sys
sys.path.append('.')
from services.llm import llm_service

async def main():
    try:
        print('client init...')
        c = llm_service.client
        print('client', type(c))
        res = await llm_service.generate(prompt='Say hello', system_instruction='You are a test assistant.')
        print('response', res[:100])
    except Exception as e:
        print(type(e).__name__, e)

asyncio.run(main())
