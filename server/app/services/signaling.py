import base64
import datetime
import hashlib
import logging
from typing import Dict, List, Optional
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from server.app.database.models import CertificateCRL
from server.app.database.crud import update_monitor_presence, update_monitor_heartbeat

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active mTLS client connections and active admin UI dashboard listeners."""

    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}  # common_name -> Client WebSocket
        self.admin_listeners: List[WebSocket] = []         # Active browser UI connections

    async def verify_and_register(self, websocket: WebSocket, db: AsyncSession) -> Optional[str]:
        """
        Registers connection. If mTLS certificate is present, it is marked as a client.
        Otherwise, registers as an admin UI listener.
        """
        transport = websocket.scope.get("extensions", {}).get("transport") or websocket.scope.get("transport")
        ssl_object = transport.get_extra_info("ssl_object") if transport else None

        # If a client cert is present, register as an mTLS Client Node
        if ssl_object and ssl_object.getpeercert():
            try:
                der_cert = ssl_object.getpeercert(binary_form=True)
                peercert = ssl_object.getpeercert()
                
                fingerprint = hashlib.sha256(der_cert).hexdigest()

                subject = peercert.get("subject", ())
                common_name = None
                for rdn in subject:
                    for name, value in rdn:
                        if name == "commonName":
                            common_name = value
                            break
            except Exception as e:
                logger.error(f"Failed to parse TLS peer certificate: {e}")
                return None

            if not common_name:
                logger.error("Rejecting connection: Client certificate missing 'commonName'.")
                return None

            # Verify against CRL
            query = select(CertificateCRL).where(CertificateCRL.fingerprint == fingerprint)
            result = await db.execute(query)
            revoked_entry = result.scalar_one_or_none()

            if revoked_entry:
                logger.critical(f"Security Alert: Revoked certificate [{fingerprint}] blocked.")
                return None

            # Accept client
            await websocket.accept()
            self.active_connections[common_name] = websocket
            await update_monitor_presence(db, common_name, common_name, "Online")
            logger.info(f"Client node registered and marked ONLINE: {common_name}")
            return common_name

        # If no certificate, treat as Admin UI Listener (handshake done over HTTP Cookie/Session)
        else:
            await websocket.accept()
            self.admin_listeners.append(websocket)
            logger.info("Admin dashboard UI registered as a listener.")
            return "ADMIN"

    async def disconnect(self, common_name: str, db: AsyncSession) -> None:
        """Deregisters client node and marks them Offline."""
        if common_name in self.active_connections:
            del self.active_connections[common_name]
        
        await update_monitor_presence(db, common_name, common_name, "Offline")
        logger.info(f"Client node marked OFFLINE: {common_name}")

    async def update_heartbeat(self, db: AsyncSession, common_name: str) -> None:
        """Refreshes client heartbeat in the database."""
        await update_monitor_heartbeat(db, common_name)

    async def broadcast_thumbnail(self, common_name: str, image_bytes: bytes) -> None:
        """Encodes raw JPEG bytes to Base64 and broadcasts to all active dashboard listeners."""
        if not self.admin_listeners:
            return

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        payload = {
            "event": "thumbnail",
            "common_name": common_name,
            "image": b64_image
        }
        
        # Dispatch to all listening admin UI frames concurrently
        dead_links = []
        for admin in self.admin_listeners:
            try:
                await admin.send_json(payload)
            except Exception:
                dead_links.append(admin)

        # Cleanup disconnected admin connections
        for dead in dead_links:
            if dead in self.admin_listeners:
                self.admin_listeners.remove(dead)


signaling_manager = ConnectionManager()