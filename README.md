# **Teachable Data Engineer – Technical Case**

## Summary

- [Architecture](#architecture)
- [Final Table](#final-table)
- [Quickstart](#quickstart)
- [Project Structure](#project-structure)
- [Data Issues Handled](#data-issues-handled)
- [Pipeline – Daily Run (D-1)](#pipeline--daily-run-d-1)
- [Possible Improvements](#possible-improvements)
- [Observations](#observations)

## **Overview**

Este projeto implementa um pipeline de dados baseado em **CDC (Change Data Capture)** para simular um cenário de ingestão de eventos em um data lake e permitir o cálculo de **GMV (Gross Merchandising Value)** diário por subsidiária.

O pipeline cobre:
- Geração de dados sintéticos com eventos **CDC**
- Simulação de inconsistências reais na camada bronze (duplicação, correções, late arrival)
- Estruturação de **arquitetura medalhão** (Bronze, Silver, Gold)
- Base para construção de camada analítica (GMV por dia e subsidiária)

---

## **Architecture**

```
    Arquitetura Medalhão: 
    Bronze (CSV)  →  Silver (Parquet)  →  Gold (Parquet particionado)
```

| Camada | Descrição |
|--------|-----------|
| **Bronze** | Ingestão mock dos 3 CSVs de eventos CDC |
| **Silver** | Deduplicação, joins e limpeza — `purchase_clean.parquet` |
| **Gold** | GMV agregado por dia e subsidiária, particionado por `release_date` |

---

## **Final Table**

**Grain:** uma linha por `transaction_date` × `subsidiary`

**Particionamento:** `data/gold/{transaction_date}/data.parquet`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `date` | date | Data de liberação do pagamento (`release_date`) |
| `subsidiary` | varchar | Subsidiária (`nacional` / `internacional`) |
| `gmv` | double | Soma do valor total das compras pagas no dia |

---

## **Quickstart**

### **Pré-requisitos**

1. **Instale o [uv](https://docs.astral.sh/uv/getting-started/installation/) — gerenciador de pacotes Python utilizado no projeto.**

2. **Clone o repositório:**

```bash
    git clone https://github.com/GabrielGRR/teste_teachable.git
    cd teste_teachable
```

3. **Execute os comandos no CLI (Terminal):**

```bash
    pip install uv
    uv sync
    uv run main.py
```

Isso executa em sequência:

1. `generate_mock_data.py` — gera os CSVs na camada bronze
2. `bronze.py` — carrega os CSVs no DuckDB
3. `silver.py` — deduplica, faz os joins e exporta `purchase_clean.parquet`
4. `gold.py` — agrega o GMV diário e exporta as partições
5. `data/` — É criado o lake com as camadas:
    - `bronze/` — CSVs mock
    - `silver/` — Parquet deduplicado
    - `gold/` — Parquet particionado por `release_date`

---

## **Project Structure**

```
teachable/
├── data/                        # Gerado localmente — não versionado
│   ├── bronze/                  # CSVs raw gerados pelo mock
│   ├── silver/                  # purchase_clean.parquet
│   ├── gold/                    # GMV particionado por data
│   └── teachable.duckdb         # Banco DuckDB local
├── docs/
│   ├── data_schema.md           # Schema das tabelas bronze
│   ├── mock_data_rules.md       # Regras de geração dos dados mock
│   └── Technical_case.pdf       # Enunciado do case
├── scripts/
│   ├── generate_mock_data.py    # Geração dos dados bronze
│   ├── silver.py                # Deduplicação e joins
│   └── gold.py                  # Agregação GMV diário
├── utils/
│   └── logging_utils.py         # Helper de logging com timezone BR
├── main.py                      # Entrypoint do pipeline
├── pyproject.toml
└── uv.lock
```

---

## **Data Issues Handled**

| Problema | Solução |
|----------|---------|
| Eventos duplicados | `ROW_NUMBER()` particionado por `purchase_id` + `purchase_partition`, ordenado por `transaction_datetime DESC` |
| Correção histórica | Mesmo dedup — o evento mais recente vence |
| Late arrivals cross-partition | Segundo dedup por `purchase_id` garante unicidade absoluta na silver |
| Pipeline idempotente | Partições já existentes são skippadas; reprocessar = deletar a partição e reexecutar |

---

## **Pipeline – Daily Run (D-1)**

O pipeline foi modelado para rodar diariamente processando D-1 (dia anterior), orquestrado via **Apache Airflow**.

### **Fluxo em produção**

```
    S3 (bronze)  →  Silver (S3)  →  Gold (S3)  →  Redshift Spectrum
```

As três camadas medalhão seriam armazenadas no **Amazon S3**. O DuckDB suporta leitura e escrita em S3 nativamente, o que significa que as queries mudariam apenas nos caminhos, a lógica de transformação permanece a mesma.

### DAG

O Airflow orquestraria a execução destes scripts via cron jobs e listeners na camada bronze, a estrutura seria algo parecida com:

```python
    @dag(
        schedule="0 6 * * *",    # diário às 06h (America/Sao_Paulo)
        catchup=True,            # reprocessa late arrivals automaticamente
    )
    def teachable_pipeline():
        wait_for_bronze = S3KeySensor(
            task_id="wait_for_bronze",
            bucket_key="bronze/{{ ds }}/*.csv",
        )

        wait_for_bronze >> run_silver >> run_gold
```

- **`S3KeySensor`** — aguarda os CSVs ou parquets do dia chegarem no bucket antes de iniciar
- **`catchup=True`** — garante que dias com late arrivals sejam reprocessados
- **`Idempotência`** — o controle de partições existentes no S3 substituiria o `Path.exists()` local, reprocessar um dia deleta a partição e faz *clear* na task no Airflow
- **`Analytics`** — a camada gold seria exposta aos analistas via **Redshift ou Athena**, apontando para as partições no S3.

---

## **Possible Improvements**

### **Data Quality**

A camada silver atualmente trata duplicatas e late arrivals via deduplicação, mas não valida a integridade dos dados. Algumas melhorias possíveis são:

- Checar nulos em campos obrigatórios (`buyer_id`, `producer_id`, `purchase_total_value`)
- Validar valores esperados (`purchase_status` fora do domínio, `item_quantity <= 0`)
- Validar consistência calculada (`purchase_total_value == item_quantity × purchase_value`)
- Exportar linhas inválidas para uma *camada de quarentena* separada para investigação

### **Pipeline Monitoring**

Em produção, o pipeline pode ser monitorado em três frentes:

- **Row counts** — a cada execução, comparar o volume de linhas processadas com a média histórica do mesmo dia da semana. Uma queda brusca pode indicar falha silenciosa na ingestão bronze ou um problema no join da silver.
- **GMV delta** — comparar o GMV do dia com a média móvel dos últimos 7 e 30 dias. Variações fora do range esperado disparariam um alerta.
- **Freshness** — verificar se a partição do dia foi criada dentro da janela esperada. Se às 12h a partição de D-1 ainda não existe, algo falhou. Há ferramenta nativa no **Airflow** para esse tipo de validação.
- **Reprocessamento de late arrivals** — como o pipeline é append-only por partição, um evento que chega com atraso só é incorporado se a partição for reprocessada. Uma rotina periódica (ex: semanal) poderia identificar partições com dados novos na bronze e acionar um *backfill* automático via Airflow.

---

## **Observations**

### Schema vs. Imagens de Exemplo do Case

O enunciado apresenta imagens de exemplo onde `purchase_id` aparece como campo dentro de `product_item`. No entanto, o schema de referência define `prod_item_id` como a chave de ligação entre `purchase` e `product_item`. Esta implementação segue o schema oficial, ignorando as imagens de exemplo por considerar o schema a fonte de verdade.

### Particionamento da Tabela Gold

O desafio pede simultaneamente uma única tabela analítica de GMV e particionamento por `transaction_date`. A solução adotada particiona os dados fisicamente em `data/gold/{transaction_date}/data.parquet`.
