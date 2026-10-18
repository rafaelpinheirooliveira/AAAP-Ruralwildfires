# Definição das tarefas e dos alvos

Este documento fixa o que cada tarefa prevê, em que momento, sobre que unidade
e como o alvo é construído. As contagens foram verificadas a partir dos
datasets gerados pelo código do repositório.

## Dois momentos de previsão

| | Momento A | Momento B |
|---|---|---|
| Instante da previsão | 23:59 do dia d−1 | `DataHoraAlerta` da ocorrência |
| Unidade de observação | concelho × dia | uma ocorrência |
| Tarefas | 1 e 2 | 3 |
| Dataset | `data/processed/territory_day.parquet` | `data/processed/occurrences.parquet` |
| Construído por | `src/build_territory_day_dataset.py` | `src/build_occurrence_dataset.py` |

As duas populações são diferentes e tratam-se em separado. No momento A ainda
não se sabe se haverá incêndio; no momento B o incêndio já existe.

## Incêndio significativo

Um incêndio é **significativo** se a sua área ardida final `A` satisfaz
`A ≥ Amin`.

- **`Amin` principal: 10 ha.** Corresponde a cerca de 3,2% das ocorrências
  (1 em 31) e é uma das fronteiras das classes de área do ICNF.
- **Análise de sensibilidade:** 5, 50 e 100 ha.
- Justificação: `results/amin_candidates.md` e `results/figures/`.

A área final serve **apenas para construir o alvo**. É informação futura e
nunca é usada como feature.

## Definição do dia

O dia d de uma ocorrência é a data de `DataHoraAlerta`. Um incêndio que se
prolonga por vários dias conta apenas para o dia do alerta.

## Tarefa 1: ocorrência de incêndio no dia seguinte

**Pergunta (RQ1).** Às 23:59 de d−1, haverá pelo menos um incêndio rural no
concelho c durante o dia d?

```
y_fire(c, d) = 1  se existe pelo menos uma ocorrência em c no dia d
             = 0  caso contrário
```

Distingue **sem incêndio** de **com incêndio**.

| Dataset | Coluna do alvo | Positivos | % |
|---|---|---:|---:|
| `territory_day` (2 538 418 linhas) | `y_fire` | 281 580 | 11,09 |
| `territory_day` | `y_fire_no_zero` (sensibilidade) | 276 778 | 10,90 |

`y_fire_no_zero` ignora as ocorrências com área ardida igual a zero. Os
registos com área zero são mantidos no alvo principal, porque foram
efetivamente registados, e a variante serve para testar o impacto dessa
escolha.

## Tarefa 2: incêndio significativo no dia seguinte

**Pergunta (RQ2).** Às 23:59 de d−1, haverá pelo menos um incêndio com
`A ≥ Amin` no concelho c durante o dia d?

```
y_sig(c, d; Amin) = 1  se max A_i (i em c, dia d) >= Amin
                  = 0  caso contrário
```

A classe negativa reúne **dois casos**: dias sem incêndio e dias só com
incêndios abaixo de `Amin`.

| Amin (ha) | Coluna | Positivos | % | Rácio |
|---:|---|---:|---:|---:|
| 5 | `y_sig_amin5` | 22 255 | 0,877 | 1:114 |
| **10** | **`y_sig_amin10`** | **13 942** | **0,549** | **1:182** |
| 50 | `y_sig_amin50` | 5 258 | 0,207 | 1:483 |
| 100 | `y_sig_amin100` | 3 178 | 0,125 | 1:799 |

Exemplo: se no mesmo concelho e dia ocorrem incêndios de 0,5 ha, 4 ha e 35 ha,
então `y_fire = 1` e, para `Amin = 10`, `y_sig = 1`, porque o máximo (35 ha) é
≥ 10.

## Tarefa 3: incêndio significativo no momento do alerta

**Pergunta (RQ3).** Dada uma ocorrência já registada, e usando apenas a
informação conhecida em `DataHoraAlerta`, vai atingir `A ≥ Amin`?

```
y_sig(i; Amin) = 1  se A_i >= Amin
               = 0  caso contrário
```

Distingue **incêndio com A < Amin** de **incêndio com A ≥ Amin**. É um problema
diferente da Tarefa 2: aqui o incêndio já é conhecido e só se estima a sua
dimensão final.

| Amin (ha) | Coluna | Positivos | % | Rácio |
|---:|---|---:|---:|---:|
| 5 | `y_sig_amin5` | 26 236 | 5,27 | 1:19 |
| **10** | **`y_sig_amin10`** | **15 851** | **3,19** | **1:31** |
| 50 | `y_sig_amin50` | 5 729 | 1,15 | 1:87 |
| 100 | `y_sig_amin100` | 3 416 | 0,69 | 1:146 |

População: 497 477 ocorrências.

## Relação entre as tarefas

| | Tarefa 1 | Tarefa 2 | Tarefa 3 |
|---|---|---|---|
| Momento | 23:59 de d−1 | 23:59 de d−1 | alerta |
| Unidade | concelho × dia | concelho × dia | ocorrência |
| Já se sabe que há incêndio? | Não | Não | Sim |
| Prevalência (Amin = 10 ha) | 11,09% (qualquer incêndio) | 0,55% | 3,19% |

A Tarefa 2 é um subconjunto da Tarefa 1: todo o dia significativo é também um
dia com incêndio.

## Colunas que nunca são features

Em `territory_day.parquet`: `y_*` e `target_only_*`.
Em `occurrences.parquet`: `y_*` e `target_only_final_burned_area_ha`.

O código impede que estas colunas entrem nas listas de features
(`FEATURES_AT_2359` e `FEATURES_AT_ALERT`). A disponibilidade de cada feature
está em `docs/feature_inventory.md`.

## Pressupostos e limitações

- **Ausência de registo = ausência de incêndio.** Assume-se, mas não se prova
  com esta fonte. Os 1 269 dias sem nenhuma ocorrência no país concentram-se
  entre novembro e março (só 7 caem entre junho e setembro), o que não sugere
  lacunas de dados. Num concelho isolado, a ausência é a situação normal.
- **Concelhos.** São os 278 que aparecem nos registos; coincide com o número
  de concelhos de Portugal continental. Será confirmado com a CAOP.
- **Deriva temporal.** A prevalência de `y_fire` desce de 14,0% (2001–2010) para
  10,7% e 6,1% (2011–2020 e 2021–2025). Esta mudança é relevante para a RQ4.
- **Alvo em escala grosseira.** Cerca de 17 595 ocorrências têm áreas residuais
  e muitas áreas estão arredondadas, por isso o problema é tratado como
  classificação binária e não como regressão da área.
