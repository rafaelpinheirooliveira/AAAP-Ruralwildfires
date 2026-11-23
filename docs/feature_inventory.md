# Inventário de features e hora de disponibilidade

Cada feature é avaliada pelo momento em que a informação passa a existir. O
critério é o do enunciado: uma feature só entra se for conhecida no instante da
previsão.

| Momento | Instante | Tarefas | Dataset |
|---|---|---|---|
| A | 23:59 do dia d−1 | 1 e 2 | `territory_day.parquet` |
| B | `DataHoraAlerta` | 3 | `occurrences.parquet` |

**Estados:** *Principal* (no conjunto base), *Pendente* (disponível mas com um
problema por resolver; só entra em ablações), *Planeada* (fonte ainda não
integrada), *Excluída* (informação posterior ao instante da previsão ou sem
valor).

As listas de features estão no código (`FEATURES_AT_2359` e
`FEATURES_AT_ALERT`, mais `FEATURES_PENDING`), e é a partir delas que os modelos
devem selecionar as colunas.

---

## Momento A: concelho × dia (Tarefas 1 e 2)

### Features existentes

| Feature | Definição | Disponível em | Estado |
|---|---|---|---|
| `feat_mes` | mês do dia d | Calendário, conhecido de antemão | Principal |
| `feat_dia_do_ano` | dia do ano de d | Idem | Principal |
| `feat_dia_da_semana` | dia da semana de d | Idem | Principal |
| `feat_n_incendios_1d` | n.º de alertas no concelho no dia d−1 | 23:59 de d−1: todos os alertas de d−1 já são conhecidos | Principal |
| `feat_n_incendios_7d` | n.º de alertas nos 7 dias d−7 a d−1 | Idem | Principal |
| `feat_n_incendios_30d` | n.º de alertas nos 30 dias d−30 a d−1 | Idem | Principal |
| `feat_dias_desde_ultimo_incendio` | dias desde o último alerta no concelho, até d−1 (máximo 365) | Idem | Principal |
| `feat_area_extinta_30d_ha` | soma da área final dos incêndios **extintos** nos 30 dias d−30 a d−1 | Ver nota abaixo | Principal |
| `feat_area_max_extinta_30d_ha` | área máxima de um incêndio extinto nesse período | Idem | Principal |

**Nota sobre a área.** A área final de um incêndio só é conhecida quando ele se
extingue. Um incêndio que começou às 22:00 de d−1 e ainda arde às 23:59 não tem
área final nesse momento. Por isso as features de área usam a **data de
extinção** e a contagem usa a data de alerta (o alerta já é conhecido). As 662
ocorrências sem `DataHora_Extincao` contam para a contagem, mas não para a área.

### Features planeadas

| Feature | Fonte | Disponível em | Estado |
|---|---|---|---|
| Índices de perigo (`FWI`, `FFMC`, `DMC`, `DC`, `ISI`, `BUI`, `DSR`) dos dias d−1, d−2, … | CEMS (ERA5) | Comparação com o ICNF apoia a mesma data diária (Spearman 0,911 em agosto de 2017), mas não confirma a hora física nem a disponibilidade em tempo real | Pendente; só em ablação retrospetiva, sem alegação operacional |
| Agregados desses índices (máximo e média em 3 e 7 dias) | CEMS | Usam apenas dias anteriores; sujeitos à mesma incerteza de disponibilidade | Pendente; só em ablação retrospetiva |
| Índices do **dia d** | CEMS | **Não** para previsão às 23:59 de d−1: a reanálise não é uma previsão disponível antecipadamente | Excluída do conjunto principal; só como experiência "previsão perfeita" (limite superior) |
| Características estáticas do concelho (área, ocupação do solo) | CAOP e outras | Estáticas, mas a validade temporal tem de ser justificada | Planeada, opcional |

### Excluídas

| Coluna | Razão |
|---|---|
| `y_*` e `target_only_*` | São o alvo |
| Qualquer informação do dia d (n.º de incêndios, área, causa) | Informação futura |

---

## Momento B: ocorrência (Tarefa 3)

### Principal

| Feature | Disponível em `DataHoraAlerta` | Nota |
|---|---|---|
| `feat_mes`, `feat_dia_do_ano`, `feat_dia_da_semana`, `feat_hora` | Sim, derivadas do próprio alerta | |
| `feat_cod_distrito`, `feat_cod_concelho` | Sim, local do ponto de início | Ver risco de memorização espacial |
| `feat_latitude`, `feat_longitude`, `feat_x_etrs89`, `feat_y_etrs89` | Sim | Nulas em 32 registos com coordenadas inválidas |

### Pendentes (prefixo `pend_`)

| Feature | Problema | Decisão |
|---|---|---|
| `pend_fonte_alerta` | Cobertura 100% até 2023, cai para ~78% em 2025: deriva temporal | Ablação |
| `pend_rnap`, `pend_rnmpf` | 96,6% e 97,7% vazias; vazio pode ser "não aplicável" ou "não registado" | Ablação |
| `pend_fwi`, `pend_dsr`, `pend_isi`, `pend_dc`, `pend_dmc`, `pend_ffmc`, `pend_bui` | Hora de cálculo desconhecida; a indicação horária do guia CEMS não confirma a hora usada pelo ICNF | Fora até confirmar; depois comparar com o CEMS |

### Excluídas (informação posterior ao alerta)

| Coluna | Razão |
|---|---|
| `AreaPov_ha`, `AreaMato_ha`, `AreaAgric_ha`, `ClasseArea` | Resultado do incêndio. Só `AreaTotal_ha` se mantém, como alvo |
| `DataHora_Extincao`, `Duracao_Horas`, `IncSup24horas` | Desfecho do incêndio |
| `DataHora_PrimeiraIntervencao` | Ocorre depois do alerta; ausente em 2001–2007 |
| `CodCausa`, `TipoCausa`, `GrupoCausa`, `DescricaoCausa` | Causa apurada depois da investigação; cobertura de 8% (2001) a 99,8% (2025) |

### Excluídas por outras razões

| Coluna | Razão |
|---|---|
| `Ano` | Identificaria o período; usa-se só para dividir os dados |
| `Freguesia`, `Local`, `DTCCFR` | Alta cardinalidade e alterações administrativas ao longo dos anos |
| `X_Militar`, `Y_Militar` | Redundantes com ETRS89 |
| `Codigo_SGIF`, `Codigo_ANEPC` | Identificadores |

---

## Riscos de leakage e como são tratados

| # | Risco | Tratamento |
|---|---|---|
| 1 | Colunas de alvo usadas como feature | O código afirma (`assert`) que não há alvo nas listas de features |
| 2 | Área final de incêndios ainda ativos em d−1 | Features de área por data de extinção |
| 3 | Janelas históricas a incluir o próprio dia d | Janelas deslocadas um dia; o script recalcula 2 000 casos aleatórios e falha se houver diferença |
| 4 | FWI do ficheiro com hora de cálculo desconhecida | Fora do conjunto principal até confirmar |
| 5 | Causa e primeira intervenção só existem depois | Excluídas |
| 6 | Deriva da cobertura de `FonteAlerta`, causa e primeira intervenção | Fora do conjunto principal; qualquer uso é uma ablação justificada |
| 7 | Memorização de regiões (concelho e coordenadas) | Comparar com e sem localização; é essencial na avaliação espacial da RQ4 |
| 8 | Duplicados possíveis (8 378 registos envolvidos) em lados diferentes da divisão | Marcados em `flag_possivel_duplicado`; a divisão deve ser por grupo ou testada sem eles |
| 9 | Normalização e imputação com dados de teste | Transformações dentro de `Pipeline`, ajustadas só ao treino de cada divisão |
| 10 | Divisão aleatória a misturar períodos e regiões | Comparar com divisões temporal, espacial e espaciotemporal |
| 11 | Primeiros dias com histórico incompleto | `flag_warmup` (30 dias) |
| 12 | Indicadores de "valor em falta" a revelar o ano | Não se usam sem análise, porque podem induzir *dataset shift* |

## Regra para a Tarefa 3 (CEMS)

O guia do CEMS descreve o índice como um instantâneo do meio-dia local. Para uma
ocorrência com alerta no dia d:

- alerta **antes do meio-dia**: só o índice de d−1 estava disponível;
- alerta **depois do meio-dia**: o índice de d poderia estar disponível, mas com
  atraso de cálculo incerto.

No NetCDF de teste, porém, `valid_time` está marcado às 00:00 UTC e tem
`long_name=initial time of forecast`. A comparação com o ICNF favorece a mesma
data de calendário, mas não determina a hora física ou a latência de publicação.
Assim, CEMS não entra no conjunto principal: pode ser avaliado numa ablação
retrospetiva usando **sempre os valores até d−1**, sem os apresentar como dados
operacionalmente disponíveis no instante da previsão.

## Por fechar

- Confirmação documental da hora física representada por `valid_time` e da latência de disponibilização do produto CEMS.
- Hora de cálculo do FWI do ficheiro do ICNF.
- Integração da CAOP e de variáveis estáticas.
- Lista final de ablações (ver metodologia experimental).
