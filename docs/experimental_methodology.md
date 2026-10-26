# Metodologia experimental preliminar

Documento de trabalho do Milestone 1. Descreve como se vão avaliar os modelos
e o que está ainda por decidir. Os números de cada divisão foram calculados a
partir dos datasets do repositório.

## 1. Princípios

1. O **teste fica fechado** até a decisão do modelo estar tomada. A seleção de
   modelos e de hiperparâmetros usa apenas treino e validação.
2. Toda a transformação (normalização, imputação, reamostragem) é ajustada
   **só ao treino** de cada divisão, dentro de um `Pipeline`.
3. A avaliação aleatória serve de referência e **nunca** é o resultado
   principal, porque mistura períodos e regiões semelhantes.
4. Cada resultado indica o protocolo de avaliação com que foi obtido.
5. Os modelos são poucos e justificados, e as comparações são feitas nas
   mesmas condições (mesma divisão, mesma métrica).

## 2. Protocolos de avaliação (RQ4)

| Protocolo | Treino | Teste | O que mede |
|---|---|---|---|
| Aleatório | `StratifiedKFold`, 5 folds, `shuffle=True`, seed 42 | Fold de teste | Referência otimista |
| Temporal | 2001–2017 | 2021–2025 | Generalização para o futuro |
| Espacial | Distritos fora do fold, todos os anos | Distritos do fold | Generalização para regiões não vistas |
| Espaciotemporal | Distritos fora do fold, 2001–2017 | Distritos do fold, 2021–2025 | Ambas em simultâneo |

**Validação (escolha de hiperparâmetros):** 2018–2020 no protocolo temporal;
nos protocolos espaciais, validação cruzada por distrito dentro do treino. O
período 2018–2020 fica entre o treino e o teste, o que evita que o fim do
treino toque no início do teste.

### Dimensão das divisões temporais

| Conjunto | Concelhos-dia | Com incêndio (T1) | Significativos, 10 ha (T2) | Ocorrências (T3) | Significativas, 10 ha (T3) |
|---|---:|---:|---:|---:|---:|
| Treino 2001–2017 | 1 726 102 | 227 331 (13,17%) | 11 461 (0,664%) | 424 147 | 13 080 (3,08%) |
| Validação 2018–2020 | 304 688 | 23 442 (7,69%) | 884 (0,290%) | 32 725 | 962 (2,94%) |
| Teste 2021–2025 | 507 628 | 30 807 (6,07%) | 1 597 (0,315%) | 40 605 | 1 809 (4,46%) |

**Consequência:** a taxa base da Tarefa 2 desce para metade entre treino
(0,66%) e teste (0,32%). Um limiar escolhido no treino ou na validação não
transfere sem cuidado, e a PR-AUC só é comparável com a prevalência do próprio
conjunto de teste.

### Divisão espacial

A unidade é o **distrito** (18 distritos, sem erros de atribuição, porque
vem do código oficial). Seis folds de três distritos, atribuídos por ordem do
código (`índice % 6`) e fixos:

| Fold | Distritos | T2 em 2021–2025 | T3 em 2021–2025 |
|---:|---|---:|---:|
| 0 | Aveiro, Évora, Porto | 249 | 277 |
| 1 | Beja, Faro, Santarém | 126 | 127 |
| 2 | Braga, Guarda, Setúbal | 392 | 447 |
| 3 | Bragança, Leiria, Viana do Castelo | 319 | 360 |
| 4 | Castelo Branco, Lisboa, Vila Real | 306 | 377 |
| 5 | Coimbra, Portalegre, Viseu | 205 | 221 |

O fold mais pequeno do teste espaciotemporal tem 126 positivos na Tarefa 2 e
127 na Tarefa 3. É o limite da robustez estatística: com `Amin` ≥ 50 ha, alguns
folds ficam com poucos positivos e os resultados serão ruidosos.

**Limitação a discutir:** distritos vizinhos em folds diferentes têm regimes de
fogo semelhantes (por exemplo, Aveiro e Coimbra), por isso o teste espacial
continua a ser parcialmente otimista. Análise de sensibilidade prevista:
agrupar por macro-regiões (agrupando distritos contíguos) em vez de distritos.

## 3. Seleção de modelos e hiperparâmetros

- Pesquisa de hiperparâmetros **pequena e justificada** (grelha de poucas
  combinações por modelo), para limitar o custo e o risco de ajustar à validação.
- A escolha usa a métrica principal (secção 6), medida na validação.
- Depois de escolhida, a configuração é treinada no treino completo e avaliada
  **uma única vez** no teste.
- A variação por fold ou por seed é sempre reportada, e não apenas a média.

## 4. Modelos

| Modelo | Papel | Notas |
|---|---|---|
| Baseline de prevalência (`DummyClassifier`) | Mínimo útil | PR-AUC igual à prevalência |
| Baseline de histórico (regra: "houve incêndio nos últimos 7 dias") | Referência simples e interpretável (Tarefas 1 e 2) | Mostra o que o histórico dá sem aprendizagem |
| Regressão logística (`StandardScaler` + `LogisticRegression`) | Modelo linear | Variáveis categóricas por codificação *one-hot* |
| Random forest (`RandomForestClassifier`) | Ensemble de árvores | Pode exigir subamostragem de negativos nas Tarefas 1 e 2 (1,7 milhões de linhas de treino) |
| Gradient boosting (`HistGradientBoostingClassifier`) | Ensemble sequencial | Escolhido em vez do `GradientBoostingClassifier` por ser muito mais rápido nestas dimensões; é uma escolha a justificar no relatório |

Todos de `scikit-learn`, o mesmo das aulas.

## 5. Desbalanceamento

| Tarefa (`Amin` = 10 ha) | Rácio (1 positivo em N observações) |
|---|---:|
| 1 | 1:9 (11,09%) |
| 2 | 1:182 (0,55%) |
| 3 | 1:31 (3,19%) |

A Tarefa 2 é a mais exigente, e piora com `Amin` maior (1:799 a 100 ha).
Estratégias a comparar na experiência E5:

1. Sem tratamento (referência).
2. Pesos de classe (`class_weight`).
3. Subamostragem dos negativos, **apenas no treino** de cada divisão.
4. Ajuste do limiar de decisão na validação.

Sobreamostragem sintética (SMOTE) não é a primeira escolha: os dados incluem
variáveis de calendário e localização, para as quais interpolar exemplos
sintéticos tem pouco sentido. Só será testada se sobrar tempo, e sempre dentro
do treino.

## 6. Métricas e limiar

| Papel | Métrica |
|---|---|
| **Principal** | PR-AUC (`average_precision_score`), por ser a mais informativa com classes raras, comparada com a prevalência |
| Complementares | ROC-AUC, precisão, *recall*, F1, matriz de confusão, `balanced_accuracy` |
| Calibração | Brier score e curva de fiabilidade, se houver tempo |

A exatidão (*accuracy*) isolada não é usada.

**Limiar:** não se assume 0,5. É escolhido **na validação**, por um critério
declarado à partida, e depois aplicado ao teste sem o alterar. Critérios
candidatos: maximizar o F1, ou fixar um *recall* mínimo (por exemplo 80%) e
reportar a precisão resultante. Mostra-se também a curva de precisão e *recall*
para que o ponto de operação seja visível.

**Incerteza:** além da variação entre folds, intervalos por *bootstrap* em
blocos (por mês ou por ano), porque os concelhos-dia do mesmo período são
correlacionados e um *bootstrap* simples subestimaria a incerteza.

## 7. Experiências

| # | Experiência | Pergunta |
|---|---|---|
| E1 | Baselines contra modelos | Os modelos batem o mínimo útil? |
| E2 | Comparação entre modelos | Qual compensa? |
| E3 | Ablação de famílias de features | Que informação ajuda? |
| E4 | Efeito de `Amin` (5, 10, 50, 100 ha) | Como muda a dificuldade? |
| E5 | Estratégias de desbalanceamento | O que ajuda de facto? |
| E6 | Aleatório contra temporal | Quanto otimismo há na divisão aleatória? |
| E7 | Aleatório contra espacial | Idem, para regiões |
| E8 | Espaciotemporal | RQ4 |
| E9 | Análise de falsos positivos e negativos | Onde e quando falha? |
| E10 | Importância das variáveis (permutação) e dependência parcial | O que usa o modelo? |

**Ablação (E3).**
- Tarefas 1 e 2: calendário → + histórico → + meteorologia (CEMS) →
  + localização.
- Tarefa 3: calendário e hora → + localização → + variáveis pendentes
  (`FonteAlerta`, áreas protegidas) → + índices FWI, quando estiverem
  confirmados.
- A comparação **com e sem localização** é essencial na avaliação espacial,
  para saber se o modelo só decora regiões.

**Cautelas na interpretação (E10).** A importância por permutação é
enganadora com variáveis correlacionadas (por exemplo, as contagens a 7 e a 30
dias), e importância não é causalidade.

## 8. Reprodutibilidade

- Seed global em `configs/config.yaml` (`seed: 42`). Para modelos
  estocásticos, vários seeds, reportando a variação.
- Cada execução principal regista **uma linha** em `results/experiments.jsonl`
  (não `.csv`, porque o `.gitignore` ignora CSV), com: versão do dataset,
  período, âmbito geográfico, tarefa, momento da previsão, `Amin`, conjunto de
  features, protocolo, modelo, hiperparâmetros, seed e métricas.
- Todos os conjuntos de features vêm das listas definidas no código
  (`FEATURES_AT_2359`, `FEATURES_AT_ALERT`).

## 9. Por decidir ou confirmar

- Os cortes temporais (treino até 2017, validação 2018–2020, teste desde 2021).
  São uma proposta: o teste cobre os 5 anos mais recentes e tem positivos
  suficientes, mas o corte pode ser revisto.
- Agrupamento espacial por distrito e a análise de sensibilidade por
  macro-regiões.
- Critério de escolha do limiar (F1 contra *recall* mínimo).
- Quais variáveis meteorológicas entram, depois de confirmada a hora de
  disponibilidade do CEMS.
- Tratamento dos possíveis duplicados (8 378 registos envolvidos) em lados
  diferentes da divisão.
- Se o custo computacional exigir subamostrar o treino nas Tarefas 1 e 2.
