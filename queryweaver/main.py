###
# Copyright (2023) Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
###

"""
CMF QueryWeaver Service

FastAPI service that wraps QueryWeaver to expose a natural language query
endpoint for the CMF MLMD PostgreSQL database.

Flow:
    CMF UI  →  CMF Backend (/nlp_query)  →  This service (/query)
            →  QueryWeaver library
            →  FalkorDB (schema graph + embeddings)
            →  Ollama (SQL generation)
            →  PostgreSQL MLMD database
"""

import asyncio
import os
import re
import logging
from contextlib import asynccontextmanager
from typing import Any, List, Optional

import asyncpg

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("cmf-queryweaver")

# ---------------------------------------------------------------------------
# Configuration from environment variables
# ---------------------------------------------------------------------------
FALKORDB_URL = os.getenv("FALKORDB_URL", "redis://falkordb:6379")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_USER = os.getenv("POSTGRES_USER", "myuser")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "mypassword")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "mlmd")
POSTGRES_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# COMPLETION_MODEL and EMBEDDING_MODEL are read directly by QueryWeaver from
# the process environment (e.g. ollama/mistral:7b, ollama/nomic-embed-text).

# ---------------------------------------------------------------------------
# Global state — QueryWeaver instance and active database connection id
# ---------------------------------------------------------------------------
qw_instance = None
db_connection_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Application lifespan — connect to MLMD database on startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global qw_instance, db_connection_id

    logger.info("Initializing QueryWeaver service ...")
    logger.info("FalkorDB URL : %s", FALKORDB_URL)
    logger.info("PostgreSQL   : %s@%s:%s/%s", POSTGRES_USER, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB)

    from queryweaver import QueryWeaver  # imported once at module level after dotenv

    max_attempts = 6
    backoff_seconds = [10, 20, 30, 40, 60]  # waits between retries

    for attempt in range(1, max_attempts + 1):
        try:
            qw_instance = QueryWeaver(falkordb_url=FALKORDB_URL)
            conn = await qw_instance.connect_database(POSTGRES_URL)
            db_connection_id = conn.database_id
            # connect_database swallows Ollama errors internally and returns
            # an empty database_id — treat that as a failure so we retry.
            if not db_connection_id:
                raise RuntimeError("connect_database returned empty database_id (Ollama may not be ready)")
            logger.info("QueryWeaver connected — database_id: %s", db_connection_id)
            break
        except Exception as exc:
            logger.error("QueryWeaver init attempt %d/%d failed: %s", attempt, max_attempts, exc)
            if attempt < max_attempts:
                wait = backoff_seconds[attempt - 1]
                logger.info("Retrying in %d seconds ...", wait)
                await asyncio.sleep(wait)
            else:
                logger.error("All %d init attempts failed — /query will return 503", max_attempts)

    yield

    if qw_instance is not None:
        try:
            await qw_instance.close()
            logger.info("QueryWeaver connection closed.")
        except Exception as exc:
            logger.warning("Error closing QueryWeaver: %s", exc)


# ---------------------------------------------------------------------------
# SQL correction helpers
# ---------------------------------------------------------------------------

def _fix_column_name(sql: str, error_msg: str) -> Optional[str]:
    """
    Ollama sometimes generates <table>_id (e.g. artifact_id) for primary key
    columns whose actual name is just 'id'.  The confusion comes from the
    sequence name artifact_id_seq appearing in the column default.

    If the error says 'column "<X>" does not exist' and X ends with _id,
    replace every occurrence of X in the SQL with 'id' and return the
    corrected SQL.  Returns None if no fix could be determined.
    """
    match = re.search(r'column "([^"]+)" does not exist', error_msg)
    if not match:
        return None
    wrong_col = match.group(1)
    if not wrong_col.endswith("_id"):
        return None
    fixed = re.sub(r'\b' + re.escape(wrong_col) + r'\b', 'id', sql)
    return fixed if fixed != sql else None


async def _execute_sql_direct(sql: str) -> List[dict]:
    """Execute SQL directly against PostgreSQL and return rows as a list of dicts."""
    conn = await asyncpg.connect(
        host=POSTGRES_HOST,
        port=int(POSTGRES_PORT),
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB,
    )
    try:
        rows = await conn.fetch(sql)
        return [dict(r) for r in rows]
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="cmf-queryweaver",
    description="Natural language query service for CMF MLMD database",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    sql_query: str
    results: Any
    ai_response: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    """Liveness / readiness probe."""
    return {
        "status": "ok",
        "db_connected": bool(db_connection_id),
        "database_id": db_connection_id or "",
    }


@app.post("/query", response_model=QueryResponse)
async def natural_language_query(request: QueryRequest):
    """
    Accept a natural language question, generate SQL via QueryWeaver / Ollama,
    execute it against the MLMD PostgreSQL database, and return the results.
    """
    if qw_instance is None or db_connection_id is None:
        raise HTTPException(
            status_code=503,
            detail="QueryWeaver is not connected to the database. Check service logs.",
        )

    logger.info("Received NL query: %s", request.question)

    try:
        result = await qw_instance.query(db_connection_id, request.question)
        logger.info("Generated SQL: %s", result.sql_query)

        ai_resp = result.ai_response or ""
        sql = result.sql_query or ""
        rows = result.results

        # If QueryWeaver returned a column-not-found error, try to auto-correct
        # the SQL (e.g. artifact_id → id) and re-execute directly.
        if "does not exist" in ai_resp and sql:
            fixed_sql = _fix_column_name(sql, ai_resp)
            if fixed_sql:
                logger.info("Auto-correcting SQL: %s → %s", sql, fixed_sql)
                try:
                    rows = await _execute_sql_direct(fixed_sql)
                    sql = fixed_sql
                    ai_resp = ""
                    logger.info("Corrected SQL executed successfully, %d rows", len(rows))
                except Exception as fix_exc:
                    logger.error("Corrected SQL also failed: %s", fix_exc)
                    # fall through and return the original error

        return QueryResponse(
            sql_query=sql,
            results=rows,
            ai_response=ai_resp,
        )
    except Exception as exc:
        logger.error("Query failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
