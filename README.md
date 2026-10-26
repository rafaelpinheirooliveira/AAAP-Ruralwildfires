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

**Fase: Milestone 1 (semana 7).**

- [x] Dados de ocorrências do ICNF/SGIF 2001–2025 obtidos e auditados
- [x] Limpeza dos registos (`src/clean_sgif.py`)
- [x] Dataset de ocorrências, Tarefa 3 (`src/build_occurrence_dataset.py`)
- [x] Dataset concelho × dia, Tarefas 1 e 2 (`src/build_territory_day_dataset.py`)
- [x] EDA da área ardida e escolha de `Amin` (`src/eda_burned_area.py`)
- [x] Definição das tarefas e dos alvos (`docs/tasks_and_targets.md`)
- [x] Inventário de features com hora de disponibilidade e riscos de leakage (`docs/feature_inventory.md`)
- [x] Metodologia experimental preliminar (`docs/experimental_methodology.md`)
- [x] Documentação das fontes: ICNF e CEMS (rascunho)
- [ ] Documentação da CAOP (limites administrativos)
- [ ] Revisão de literatura: rascunho em `docs/literature_review.md`; falta ler os artigos

**Para o Milestone 2:** descarregar e integrar a meteorologia (CEMS), confirmar a
hora do valor diário, treinar os modelos e executar os protocolos de avaliação.

## Dados

| Fonte | Instituição | Conteúdo | Estado |
|---|---|---|---|
| Registos de incêndios SGIF 2001–2025 | ICNF | 497 478 ocorrências, 41 colunas, Portugal continental (278 concelhos), de 2001-01-05 a 2025-12-31 | Obtido |
| Limites administrativos (CAOP) | DGT | Geometria dos concelhos | A obter |
| Índices de perigo de incêndio diários (CEMS, ERA5) | Copernicus | FWI e componentes, grelha de 0,25° | Escolhida; por descarregar |

Os dados **não são versionados no Git**. O ficheiro de registos do ICNF foi
fornecido pelo professor da UC. Para reproduzir o projeto:

1. Obter `Combined_Registos_Incendios_SGIF_2001_2025.xlsx` junto do docente.
   A origem institucional é o
   [ICNF, estatísticas de incêndios rurais](https://www.icnf.pt/florestas/gfr/gfrgestaoinformacao/estatisticas).
2. Colocá-lo em `data/raw/Combined_Registos_Incendios_SGIF_2001_2025.xlsx`.

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

## Reprodutibilidade

- Seed global em `configs/config.yaml` (`seed: 42`), registada em cada experiência.
- Para cada experiência principal serão registados: versão do dataset, período
  de estudo, âmbito geográfico, tarefa, momento da previsão, `Amin`, conjunto
  de features, protocolo de treino/validação/teste, modelo, hiperparâmetros,
  seed e métricas, numa linha de `results/experiments.jsonl` (previsto para o
  Milestone 2).

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
