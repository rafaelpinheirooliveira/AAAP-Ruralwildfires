# Revisão de literatura e contextualização (rascunho atualizado)

Rascunho para o Milestone 1, atualizado após consulta dos textos integrais de
Caiado e Marques (metodologia e conclusões) e Laghmich et al., e da introdução
e discussão/conclusões de Roberts et al. As sínteses abaixo distinguem os
resultados dos artigos das inferências para este projeto.

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
| Caiado e Marques (2025) | Prevê ocorrência diária em Lisboa, Porto, Setúbal e Viseu (2001–2023), por três classes que o artigo chama *settlements*, matos e agricultura; usa ICNF, meteorologia do IPMA, regressão logística, Random Forest, XGBoost e SMOTE | Comparação mais próxima da Tarefa 1; alerta para validação aleatória e para verificar o significado da classe *settlements* | Metodologia e conclusões |
| Laghmich et al. (2026) | Mapeia suscetibilidade à escala nacional com amostras pontuais MODIS, variáveis ambientais estáticas/agregadas e quatro modelos; reporta validação cruzada espacial de 78 blocos | Exemplo português de validação espacial, mas não de previsão diária nem de generalização temporal | Artigo integral |
| Roberts et al. (2017) | Síntese, simulações e estudos de caso sobre validação com dependência temporal, espacial, hierárquica ou filogenética | Fundamenta a escolha dos protocolos e as cautelas sobre escala dos blocos e extrapolação | Introdução e discussão/conclusões |
| Saito e Rehmsmeier (2015) | Mostra que as curvas de precisão e *recall* são mais informativas do que as ROC em dados muito desbalanceados | Justifica a PR-AUC como métrica principal | Resumo |
| Vitolo et al. (2020) | Descreve o conjunto GEFF-ERA5 de índices de perigo de incêndio (sistema canadiano) com reanálise ERA5 | Fonte da meteorologia (CEMS); explica que os índices medem condições de propagação, não a ignição | Resumo e descrição do dataset |
| Jain et al. (2020) | Revisão de aprendizagem automática em ciência e gestão de incêndios | Enquadramento geral e vocabulário | Resumo |

## 3. Síntese dos três artigos prioritários

**Aprendizagem automática para ocorrência de incêndios em Portugal.**
Caiado e Marques (2025) usam registos ICNF de 2001–2023 em quatro distritos e
agregam a ocorrência por dia e por classe de área/uso, combinando-os com
temperatura, precipitação e humidade do IPMA. As variáveis de ano e mês são
codificadas *one-hot*. Comparam regressão logística, Random Forest e XGBoost;
avaliam exatidão, precisão, *recall*, F1 e ROC-AUC. Experimentam divisões
treino/teste 60:40, 70:30 e 80:20, escolhem 70:30 e dizem estratificar para
preservar a distribuição das classes. A metodologia menciona validação cruzada
para afinação; a avaliação relatada continua a ser uma divisão aleatória, sem
teste temporal ou por região não vista. O SMOTE é aplicado ao treino e tende a
aumentar o *recall* de classes minoritárias à custa da precisão.

Os autores encontram F1 acima de 0,93 para matos; *settlements* é a classe mais
difícil, e agricultura tem desempenho intermédio. XGBoost é destacado nas
conclusões, mas os quadros mostram que o melhor modelo depende da classe, da
métrica e da divisão. O artigo não reporta PR-AUC. Para este projeto, é
referência direta para a Tarefa 1 e para comparação de modelos, mas não prova
generalização a anos futuros ou a outros concelhos.

**Cuidado com a categoria *settlements*.** O artigo usa esse termo como se
representasse ignições em povoações/WUI, mas os registos ICNF distinguem
`AreaPov_ha` como área ardida em **povoamentos florestais**, não em
povoamentos/assentamentos urbanos. O texto não torna suficientemente clara a
correspondência entre a categoria e a coluna original. Não se deve repetir a
interpretação urbana sem confirmar a definição dos dados usados pelos autores.

**Suscetibilidade espacial em Portugal.** Laghmich et al. (2026) não prevêem o
incêndio de amanhã: estimam onde a presença histórica de fogo é mais provável.
Usam 1 000 pontos positivos de deteção ativa MODIS (2015–2024) e 1 000 pontos
sem deteção, escolhidos para obter uma amostra equilibrada. Os seis preditores
são NDVI médio, uso/cobertura do solo, declive, temperatura da superfície,
vento e distância a povoações; são estáticos ou agregados no período. Comparam
Random Forest, CART, Gradient Boosting e XGBoost, com afinação por grelha e
validação cruzada espacial descrita como 78 blocos. Reportam para XGBoost
exatidão de 90,03%, precisão de 86,17%, *recall* de 87,10%, F1 de 85,12% e
AUC de 0,951.

É uma referência relevante para justificar avaliação espacial em Portugal, mas
os resultados não são comparáveis diretamente com as tarefas deste projeto: a
amostra 1:1 foi construída por amostragem, não tem a prevalência real de
concelho-dia, e os autores mapeiam suscetibilidade a partir de variáveis
estáticas/agregadas, não fazem previsão temporal. A validação de blocos não
substitui um teste em anos futuros. O artigo não explicita com detalhe
suficiente a geometria/distância dos 78 blocos para reproduzir exatamente a
partição apenas a partir do texto. As previsões pontuais são ainda interpoladas
por *simple kriging* para produzir mapas de 1 km.

Os próprios autores assinalam viés de amostragem e sub-registo, resolução
espacial variável e ausência de variáveis temporais sazonais. Há também uma
inconsistência interna nos valores de área ardida de janeiro a agosto de 2025:
o artigo apresenta 25 429,5 ha numa passagem e 254 295 ha noutra; não reutilizar
esse valor sem confirmação independente.

**Validação com estrutura espaciotemporal.** Roberts et al. (2017) explicam
duas fontes de otimismo na validação aleatória: observações de treino e teste
podem continuar dependentes, e preditores correlacionados com espaço/tempo
podem fazer o modelo aprender essa estrutura. O problema pode persistir mesmo
quando os resíduos parecem pouco autocorrelacionados ou o modelo inclui uma
estrutura de correlação. Para previsões em novos períodos ou regiões, a
validação deve bloquear a estrutura relevante; blocos temporais contíguos são
análogos aos espaciais.

Os autores não propõem um único esquema universal. A escala e a organização
dos blocos devem corresponder ao objetivo de previsão e à dependência observada.
Blocos podem restringir o espaço de preditores e criar extrapolação, tornando
as estimativas demasiado pessimistas quando o objetivo é interpolar. Também
podem deixar folds sem positivos ou negativos em dados raros/desbalanceados.
Recomendam avaliar a estrutura nos dados brutos, escolher os blocos conforme
objetivo e escala de autocorrelação, e inspecionar o equilíbrio/prevalência e a
extrapolação de cada fold.

Para a RQ4, isto apoia manter a validação aleatória apenas como referência e
reportar separadamente os testes temporal, espacial e espaciotemporal. Também
justifica a análise por macro-regiões e a verificação de vizinhança entre
distritos: agrupar por distrito, por si só, não garante independência espacial.

**Desbalanceamento e métricas.** Saito e Rehmsmeier (2015) sustentam a escolha
da PR-AUC. A taxa base da Tarefa 2 (0,55%) e a sua variação entre treino e
teste (0,66% e 0,32%) reforçam que a PR-AUC deve ser lida ao lado da
prevalência do conjunto de teste.

**Meteorologia.** O conjunto GEFF-ERA5 (Vitolo et al., 2020) fornece os
índices do sistema canadiano diariamente e desde 1940. Os índices descrevem se
as condições favorecem a propagação de um fogo, condicionado a existir
ignição, por isso não substituem informação sobre as causas da ignição.

## 4. Lacuna que o projeto procura preencher

Os estudos prioritários cobrem partes diferentes do problema: Caiado e Marques
avaliam ocorrência diária em quatro distritos com divisão aleatória; Laghmich
et al. fazem validação espacial para um mapa de suscetibilidade, com variáveis
estáticas/agregadas e uma amostra equilibrada. Nas pesquisas feitas **não
encontrei** um estudo para Portugal que:

1. avalie previsão de incêndios com protocolos temporal, espacial e
   espaciotemporal comparados com a divisão aleatória, no mesmo conjunto de
   dados e em todo o território continental; e
2. preveja a **dimensão** do incêndio (acima de um limiar) em dois momentos
   distintos: antes de haver incêndio (Tarefa 2) e no momento do alerta
   (Tarefa 3).

Esta é uma lacuna de trabalho a confirmar, não uma afirmação de inexistência:
resulta de pesquisas limitadas e deve ser verificada com uma pesquisa mais
completa antes de ser apresentada como contribuição original no relatório.

## 5. Por verificar ou ler

- **Saito e Rehmsmeier (2015), Vitolo et al. (2020) e Jain et al. (2020):**
  confirmar no texto integral as afirmações resumidas a partir do resumo ou da
  descrição do dataset.
- **Jain et al. (2020):** as fontes consultadas diferem no número do fascículo
  (28(3) e 28(4)); o artigo de Caiado e Marques cita 28, 478–505.
- Trabalho **"Predicting burned areas: a machine learning approach"**
  (seis distritos, dados 2001–2023, aplicação a seguros): identificar autoria e
  tipo de publicação antes de citar.
- **Cortez e Morais (2007)**, citado por Caiado e Marques como trabalho pioneiro
  em Portugal; não verificado diretamente.
- **Categorias em Caiado e Marques (2025):** confirmar nos dados/artigo a
  correspondência exata entre *settlements* e a coluna ICNF. Até essa
  confirmação, não interpretar a classe como área urbana.
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
  learning approach in Portugal. *South-east European Forestry, 17*(1), 26014.
  https://doi.org/10.15177/seefor.26-014
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
