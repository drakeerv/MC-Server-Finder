from ipaddress import ip_address
from mcstatus import MinecraftServer

import logging
import asyncio
import time
import json
import aiofiles

MAX_TASKS = 10  # Max async tasks
MIN_IP = int(ip_address("1.0.0.0"))
MAX_IP = int(ip_address("223.225.225.225"))
IP_RANGE = MAX_IP - MIN_IP


logging.basicConfig(
    format="%(asctime)s %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level="DEBUG",
)
logger = logging.getLogger("finder")
current_ip: int = 0
ips_scanned = 0


try:
    json_db: dict = json.loads(open("./findings.json", "r").read())
except FileNotFoundError:
    with open("./findings.json", "w") as f:  # Creates json file
        f.write("{}")
    json_db = {}


async def scan_ip(ip: str):
    server = MinecraftServer.lookup(ip)

    try:
        status = await server.async_status()
    except Exception as e:
        if e not in [asyncio.exceptions.TimeoutError, OSError]:
            logger.debug(
                f"Did not get a response from {ip}. Reason: {type(e).__name__}"
            )
        return

    logger.info(f"Got response from {ip}. Latency: {int(status.latency)}ms")
    updated_at = int(time.time())  # Unix epoch

    payload = {
        "updated_at": updated_at,
        "version": {"name": status.version.name, "protocol": status.version.protocol},
        "description": status.description,
        "latency": status.latency,
        "players": {
            "max": status.players.max,
            "online": status.players.online,
            "players": [{"id": i.id, "name": i.name} for i in status.players.sample]
            if type(status.players.sample) == type([])
            else None,
        },
    }

    try:
        # Sometimes this thing times out
        query = await server.async_query()
        payload.update(
            {
                "software": {
                    "version": query.software.version,
                    "plugins": query.software.plugins,
                    "brand": query.software.brand,
                },
                "motd": query.motd,
            }
        )
    except Exception as e:
        logger.error(f"Query failed for {ip}, moving on. Reason: {type(e).__name__}")

    return payload


async def handle_ip_chunk(task_num: int, _min: int, _max: int):
    global json_db, current_ip, ips_scanned
    logger.debug(f"Scanner {task_num} has been spawned")

    for ip_num in range(_min, _max):
        ip = str(ip_address(ip_num))
        current_ip = ip

        if ip in json_db:
            logger.info(f"{ip} has already been scanned, not scanning again..")
            return

        payload = await scan_ip(ip)

        if not payload:
            continue

        json_db[ip] = payload

        async with aiofiles.open("./findings.json", mode="w") as f:
            await f.write(json.dumps(json_db, indent=4))

        ips_scanned = ips_scanned + 1
        await asyncio.sleep(0.2)


async def main():
    logger.info(
        f"Searching {IP_RANGE:,} IPs... Starting from: {str(ip_address(MIN_IP))}"
    )

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


if __name__ == "__main__":
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