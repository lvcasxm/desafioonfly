# Entrega — Consolidador de reservas Onfly

## Defeitos corrigidos

| # | Arquivo | Defeito | Causa raiz |
|---|---------|---------|------------|
| 1 | `repositories/csv_reservation_repository.py` | Só as 200 primeiras reservas eram lidas (o arquivo tem 300). | Um `break` em `len(rows) == 200` truncava a leitura silenciosamente. |
| 2 | `services/status_policy.py` | `NO_SHOW` entrava em noites, valores, `by_month` e `top_hotels`. | `is_billable` testava `status != "CANCELLED"` em vez de `status == "CONFIRMED"`. |
| 3 | `services/stay_calculator.py` | Noites erradas (até negativas) quando a estadia atravessa mês/ano. | Subtraía `checkout.day - checkin.day` (dia do mês) em vez de `(checkout - checkin).days`. |
| 4 | `services/currency_converter.py` | Valores em USD/EUR convertidos errado e com ruído de ponto flutuante. | Dividia pela taxa em vez de multiplicar, e passava por `float` antes de voltar a `Decimal`. |
| 5 | `services/report_builder.py` | `top_hotels` listava os hotéis de **menor** valor. | A ordenação usava `amount` ascendente; passou a usar `-amount` com desempate por `hotel_id` ascendente. |

Ajuste adicional (robustez, sem mudar contrato): uma moeda sem taxa na tabela agora gera `InputFileError`
(código de saída `2`, "entrada inválida") em vez de um `KeyError` genérico (código `1`). O dataset fornecido
não é afetado — todas as moedas têm taxa.

Nada mais foi alterado: comando, argumentos, schema do JSON e arquivos de `data/` permanecem iguais, e os
testes fornecidos não foram tocados.

## Como investiguei

1. Li o README inteiro e listei cada regra verificável (status, noites, câmbio, exatidão, ordenação, contrato).
2. Rodei `pytest -q` para registrar o baseline: 5 de 5 falhando, cada um apontando para uma regra diferente.
3. Li o pipeline seguindo a ordem do README (`ler → converter tipos → contar status → filtrar CONFIRMED → agregar`)
   e comparei cada etapa com a regra correspondente. Isso revelou os defeitos 2–5 diretamente e o defeito 1,
   que **nenhum teste fornecido detecta** (os testes usam poucas linhas) — só aparece ao comparar
   `total_reservations` com as 300 linhas do CSV.
4. Perfilei `data/reservas_hoteis.csv` (valores distintos de status, moeda, quartos; IDs duplicados; nomes de
   hotel divergentes por `hotel_id`; datas e valores malformados) para confirmar que os dados são
   consistentes e que os defeitos estão só no CLI.
5. Corrigi cada defeito na menor alteração possível, no módulo responsável.
6. Validei contra a amostra do README (bate campo a campo) e recalculei o relatório completo com um script
   independente (biblioteca padrão, sem importar o projeto): `summary`, `by_month` e `top_hotels` idênticos.
7. Adicionei `tests/test_additional_rules.py` para travar os cenários que os testes fornecidos não cobrem.

## Testes adicionados (`tests/test_additional_rules.py`)

- Amostra de validação do README reproduzida integralmente (summary, `by_month`, `top_hotels`, ordem das chaves, offset `-03:00`).
- Arquivo com 250 reservas — nenhuma linha descartada (regressão do defeito 1).
- Virada de ano com 2 quartos; mês do `by_month` é o do check-in.
- `CANCELLED`/`NO_SHOW` ausentes de `by_month` e `top_hotels`.
- Desempate de `top_hotels` por `hotel_id` e limite de `--top`; menos itens quando há menos hotéis.
- Soma exata antes de arredondar (`3 × 0.333 → "1.00"`) e half-up (`0.125 → "0.13"`).
- Precisão `Decimal` na conversão (`10 × EUR 0.01 → "0.59"`).
- Sem reservas confirmadas: zeros, `"0.00"` e listas vazias.
- Códigos de saída `2` para input inexistente, `--top 0` e moeda sem taxa.

## Como validar

```bash
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

pytest -q

PYTHONPATH=src python -m onfly_report \
  --input data/exemplo-validacao.csv \
  --rates data/taxas_cambio.csv \
  --output output/exemplo.json      # compare com a tabela "Amostra de validação" do README

PYTHONPATH=src python -m onfly_report \
  --input data/reservas_hoteis.csv \
  --rates data/taxas_cambio.csv \
  --output output/report.json
```

Resumo esperado no stdout para o dataset completo:

```
Reservas: 300 | Confirmadas: 235 | Noites: 1347 | Total BRL: 396170.00
```

## Resultado do `pytest`

```
$ pytest -q
.................                                                        [100%]
17 passed
```

5 testes fornecidos + 12 adicionais. `ruff check src tests` também passa.

> Ambiente de execução: os testes foram rodados com Python 3.15; o código usa apenas a biblioteca padrão e
> nenhuma API posterior à 3.11.
