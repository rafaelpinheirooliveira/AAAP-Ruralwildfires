# Metodologia experimental

Metodologia da execução do Milestone 2. Os números de cada divisão foram
calculados a partir dos datasets do repositório; as decisões ainda não
executadas ou confirmadas estão assinaladas.

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
| Aleatório | Tarefas 1–2: `StratifiedKFold`, 5 folds; Tarefa 3: 5 folds aleatórios por grupos concelho-dia, sem separar alertas do mesmo grupo; seed 42 | Fold de teste | Referência otimista |
| Temporal | 2001–2017 | 2021–2025 | Generalização para o futuro |
| Espacial | Distritos fora do fold, todos os anos | Distritos do fold | Generalização para regiões não vistas |
| Espaciotemporal | Distritos fora do fold, 2001–2017 | Distritos do fold, 2021–2025 | Ambas em simultâneo |

**Validação (escolha de hiperparâmetros e limiar):** 2018–2020 no protocolo
temporal. Nos protocolos espacial e espaciotemporal, um fold de três distritos
é reservado para validação e os restantes distritos (exceto o fold de teste)
para treino. O fold de validação roda para que não coincida com o de teste. Na
avaliação aleatória, cada fold de treino é subdividido numa validação interna;
na Tarefa 3, os grupos concelho-dia também não são separados na validação. Os
grupos são distribuídos aleatoriamente por fold; a prevalência de cada fold é
registada para revelar desequilíbrios residuais.

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

- Pesquisa de hiperparâmetros **pequena e justificada** (logística: `C=1` com
  pesos `None` ou `balanced`; HistGradientBoosting: 15 ou 31 folhas, 100
  iterações e pesos `balanced`), para limitar o custo e o risco de ajustar à
  validação.
- A escolha usa a métrica principal (secção 6), medida na validação.
- O estimador selecionado fica ajustado apenas ao treino; a validação escolhe
  o estimador e o limiar, e o teste é avaliado **uma única vez**.
- A variação por fold ou por seed é sempre reportada, e não apenas a média.

## 4. Modelos

| Modelo | Papel | Notas |
|---|---|---|
| Baseline de prevalência (`DummyClassifier`) | Mínimo útil | PR-AUC igual à prevalência |
| Baseline de histórico (regra: "houve incêndio nos últimos 7 dias") | Referência simples e interpretável (Tarefas 1 e 2) | Mostra o que o histórico dá sem aprendizagem |
| Regressão logística (`StandardScaler` + `LogisticRegression`) | Modelo linear | Imputação mediana; testa `class_weight=None` e `balanced` |
| HistGradientBoosting (`HistGradientBoostingClassifier`) | Ensemble sequencial de árvores | Compara 15 e 31 folhas, 100 iterações e `class_weight=balanced` |

Todos de `scikit-learn`, o mesmo das aulas. A floresta aleatória foi retirada
da primeira execução devido ao custo em milhões de linhas; o boosting cobre a
família de ensembles de árvores. Esta decisão deve ser explicitada no relatório.

**Conjuntos usados nesta avaliação sem CEMS:** Tarefas 1–2 usam as nove
features de calendário e histórico de `FEATURES_AT_2359`. A Tarefa 3 usa seis
features: mês, dia do ano, dia da semana, hora do alerta e latitude/longitude.
Os códigos de distrito/concelho e as coordenadas projetadas, embora disponíveis
no inventário de dez features do alerta, ficam fora deste conjunto principal:
os códigos exigiriam codificação categórica e X/Y são uma representação
redundante das coordenadas geográficas. A inclusão dessas representações fica
para uma ablação específica, não para a comparação base entre protocolos.

## 5. Desbalanceamento

| Tarefa (`Amin` = 10 ha) | Rácio (1 positivo em N observações) |
|---|---:|
| 1 | 1:9 (11,09%) |
| 2 | 1:182 (0,55%) |
| 3 | 1:31 (3,19%) |

A Tarefa 2 é a mais exigente, e piora com `Amin` maior (1:799 a 100 ha).
Estratégias a comparar na experiência E5:

1. Sem tratamento (`class_weight=None`).
2. Peso de classe (`class_weight="balanced"`).
3. Subamostragem aleatória dos negativos sem reposição, até 10 negativos por
   positivo, **apenas no treino**.

Sobreamostragem sintética (SMOTE) não é a primeira escolha: os dados incluem
variáveis de calendário e localização, para as quais interpolar exemplos
sintéticos tem pouco sentido. Só será testada se sobrar tempo, e sempre dentro
do treino.

Na E5, a regressão logística (`C=1`) é mantida fixa para isolar o efeito das
estratégias; executa-se a comparação nas três tarefas e nos quatro protocolos.
Cada estratégia usa a mesma divisão, a validação e o teste conservam a
prevalência natural, e o limiar F1 é escolhido separadamente na validação.
Subamostrar altera a prevalência de treino para, no máximo, 1:10; as métricas
de probabilidades, em particular Brier, devem ser lidas com cautela porque não
há recalibração posterior. Esta E5 não compara o efeito das estratégias no
HistGradientBoosting.

## 6. Métricas e limiar

| Papel | Métrica |
|---|---|
| **Principal** | PR-AUC (`average_precision_score`), por ser a mais informativa com classes raras, comparada com a prevalência |
| Complementares | ROC-AUC, precisão, *recall*, F1, matriz de confusão, `balanced_accuracy` |
| Calibração | Brier score e curva de fiabilidade, se houver tempo |

A exatidão (*accuracy*) isolada não é usada.

**Limiar:** não se assume 0,5 para os modelos aprendidos e o baseline de
histórico. É escolhido **na validação** maximizando F1 e aplicado ao teste sem
o alterar. O baseline de prevalência usa 0,5, pois a sua pontuação é constante.

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

### Resultados da avaliação sem CEMS

Foram concluídos os protocolos aleatório, espacial e espaciotemporal para as
três tarefas, usando logística e HistGradientBoosting, sem features
meteorológicas. São 102 registos (17 dobras por tarefa e dois modelos) no
`results/experiments.jsonl`; as métricas por dobra, prevalências, parâmetros
selecionados na validação e limiares estão nesse ficheiro.

| Tarefa | Protocolo | AP baseline (prevalência média) | Histórico (AP média) | Logística (AP média) | HistGradientBoosting (AP média) |
|---|---|---:|---:|---:|---:|
| 1 | Aleatório (5 folds) | 0,1109 | 0,4256 | 0,4809 | **0,5127** |
| 1 | Espacial (6 folds) | 0,1133 | 0,3981 | 0,4478 | **0,4799** |
| 1 | Espaciotemporal (6 folds) | 0,0615 | 0,2137 | 0,2581 | **0,2803** |
| 2 | Aleatório (5 folds) | 0,0055 | 0,0465 | 0,0586 | **0,0920** |
| 2 | Espacial (6 folds) | 0,0058 | 0,0498 | 0,0596 | **0,0832** |
| 2 | Espaciotemporal (6 folds) | 0,0033 | 0,0392 | 0,0436 | **0,0660** |
| 3 | Aleatório (5 folds) | 0,0319 | — | 0,0613 | **0,1072** |
| 3 | Espacial (6 folds) | 0,0346 | — | 0,0546 | **0,0727** |
| 3 | Espaciotemporal (6 folds) | 0,0477 | — | 0,0627 | **0,0851** |

A AP média supera a prevalência e o baseline histórico nas seis combinações
das Tarefas 1–2. Na Tarefa 3, ambos os modelos superam a prevalência.
HistGradientBoosting tem a maior AP média nas nove combinações, embora a
logística seja melhor em algumas dobras individuais da Tarefa 3. A diferença entre
protocolos reflete, além da dificuldade de generalização, as diferentes
prevalências e conjuntos de teste; a AP não deve ser interpretada sem o
baseline de cada linha. Estes resultados fecham a avaliação comparativa de
referência sem CEMS; não substituem a ablação de features nem a análise de
erros.

### E5 — estratégias de desbalanceamento

A E5 comparou regressão logística com `C=1`, sem tratamento, pesos de classe
`balanced` e subamostragem de negativos até 10:1, nas três tarefas e nos quatro
protocolos. Foram registadas 162 execuções (54 dobras × 3 estratégias) em
`results/e5_imbalance.jsonl`; cada dobra usa a mesma divisão entre estratégias.
A validação e o teste mantêm a prevalência natural, e cada limiar F1 é escolhido
separadamente na validação. A tabela completa de AP e F1 está no
[README](../README.md).

Não houve estratégia universalmente superior. Para a Tarefa 2, a
subamostragem aumentou ligeiramente a AP temporal (0,0383 → 0,0401) e aleatória
(0,0586 → 0,0589), mas não a espacial (0,0604 → 0,0594) ou espaciotemporal
(0,0453 → 0,0452). Na Tarefa 3 as diferenças foram muito pequenas. Na Tarefa 1
o treino já tinha menos de dez negativos por positivo, pelo que a subamostragem
não removeu linhas. As comparações E5 foram feitas apenas com logística; não
permitem determinar a melhor estratégia para HistGradientBoosting.

### E9 — análise de erros

A E9 caracteriza, sem voltar a selecionar modelos no teste, os falsos positivos
e negativos do protocolo temporal principal (teste 2021–2025) para logística e
HistGradientBoosting nas três tarefas. O modelo e o limiar são reproduzidos
pela seleção na validação (2018–2020); o script confirma parâmetros, limiar e
métricas contra `results/experiments.jsonl` antes de resumir os erros por ano,
mês, distrito e concelho. Na Tarefa 3 acrescenta-se a hora do alerta; nas
Tarefas 2 e 3, os erros são ainda decompostos pela área ardida final. Os
resultados agregados das seis combinações (três tarefas × dois modelos) ficam
em `results/e9_error_analysis.json`. A taxa de falsos negativos é elevada nas
Tarefas 2 e 3, e a maioria dos falsos negativos destas tarefas está na classe
de menor dimensão significativa (10–50 ha). A tabela e a discussão estão no
[README](../README.md). A distribuição foi analisada apenas no teste temporal;
não se presume que se repita nos outros protocolos.

### Sensibilidade a possíveis duplicados (Tarefa 3)

A marca `flag_possivel_duplicado` assinala 8 378 registos (mesma freguesia e
mesmo minuto de alerta); 133 são positivos para `A ≥ 10 ha`. Como são possíveis
duplicados, não se removem da análise principal. Executou-se uma sensibilidade
que exclui todos os sinalizados, para os quatro protocolos, com baseline de
prevalência, logística e HistGradientBoosting. Cada registo inclui a indicação
de exclusão e a contagem removida.

| Protocolo | Prevalência: completo → sem sinalizados | Logística: AP completo → sem sinalizados | HistGradientBoosting: AP completo → sem sinalizados |
|---|---:|---:|---:|
| Aleatório | 3,186% → 3,213% | 0,0613 → 0,0615 | 0,1072 → 0,1074 |
| Temporal | 4,455% → 4,458% | 0,0680 → 0,0682 | 0,1159 → 0,1153 |
| Espacial | 3,459% → 3,469% | 0,0546 → 0,0547 | 0,0727 → 0,0742 |
| Espaciotemporal | 4,770% → 4,773% | 0,0627 → 0,0626 | 0,0851 → 0,0879 |

As diferenças médias são pequenas, embora algumas dobras espaciais e
espaciotemporais do HistGradientBoosting variem mais. A exclusão altera a
prevalência; por isso a AP é sempre interpretada contra o baseline de cada
população. Além disso, os grupos de suspeitas não são separados pelas
divisões principais: a Tarefa 3 aleatória mantém concelho-dia, a espacial
mantém distrito e as temporais mantêm período. A sensibilidade mede o efeito
da população sinalizada, não corrige fuga entre divisões.

## 8. Reprodutibilidade

- Seed global em `configs/config.yaml` (`seed: 42`). Para modelos
  estocásticos, vários seeds, reportando a variação.
- Cada execução principal regista **uma linha** em `results/experiments.jsonl`
  (não `.csv`, porque o `.gitignore` ignora CSV), com: versão do dataset,
  período, âmbito geográfico, tarefa, momento da previsão, `Amin`, conjunto de
  features, protocolo, modelo, hiperparâmetros, seed e métricas.
- As execuções E5 ficam separadas em `results/e5_imbalance.jsonl`, com a
  estratégia e o número de linhas/positivos usados no ajuste; `--resume`
  distingue também as estratégias.
- A subamostragem usa `seed + índice da dobra` e seleção sem reposição.
- Para repetir uma combinação, usa-se
  `python src/run_experiments.py --task 2 --protocol temporal --models logistic --imbalance-strategy all --output results/e5_reproduction.jsonl`;
  repetir para as restantes tarefas e protocolos. `--resume` pode ser
  acrescentado para continuar uma execução interrompida.
- Todos os conjuntos de features vêm das listas definidas no código
  (`FEATURES_AT_2359`, `FEATURES_AT_ALERT`). As ablações CEMS acrescentam
  explicitamente os índices de d−1. A implementação atual usa as sete
  componentes no atraso de um dia; as janelas de 3 e 7 dias são geradas, mas
  ainda não fazem parte das experiências do runner.
- O runner permite retomar uma execução com `--resume`, saltando combinações
  tarefa/alvo/protocolo/conjunto de features/dobra/modelo já presentes no
  ficheiro de saída.
- `run_experiments.py` aceita `--seed`, permitindo medir a variação de divisões
  aleatórias e inicializações estocásticas sem alterar a seed principal.
- `bootstrap_uncertainty.py` reconstrói as experiências de seed 42,
  ajusta o estimador aprovado na validação e usa bootstrap com substituição
  de meses completos no conjunto de teste. Os intervalos são de 95% por
  defeito e ficam em `results/uncertainty.jsonl`.

### Incerteza por bootstrap mensal

O ficheiro `results/uncertainty.jsonl` contém 108 intervalos de seed 42:
três tarefas × logística/HistGradientBoosting × (uma dobra temporal, cinco
aleatórias, seis espaciais e seis espaciotemporais). Cada intervalo usa 1000
réplicas a resamplear meses completos do conjunto de teste. O bloco mensal
preserva a dependência temporal dentro de cada mês melhor do que um bootstrap
de linhas independentes.

Para a comparação aleatória, a AP média de seeds 42, 43 e 44 variou menos de
0,001 em todas as tarefas/modelos. Os intervalos mensais não substituem a
variação entre dobras ou macro-regiões; reportam a incerteza amostral de cada
dobra individual e devem ser interpretados juntamente com o intervalo entre
resultados espaciais.

## 9. Por decidir ou confirmar

- Os cortes temporais estão implementados para a execução inicial; a análise
  de sensibilidade a outros cortes permanece por fazer.
- Os folds distritais estão implementados; a análise de sensibilidade por
  macro-regiões permanece por fazer.
- O critério inicial do limiar é F1; a alternativa de fixar um *recall* mínimo
  não está implementada.
- A hora física e a latência de disponibilização do CEMS continuam por
  confirmar; por isso CEMS não é feature principal e qualquer ablação é
  retrospetiva.
- A divisão aleatória da Tarefa 3 agrupa concelho-dia; a verificação de
  sensibilidade excluindo os registos assinalados como possíveis duplicados
  foi executada nos quatro protocolos, sem os tratar como duplicados
  confirmados.
- A avaliação principal sem CEMS está concluída nos quatro protocolos; a
  experiência temporal está resumida no README e os resultados por dobra estão
  no JSONL.
- A sensibilidade a `Amin` (5, 10, 50 e 100 ha) está concluída nas Tarefas 2 e
  3 nos quatro protocolos. Os positivos diminuem de 22 255 para 3 178 na
  população Tarefa 2 e de 26 236 para 3 416 na Tarefa 3; a AP também diminui
  em geral, refletindo a maior raridade.
- A E5 está concluída para a logística, nas três tarefas e quatro protocolos;
  os resultados não determinam a estratégia ótima para HistGradientBoosting.
- A E9 foi concluída no teste temporal principal para as três tarefas e ambos
  os modelos; a análise de erro por dobra dos outros protocolos permanece por
  fazer.
- A importância por permutação e dependência parcial (E10) permanece por
  executar.
