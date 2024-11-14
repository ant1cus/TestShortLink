from fastapi import FastAPI
from database import create_tables, delete_tables
from router import router as link_router
from contextlib import asynccontextmanager
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    await delete_tables()
    print('База очищена')
    await create_tables()
    print("База готова к работе")
    yield
    print("Выключение")

app = FastAPI(lifespan=lifespan)
app.include_router(link_router)

if __name__ == '__main__':
    uvicorn.run(app, port=3000, host='localhost', log_config=f'./log.ini')