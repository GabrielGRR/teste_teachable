import duckdb

from utils.logging_utils import get_logger, setup_logging
from utils import PATH_DB_FILE, PATH_SILVER_DIR, PATH_BRONZE_DIR

logger = get_logger(__name__)

DB_FILE    = PATH_DB_FILE
SILVER_DIR = PATH_SILVER_DIR
BRONZE_DIR = PATH_BRONZE_DIR

SILVER_DIR.mkdir(parents=True, exist_ok=True)

def load_bronze(conn: duckdb.DuckDBPyConnection) -> None:
    tables = {
        "purchase":            "purchase.csv",
        "product_item":        "product_item.csv",
        "purchase_extra_info": "purchase_extra_info.csv",
    }

    for table_name, filename in tables.items():
        csv_path = (BRONZE_DIR / filename).as_posix()
        conn.execute(f"""
            CREATE OR REPLACE TABLE {table_name} AS
            SELECT * FROM read_csv_auto('{csv_path}')
        """)
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        logger.info(f"Bronze carregada: {table_name} ({count} linhas)")

def create_purchase_clean(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(f"""
        CREATE OR REPLACE TABLE purchase_clean AS

        WITH purchase_dedup AS (
            SELECT *
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY purchase_id, purchase_partition
                           ORDER BY transaction_datetime DESC
                       ) AS rn
                FROM purchase
            )
            WHERE rn = 1
        ),

        product_item_dedup AS (
            SELECT *
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY prod_item_id, prod_item_partition
                           ORDER BY transaction_datetime DESC
                       ) AS rn
                FROM product_item
            )
            WHERE rn = 1
        ),

        purchase_extra_info_dedup AS (
            SELECT *
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY purchase_id, purchase_partition
                           ORDER BY transaction_datetime DESC
                       ) AS rn
                FROM purchase_extra_info
            )
            WHERE rn = 1
        )

        SELECT
            p.purchase_id,
            p.buyer_id,
            p.producer_id,

            p.prod_item_id,

            p.order_date,
            p.release_date,

            p.purchase_status,
            p.purchase_total_value,

            pi.product_id,
            pi.item_quantity,
            pi.purchase_value,

            pei.subsidiary,

            p.transaction_datetime,
            p.transaction_date

        FROM purchase_dedup p

        LEFT JOIN product_item_dedup pi
            ON p.prod_item_id = pi.prod_item_id
           AND p.prod_item_partition = pi.prod_item_partition

        LEFT JOIN purchase_extra_info_dedup pei
            ON p.purchase_id = pei.purchase_id
           AND p.purchase_partition = pei.purchase_partition
    """)

    logger.info(f"Tabela purchase_clean criada com sucesso: {conn.execute('SELECT COUNT(*) FROM purchase_clean').fetchone()[0]} linhas")


def export_purchase_clean(conn: duckdb.DuckDBPyConnection) -> None:
    output_file = SILVER_DIR / "purchase_clean.parquet"

    conn.execute(f"""
        COPY purchase_clean
        TO '{output_file.as_posix()}'
        (FORMAT PARQUET)
    """)

    logger.info(f"Tabela purchase_clean exportada com sucesso: {output_file}")


def main() -> None:
    setup_logging()

    conn = duckdb.connect(DB_FILE)
    load_bronze(conn)
    create_purchase_clean(conn)
    export_purchase_clean(conn)

    conn.close()


if __name__ == "__main__":
    main()