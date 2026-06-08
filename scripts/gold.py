from datetime import date
import duckdb

from utils.logging_utils import get_logger, setup_logging
from utils import PATH_DB_FILE, PATH_SILVER_DIR, PATH_GOLD_DIR

logger = get_logger(__name__)

DB_FILE    = PATH_DB_FILE
GOLD_DIR   = PATH_GOLD_DIR
SILVER_DIR = PATH_SILVER_DIR

GOLD_DIR.mkdir(parents=True, exist_ok=True)


def load_silver(conn: duckdb.DuckDBPyConnection) -> None:
    silver_file = (SILVER_DIR / "purchase_clean.parquet").as_posix()
    conn.execute(f"""
        CREATE OR REPLACE TABLE purchase_clean AS
        SELECT * FROM read_parquet('{silver_file}')
    """)
    logger.info("Silver carregada em memória")


def compute_daily_gmv(conn: duckdb.DuckDBPyConnection, start_date: date, end_date: date) -> None:
    conn.execute(f"""
        CREATE OR REPLACE TABLE daily_gmv AS

        SELECT
            release_date              AS date,
            subsidiary,
            SUM(purchase_total_value) AS gmv

        FROM purchase_clean
        WHERE
            release_date IS NOT NULL
            AND purchase_status != 'CANCELADA'
            AND release_date BETWEEN '{start_date}' AND '{end_date}'

        GROUP BY
            release_date,
            subsidiary

        ORDER BY
            release_date,
            subsidiary
    """)
    count = conn.execute("SELECT COUNT(*) FROM daily_gmv").fetchone()[0]
    logger.info(f"daily_gmv computada: {count} linhas ({start_date} → {end_date})")


def export_daily_gmv(conn: duckdb.DuckDBPyConnection) -> None:
    dates = conn.execute("""
        SELECT DISTINCT date FROM daily_gmv ORDER BY 1
    """).fetchall()

    exported = 0
    skipped  = 0

    for (dt,) in dates:
        partition_dir = GOLD_DIR / str(dt)

        if partition_dir.exists():
            skipped += 1
            continue

        partition_dir.mkdir(parents=True, exist_ok=True)
        output_file = partition_dir / "data.parquet"

        conn.execute(f"""
            COPY (
                SELECT * FROM daily_gmv
                WHERE date = '{dt}'
            )
            TO '{output_file.as_posix()}' (FORMAT PARQUET)
        """)
        exported += 1

    logger.info(f"Gold exportada: {exported} dias novos | {skipped} dias já existentes (skipped)")


def main(start_date: date, end_date: date) -> None:
    setup_logging()
    
    conn = duckdb.connect(DB_FILE)

    load_silver(conn)
    compute_daily_gmv(conn, start_date, end_date)
    export_daily_gmv(conn)

    conn.close()
    logger.info("Gold criada com sucesso")


if __name__ == "__main__":
    main()