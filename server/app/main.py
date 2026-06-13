# ==============================================================================
# MONKEYPATCH: Dynamically inject asyncio transport into the ASGI scope
# ==============================================================================
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ASGIAppWrapper:
    """Wraps the FastAPI app call to inject the low-level socket transport."""
    def __init__(self, app: Any, protocol_instance: Any) -> None:
        self.app = app
        self.protocol_instance = protocol_instance

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        # Inject the active socket transport directly into the connection scope
        if hasattr(self.protocol_instance, "transport"):
            scope["transport"] = self.protocol_instance.transport
        await self.app(scope, receive, send)


def make_patched_init(old_init: Any) -> Any:
    """Factory function to isolate scope and prevent cross-class contamination."""
    def new_init(self: Any, *args: Any, **kwargs: Any) -> None:
        old_init(self, *args, **kwargs)
        if hasattr(self, "app") and self.app is not None:
            # Wrap the application target in our dynamic scope injector
            self.app = ASGIAppWrapper(self.app, self)
    return new_init


def patch_uvicorn_protocols() -> None:
    """Safely intercepts and patches whatever Uvicorn protocol classes are present."""
    protocols_to_patch = []

    # Safely try to load standard HTTP 1.1 protocol
    try:
        from uvicorn.protocols.http.h11_impl import H11Protocol
        protocols_to_patch.append(H11Protocol)
    except ImportError:
        pass

    # Safely try to load high-performance HTTP protocol
    try:
        from uvicorn.protocols.http.httptools_impl import HttpToolsProtocol
        protocols_to_patch.append(HttpToolsProtocol)
    except ImportError:
        pass

    # Safely try to load default Websockets protocol
    try:
        from uvicorn.protocols.websockets.websockets_impl import WebSocketProtocol
        protocols_to_patch.append(WebSocketProtocol)
    except ImportError:
        pass

    # Safely try to load alternative Wsprotocols (resolved dynamically to keep type checker happy)
    try:
        import importlib
        wsproto_mod = importlib.import_module("uvicorn.protocols.websockets.wsproto_impl")
        wsproto_class = getattr(wsproto_mod, "WSProtoProtocol")
        protocols_to_patch.append(wsproto_class)
    except (ImportError, AttributeError):
        pass

    for protocol_class in protocols_to_patch:
        try:
            old_init = protocol_class.__init__
            # Bind old_init locally using our factory function
            protocol_class.__init__ = make_patched_init(old_init)
            logger.info(f"Successfully patched uvicorn protocol: {protocol_class.__name__}")
        except Exception as e:
            logger.error(f"Failed to patch uvicorn protocol {protocol_class.__name__}: {e}")


# Run the patcher during server module load
patch_uvicorn_protocols()
# ==============================================================================

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, status, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.core.database import init_db, get_db
from server.app.api.v1 import enroll
from server.app.services.signaling import signaling_manager
from server.app.api.v1 import auth
from server.app.api.v1.auth import get_current_user_session, templates


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Initialize SQLite database schema on startup
    await init_db()
    yield


app = FastAPI(
    title="SensiWatch Enterprise",
    description="Headless screen-monitoring platform backend",
    version="0.1.0",
    lifespan=lifespan
)

app.include_router(enroll.router, prefix="/api/v1", tags=["Enrollment"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])


@app.get("/", response_class=RedirectResponse)
async def root_redirect() -> RedirectResponse:
    """Redirect unauthenticated visitors to the login entrance."""
    return RedirectResponse(url="/api/v1/auth/login")


@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request) -> Response:
    """Renders the paginated active grid view for authenticated administrators."""
    username = get_current_user_session(request)
    if not username:
        return RedirectResponse(url="/api/v1/auth/login", status_code=status.HTTP_303_SEE_OTHER)
        
    return templates.TemplateResponse(request, "dashboard.html", {"username": username})


@app.websocket("/ws/signaling")
async def websocket_signaling_endpoint(
    websocket: WebSocket, 
    db: AsyncSession = Depends(get_db)
) -> None:
    """Persistent mTLS secured WebSocket signaling endpoint."""
    common_name = await signaling_manager.verify_and_register(websocket, db)
    if not common_name:
        return

    try:
        while True:
            # Read ASGI event dictionaries directly to support both bytes and text on one port
            data = await websocket.receive()
            
            # Explicitly catch ASGI disconnect events to trigger clean exit and db updates
            if data.get("type") == "websocket.disconnect":
                raise WebSocketDisconnect(code=data.get("code", 1000))
            
            if "bytes" in data:
                # Raw binary frame from client capture engine
                await signaling_manager.broadcast_thumbnail(common_name, data["bytes"])
            elif "text" in data:
                # Command / WebRTC signal
                # Update client heartbeat timestamp
                await signaling_manager.update_heartbeat(db, common_name)
                
    except WebSocketDisconnect:
        if common_name == "ADMIN":
            if websocket in signaling_manager.admin_listeners:
                signaling_manager.admin_listeners.remove(websocket)
        else:
            await signaling_manager.disconnect(common_name, db)