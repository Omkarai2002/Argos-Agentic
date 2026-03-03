import socketio
import asyncio
import logging
from typing import Dict, Any
import uuid
import signal

# Import your real mission generator
from app.prompt_run import MissionEngine  # <-- your existing function


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ArgosMissionClient")


class ArgosMissionClient:
    """
    WebSocket client that:
    - Connects to Argos
    - Receives mission prompts
    - Runs mission planning using main()
    - Sends mission plan back
    """

    def __init__(
        self,
        url: str,
        token: str,
        max_concurrent_jobs: int = 5
    ):
        self.url = url
        self.token = token

        # Async Socket.IO client
        self.sio = socketio.AsyncClient(
            reconnection=True,
            reconnection_attempts=0,   # infinite retries
            reconnection_delay=1,
            reconnection_delay_max=5,
        )
        self.engine=MissionEngine()
        # Limit concurrent mission processing
        self.semaphore = asyncio.Semaphore(max_concurrent_jobs)

        self._register_handlers()

    # ---------------------------------------------------
    # SAFE WRAPPER FOR YOUR SYNC main()
    # ---------------------------------------------------

    async def run_mission_logic(self, data: Dict[str, Any]):
        """
        Runs your synchronous main(data, validated)
        safely inside a thread pool.
        """

        validated = {
            "db_record_id": None,
            "user_id": data["user_id"],
            "site_id": data["site_id"],
            "org_id": data["org_id"],
            "prompt": data["prompt"],
        }

        loop = asyncio.get_running_loop()

        # Run blocking code in background thread
        result = await loop.run_in_executor(
            None,
            self.engine.main,
            data,
            validated
        )

        return result

    # ---------------------------------------------------
    # Connection Lifecycle
    # ---------------------------------------------------

    async def connect(self):
        try:
            await self.sio.connect(
                self.url,
                auth={"token": self.token},
                transports=["websocket"],
            )
            logger.info("Connected to Argos")
        except Exception:
            logger.exception("Connection failed")

    async def stop(self):
        await self.sio.disconnect()
        logger.info("Disconnected gracefully")

    async def start(self):
        await self.connect()
        await self.sio.wait()

    # ---------------------------------------------------
    # Event Handlers
    # ---------------------------------------------------

    def _register_handlers(self):

        @self.sio.event
        async def connect():
            logger.info("Socket connected")

        @self.sio.event
        async def disconnect():
            logger.warning("Socket disconnected")

        @self.sio.event
        async def connect_error(data):
            logger.error(f"Connection error: {data}")

        # 🔥 Core handler
        @self.sio.on("mission:prompt")
        async def handle_prompt(data: Dict[str, Any]):
            """
            Expected payload from Argos:
            {
                request_id,
                user_id,
                org_id,
                site_id,
                prompt
            }
            """

            logger.info(f"Received mission prompt: {data}")

            async with self.semaphore:

                request_id = data.get("request_id", str(uuid.uuid4()))

                try:
                    mission_json = await self.run_mission_logic(data)

                    response_payload = {
                        "request_id": request_id,
                        "status": "success",
                        "mission": mission_json
                    }

                    await self.sio.emit("mission:plan_create", response_payload)

                    logger.info(f"Mission plan sent for {request_id}")

                except Exception as e:
                    logger.exception("Mission planning failed")

                    error_payload = {
                        "request_id": request_id,
                        "status": "error",
                        "message": str(e)
                    }

                    await self.sio.emit("mission:error", error_payload)


# ---------------------------------------------------
# Graceful Shutdown
# ---------------------------------------------------

async def main_entry():
    client = ArgosMissionClient(
        url="http://localhost:8000",  # change when Argos is deployed
        token="SERVICE_TOKEN",
        max_concurrent_jobs=5
    )

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def shutdown():
        logger.info("Shutdown signal received")
        stop_event.set()

    loop.add_signal_handler(signal.SIGINT, shutdown)
    loop.add_signal_handler(signal.SIGTERM, shutdown)

    await client.connect()

    wait_task = asyncio.create_task(client.sio.wait())
    stop_task = asyncio.create_task(stop_event.wait())

    await asyncio.wait(
        [wait_task, stop_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    await client.stop()


if __name__ == "__main__":
    asyncio.run(main_entry())