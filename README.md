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

**Fase: Milestone 1 (semana 7), em curso.**

- [x] Dados de ocorrências do ICNF/SGIF 2001–2025 obtidos e auditados
- [ ] Documentação das restantes fontes (limites administrativos, meteorologia/FWI)
- [ ] Limpeza dos registos de ocorrências
- [ ] EDA da área ardida e escolha de `Amin`
- [ ] Dataset concelho × dia
- [ ] Dataset de ocorrências
- [ ] Inventário de features com hora de disponibilidade
- [ ] Revisão de literatura

## Dados

| Fonte | Instituição | Conteúdo | Estado |
|---|---|---|---|
| Registos de incêndios SGIF 2001–2025 | ICNF | 497 478 ocorrências, 41 colunas, Portugal continental (278 concelhos), de 2001-01-05 a 2025-12-31 | Obtido |
| Limites administrativos (CAOP) | DGT | Geometria dos concelhos | A obter |
| Meteorologia e índice FWI diários por concelho | A definir | Variáveis disponíveis às 23:59 de d−1 | A definir |

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
├── configs/        # Amin, período de estudo, seeds
├── data/           # fora do Git (raw/ e processed/)
├── docs/           # fontes de dados, definição das tarefas, inventário de features
├── notebooks/      # análise exploratória
└── src/            # aquisição, limpeza e construção dos datasets
```

## Reprodução

> A preencher à medida que os scripts forem sendo escritos.

```bash
# 1. ambiente
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. limpeza e construção dos datasets (a definir)
```

## Reprodutibilidade

- Seed global definida em `configs/` (a definir) e registada em cada experiência.
- Para cada experiência principal serão registados: versão do dataset, período
  de estudo, âmbito geográfico, tarefa, momento da previsão, `Amin`, conjunto
  de features, protocolo de treino/validação/teste, modelo, hiperparâmetros,
  seed e métricas.

## Decisões metodológicas já tomadas

- Unidade territorial de referência: **concelho** (278 em Portugal continental).
- A hora de referência dos registos é `DataHoraAlerta`; as colunas `Ano`, `Mes`,
  `Dia` e `Hora` do ficheiro original não são usadas por terem 843
  inconsistências com ela.
- `Amin` principal proposto: **10 ha**, com 5, 50 e 100 ha como análise de
  sensibilidade (a confirmar na EDA).

## Licença e dados

Os dados pertencem às instituições referidas. Este repositório contém apenas o
código e a documentação.
