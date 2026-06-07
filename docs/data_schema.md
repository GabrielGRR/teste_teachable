# purchase

| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| purchase_id | bigint | identificador da compra |
| buyer_id | bigint | identificador do comprador |
| prod_item_id | bigint | identificador do item de compra |
| order_date | date | data do pedido de compra |
| release_date | date | data de liberação da compra mediante a confirmação do pagamento |
| producer_id | bigint | identificador do produtor |
| purchase_partition | bigint | partição no lake para a compra |
| prod_item_partition | bigint | partição no lake para o item de compra |
| purchase_total_value | float | valor total da compra |
| purchase_status | string | status da compra: INICIADA, APROVADA, CANCELADA, REEMBOLSADA |
| transaction_datetime | datetime | momento de inserção do dado no lake |
| transaction_date | date | data de inserção do dado no lake |

# order_transaction_cost_hist

| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| purchase_id | bigint | identificador da compra |
| purchase_partition | bigint | partição no lake para a compra |
| order_transaction_cost_vat_value | float | valor VAT referente a compra |
| order_transaction_cost_installment_value | float | valor do parcelamento da compra |
| order_transaction_cost_date | date | data da efetivação do parcelamento |
| transaction_datetime | datetime | momento de inserção do dado no lake |
| transaction_date | date | data de inserção do dado no lake |

# product_item

| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| prod_item_id | bigint | identificador do item de compra |
| prod_item_partition | bigint | partição no lake para o item da compra |
| product_id | bigint | identificador do produto |
| item_quantity | int | quantidade comprada por item |
| purchase_value | float | valor do item de compra |
| transaction_datetime | datetime | momento de inserção do dado no lake |
| transaction_date | date | data de inserção do dado no lake |

# purchase_extra_info

| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| purchase_id | bigint | identificador da compra |
| purchase_partition | bigint | partição no lake para a compra |
| subsidiary | string | Empresa que, embora controlada (dirigida) por outra, possui grande parte ou o total de suas ações |
| transaction_datetime | datetime | momento de inserção do dado no lake |
| transaction_date | date | data de inserção do dado no lake |

# Relacionamentos

* `purchase.prod_item_id < product_item.prod_item_id`
* `purchase.prod_item_partition < product_item.prod_item_partition`
* `order_transaction_cost_hist.purchase_id > purchase.purchase_id`
* `order_transaction_cost_hist.purchase_partition > purchase.purchase_partition`
* `purchase_extra_info.purchase_id > purchase.purchase_id`
* `purchase_extra_info.purchase_partition > purchase.purchase_partition`