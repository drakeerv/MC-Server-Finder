from tortoise import Tortoise
from .models import Server

import os
import logging


async def init_db():
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    host = os.environ["POSTGRES_HOST"]
    port = os.environ["POSTGRES_PORT"]
    database = os.environ["POSTGRES_DB"]

    await Tortoise.init(
        db_url=f"postgres://{user}:{password}@{host}:{port}/{database}",
        modules={"models": ["db.models"]},
    )

    logging.info("Connected to PostgreSQL")

    # Generate schema
    await Tortoise.generate_schemas()
