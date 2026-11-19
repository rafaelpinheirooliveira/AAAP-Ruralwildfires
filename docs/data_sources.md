# Fontes de dados

Cada fonte é documentada com: instituição, descrição, cobertura temporal e
espacial, resolução, método de aquisição e limitações.

Estado: **ICNF e CAOP verificados; o pedido de teste CEMS foi executado e o
NetCDF aberto. Falta reconciliar a hora indicada no guia com a coordenada
temporal do ficheiro.**

| # | Fonte | Estado |
|---|---|---|
| 1 | Registos de incêndios rurais SGIF (ICNF) | Documentada |
| 2 | Limites administrativos (CAOP, DGT) | Documentada e obtida; ficheiros fora do Git |
| 3 | Índices de perigo de incêndio diários (CEMS, Copernicus) | Pedido de teste executado; interpretação da hora pendente |

---

## 1. Registos de incêndios rurais SGIF (ICNF)

### Identificação

| Campo | Valor |
|---|---|
| Instituição responsável | Instituto da Conservação da Natureza e das Florestas (ICNF) |
| Sistema de origem | Sistema de Gestão de Informação de Incêndios Florestais (SGIF) |
| Página de referência do ICNF | https://www.icnf.pt/florestas/gfr/gfrgestaoinformacao/estatisticas |
| Ficheiro usado | `Combined_Registos_Incendios_SGIF_2001_2025.xlsx` (142 MB, fornecido pelo professor) |
| Dicionário de dados | `docs/icnf_fire_desc_pt.md` (fornecido pelo professor) |
| Auditoria de disponibilidade | `docs/auditoria_disponibilidade_features_sgif_pt.md` (fornecida pelo professor) |
| Estudo citado na auditoria | `docs/estudo_features_temporais_modelos_incendio_pt.md` (referido no ponto 6 da auditoria; não disponível) |

### Descrição

Cada linha é uma ocorrência de incêndio rural registada no SGIF, com 41
colunas: identificação e data, área ardida, tempos da ocorrência, localização
administrativa, coordenadas do ponto de início, índices meteorológicos de
perigo de incêndio (sistema canadiano FWI), causa e origem do alerta.

### Cobertura e resolução

| Dimensão | Valor |
|---|---|
| Registos | 497 478 (sem `Codigo_SGIF` duplicado nem linhas repetidas) |
| Cobertura temporal | 2001-01-05 a 2025-12-31 |
| Cobertura espacial | Portugal continental: 18 distritos, 278 concelhos |
| Resolução espacial | Ponto de início (latitude/longitude, ETRS89/PT-TM06 e coordenadas militares), com freguesia, concelho e distrito |
| Resolução temporal | Minuto em `DataHoraAlerta` (96% dos registos têm minutos diferentes de zero) |

### Aquisição

O ficheiro combinado e o dicionário de dados foram **fornecidos pelo
professor** no âmbito da UC. A origem institucional é o ICNF (SGIF), mas o
projeto não repete o descarregamento a partir do site.

Segundo a auditoria de disponibilidade, o ficheiro combinado resulta do
empilhamento de três ficheiros por período (2001–2010, 2011–2020, 2021–2025),
sem *join* por chave. Reconciliação: 279 743 + 177 129 + 40 606 = 497 478
linhas, 41 colunas idênticas nos três ficheiros. Só o ficheiro combinado foi
usado neste projeto, e as contagens foram reconfirmadas ao lê-lo. O ficheiro
não é versionado no Git.

### Hora de disponibilidade por grupo de colunas

| Grupo | Colunas | Disponível em d−1 23:59 (Tarefas 1–2)? | Disponível em `DataHoraAlerta` (Tarefa 3)? |
|---|---|---|---|
| Data e hora do alerta | `DataHoraAlerta` | Não (é o evento) | Sim |
| Localização do ponto de início | `DTCCFR`, `Concelho`, `Freguesia`, `Latitude`, `Longitude`, coordenadas | Não (só existe com o fogo); usar o território como unidade | Sim |
| Área ardida | `AreaPov_ha`, `AreaMato_ha`, `AreaAgric_ha`, `AreaTotal_ha`, `ClasseArea` | Não | **Não: usada apenas para construir o alvo** |
| Tempos posteriores | `DataHora_Extincao`, `Duracao_Horas`, `IncSup24horas` | Não | **Não** |
| Primeira intervenção | `DataHora_PrimeiraIntervencao` | Não | **A decidir** (ocorre depois do alerta; ausente em 2001–2007) |
| Causa | `CodCausa`, `TipoCausa`, `GrupoCausa`, `DescricaoCausa` | Não | **Não** (apurada depois; cobertura 8% em 2001 e 99,8% em 2025) |
| Origem do alerta | `FonteAlerta` | Não | **A decidir** (cobertura cai para 78% em 2025) |
| Áreas protegidas | `RNAP`, `RNMPF` | Não | Provavelmente sim, a confirmar (ausência ambígua) |
| Índices FWI | `DSR`, `FWI`, `ISI`, `DC`, `DMC`, `FFMC`, `BUI` | Não (só existem em dias com fogo) | **A confirmar** (hora de cálculo desconhecida) |

### Limitações e problemas conhecidos

**Valores em falta**

| Coluna | Em falta | Nota |
|---|---:|---|
| `DataHora_PrimeiraIntervencao` | 43,2% | Ausência estrutural em 2001–2007 |
| `CodCausa` e restantes de causa | 50,3% | Cobertura cresce de 8% (2001) para 99,8% (2025) |
| `RNAP` | 96,7% | Vazio pode significar "não aplicável" |
| `RNMPF` | 97,7% | Idem |
| `FonteAlerta` | 0,6% | Falha concentrada em 2024–2025 |
| `FWI`, `DSR` | 0,12% | |
| `DataHora_Extincao` | 0,13% | |

**Anomalias a tratar na limpeza**

- **`AreaTotal_ha = 0`:** 15 164 registos, cerca de 98% entre 2001 e 2012, todos classificados em `]0 a 1 ha[`, o que contradiz a notação do intervalo. Decisão pendente: manter, excluir ou tratar como "área não apurada".
- **Áreas residuais e arredondadas:** além dos 15 164 registos com área zero,
  há 17 595 com `0 < área < 0,001 ha` (10 m²), incluindo valores como 1e-12, que
  parecem marcadores de "área residual". As áreas estão também muito
  concentradas em valores redondos (0,01, 0,05, 0,1, 0,5 ha). Não afeta o
  `Amin` (≥ 5 ha), mas convém não usar a área em escala fina como feature
  nem como alvo de regressão.
- **`Hora` ≠ hora de `DataHoraAlerta`:** 843 registos (2008–2018). Usa-se sempre `DataHoraAlerta` e ignoram-se `Ano`, `Mes`, `Dia`, `Hora`.
- **Nomes de concelho:** 379 grafias para 278 concelhos. Chave de junção: 4 primeiros dígitos de `DTCCFR`.
- **`Distrito`:** variantes de grafia ("Viana do Castelo" / "Viana Do Castelo" / "BRAGA").
- **Coordenadas impossíveis:** cerca de 5 registos (por exemplo, (0, 0) e latitude 48) e 32 fora da caixa do continente. Corrigir pelo `DTCCFR` ou excluir.
- **Possíveis duplicados:** 4 216 registos partilham a mesma freguesia e o mesmo minuto de alerta. Por investigar: podem ser ignições distintas ou registos repetidos.

**Deriva temporal (relevante para a RQ4)**

- Os territórios-dia com fogo descem de cerca de 13 000 (2001) para cerca de 4 700 (2024).
- A proporção de ocorrências com `A ≥ 10 ha` sobe de 2,85% (2001–2010) para 3,43% (2011–2020) e 4,46% (2021–2025).
- A cobertura de várias colunas muda com os anos (ver tabela acima), o que pode introduzir *dataset shift* se forem usadas como features.

**Interpretação**

- Um vazio significa "não registado" ou "não aplicável", nunca zero.
- Para as Tarefas 1 e 2, o dataset só contém dias **com** fogo. Os dias sem registo só podem ser negativos se a ausência de registo corresponder a ausência de fogo, o que se assume mas não se prova com esta fonte.

---

## 2. Limites administrativos (CAOP, DGT)

### Identificação

| Campo | Valor |
|---|---|
| Instituição responsável | Direção-Geral do Território (DGT) |
| Dataset | Carta Administrativa Oficial de Portugal (CAOP) |
| Versão | **CAOP2025**, aprovada por despacho de 28 de janeiro de 2026 e publicada no Aviso n.º 3502/2026/2, de 18 de fevereiro de 2026 |
| Alterações incluídas | Alterações administrativas publicadas entre 16 de março e 31 de dezembro de 2025 |
| Documentação oficial | [Página CAOP da DGT](https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop), [metadados](https://snig.dgterritorio.gov.pt/catalogo/srv/por/catalog.search#/metadata/198497815bf647ecaa990c34c42e932e) e [lista de alterações CAOP2025](https://www.dgterritorio.gov.pt/sites/default/files/ficheiros-cartografia/alteracoes_CAOP2025.pdf) |
| Licença | CC-BY 4.0 para informação geográfica aberta da DGT; atribuir os dados à Direção-Geral do Território |

### Descrição

Delimitação administrativa oficial de Portugal. A versão CAOP2025 disponibiliza
separadamente os dados do continente, Açores e Madeira. Para este projeto usa-se
apenas o GeoPackage do continente, que contém geometrias vetoriais das unidades
administrativas; a CAOP tem também informação associada sobre áreas e perímetros.

### Cobertura e resolução

| Dimensão | Valor |
|---|---|
| Cobertura espacial | Portugal: continente, Açores e Madeira (o projeto usa só o continente) |
| Sistema de referência (continente) | PT-TM06 / ETRS89 (EPSG:3763), confirmado nas camadas do GeoPackage |
| Formato de descarga | GeoPackage, dentro de um ZIP |
| Atualização | Versões anuais; CAOP2025 era a versão mais recente publicada pela DGT em 19 de novembro de 2026 |

### Uso no projeto

| Uso | Detalhe |
|---|---|
| Confirmar a lista de concelhos | A camada `cont_municipios` tem 278 linhas e 278 códigos `dtmn` distintos, correspondentes aos 278 códigos de concelho do ICNF |
| Agregar o CEMS aos concelhos | A grelha do CEMS tem cerca de 25 km; com os polígonos calcula-se o valor de cada concelho (média ponderada pela área), depois de reprojetar para um sistema comum |
| Característica estática | Área do concelho como feature opcional |
| Avaliação espacial | Vizinhança entre concelhos e distritos, para definir macro-regiões na análise de sensibilidade da RQ4 |
| Ligação ao ICNF | Usar `dtmn` na camada `cont_municipios`; os 278 códigos correspondem aos quatro primeiros dígitos de `DTCCFR` |

A camada municipal inclui ainda `municipio`, `distrito_ilha`, `area_ha`,
`perimetro_km` e `n_freguesias`. Não há códigos repetidos nem áreas em falta
ou não positivas nessa camada.

### Aquisição

Os ficheiros fornecidos para este projeto foram copiados para `data/raw/caop/`
(fora do Git): `CAOP_Continente_2025-gpkg.zip` e
`Areas_Freg_Mun_Dist_Pais_CAOP2025.zip`. Para reproduzir o projeto, descarregá-los
na [página oficial da CAOP](https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop).
A página também disponibiliza os GeoPackages dos Açores e da Madeira, os
metadados e tabelas de áreas. O GeoPackage foi inspecionado sem alterar os
ficheiros de origem.

### Limitações

- **Versão atual contra período 2001–2025.** A CAOP2025 representa os limites
  administrativos publicados até ao fim de 2025, não reconstitui os limites de
  cada ano do estudo. A divisão de freguesias mudou, nomeadamente em 2013; não
  se deve ligar por freguesia sem harmonização histórica.
- **Os nomes de freguesias do ICNF** refletem a divisão do ano do registo (como
  diz o dicionário), por isso o projeto liga-se pelo concelho, não pela
  freguesia.
- **Fronteira costeira e de rio.** Os polígonos seguem a linha de costa
  oficial; pontos de ignição perto do litoral ou de fronteiras podem não ficar
  dentro de um polígono municipal após a junção espacial.
- **Ilhas excluídas.** O ficheiro do ICNF só cobre o continente.

---

## 3. Índices de perigo de incêndio diários (CEMS, Copernicus)

> O pedido foi executado com sucesso e o NetCDF de teste foi inspecionado. O
> guia do ECMWF descreve valores às 12:00 locais, mas a coordenada temporal do
> ficheiro de teste apresenta 00:00 UTC; é preciso reconciliar esses metadados.

### Identificação

| Campo | Valor |
|---|---|
| Instituição responsável | Serviço de Gestão de Emergências do Copernicus (CEMS), produzido pelo ECMWF em nome do Joint Research Centre (JRC) da Comissão Europeia |
| Dataset | *Fire danger indices historical data from the Copernicus Emergency Management Service* (`cems-fire-historical-v1`) |
| Portal | CEMS Early Warning Data Store: https://ewds.climate.copernicus.eu/datasets/cems-fire-historical-v1 |
| DOI | 10.24381/cds.0e89c522 |
| Licença | CC-BY 4.0 (exige atribuição) |

### Descrição

Reconstrução histórica das condições meteorológicas favoráveis ao início e à
propagação de incêndios. Os índices são calculados com o modelo GEFF, forçado
pela reanálise ERA5 do ECMWF. O dataset inclui os índices dos sistemas
canadiano (FWI), norte-americano e australiano. Interessam as componentes do
sistema canadiano, as mesmas sete que existem no ficheiro do ICNF:

| Componente | Nome no pedido | Nome no NetCDF de teste |
|---|---|---|
| `FWI` | `fire_weather_index` | `fwinx` |
| `FFMC` | `fine_fuel_moisture_code` | `ffmcode` |
| `DMC` | `duff_moisture_code` | `dufmcode` |
| `DC` | `drought_code` | `drtcode` |
| `ISI` | `initial_fire_spread_index` | `infsinx` |
| `BUI` | `build_up_index` | `fbupinx` |
| `DSR` | `fire_daily_severity_rating` | `fdsrte` |

### Cobertura e resolução

| Dimensão | Valor |
|---|---|
| Cobertura temporal | Desde 1940; o catálogo indicava dados até 14 de novembro de 2026 quando consultado (inclui 2001–2025) |
| Resolução temporal | Diária |
| Resolução espacial | O formulário oferece a grelha original, 0,5° x 0,5° e 0,25° x 0,25° (as duas últimas interpoladas). Usa-se 0,25° (cerca de 25 km); a grelha original da reanálise é uma grelha gaussiana reduzida N320 (cerca de 31 km) |
| Formato | GRIB ou NetCDF4 (marcado como experimental no formulário) |
| Tipo de produto | Reanálise (não são observações diretas nem previsões) |

### Aquisição

Descarregamento a partir do portal, com pedido por variável, período e
caixa geográfica (Portugal continental). O guia indica que o utilizador tem de
estar registado; o pedido faz-se no formulário web ou pela API (`cdsapi`). Os
parâmetros e as opções estão publicados nos [metadados da API do dataset](https://ewds.climate.copernicus.eu/api/retrieve/v1/processes/cems-fire-historical-v1).
O pedido implementado em `src/download_cems.py` usa
`product_type: reanalysis`, `dataset_type: consolidated_dataset`,
`system_version: 4_1`, `grid: 0.25/0.25`, `data_format: netcdf` e uma caixa
envolvente de Portugal continental. Os nomes e parâmetros foram registados a
partir do código de pedido do portal. `src/inspect_cems.py` inspeciona
dimensões, variáveis, datas e valores em falta.

### Resultado do pedido de teste

O ficheiro `cems_fire_2017-08_test.nc` abriu como NetCDF4 e contém 31 instantes,
25 latitudes e 19 longitudes. Cada uma das sete variáveis listadas acima tem
3 038 valores em falta em 14 725 células-tempo. A coordenada `valid_time` vai
de `2017-08-01 00:00:00` a `2017-08-31 00:00:00`, com unidades
`seconds since 1970-01-01`; o atributo `long_name` chama-lhe “initial time of
forecast”. Isto confirma o carimbo temporal guardado no ficheiro, mas não
esclarece, por si só, se é a hora física a que o índice diário se refere ou
apenas uma referência do produto. O guia do utilizador indica 12:00 locais;
esta diferença deve ser resolvida antes de afirmar a disponibilidade exata do
valor diário.

As credenciais são um token pessoal guardado em `~/.cdsapirc`, fora do
repositório. É necessário aceitar os termos de uso no portal antes do primeiro
descarregamento. O script suporta `--test` (agosto de 2017) e `--dry-run`;
descarrega um ficheiro por ano de 2001 a 2025.

**Aviso do portal consultado em 19 de novembro de 2026:** as atualizações do
dataset foram suspensas a partir de 16 de novembro de 2026, até nova ordem, por
ser necessária uma nova configuração do arquivo MARS. O catálogo continuava
disponível, mas convém descarregar cedo os dados do período de estudo.

### Hora de disponibilidade

| Pergunta | Estado |
|---|---|
| A que hora do dia corresponde o valor diário? | Pendente: o guia descreve um instantâneo às 12:00 locais; no teste, `valid_time` mostra 00:00 UTC e tem `long_name=initial time of forecast` |
| Valor do dia d−1 disponível às 23:59 de d−1? | O guia sugere que sim, mas a interpretação da coordenada do NetCDF ainda precisa de confirmação |
| Valor do dia d disponível às 23:59 de d−1? | **Não.** Só existiria como previsão, e este dataset não é uma previsão |

Consequência para os conjuntos de features:

| Tarefa | Uso permitido | Uso proibido |
|---|---|---|
| 1 e 2 | Índices dos dias d−1, d−2, … e agregados desses dias (máximos e médias de 3 e 7 dias), depois de confirmar a interpretação temporal de d−1 | Índices do dia d |
| 3 | Índices do dia anterior ao alerta, depois de confirmar a interpretação temporal; regra conservadora: nunca usar o índice do dia do alerta | Índices do próprio dia ou posteriores ao alerta |

O índice do dia d só será usado numa experiência à parte, identificada como
"previsão perfeita" (limite superior do desempenho), nunca como resultado
principal.

### Limitações

- **Reanálise, não observação.** O ERA5 assimila observações a posteriori, por
  isso os valores são ligeiramente mais "limpos" do que o que existiria em
  tempo real.
- **Resolução grosseira.** Cerca de 25 km, face a concelhos frequentemente
  menores. Concelhos vizinhos podem partilhar a mesma célula, o que reduz a
  variabilidade espacial dos índices e é relevante para a avaliação espacial
  (RQ4). Método de agregação a decidir (célula do centroide ou média
  ponderada pela área, com os limites da CAOP).
- **Previsões históricas.** Segundo a página de acesso aos dados do CEMS-Fire,
  as previsões de perigo a 10 dias em tempo real obtêm-se apenas pelo EFFIS/GWIS,
  e o ECMWF guarda uma cópia no arquivo MARS (só produtos com mais de 30 dias).
  As condições de acesso ao MARS não foram verificadas, por isso o Momento A
  usa, para já, só valores reanalisados até d−1. As previsões ficam como
  extensão possível **[a confirmar]**. O dataset sazonal do CEMS não serve:
  é de longo prazo e não do dia seguinte.
- **O FWI mede condições meteorológicas, não ignições.** O guia refere que o
  índice não considera as fontes de ignição, e a descrição do dataset (Vitolo et
  al., 2020) enquadra-o como condições em que um fogo se propaga, condicionado
  à existência de ignição. É coerente com a Tarefa 3, mas limita a Tarefa 1.
- **Diferença face ao FWI do ICNF.** As colunas `FWI`, `DSR`, etc. do ficheiro
  do ICNF podem ter sido calculadas por outro método e a hora de cálculo é
  desconhecida **[a confirmar]**; o sistema canadiano usa o meio-dia, o que sugere
  a mesma convenção. Não se misturam as duas fontes no mesmo
  modelo. Nos dias com fogo comparam-se as duas (correlação), como validação.
