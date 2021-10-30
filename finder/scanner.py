from ipaddress import ip_address
from mcstatus import MinecraftServer
from db import init_db, Server

import logging
import asyncio
import time
import os

MAX_TASKS = 10  # Max async tasks
MIN_IP = int(ip_address("1.0.0.0"))
MAX_IP = int(ip_address("223.225.225.225"))
IP_RANGE = MAX_IP - MIN_IP

DELAY_PER_IP = 0.2  # seconds
RUN_INFINITELY = False  # Set this to true if you want scanner to auto-restart after it's done with all IPs
TRIES = 3


logging.basicConfig(
    format="%(asctime)s %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level="DEBUG",
)
logger = logging.getLogger("finder")
current_ip: int = 0
ips_scanned = 0


if os.name == "nt":
    # Setting event loop policy since asyncio crashes
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def scan_ip(ip: str):
    server = MinecraftServer.lookup(ip)

    try:
        status = await server.async_status(tries=TRIES)
    except Exception as e:
        if type(e) not in [asyncio.TimeoutError, OSError, ConnectionRefusedError, ConnectionResetError]:
            logger.debug(
                f"Did not get a response from {ip}. Reason: {type(e).__name__}"
            )
        return

    logger.info(f"Got response from {ip}. Latency: {int(status.latency)}ms")
    updated_at = int(time.time())  # Unix epoch

    existing_server = await Server.filter(
        ip=ip
    ).get_or_none()  # Returns None if server exists in DB

    if existing_server:
        logger.info(f"{ip} has already been scanned, not scanning again..")
        return

    payload = {
        "ip": ip,
        "description": status.description,
        "latency": status.latency,
        "version": status.version.name,
        "players_max": status.players.max,
        "players_online": status.players.online,
        "updated_at": updated_at,
    }

    await Server.create(**payload)


async def handle_ip_chunk(task_num: int, _min: int, _max: int):
    global current_ip, ips_scanned
    logger.debug(f"Scanner {task_num} has been spawned")

    for ip_num in range(_min, _max):
        ip = str(ip_address(ip_num))

        await scan_ip(ip)

        ips_scanned += 1
        await asyncio.sleep(DELAY_PER_IP)


async def run_scanner_tasks():
    logger.info(
        f"Searching {IP_RANGE:,} IPs... Starting from: {str(ip_address(MIN_IP))}"
    )
    logger.info("Spawning tasks")

    # Chunking all IPs into multiple parts and creating tasks
    ips_per_task, remaining = divmod(IP_RANGE, MAX_TASKS)
    current_interval = 0
    for task_number in range(MAX_TASKS):
        min_range = current_interval + MIN_IP

        current_interval += ips_per_task
        if remaining:
            current_interval += 1
            remaining -= 1
        if task_number + 1 == MAX_TASKS:
            current_interval += 1

        max_range = current_interval + MIN_IP

        asyncio.create_task(
            handle_ip_chunk(task_number, min_range, max_range)
        ).set_name(f"Scanner process {task_number}")

    await asyncio.gather(*asyncio.all_tasks() - {asyncio.current_task()})


async def main():
    global ips_scanned
    await init_db()

    if RUN_INFINITELY:
        logger.info(
            "RUN_INFINITELY has been set to True. Scanner will keep running until stopped"
        )
        while True:
            ips_scanned = 0
            await run_scanner_tasks()
    else:
        logger.info(
            "RUN_INFINITELY has been set to False. Scanner will run once and then exit"
        )
        await run_scanner_tasks()


def run_scanner():
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Stopping...")
        logger.info(f"IPs scanned: {ips_scanned:,}. Last scanned IP: {current_ip}")

        # Cleaning up async tasks
        try:
            # Sometimes raises "no running event loop"
            tasks = asyncio.gather(*asyncio.all_tasks(), return_exceptions=True)
            tasks.cancel()
        except Exception as ex:
            logger.error(str(ex))
        finally:
            loop.stop()
