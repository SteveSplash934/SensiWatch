import datetime
import hashlib
import logging
from typing import Dict, Optional
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from server.app.database.models import CertificateCRL
from server.app.database.crud import update_monitor_presence, update_monitor_heartbeat

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active, mTLS-verified WebSocket signaling connections."""

    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}  # common_name -> WebSocket

    async def verify_and_register(self, websocket: WebSocket, db: AsyncSession) -> Optional[str]:
        """
        Extracts mTLS credentials, validates them against the CRL,
        registers the socket, and marks the node "Online" in SQLite [2].
        """
        transport = websocket.scope.get("extensions", {}).get("transport") or websocket.scope.get("transport")
        if not transport:
            logger.error("Rejecting connection: No underlying transport layer detected.")
            return None

        ssl_object = transport.get_extra_info("ssl_object")
        if not ssl_object:
            logger.error("Rejecting connection: mTLS handshake was not completed.")
            return None

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
            logger.error("Rejecting connection: Client certificate missing 'commonName' attribute.")
            return None

        # Verify against Revocation List (CRL) in SQLite
        query = select(CertificateCRL).where(CertificateCRL.fingerprint == fingerprint)
        result = await db.execute(query)
        revoked_entry = result.scalar_one_or_none()

        if revoked_entry:
            logger.critical(f"Security Alert: Revoked certificate [{fingerprint}] attempted connection.")
            return None

        # Accept connection and update state to Online
        await websocket.accept()
        self.active_connections[common_name] = websocket
        
        # Use common_name as both CN and hostname for the initial entry
        await update_monitor_presence(db, common_name, common_name, "Online")
        
        logger.info(f"Node verified and marked ONLINE. CN: {common_name}")
        return common_name

    async def disconnect(self, common_name: str, db: AsyncSession) -> None:
        """Deregisters client node and marks them "Offline" [2]."""
        if common_name in self.active_connections:
            del self.active_connections[common_name]
        
        # Keep entry but update state to Offline
        await update_monitor_presence(db, common_name, common_name, "Offline")
        logger.info(f"Node marked OFFLINE: {common_name}")

    async def update_heartbeat(self, db: AsyncSession, common_name: str) -> None:
        """Updates timestamp during alive ping loops."""
        await update_monitor_heartbeat(db, common_name)


signaling_manager = ConnectionManager()