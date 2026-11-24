# Previsão de risco de incêndios rurais em Portugal e generalização espaciotemporal

Projeto semestral de Aprendizagem Automática Aplicada (AAAP), UFP, 2026/27.
Trabalho individual.

## Objetivo

Investigar em que medida a Aprendizagem Automática consegue apoiar a avaliação
do risco de incêndio rural em Portugal continental e, sobretudo, se os modelos
mantêm o desempenho em **períodos futuros** e em **regiões não vistas no
treino**.

## Tarefas

Todas são classificações binárias. `Amin` é o limiar de área ardida final que
define um incêndio significativo (`A ≥ Amin`).

| Tarefa | Momento da previsão | Unidade de observação | Pergunta |
|---|---|---|---|
| 1 | 23:59 do dia d−1 | concelho × dia | Haverá pelo menos um incêndio no dia d? |
| 2 | 23:59 do dia d−1 | concelho × dia | Haverá pelo menos um incêndio com `A ≥ Amin` no dia d? |
| 3 | `DataHoraAlerta` | ocorrência | Esta ocorrência vai atingir `A ≥ Amin`? |

A área ardida final só é usada para construir o alvo, nunca como feature.

## Questões de investigação

- **RQ1:** até que ponto a informação disponível às 23:59 de d−1 prevê a ocorrência de incêndio no dia d?
- **RQ2:** e a ocorrência de pelo menos um incêndio com `A ≥ Amin`?
- **RQ3:** no momento do alerta, é possível prever se a ocorrência atingirá `A ≥ Amin`?
- **RQ4:** os modelos mantêm o desempenho em períodos futuros e/ou regiões não vistas?

## Estado atual

**Estado: Milestone 1 concluído; Milestone 2 em curso.**

- [x] Dados de ocorrências do ICNF/SGIF 2001–2025 obtidos e auditados
- [x] Limpeza dos registos (`src/clean_sgif.py`)
- [x] Dataset de ocorrências, Tarefa 3 (`src/build_occurrence_dataset.py`)
- [x] Dataset concelho × dia, Tarefas 1 e 2 (`src/build_territory_day_dataset.py`)
- [x] EDA da área ardida e escolha de `Amin` (`src/eda_burned_area.py`)
- [x] Definição das tarefas e dos alvos (`docs/tasks_and_targets.md`)
- [x] Inventário de features com hora de disponibilidade e riscos de leakage (`docs/feature_inventory.md`)
- [x] Metodologia experimental preliminar (`docs/experimental_methodology.md`)
- [x] Documentação das fontes: ICNF e CAOP; teste CEMS descarregado, inspecionado e agregado
- [x] Avaliação exploratória da data diária CEMS contra o FWI do ICNF
- [x] Scripts de integração espacial e construção de features CEMS até d−1
- [x] Avaliação reprodutível sem CEMS: modelos temporais, aleatórios, espaciais e espaciotemporais
- [x] Sensibilidade da Tarefa 3 sem os 8 378 registos marcados como possíveis duplicados
- [ ] CEMS anual 2001–2025: só 2001 e 2002 obtidos; 2003–2021 sem descarga
      após duas tentativas por ano; 2022–2025 ainda por testar. O ficheiro de
      agosto de 2017 é apenas um teste mensal; falta a integração completa e a
      ablação meteorológica.
- [ ] Sensibilidade de `Amin`, subamostragem, bootstrap em blocos, análises de
      erros e importância/explicações permanecem por fazer.
- [ ] Revisão de literatura: rascunho atualizado; três artigos prioritários revistos, leituras secundárias pendentes

**Para o Milestone 2:** concluir a avaliação de referência sem meteorologia
(já executada), tentar obter o CEMS e, se possível, acrescentá-lo como ablação
retrospetiva. A comparação com o ICNF favorece o alinhamento pela mesma data
de calendário, mas não confirma a hora exata nem a disponibilidade operacional
da reanálise. O CEMS não é necessário para os resultados aqui apresentados.

## Dados

| Fonte | Instituição | Conteúdo | Estado |
|---|---|---|---|
| Registos de incêndios SGIF 2001–2025 | ICNF | 497 478 ocorrências, 41 colunas, Portugal continental (278 concelhos), de 2001-01-05 a 2025-12-31 | Obtido |
| Limites administrativos (CAOP2025) | DGT | Geometrias e áreas dos concelhos | Obtida localmente; ficheiros fora do Git |
| Índices de perigo de incêndio diários (CEMS, ERA5) | Copernicus | FWI e componentes, grelha de 0,25° | Teste agregado; anuais de 2001–2002 obtidos; restantes por obter; hora/disponibilidade exatas pendentes |

Os dados **não são versionados no Git**. O ficheiro de registos do ICNF foi
fornecido pelo professor da UC. Para reproduzir o projeto:

1. Obter `Combined_Registos_Incendios_SGIF_2001_2025.xlsx` junto do docente.
   A origem institucional é o
   [ICNF, estatísticas de incêndios rurais](https://www.icnf.pt/florestas/gfr/gfrgestaoinformacao/estatisticas).
2. Colocá-lo em `data/raw/Combined_Registos_Incendios_SGIF_2001_2025.xlsx`.
3. Obter o [GeoPackage CAOP2025 do continente](https://geo2.dgterritorio.gov.pt/caop/CAOP_Continente_2025-gpkg.zip)
   e a tabela de [áreas CAOP2025](https://www.dgterritorio.gov.pt/sites/default/files/ficheiros-cartografia/Areas_Freg_Mun_Dist_Pais_CAOP2025.zip)
   na [página da DGT](https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop),
   e guardá-los em `data/raw/caop/`.

Descrição das colunas e auditoria da disponibilidade temporal das features:
`docs/` (ver abaixo).

## Estrutura do repositório

```
.
├── README.md
├── requirements.txt
├── .gitignore
├── configs/        # seed, Amin, período de estudo
├── data/           # fora do Git (raw/ e processed/)
├── docs/           # documentação (ver abaixo)
├── notebooks/      # análise exploratória
├── results/        # figuras e tabelas
└── src/            # limpeza, construção dos datasets e EDA
```

### Documentação (`docs/`)

| Ficheiro | Conteúdo |
|---|---|
| `data_sources.md` | Fontes de dados, cobertura, limitações e anomalias |
| `tasks_and_targets.md` | Tarefas 1 a 3, alvos e prevalências |
| `feature_inventory.md` | Features, hora de disponibilidade e riscos de leakage |
| `experimental_methodology.md` | Protocolos de avaliação, modelos, métricas e experiências |
| `literature_review.md` | Revisão de literatura e contextualização (rascunho) |
| `icnf_fire_desc_pt.md` | Dicionário de dados (fornecido pelo professor) |
| `auditoria_disponibilidade_features_sgif_pt.md` | Auditoria da disponibilidade (fornecida pelo professor) |

## Reprodução

Testado em Python 3.12 e 3.14. Executar a partir da raiz do repositório, com o
ficheiro do ICNF já em `data/raw/`.

```powershell
# 1. ambiente (Windows PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```bash
# 1. ambiente (macOS / Linux)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

```bash
# 2. pipeline (a leitura do xlsx demora 4 a 10 minutos)
python src/clean_sgif.py                    # -> data/processed/sgif_clean.parquet
python src/build_occurrence_dataset.py      # -> data/processed/occurrences.parquet
python src/build_territory_day_dataset.py   # -> data/processed/territory_day.parquet
python src/eda_burned_area.py               # -> results/figures/ e results/amin_candidates.md
```

### Meteorologia (CEMS), a partir do Milestone 2

Requer conta gratuita no portal do Copernicus e as credenciais em `~/.cdsapirc`.

```bash
python src/download_cems.py --test       # só agosto de 2017
python src/inspect_cems.py data/raw/cems/cems_fire_2017-08_test.nc
python src/integrate_cems.py --test      # agrega o teste aos concelhos CAOP2025
python src/attach_cems_features.py --test  # verifica os lags no mês de teste
python src/download_cems.py              # 2001 a 2025, um ficheiro por ano
python src/integrate_cems.py             # após concluir a descarga anual
python src/attach_cems_features.py       # lags e janelas até d-1 para ablações retrospetivas
```

O descarregador pode ser limitado a um ano com `--year 2003`. Cada ano tem
duas tentativas, com espera de 30 segundos por pedido; se continuar apenas
`accepted`, pede o cancelamento e avança, permitindo retomar sem bloquear nos
anos seguintes.

O alinhamento no mesmo dia teve correlação de Spearman 0,911 com o FWI do
ICNF em agosto de 2017, superior aos alinhamentos com um ou dois dias de atraso.
Isto apoia a data diária, não prova a hora física nem a disponibilidade em
tempo real. A experiência CEMS usa só dados até d−1 e não sustenta uma alegação
de previsão operacional.

### Modelação e avaliação

Depois de gerar os datasets de ocorrências e concelho-dia, executar uma tarefa
e protocolo por comando:

```powershell
python src/run_experiments.py --task 1 --protocol temporal
python src/run_experiments.py --task 2 --protocol temporal
python src/run_experiments.py --task 3 --protocol temporal
```

Protocolos disponíveis: `random`, `temporal`, `spatial` e `spatiotemporal`.
`--dry-run` mostra os tamanhos e positivos de cada divisão sem treinar;
`--max-folds 1` permite testar um fold espacial. Cada execução acrescenta
métricas e parâmetros a `results/experiments.jsonl`. O pipeline compara
prevalência, histórico recente quando aplicável, regressão logística e
HistGradientBoosting; os limiares dos modelos são escolhidos na validação.
`--resume` retoma execuções interrompidas sem repetir dobras já guardadas.
Features CEMS só entram quando se escolhe explicitamente um conjunto `*-cems`.
Para a sensibilidade a possíveis duplicados da Tarefa 3, acrescenta
`--exclude-possible-duplicates`; os resultados ficam identificados no JSONL.

### Resultados de referência

Se a execução estiver correta, os relatórios gerados em `data/processed/`
devem coincidir com estes valores.

| Passo | Resultado |
|---|---|
| Limpeza | 497 478 linhas à entrada, 497 477 à saída (1 sem chave de concelho) |
| Concelhos e distritos | 379 grafias unificadas em 278 concelhos, 18 distritos |
| Anomalias marcadas | 843 inconsistências de hora, 32 coordenadas inválidas, 15 164 áreas zero, 8 378 possíveis duplicados |
| Ocorrências (Tarefa 3, `Amin` = 10 ha) | 497 477 linhas; 15 851 positivos (3,19%) |
| Concelho × dia (Tarefas 1 e 2) | 2 538 418 linhas (9 131 dias × 278 concelhos); `y_fire` 281 580 (11,09%); `y_sig_amin10` 13 942 (0,55%) |

### Avaliação temporal (sem CEMS)

Teste temporal fechado: 2021–2025; seleção do modelo e do limiar na validação
2018–2020. A métrica principal é Average Precision (AP); a prevalência é o AP
do baseline constante. Estes são resultados iniciais, não substituem as
avaliações espacial e espaciotemporal nem as análises de sensibilidade.

| Tarefa | Prevalência no teste | Baseline | Histórico | Logística | HistGradientBoosting |
|---|---:|---:|---:|---:|---:|
| 1 — ocorrência | 6,07% | 0,0607 | 0,2360 | 0,2865 | **0,3084** |
| 2 — incêndio ≥10 ha | 0,315% | 0,0031 | 0,0348 | 0,0376 | **0,0701** |
| 3 — ocorrência ≥10 ha | 4,46% | 0,0446 | — | 0,0680 | **0,1159** |

O CEMS foi deliberadamente excluído: é uma reanálise e a sua disponibilidade
operacional no instante previsto não foi demonstrada.

### Avaliação não temporal (sem CEMS)

Média da Average Precision (AP) entre os cinco folds aleatórios ou seis folds
por distrito. Para o baseline constante, a AP é igual à prevalência indicada.
Cada fold e as métricas complementares estão em `results/experiments.jsonl`.

| Tarefa | Protocolo | Prevalência / AP baseline | Histórico (AP) | Logística (AP) | HistGradientBoosting (AP) |
|---|---|---:|---:|---:|---:|
| 1 — ocorrência | Aleatório | 11,09% | 0,4256 | 0,4809 | **0,5127** |
| 1 — ocorrência | Espacial | 11,33% | 0,3981 | 0,4478 | **0,4799** |
| 1 — ocorrência | Espaciotemporal | 6,15% | 0,2137 | 0,2581 | **0,2803** |
| 2 — incêndio ≥10 ha | Aleatório | 0,549% | 0,0465 | 0,0586 | **0,0920** |
| 2 — incêndio ≥10 ha | Espacial | 0,579% | 0,0498 | 0,0596 | **0,0832** |
| 2 — incêndio ≥10 ha | Espaciotemporal | 0,333% | 0,0392 | 0,0436 | **0,0660** |
| 3 — ocorrência ≥10 ha | Aleatório | 3,19% | — | 0,0613 | **0,1072** |
| 3 — ocorrência ≥10 ha | Espacial | 3,46% | — | 0,0546 | **0,0727** |
| 3 — ocorrência ≥10 ha | Espaciotemporal | 4,77% | — | 0,0627 | **0,0851** |

Em média, ambos os modelos aprendidos superam o baseline de prevalência em
todos os protocolos e tarefas; o HistGradientBoosting tem a maior AP média
nas nove combinações. A dispersão entre folds é importante, sobretudo nos
protocolos espaciais, e os valores não devem ser comparados sem considerar a
prevalência e a composição de cada teste. Isto completa a comparação de
referência sem CEMS, não as análises de sensibilidade nem a ablação
meteorológica.

### Sensibilidade a possíveis duplicados (Tarefa 3)

Foram excluídos os 8 378 registos marcados pela regra “mesma freguesia e mesmo
minuto de alerta”; 133 eram positivos para `A ≥ 10 ha`. São suspeitas, não
duplicados confirmados. A AP média mudou pouco:

| Protocolo | Prevalência: completo → sem sinalizados | Logística: AP completo → sem sinalizados | HistGradientBoosting: AP completo → sem sinalizados |
|---|---:|---:|---:|
| Aleatório | 3,186% → 3,213% | 0,0613 → 0,0615 | 0,1072 → 0,1074 |
| Temporal | 4,455% → 4,458% | 0,0680 → 0,0682 | 0,1159 → 0,1153 |
| Espacial | 3,459% → 3,469% | 0,0546 → 0,0547 | 0,0727 → 0,0742 |
| Espaciotemporal | 4,770% → 4,773% | 0,0627 → 0,0626 | 0,0851 → 0,0879 |

O teste de sensibilidade acrescenta 54 registos ao `results/experiments.jsonl`.
Os folds espaciais e temporais mantêm os grupos territoriais/temporais; na
avaliação aleatória da Tarefa 3 os grupos concelho-dia são indivisíveis, pelo
que suspeitas da mesma freguesia e minuto não atravessam treino/validação/teste.

## Reprodutibilidade

- Seed global em `configs/config.yaml` (`seed: 42`), registada em cada experiência.
- Cada execução regista: versão do dataset, período
  de estudo, âmbito geográfico, tarefa, momento da previsão, `Amin`, conjunto
  de features, protocolo de treino/validação/teste, modelo, hiperparâmetros,
  seed e métricas numa linha de `results/experiments.jsonl`. O ficheiro tem
  atualmente 252 registos, incluindo os 102 resultados dos modelos aprendidos
  nas 51 dobras não temporais e 54 registos de sensibilidade a possíveis
  duplicados da Tarefa 3.

  Os intervalos mensais de 95% para a AP estão em
  `results/uncertainty.jsonl`, com 108 registos de seed 42 e 1000 réplicas por
  dobra.

### Incerteza

Os intervalos bootstrap de 95% por mês estão em
`results/uncertainty.jsonl`. O bloco é o mês da observação do teste, evitando
que dias do mesmo mês sejam tratados como independentes. Execute e recalcule:

```powershell
python src/bootstrap_uncertainty.py --replicates 1000 --resume
python src/run_experiments.py --task 1 --protocol random --models logistic histgb --seed 43 --resume
python src/run_experiments.py --task 1 --protocol random --models logistic histgb --seed 44 --resume
```

Na comparação aleatória, a AP média variou menos de 0,001 entre as seeds 42,
43 e 44. A variação espacial continua substancial entre distritos; os
intervalos mensais por dobra estão no ficheiro de incerteza e não são
intervalos sobre a média de folds.

## Decisões metodológicas já tomadas

- Unidade territorial de referência: **concelho** (278 em Portugal continental).
- A hora de referência dos registos é `DataHoraAlerta`; as colunas `Ano`, `Mes`,
  `Dia` e `Hora` do ficheiro original não são usadas por terem 843
  inconsistências com ela.
- `Amin` principal: **10 ha**, com 5, 50 e 100 ha como análise de
  sensibilidade. Justificação na EDA da área ardida
  (`results/amin_candidates.md` e `results/figures/`).
- Os registos com área zero **são mantidos** e marcados (`flag_area_zero`); a
  sensibilidade é testada com o alvo `y_fire_no_zero`.
- As features de área do histórico usam a data de **extinção**, porque a área
  final só é conhecida quando o incêndio se extingue.
- Os índices FWI do ficheiro do ICNF ficam fora das features principais até se
  confirmar a hora de cálculo.
- Divisões propostas (a rever): treino 2001–2017, validação 2018–2020, teste
  2021–2025; folds espaciais por distrito. Ver `docs/experimental_methodology.md`.

## Licença e dados

Os dados pertencem às instituições referidas. Este repositório contém apenas o
código e a documentação.
