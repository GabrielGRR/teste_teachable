import os
import random
from datetime import date, datetime, timedelta
import pandas as pd

# Constants
random.seed(30)

START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 12, 31)

PRODUCTS_ID = list(range(5000, 5026))

PRODUCER_ID = {
    1001: list(range(5000, 5011)),
    1002: list(range(5011, 5016)),
    1003: list(range(5016, 5021)),
    1004: list(range(5021, 5025)),
    1005: list(range(5025, 5026)),
}

BUYER_ID = list(range(10000, 99999))

PRODUCT_PRICE = 50.0
PARTITION = 1
N_PURCHASES = 7000

SUBSIDIARIES = ["nacional", "internacional"]


def producer_from_product(product_id):
    for producer_id, products in PRODUCER_ID.items():
        if product_id in products:
            return producer_id
    raise ValueError(product_id)


def random_date():
    days = (END_DATE - START_DATE).days
    return START_DATE + timedelta(days=random.randint(0, days))


def lake_timestamp(base_date):
    dt = datetime.combine(base_date, datetime.min.time())
    dt += timedelta(
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    return dt


def get_buyer_id(purchase_id, existing_buyers):
    if purchase_id % 20 == 0 and existing_buyers:
        return random.choice(existing_buyers)
    buyer_id = random.choice(BUYER_ID)
    existing_buyers.append(buyer_id)
    return buyer_id


def determine_purchase_status(order_date):
    status_bucket = random.random()
    if status_bucket < 0.30:
        return "INICIADA", None
    elif status_bucket < 0.70:
        return "APROVADA", order_date + timedelta(days=random.randint(0, 5))
    elif status_bucket < 0.90:
        return "CANCELADA", None
    else:
        return "REEMBOLSADA", order_date + timedelta(days=random.randint(0, 5))


def generate_single_purchase_flow(purchase_id, buyer_id):
    product_id = random.choice(PRODUCTS_ID)
    prod_item_id = purchase_id
    producer_id = producer_from_product(product_id)

    qty = random.randint(1, 6)
    total_value = PRODUCT_PRICE * qty

    order_date = random_date()
    final_status, release_date = determine_purchase_status(order_date)

    # Initial event timestamp
    event_time = lake_timestamp(order_date)

    purchase_events = []
    purchase_events.append({
        "purchase_id": purchase_id,
        "buyer_id": buyer_id,
        "prod_item_id": prod_item_id,
        "order_date": order_date,
        "release_date": None,
        "producer_id": producer_id,
        "purchase_partition": PARTITION,
        "prod_item_partition": PARTITION,
        "purchase_total_value": total_value,
        "purchase_status": "INICIADA",
        "transaction_datetime": event_time,
        "transaction_date": event_time.date()
    })

    if final_status != "INICIADA":
        event_time_2 = event_time + timedelta(minutes=random.randint(1, 20))
        purchase_events.append({
            "purchase_id": purchase_id,
            "buyer_id": buyer_id,
            "prod_item_id": prod_item_id,
            "order_date": order_date,
            "release_date": release_date,
            "producer_id": producer_id,
            "purchase_partition": PARTITION,
            "prod_item_partition": PARTITION,
            "purchase_total_value": total_value,
            "purchase_status": final_status,
            "transaction_datetime": event_time_2,
            "transaction_date": event_time_2.date()
        })

    product_item_event = {
        "prod_item_id": prod_item_id,
        "prod_item_partition": PARTITION,
        "product_id": product_id,
        "item_quantity": qty,
        "purchase_value": PRODUCT_PRICE,
        "transaction_datetime": event_time,
        "transaction_date": event_time.date()
    }

    purchase_extra_event = {
        "purchase_id": purchase_id,
        "purchase_partition": PARTITION,
        "subsidiary": random.choice(SUBSIDIARIES),
        "transaction_datetime": event_time,
        "transaction_date": event_time.date()
    }

    cost_event = {
        "purchase_id": purchase_id,
        "purchase_partition": PARTITION,
        "order_transaction_cost_vat_value": round(total_value * 0.12, 2),
        "order_transaction_cost_installment_value": round(total_value * 0.03, 2),
        "order_transaction_cost_date": order_date,
        "transaction_datetime": event_time,
        "transaction_date": event_time.date()
    }

    return purchase_events, product_item_event, purchase_extra_event, cost_event


def generate_data():
    print(f"Iniciando a geração de dados. Total planejado: {N_PURCHASES} compras base.")
    
    purchase_rows = []
    product_item_rows = []
    purchase_extra_rows = []
    cost_rows = []

    existing_buyers = []

    for purchase_id in range(1, N_PURCHASES + 1):
        buyer_id = get_buyer_id(purchase_id, existing_buyers)
        
        p_events, p_item, p_extra, p_cost = generate_single_purchase_flow(purchase_id, buyer_id)
        
        purchase_rows.extend(p_events)
        product_item_rows.append(p_item)
        purchase_extra_rows.append(p_extra)
        cost_rows.append(p_cost)

        # Print de progresso a cada 20% do total
        if purchase_id % (N_PURCHASES // 5) == 0:
            pct = int((purchase_id / N_PURCHASES) * 100)
            print(f"  Progresso: {pct}% concluído ({purchase_id}/{N_PURCHASES} compras)...")

    print("\nGeração concluída. Montando DataFrames...")
    purchase_df = pd.DataFrame(purchase_rows)
    product_item_df = pd.DataFrame(product_item_rows)
    purchase_extra_df = pd.DataFrame(purchase_extra_rows)
    cost_df = pd.DataFrame(cost_rows)

    print(f"Resumo da geração:")
    print(f"  - purchase: {len(purchase_df)} linhas (inclui históricos de status)")
    print(f"  - product_item: {len(product_item_df)} linhas")
    print(f"  - purchase_extra: {len(purchase_extra_df)} linhas")
    print(f"  - cost: {len(cost_df)} linhas")

    return purchase_df, product_item_df, purchase_extra_df, cost_df


def save_data(purchase_df, product_item_df, purchase_extra_df, cost_df):
    # Save outputs to mock_user_data directory relative to script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "mock_user_data")
    os.makedirs(output_dir, exist_ok=True)

    print(f"\nSalvando arquivos CSV em: {output_dir} ...")
    
    purchase_df.to_csv(os.path.join(output_dir, "purchase.csv"), index=False)
    product_item_df.to_csv(os.path.join(output_dir, "product_item.csv"), index=False)
    purchase_extra_df.to_csv(os.path.join(output_dir, "purchase_extra_info.csv"), index=False)
    cost_df.to_csv(os.path.join(output_dir, "order_transaction_cost_hist.csv"), index=False)

    print("Todos os arquivos foram gravados com sucesso!")


if __name__ == "__main__":
    purchase_df, product_item_df, purchase_extra_df, cost_df = generate_data()
    save_data(purchase_df, product_item_df, purchase_extra_df, cost_df)
