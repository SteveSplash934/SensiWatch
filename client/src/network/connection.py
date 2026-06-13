import asyncio
import ssl
import logging
from typing import Optional, Any
from websockets.asyncio.client import connect, ClientConnection

from client.src.core.storage import get_cert_dir

logger = logging.getLogger(__name__)


class MTLSWebSocketClient:
    """
    Handles persistent, mTLS-secured connection states to the parent server.
    Ensures safe reconnection and certificate injection.
    """

    def __init__(self, server_ws_url: str):
        self.server_ws_url = server_ws_url
        self.cert_dir = get_cert_dir()
        self.key_path = self.cert_dir / "client_key.pem"
        self.cert_path = self.cert_dir / "client_cert.pem"
        self.websocket: Optional[ClientConnection] = None

    def _build_ssl_context(self) -> ssl.SSLContext:
        """Configures mTLS SSLContext with generated certificate keys."""
        if not self.key_path.exists() or not self.cert_path.exists():
            raise FileNotFoundError("mTLS client credentials are not initialized. Please run bootstrap first.")

        # Create context configured strictly for mTLS client authorization
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        
        # Load local signed certificates
        ssl_context.load_cert_chain(
            certfile=self.cert_path,
            keyfile=self.key_path
        )
        
        # Disable hostname verification for self-signed local server certs
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        return ssl_context

    async def connect_and_listen(self, daemon: Any) -> None:
        """
        Establishes and maintains the persistent WebSocket connection.
        Spawns the thumbnail streaming task concurrently while connected.
        """
        ssl_context = self._build_ssl_context()
        logger.info(f"Attempting mTLS WebSocket handshake to {self.server_ws_url}...")

        try:
            # Using the modern 13+ asyncio connect context manager
            async with connect(
                self.server_ws_url,
                ssl=ssl_context,
                ping_interval=20,
                ping_timeout=20
            ) as websocket:
                self.websocket = websocket
                logger.info("Persistent mTLS WebSocket connection established.")

                # Spawn the client's screen capturing loop concurrently
                thumbnail_task = asyncio.create_task(daemon.stream_thumbnails(websocket))

                try:
                    # Keep connection alive and process incoming packets
                    async for message in websocket:
                        logger.debug(f"Received signaling packet: {message}")
                        # WebRTC packets will be routed here in Step 3.3
                finally:
                    # Automatically cancel streaming task if connection drops
                    thumbnail_task.cancel()

        except Exception as e:
            logger.error(f"WebSocket connection encountered an error: {e}")
            self.websocket = None