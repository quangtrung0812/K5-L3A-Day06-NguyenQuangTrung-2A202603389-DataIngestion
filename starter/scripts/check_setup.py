"""Read-only setup check; this is a utility, not the student pipeline solution."""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
url = os.getenv('DATABASE_URL')
if not url:
    sys.exit('DATABASE_URL missing: copy starter/.env.example to starter/.env first.')

QUERY = "SELECT current_database(), current_setting('server_version'), extversion FROM pg_extension WHERE extname = 'vector'"

row = None
try:
    import psycopg
    with psycopg.connect(url, connect_timeout=5) as connection:
        with connection.cursor() as cursor:
            cursor.execute(QUERY)
            row = cursor.fetchone()
except ImportError:
    import pg8000.dbapi
    parsed = urlparse(url)
    conn = pg8000.dbapi.connect(
        user=parsed.username,
        password=parsed.password,
        host=parsed.hostname or '127.0.0.1',
        port=parsed.port or 5432,
        database=(parsed.path or '/').lstrip('/'),
        timeout=5,
    )
    try:
        cursor = conn.cursor()
        cursor.execute(QUERY)
        row = cursor.fetchone()
    finally:
        conn.close()
except Exception as exc:
    sys.exit(f'Database connection failed ({exc}). Check Docker, port and DATABASE_URL in starter/.env.')

if not row:
    sys.exit('Connected, but pgvector extension is missing. See starter/README.md.')
print(f'Database: {row[0]} | PostgreSQL: {row[1]} | pgvector: {row[2]}')
print('Setup OK. Pipeline functions still need to be implemented.')

