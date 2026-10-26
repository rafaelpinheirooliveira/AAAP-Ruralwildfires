# Revisão de literatura e contextualização (rascunho)

Rascunho para o Milestone 1. Reúne os trabalhos encontrados, o que cada um
acrescenta ao projeto e como se relacionam com as RQ1 a RQ4. **Não substitui a
leitura dos artigos:** a coluna "Leitura" indica o que foi efetivamente lido ao
preparar este documento, e as citações do relatório final devem ser
confirmadas nos próprios artigos.

## 1. Contexto do problema

Os incêndios rurais são um problema recorrente em Portugal, e a literatura
aplica aprendizagem automática a vários problemas distintos: ocorrência,
suscetibilidade, área ardida e propagação. Uma revisão abrangente identificou
cerca de 300 trabalhos de aprendizagem automática em ciência dos incêndios até
ao fim de 2019, onde os métodos mais usados incluem as florestas aleatórias
(Jain et al., 2020). Este projeto situa-se no domínio "ocorrência e risco" e
acrescenta a previsão da dimensão do incêndio (Tarefas 2 e 3).

## 2. Trabalhos considerados

| Referência | O que faz | Relevância para este projeto | Leitura |
|---|---|---|---|
| Caiado e Marques (2025) | Compara regressão logística, floresta aleatória e XGBoost na previsão de ocorrência em 4 distritos (Lisboa, Porto, Setúbal, Viseu), com dados do ICNF 2001–2023 e meteorologia do IPMA, separando três categorias de uso do solo (a que os autores chamam *settlements*, matos e agricultura). Aplica SMOTE | É o trabalho mais próximo da Tarefa 1: mesma fonte (ICNF), mesma família de modelos, tratamento do desbalanceamento | Completa |
| Laghmich et al. (2026) | Compara quatro classificadores de conjunto (floresta aleatória, CART, gradient boosting, XGBoost) para suscetibilidade em Portugal com **validação cruzada por blocos espaciais** | Referência para o protocolo espacial (RQ4) | Resumo |
| Roberts et al. (2017) | Revê estratégias de validação cruzada para dados com estrutura temporal, espacial ou hierárquica; recomenda validação por blocos quando há dependências | Justifica os protocolos temporal, espacial e espaciotemporal | Resumo e introdução |
| Saito e Rehmsmeier (2015) | Mostra que as curvas de precisão e *recall* são mais informativas do que as ROC em dados muito desbalanceados | Justifica a PR-AUC como métrica principal | Resumo |
| Vitolo et al. (2020) | Descreve o conjunto GEFF-ERA5 de índices de perigo de incêndio (sistema canadiano) com reanálise ERA5 | Fonte da meteorologia (CEMS); explica que os índices medem condições de propagação, não a ignição | Resumo e descrição do dataset |
| Jain et al. (2020) | Revisão de aprendizagem automática em ciência e gestão de incêndios | Enquadramento geral e vocabulário | Resumo |

## 3. Síntese

**Aprendizagem automática para ocorrência de incêndios em Portugal.**
Caiado e Marques (2025) usam dados do ICNF e do IPMA e concluem que os fogos
em matos são os mais previsíveis, com F1 superior a 0,93, e que a categoria
*settlements* é a mais difícil. Segundo os autores, o XGBoost superou de forma
consistente os modelos lineares, embora nas tabelas de Lisboa a regressão
logística tenha a melhor exatidão em alguns casos. O SMOTE melhora o *recall*
à custa da precisão. Há três diferenças face a este projeto:

- A divisão é **aleatória e estratificada** (70:30), que o enunciado trata como
  referência otimista. Os próprios autores indicam como trabalho futuro testar
  a transferibilidade entre regiões.
- O ano entra como variável (codificação *one-hot*) e aparece entre as mais
  importantes. Os autores interpretam-no como reflexo de mudanças de política,
  uso do solo ou do sistema de registo, e é exatamente o tipo de informação que
  não generaliza para o futuro.
- A métrica principal é o F1, com ROC-AUC e exatidão, e não a PR-AUC.

**Validação com estrutura espaciotemporal.** Roberts et al. (2017) mostram que
a validação cruzada aleatória subestima o erro quando os dados têm dependências
temporais ou espaciais, e recomendam blocos. Laghmich et al. (2026) aplicam
blocos espaciais a dados portugueses. Este projeto estende a ideia à dimensão
temporal e à combinação das duas (RQ4).

**Desbalanceamento e métricas.** Saito e Rehmsmeier (2015) sustentam a escolha
da PR-AUC. A taxa base da Tarefa 2 (0,55%) e a sua variação entre treino e
teste (0,66% e 0,32%) reforçam que a PR-AUC deve ser lida ao lado da
prevalência do conjunto de teste.

**Meteorologia.** O conjunto GEFF-ERA5 (Vitolo et al., 2020) fornece os
índices do sistema canadiano diariamente e desde 1940. Os índices descrevem se
as condições favorecem a propagação de um fogo, condicionado a existir
ignição, por isso não substituem informação sobre as causas da ignição.

## 4. Lacuna que o projeto procura preencher

Nas pesquisas feitas **não encontrei** um estudo para Portugal que:

1. avalie previsão de incêndios com protocolos temporal, espacial e
   espaciotemporal comparados com a divisão aleatória, em todo o território
   continental; e
2. preveja a **dimensão** do incêndio (acima de um limiar) em dois momentos
   distintos: antes de haver incêndio (Tarefa 2) e no momento do alerta
   (Tarefa 3).

Esta afirmação resulta de pesquisas limitadas e deve ser verificada com uma
pesquisa mais completa antes de ser escrita como contribuição no relatório.

## 5. Por verificar ou ler

- **Texto completo** de Laghmich et al. (2026), Roberts et al. (2017) e Jain et
  al. (2020), e o artigo de Vitolo et al. (2020), para citar com rigor.
- **DOI de Laghmich et al. (2026):** o portal indica `10.15177/seefor.26-014`
  na página do artigo e `seefor.26014` na citação; confirmar.
- **Jain et al. (2020):** as fontes consultadas diferem no número do fascículo
  (28(3) e 28(4)); o artigo de Caiado e Marques cita 28, 478–505.
- Trabalho **"Predicting burned areas: a machine learning approach"**
  (seis distritos, dados 2001–2023, aplicação a seguros): identificar autoria e
  tipo de publicação antes de citar.
- **Cortez e Morais (2007)**, citado por Caiado e Marques como trabalho pioneiro
  em Portugal; não verificado diretamente.
- **Categorias de uso do solo em Caiado e Marques (2025):** chamam *settlements*
  à categoria que, segundo o ICNF, parece corresponder a `AreaPov_ha`, isto é,
  povoamentos **florestais** (no dicionário do professor, "área ardida de
  povoamentos florestais"). Pode ser um problema de tradução; confirmar antes
  de citar a interpretação dos autores sobre fogos em zonas urbanas.
- **Pesquisas a fazer:** previsão da área ardida ou de "grandes incêndios",
  previsão de propagação em Portugal, e validação cruzada espacial em risco de
  incêndio na Europa mediterrânica.

## Referências

- Caiado, J., & Marques, M. (2025). Predicting wildfire occurrences in Portugal
  using machine learning classification models. *Ecological Informatics, 92*,
  103455. https://doi.org/10.1016/j.ecoinf.2025.103455
- Jain, P., Coogan, S. C. P., Subramanian, S. G., Crowley, M., Taylor, S., &
  Flannigan, M. D. (2020). A review of machine learning applications in wildfire
  science and management. *Environmental Reviews, 28*(4), 478–505.
  https://doi.org/10.1139/er-2020-0019
- Laghmich, M. A., Ariche, M., & Ahayk, B. (2026). Assessing wildfire
  susceptibility in Mediterranean forest ecosystems: a spatial ensemble machine
  learning approach in Portugal. *South-east European Forestry, 17*(1), 26016.
  (DOI a confirmar.)
- Roberts, D. R., Bahn, V., Ciuti, S., Boyce, M. S., Elith, J.,
  Guillera-Arroita, G., et al. (2017). Cross-validation strategies for data with
  temporal, spatial, hierarchical, or phylogenetic structure. *Ecography,
  40*(8), 913–929. https://doi.org/10.1111/ecog.02881
- Saito, T., & Rehmsmeier, M. (2015). The precision-recall plot is more
  informative than the ROC plot when evaluating binary classifiers on
  imbalanced datasets. *PLOS ONE, 10*(3), e0118432.
  https://doi.org/10.1371/journal.pone.0118432
- Vitolo, C., Di Giuseppe, F., Barnard, C., Coughlan, R., San-Miguel-Ayanz, J.,
  Libertá, G., & Krzeminski, B. (2020). ERA5-based global meteorological
  wildfire danger maps. *Scientific Data, 7*, 216.
  https://doi.org/10.1038/s41597-020-0554-z
