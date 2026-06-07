# Mock Data Generator — CDC Pipeline (Teachable Technical Case)

## 📋 Arquitetura em Camadas

1. **Config**: Definição de constantes globais e regras de negócio de tempo/valores.
2. **Factory**: Fábrica da compra base (`make_purchase`).
3. **Scenarios**: 3 cenários de alteração de dados CDC.
4. **Orchestrator**: Controle do status e decisão de qual cenário aplicar para acumular os eventos.
5. **Tables**: Montagem dos DataFrames e exportação dos arquivos CSV.

---

## 1. ⚙️ Configurações Globais (Config)

- Adicionar um ruído de até 20 minutos entre transações.
- **Parâmetros de Data**:
  - `START_DATE` = `2026-01-01`
  - `END_DATE` = `2026-12-31`
- **Identificadores (IDs)**:
  - `PRODUCTS_ID` = `[5000, ..., 5025]` (26 produtos)
  - `PRODUCER_ID` = Mapeamento de produtores para faixas de IDs de produtos:
    - `1001`: `5000` a `5010`
    - `1002`: `5011` a `5015`
    - `1003`: `5016` a `5020`
    - `1004`: `5021` a `5024`
    - `1005`: `5025`
  - `BUYER_ID` = `[10000, ..., 99999]`
- **Preços e Quantidades**:
  - `PRODUCTS_PRICE` = `50`
  - `ITEM_QUANTITY` <= `6`
- **Partições e Volumes**:
  - `PARTITION` = `1` (todos os campos de partição fixados com valor `1` para respeitar o schema)
  - `N_PURCHASES` = `7000` compras base (resultando em cerca de `10000` eventos CDC finais)
- **Categorias e Opções**:
  - `SUBSIDIARIES` = `["nacional", "internacional"]`
  - `PURCHASE_STATUS` = `["INICIADA", "APROVADA", "CANCELADA", "REEMBOLSADA"]`

---

## 2. 🛍️ Entidade Compra (Purchase)

- Deve seguir rigorosamente o schema estrutural fornecido.

---

## 3. 🔄 Cenários de Alteração (Scenario)

O banco de dados deve conter aproximadamente **10.000 eventos**, onde **20% das compras** devem receber um comportamento CDC adicional:

| Cenário | Distribuição | Comportamento Esperado |
| :--- | :---: | :--- |
| **I. Duplicidade** | 25% | Apenas duplicar o evento, sem alterar nenhum valor. |
| **II. Correção Histórica** | 25% | Alterar `purchase_total_value`, `purchase_value` e `item_quantity`. Gerar novo evento mantendo o mesmo `purchase_id`. |
| **III. Evento Fora de Ordem (Late Arrival)** | 50% | Manter o mesmo `purchase_id`. A data `transaction_datetime` deve ser posterior à data do evento de negócio. A data `transaction_date` deve ser entre 1 e 15 dias maior que: `order_date`, `release_date` ou `order_transaction_cost_date`. O evento deve chegar ao lake depois de outros eventos mais recentes da mesma compra. |

---

## 4. 🔀 Orquestrador de Estados (Orchestrator)

As compras base devem ser distribuídas nas seguintes taxas de status final:

- **30%** permanecem como `INICIADA`
- **40%** terminam como `APROVADA`
- **20%** terminam como `CANCELADA`
- **10%** terminam como `REEMBOLSADA`

> [!IMPORTANT]
> Todas as compras com status final `APROVADA`, `CANCELADA` e `REEMBOLSADA` devem ter obrigatoriamente evoluído a partir do status inicial `INICIADA`.

---

## 5. 📊 Estrutura das Tabelas (Tables)

O gerador deve exportar **4 arquivos CSV** simulando as tabelas extraídas via CDC:

### 🔹 Tabela: `purchase`
- `purchase_id` deve ser único na criação da compra base.
- `buyer_id` deve seguir os limites de `BUYER_ID`. A cada 20 registros, deve repetir aleatoriamente algum `buyer_id` já existente.
- `prod_item_id` deve seguir a lógica de `PRODUCTS_ID` aleatoriamente.
- `producer_id` deve ser determinado a partir do `product_id` correspondente.
- `purchase_status` deve seguir as proporções definidas pelo **Orchestrator**.
- `transaction_datetime` e `transaction_date` devem seguir as regras de data e cenários CDC (ex: Cenário III).
- Múltiplos registros com o mesmo `purchase_id` podem ser gerados pelos cenários CDC.
- `release_date` deve ser preenchido apenas para compras aprovadas ou reembolsadas.
- `transaction_datetime` representa o momento exato em que o evento foi inserido no lake.
- `item_quantity`: valor aleatório entre 1 e 6.
- `purchase_total_value`: calculado como `PRODUCT_PRICE * item_quantity`.

### 🔹 Tabela: `product_item`
- Deve possuir integridade referencial com `purchase.prod_item_id`.
- O valor unitário `purchase_value` é fixo em `PRODUCT_PRICE`.
- Cenários de alteração CDC podem gerar múltiplos registros para o mesmo `prod_item_id`.

### 🔹 Tabela: `purchase_extra_info`
- Deve possuir integridade referencial com `purchase.purchase_id`.
- O campo `subsidiary` deve ser escolhido aleatoriamente de `SUBSIDIARIES`.
- Cenários CDC podem gerar eventos duplicados ou atrasados.

### 🔹 Tabela: `order_transaction_cost_hist`
- Deve possuir integridade referencial com `purchase.purchase_id`.
- Os valores devem representar as taxas e custos associados à transação de compra.
- Pode receber eventos atrasados (*late arrival*).