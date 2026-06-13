import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from server.app.core.database import get_db
from server.app.database.models import EnrollmentToken
from server.app.core.security.ca_engine import EmbeddedCA

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize the CA Engine to store keys in a local ca_storage dir
ca_engine = EmbeddedCA(ca_dir=Path("ca_storage"))

class EnrollRequest(BaseModel):
    token: str
    csr: str

class EnrollResponse(BaseModel):
    certificate: str

@router.post("/enroll", response_model=EnrollResponse)
async def enroll_client(
    request: EnrollRequest, 
    db: AsyncSession = Depends(get_db)
) -> EnrollResponse:
    """
    Exchange a one-time enrollment token + CSR for a signed mTLS certificate.
    """
    # 1. Fetch token from SQLite
    query = select(EnrollmentToken).where(EnrollmentToken.token_value == request.token)
    result = await db.execute(query)
    db_token = result.scalar_one_or_none()

    # 2. Strict Validation Check
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid enrollment token."
        )
    
    if db_token.is_used:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token has already been used."
        )
        
    # Database timezone normalization (safely handles SQLite's naive datetime representation)
    token_expiry = db_token.expires_at
    if token_expiry.tzinfo is None:
        token_expiry = token_expiry.replace(tzinfo=timezone.utc)

    # Timezone-aware expiration check
    if token_expiry < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token has expired."
        )

    # 3. Mark Token as Consumed (Burn it)
    db_token.is_used = True
    await db.commit()

    # 4. Sign the CSR using the Embedded CA
    try:
        cert_pem = ca_engine.sign_client_csr(request.csr.encode("utf-8"))
    except ValueError as e:
        logger.error(f"CSR Validation Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid Certificate Signing Request."
        )
    except Exception as e:
        logger.error(f"CA Engine Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal CA Error."
        )

    return EnrollResponse(certificate=cert_pem.decode("utf-8"))