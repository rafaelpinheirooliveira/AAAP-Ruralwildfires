# Fontes de dados

Cada fonte é documentada com: instituição, descrição, cobertura temporal e
espacial, resolução, método de aquisição e limitações.

Estado: **1 fonte documentada e 1 em rascunho** (a restante é acrescentada
à medida que for analisada).

| # | Fonte | Estado |
|---|---|---|
| 1 | Registos de incêndios rurais SGIF (ICNF) | Documentada |
| 2 | Limites administrativos (CAOP, DGT) | A documentar |
| 3 | Índices de perigo de incêndio diários (CEMS, Copernicus) | Rascunho; pontos por confirmar assinalados |

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

## 3. Índices de perigo de incêndio diários (CEMS, Copernicus)

> **Rascunho.** Escrito a partir da página oficial do dataset, sem ter ainda
> descarregado dados. Os pontos marcados **[a confirmar]** dependem de um
> descarregamento de teste e da documentação técnica.

### Identificação

| Campo | Valor |
|---|---|
| Instituição responsável | Serviço de Gestão de Emergências do Copernicus (CEMS), produzido pelo ECMWF em nome do Joint Research Centre (JRC) da Comissão Europeia |
| Dataset | *Fire danger indices historical data from the Copernicus Emergency Management Service* (`cems-fire-historical-v1`) |
| Portal | CEMS Early Warning Data Store: https://ewds.climate.copernicus.eu/datasets/cems-fire-historical-v1 |
| DOI | 10.24381/cds.0e89c522 |
| Licença | CC-BY (exige atribuição) |

### Descrição

Reconstrução histórica das condições meteorológicas favoráveis ao início e à
propagação de incêndios. Os índices são calculados com o modelo GEFF, forçado
pela reanálise ERA5 do ECMWF. O dataset inclui os índices dos sistemas
canadiano (FWI), norte-americano e australiano. Interessam as componentes do
sistema canadiano, as mesmas sete que existem no ficheiro do ICNF:

| Componente | Nome no dataset |
|---|---|
| `FWI` | Fire weather index |
| `FFMC` | Fine fuel moisture code |
| `DMC` | Duff moisture code |
| `DC` | Drought code |
| `ISI` | Initial spread index |
| `BUI` | Build-up index |
| `DSR` | Fire daily severity index **[a confirmar a correspondência]** |

### Cobertura e resolução

| Dimensão | Valor |
|---|---|
| Cobertura temporal | 1940 até ao presente, atualizado diariamente (cobre 2001–2025) |
| Resolução temporal | Diária |
| Resolução espacial | Grelha regular de 0,25° x 0,25° (cerca de 25 km); a grelha original da reanálise é uma grelha gaussiana reduzida N320 (cerca de 31 km) |
| Formato | NetCDF (grelha interpolada) e GRIB2 |
| Tipo de produto | Reanálise (não são observações diretas nem previsões) |

### Aquisição

Descarregamento a partir do portal, com pedido por variável, período e
caixa geográfica (Portugal continental). O acesso exige registo no portal
**[a confirmar]**. A chave de API fica no ficheiro `.env`, que não é
versionado. O script de descarregamento será acrescentado a `src/`.

### Hora de disponibilidade

| Pergunta | Estado |
|---|---|
| A que hora do dia corresponde o valor diário? | **[a confirmar]**. A documentação de outro dataset do Copernicus (projeções climáticas) descreve o FWI com valores ao meio-dia; não está confirmado para este dataset |
| Valor do dia d−1 disponível às 23:59 de d−1? | Sim, **se** o valor corresponder ao meio-dia de d−1 |
| Valor do dia d disponível às 23:59 de d−1? | **Não.** Só existiria como previsão, e este dataset não é uma previsão |

Consequência para os conjuntos de features:

| Tarefa | Uso permitido | Uso proibido |
|---|---|---|
| 1 e 2 | Índices dos dias d−1, d−2, … e agregados desses dias (máximos e médias de 3 e 7 dias) | Índices do dia d |
| 3 | A definir depois de confirmar a hora do valor diário face à hora do alerta | Índices posteriores ao alerta |

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
- **Sem previsões históricas.** Não foi encontrado um arquivo gratuito de
  previsões meteorológicas para o dia seguinte, por isso o Momento A só pode
  usar valores observados (reanalisados) até d−1.
- **Diferença face ao FWI do ICNF.** As colunas `FWI`, `DSR`, etc. do ficheiro
  do ICNF podem ter sido calculadas por outro método e a hora de cálculo é
  desconhecida **[a confirmar]**. Não se misturam as duas fontes no mesmo
  modelo. Nos dias com fogo comparam-se as duas (correlação), como validação.
