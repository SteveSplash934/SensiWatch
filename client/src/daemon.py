import argparse
import asyncio
import enum
import logging
import platform
import signal
import sys
import time

from client.src.core.storage import get_cert_dir
from client.src.network.bootstrap import run_bootstrap
from client.src.network.connection import MTLSWebSocketClient

logger = logging.getLogger(__name__)


class DaemonState(enum.StrEnum):
    UNINITIALIZED = "UNINITIALIZED"
    BOOTSTRAPPING = "BOOTSTRAPPING"
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    STOPPED = "STOPPED"


class SensiWatchDaemon:
    """
    Central background client daemon operating as a finite state machine.
    Manages client identity, silent auto-reconnections, and WebRTC signalling hooks.
    """

    def __init__(self, server_url: str, ws_url: str, token: str | None = None):
        self.server_url = server_url
        self.ws_url = ws_url
        self.token = token
        self.state = DaemonState.UNINITIALIZED
        self.ws_client = MTLSWebSocketClient(self.ws_url)
        self._running = False
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 60.0

    async def start(self) -> None:
        """Main execution loop of the daemon state machine."""
        self._running = True
        logger.info("SensiWatch Daemon execution started.")
        while self._running:
            await self._transition_and_execute()

    def stop(self) -> None:
        """Gracefully halts the daemon."""
        logger.info("SensiWatch Daemon stopping...")
        self._running = False
        self.state = DaemonState.STOPPED

    async def _transition_and_execute(self) -> None:
        """Structural pattern matching router for FSM execution."""
        match self.state:
            case DaemonState.UNINITIALIZED:
                await self._handle_uninitialized()
            case DaemonState.BOOTSTRAPPING:
                await self._handle_bootstrapping()
            case DaemonState.DISCONNECTED:
                await self._handle_disconnected()
            case DaemonState.CONNECTING:
                await self._handle_connecting()
            case DaemonState.CONNECTED:
                # The CONNECTED logic is blocking inside the websockets loop.
                # If we ever land back here, we yield execution.
                await asyncio.sleep(1) 
            case DaemonState.STOPPED:
                self._running = False

    async def _handle_uninitialized(self) -> None:
        """Inspects disk to determine if we possess a verified identity."""
        cert_dir = get_cert_dir()
        key_path = cert_dir / "client_key.pem"
        cert_path = cert_dir / "client_cert.pem"

        if key_path.exists() and cert_path.exists():
            logger.info("Local mTLS credentials validated. Transitioning to DISCONNECTED.")
            self.state = DaemonState.DISCONNECTED
        else:
            if self.token:
                logger.info("Local credentials missing. Transitioning to BOOTSTRAPPING.")
                self.state = DaemonState.BOOTSTRAPPING
            else:
                logger.critical("Fatal: No local credentials found and no bootstrap token provided.")
                self.stop()

    async def _handle_bootstrapping(self) -> None:
        """Runs the one-time registration handshake to obtain local certificates."""
        logger.info("Executing bootstrap identity acquisition...")
        if not self.token:
            logger.error("Bootstrap failed: Missing token configuration.")
            self.state = DaemonState.UNINITIALIZED
            return

        success = await run_bootstrap(self.token, self.server_url)
        if success:
            logger.info("Bootstrap identity acquired successfully. Transitioning to DISCONNECTED.")
            self.state = DaemonState.DISCONNECTED
        else:
            logger.warning("Bootstrap execution failed. Retrying in 10 seconds...")
            await asyncio.sleep(10)

    async def _handle_disconnected(self) -> None:
        """Handles offline back-off sleep intervals before retrying connection."""
        logger.info(f"Offline. Retrying connection in {self._reconnect_delay:.1f}s...")
        await asyncio.sleep(self._reconnect_delay)
        self.state = DaemonState.CONNECTING

    async def _handle_connecting(self) -> None:
        """Attempts mTLS handshakes and handles silent exponential back-off."""
        logger.info("Attempting secure mTLS connection to signaling host...")
        start_time = time.time()
        
        try:
            self.state = DaemonState.CONNECTED
            # Blocks here while the websocket connection is actively alive
            await self.ws_client.connect_and_listen()
            logger.warning("mTLS socket connection closed cleanly.")
        except Exception as e:
            logger.error(f"mTLS Connection attempt failed: {e}")

        # Calculate the stability of the connection
        connection_duration = time.time() - start_time
        self.state = DaemonState.DISCONNECTED
        
        # Exponential back-off algorithm
        if connection_duration > 15.0:
            # Connection was stable; reset back-off to baseline immediately
            self._reconnect_delay = 1.0
            logger.info("Resetting exponential back-off delay after stable connection duration.")
        else:
            # Connection was unstable/failed; double back-off up to max ceiling
            self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)


async def main_async() -> None:
    parser = argparse.ArgumentParser(description="SensiWatch Enterprise Daemon")
    parser.add_argument("--server", default="http://127.0.0.1:8000", help="Server HTTP API URL")
    parser.add_argument("--ws", default="ws://127.0.0.1:8000/ws/signaling", help="Server WebSocket WS URL")
    parser.add_argument("--token", help="One-time bootstrap enrollment token")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    daemon = SensiWatchDaemon(server_url=args.server, ws_url=args.ws, token=args.token)

    # Cross-platform signal wrapping
    loop = asyncio.get_running_loop()
    if platform.system() != "Windows":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, daemon.stop)

    try:
        await daemon.start()
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        daemon.stop()


def main() -> None:
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()