Mock Data Generator — CDC Pipeline (Teachable Technical Case)
=============================================================

Camadas:
    1. config        — constantes globais
    2. factory       — fábrica da compra base (make_purchase)
    3. scenarios     — 3 tipos de cenários de alteração dos dados
    4. orchestrator  — decide qual cenário aplicar e acumula eventos
    5. tables        — monta DataFrames e exporta CSVs

1. Config:

- Adicionar um ruído de até 20 minutos entre transações

- START_DATE   = date(2026, 1, 1)
- END_DATE     = date(2026, 12, 31)
- PRODUCTS_ID = list(range(5_000, 5_026))
- PRODUCER_ID = {1_001: list(range(5_000, 5_011)), 
                 1_002: list(range(5_011, 5_016)), 
                 1_003: list(range(5_016, 5_021)), 
                 1_004: list(range(5_021, 5_025)), 
                 1_005: list(range(5_025, 5_026))}
- BUYER_ID = list(range(10_000, 99_999))
- PRODUCTS_PRICE = 50
- PARTITION = 1
- ITEM_QUANTITY <= 6

- N_PURCHASES  = 7_000          # compras-base; eventos CDC totais ficam em torno de 10.000

- SUBSIDIARIES = ["nacional", "internacional"]
- PURCHASE_STATUS = ['INICIADA', 'APROVADA', 'CANCELADA', 'REEMBOLSADA']

2. Purchase:

- Deve seguir o schema em anexo

3. Scenario:

o BD deve ter algo em torno de 10.000 eventos, sendo que 20% das compras devem receber um comportamento CDC adicional:

I. Duplicidade           : 25%,
II. Correção histórica   : 25%,
III. Evento fora de ordem: 50%,

O que mudar nos comportamentos:
I. Duplicidade:
Apenas duplicar, sem alterar nenhum valor.

II. Correção histórica:
- Alterar purchase_total_value
- Alterar purchase_value correspondente
- Alterar item_quantity correspondente
- Gerar novo evento
- Manter purchase_id

III. Evento fora de ordem / late arrival:

- Manter purchase_id.
- transaction_datetime deve ser posterior à data do evento de negócio.
- transaction_date deve ser entre 1 e 15 dias maior que:
    - order_date, ou
    - release_date, ou
    - order_transaction_cost_date
- O evento deve chegar ao lake depois de outros eventos mais recentes da mesma compra.

4. ORCHESTRATOR:
As compras devem ser divididas em 4 categorias de status:

- 30% permanecem INICIADA
- 40% terminam em APROVADA
- 20% terminam em CANCELADA
- 10% terminam em REEMBOLSADA

- Todas as compras APROVADA, CANCELADA e REEMBOLSADA devem ter sido evoluidas de INICIADA

5. TABLES:

O gerador deve produzir 4 arquivos CSV simulando as tabelas CDC do ambiente:

- tabela purchase
    - purchase_id deve ser único na criação da compra base.
    - buyer_id deve seguir a referência lógica do escopo BUYER_ID
        - A cada 20 registros, deve repetir aleatoriamente algum buyer já existente
    - prod_item_id deve seguir a lógica de PRODUCTS_ID, de forma aleatória
    - producer_id deve ser determinado a partir do product_id.
    - purchase_status deve seguir a lógica do ORCHESTRATOR
    - transaction_datetime e transaction_date deve seguir as regras do cenário III.
    - Cenários CDC podem gerar múltiplos registros para o mesmo purchase_id.
    - release_date deve existir apenas para compras aprovadas ou reembolsadas.
    - transaction_datetime representa o momento em que o evento foi inserido no lake.
    - item_quantity: deve ser aleatório de 1 a 6
    - purchase_total_value: PRODUCT_PRICE * item_quantity
- tabela product_item
    - Deve existir correspondência com purchase.prod_item_id.
    - purchase_value sempre será igual a PRODUCT_PRICE.
    - Cenários CDC podem gerar múltiplos registros para o mesmo prod_item_id.
- tabela purchase_extra_info
    - Deve existir correspondência com purchase.purchase_id.
    - subsidiary deve ser escolhida entre: nacional, internacional.
    - Cenários CDC podem gerar eventos duplicados ou atrasados.
- tabela order_transaction_cost_hist
    - Deve existir correspondência com purchase.purchase_id.
    - Valores devem representar taxas e custos da compra.
    - Pode receber eventos atrasados (late arrival).

- Consultar SCHEMA fornecido para os itens acima.

- Todos os campos de "partição" serão fixados com valor 1.
- O campo é mantido apenas para respeitar o schema fornecido.