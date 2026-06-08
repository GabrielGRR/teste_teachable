import os
import random
from datetime import datetime, timedelta
import pandas as pd
from utils.logging_utils import get_logger, setup_logging

logger = get_logger(__name__)

# Constants (Config)
random.seed(30)

PRODUCTS_ID = list(range(5001, 5026))

PRODUCER_ID = {
    1001: list(range(5001, 5011)),
    1002: list(range(5011, 5016)),
    1003: list(range(5016, 5021)),
    1004: list(range(5021, 5025)),
    1005: list(range(5025, 5026)),
}

BUYER_ID = list(range(10000, 99999))

PRODUCT_PRICE = 50.0
N_PURCHASES = 7000

SUBSIDIARIES = ["nacional", "internacional"]


def producer_from_product(product_id):
    for producer_id, products in PRODUCER_ID.items():
        if product_id in products:
            return producer_id
    raise ValueError(product_id)


def random_date(START_DATE, END_DATE):
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


def CDC_apply_duplicity(purchase_events, product_item_events, purchase_extra_events):
    # Duplicate every event exactly
    purchase_events.extend([dict(ev) for ev in purchase_events])
    product_item_events.extend([dict(ev) for ev in product_item_events])
    purchase_extra_events.extend([dict(ev) for ev in purchase_extra_events])


def CDC_apply_correction(purchase_events, product_item_events, purchase_extra_events, product_id, prod_item_id, order_date):
    # Retrieve the last events to get current state
    last_p = purchase_events[-1]
    last_item = product_item_events[-1]
    
    original_qty = last_item["item_quantity"]
    new_qty = random.choice([q for q in range(1, 7) if q != original_qty])
    
    last_time = last_p["transaction_datetime"]
    correction_time = last_time + timedelta(hours=random.randint(1, 5))

    new_total_value = PRODUCT_PRICE * new_qty
    
    corr_p = dict(last_p)
    corr_p.update({
        "purchase_total_value": new_total_value,
        "transaction_datetime": correction_time,
        "transaction_date": correction_time.date()
    })
    purchase_events.append(corr_p)
    
    corr_item = dict(last_item)
    corr_item.update({
        "item_quantity": new_qty,
        "purchase_value": PRODUCT_PRICE,
        "transaction_datetime": correction_time,
        "transaction_date": correction_time.date()
    })
    product_item_events.append(corr_item)


def CDC_apply_late_arrival(purchase_events, product_item_events, purchase_extra_events, order_date, release_date):
    # Determine the latest business date to base delay on
    dates_to_compare = [order_date]
    if release_date is not None:
        dates_to_compare.append(release_date)
    max_business_date = max(dates_to_compare)
    
    # transaction_date must be between 1 and 15 days greater than the max business date
    delay_days = random.randint(1, 15)
    new_date = max_business_date + timedelta(days=delay_days)
    
    # Build a delayed datetime
    new_time = datetime.combine(new_date, datetime.min.time()) + timedelta(
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59)
    )
    
    # Delay the initial INICIADA event of the purchase
    purchase_events[0]["transaction_datetime"] = new_time
    purchase_events[0]["transaction_date"] = new_date
    
    # Delay the initial event of extra_info table
    purchase_extra_events[0]["transaction_datetime"] = new_time
    purchase_extra_events[0]["transaction_date"] = new_date


def generate_single_purchase_flow(START_DATE, END_DATE, purchase_id, buyer_id):
    prod_item_id = purchase_id
    product_id = random.choice(PRODUCTS_ID)
    producer_id = producer_from_product(product_id)

    qty = random.randint(1, 6)
    total_value = PRODUCT_PRICE * qty

    order_date = random_date(START_DATE, END_DATE)
    final_status, release_date = determine_purchase_status(order_date)

    # Initial event timestamp
    event_time = lake_timestamp(order_date)

    partition = int(order_date.strftime("%Y%m"))

    def make_purchase_event(status, ts, rel_date):
        return {
            "purchase_id": purchase_id,
            "buyer_id": buyer_id,
            "prod_item_id": prod_item_id,
            "order_date": order_date,
            "release_date": rel_date,
            "producer_id": producer_id,
            "purchase_partition": partition,
            "prod_item_partition": partition,
            "purchase_total_value": total_value,
            "purchase_status": status,
            "transaction_datetime": ts,
            "transaction_date": ts.date(),
        }

    def next_event_time(ts):
        return ts + timedelta(minutes=random.randint(1, 20))

    purchase_events = [make_purchase_event("INICIADA", event_time, None)]

    if final_status != "INICIADA":
        event_time_2 = next_event_time(event_time)

        # REEMBOLSADA must go through APROVADA first
        if final_status == "REEMBOLSADA":
            purchase_events.append(make_purchase_event("APROVADA", event_time_2, release_date))
            purchase_events.append(make_purchase_event("REEMBOLSADA", next_event_time(event_time_2), release_date))
        else:
            purchase_events.append(make_purchase_event(final_status, event_time_2, release_date))

    product_item_events = [{
        "prod_item_id": prod_item_id,
        "prod_item_partition": partition,
        "product_id": product_id,
        "item_quantity": qty,
        "purchase_value": PRODUCT_PRICE,
        "transaction_datetime": event_time,
        "transaction_date": event_time.date()
    }]

    purchase_extra_events = [{
        "purchase_id": purchase_id,
        "purchase_partition": partition,
        "subsidiary": random.choice(SUBSIDIARIES),
        "transaction_datetime": event_time,
        "transaction_date": event_time.date()
    }]

    # CDC Scenario decision (20% of purchases)
    scenario_type = None
    if random.random() < 0.20:
        cdc_bucket = random.random()
        if cdc_bucket < 0.25:
            scenario_type = "Duplicidade"
            CDC_apply_duplicity(purchase_events, product_item_events, purchase_extra_events)
        elif cdc_bucket < 0.50:
            scenario_type = "Correção Histórica"
            CDC_apply_correction(purchase_events, product_item_events, purchase_extra_events, product_id, prod_item_id, order_date)
        else:
            scenario_type = "Evento Fora de Ordem"
            CDC_apply_late_arrival(purchase_events, product_item_events, purchase_extra_events, order_date, release_date)

    return purchase_events, product_item_events, purchase_extra_events, scenario_type


def generate_data(START_DATE, END_DATE):
    logger.info(f"Iniciando a geração de dados. Total planejado: {N_PURCHASES} compras base.")
    
    purchase_rows = []
    product_item_rows = []
    purchase_extra_rows = []

    existing_buyers = []
    
    # Track scenario distributions for confirmation logs
    scenario_counts = {
        "Duplicidade": 0,
        "Correção Histórica": 0,
        "Evento Fora de Ordem": 0
    }

    for purchase_id in range(1, N_PURCHASES + 1):
        buyer_id = get_buyer_id(purchase_id, existing_buyers)
        
        p_events, p_items, p_extras, scenario_type = generate_single_purchase_flow(START_DATE, END_DATE, purchase_id, buyer_id)
        
        purchase_rows.extend(p_events)
        product_item_rows.extend(p_items)
        purchase_extra_rows.extend(p_extras)

        if scenario_type:
            scenario_counts[scenario_type] += 1

        # Print de progresso a cada 20% do total
        if purchase_id % (N_PURCHASES // 5) == 0:
            pct = int((purchase_id / N_PURCHASES) * 100)
            logger.info(f"  Progresso: {pct}% concluído ({purchase_id}/{N_PURCHASES} compras)...")

    logger.info("Geração concluída. Montando DataFrames...")
    purchase_df = pd.DataFrame(purchase_rows)
    product_item_df = pd.DataFrame(product_item_rows)
    purchase_extra_df = pd.DataFrame(purchase_extra_rows)

    total_mutations = sum(scenario_counts.values())
    logger.info(f"Resumo da geração:")
    logger.info(f"  - purchase: {len(purchase_df)} linhas")
    logger.info(f"  - product_item: {len(product_item_df)} linhas")
    logger.info(f"  - purchase_extra: {len(purchase_extra_df)} linhas")
    logger.info(f"Distribuição de cenários CDC aplicados (Total: {total_mutations} compras afetadas, ~{total_mutations/N_PURCHASES*100:.1f}%):")
    for scen, count in scenario_counts.items():
        pct = (count / total_mutations * 100) if total_mutations > 0 else 0.0
        logger.info(f"  - {scen}: {count} ({pct:.1f}%)")

    return purchase_df, product_item_df, purchase_extra_df


def save_data(purchase_df, product_item_df, purchase_extra_df):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "../data/bronze")
    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"Salvando arquivos CSV em: {output_dir} ...")
    
    purchase_df.to_csv(os.path.join(output_dir, "purchase.csv"), index=False)
    product_item_df.to_csv(os.path.join(output_dir, "product_item.csv"), index=False)
    purchase_extra_df.to_csv(os.path.join(output_dir, "purchase_extra_info.csv"), index=False)

    logger.info("Todos os arquivos foram gravados com sucesso!")


def main(START_DATE, END_DATE):
    setup_logging()

    purchase_df, product_item_df, purchase_extra_df = generate_data(START_DATE, END_DATE)
    save_data(purchase_df, product_item_df, purchase_extra_df)


if __name__ == "__main__":
    main()