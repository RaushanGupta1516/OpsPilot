from prisma import Prisma
from app.core.config import settings

db = Prisma()


async def connect_db():
    await db.connect()
    print(f"[db] connected to postgres")


async def disconnect_db():
    await db.disconnect()
    print(f"[db] disconnected")