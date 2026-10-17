# Dicionário de dados dos registos de incêndios do ICNF

Este documento descreve as 41 colunas do ficheiro
`Combined_Registos_Incendios_SGIF_2001_2025.xlsx`. Cada linha do dataset
representa uma ocorrência de incêndio rural registada no Sistema de Gestão de
Informação de Incêndios Florestais (SGIF).

Os tipos indicados abaixo correspondem ao conteúdo do ficheiro combinado. Uma
coluna pode conter valores em falta, mesmo quando o seu tipo principal é
numérico ou temporal.

## Identificação e data da ocorrência

| Coluna | Tipo/unidade | Descrição |
|---|---|---|
| `Codigo_SGIF` | Texto | Identificador da ocorrência no SGIF. |
| `Codigo_ANEPC` | Inteiro | Identificador da ocorrência atribuído pela Autoridade Nacional de Emergência e Proteção Civil (ANEPC). Pode estar em falta. |
| `Ano` | Inteiro | Ano civil da ocorrência, extraído da data/hora do alerta. |
| `Mes` | Inteiro, 1–12 | Mês da ocorrência, extraído da data/hora do alerta. |
| `Dia` | Inteiro, 1–31 | Dia do mês da ocorrência, extraído da data/hora do alerta. |
| `Hora` | Inteiro, 0–23 | Hora do dia em que foi dado o alerta. Não inclui os minutos. |

## Área ardida

| Coluna | Tipo/unidade | Descrição |
|---|---|---|
| `AreaPov_ha` | Decimal, hectares | Área ardida de povoamentos florestais. |
| `AreaMato_ha` | Decimal, hectares | Área ardida de matos. |
| `AreaAgric_ha` | Decimal, hectares | Área ardida em terrenos agrícolas. |
| `AreaTotal_ha` | Decimal, hectares | Área total ardida na ocorrência; corresponde à soma das áreas de povoamentos, matos e agricultura, salvo eventuais inconsistências do registo de origem. |
| `ClasseArea` | Categoria | Classe de dimensão da área total ardida. No ficheiro existem as classes `]0 a 1 ha[`, `[1 a 10 ha]`, `[10 a 20 ha]`, `[20 a 50 ha]`, `[50 a 100 ha]`, `[100 a 500 ha]`, `[500 a 1000 ha]` e `[superior a 1000 ha]`. A notação é a que consta na fonte. |

## Tempos da ocorrência

| Coluna | Tipo/unidade | Descrição |
|---|---|---|
| `DataHoraAlerta` | Data e hora | Momento em que o alerta da ocorrência foi registado. |
| `DataHora_PrimeiraIntervencao` | Data e hora | Momento da primeira intervenção dos meios de combate. Pode estar em falta, sobretudo nos registos mais antigos. |
| `DataHora_Extincao` | Data e hora | Momento em que o incêndio foi dado como extinto. Pode estar em falta. |
| `Duracao_Horas` | Decimal, horas | Duração entre o alerta e a extinção, expressa em horas. Por exemplo, `0,5` representa 30 minutos. Pode estar em falta quando não existe uma das datas necessárias. |
| `IncSup24horas` | Indicador binário | Indica se a duração da ocorrência foi superior a 24 horas: `1` = sim e `0` = não. |

## Localização administrativa e territorial

| Coluna | Tipo/unidade | Descrição |
|---|---|---|
| `DTCCFR` | Inteiro/código | Código DICOFRE da freguesia do ponto de início. O código agrega a codificação de distrito, concelho e freguesia vigente no registo. Deve ser tratado como identificador, e não como medida numérica. |
| `Distrito` | Texto | Distrito do ponto de início da ocorrência. |
| `Concelho` | Texto | Concelho do ponto de início da ocorrência. |
| `Freguesia` | Texto | Freguesia do ponto de início da ocorrência. A designação pode refletir a divisão administrativa existente no ano do registo. |
| `Local` | Texto | Local ou topónimo mais específico associado ao ponto de início. Pode estar em falta. |
| `RNAP` | Texto | Nome da área da Rede Nacional de Áreas Protegidas (RNAP) onde se localiza a ocorrência. Fica vazio quando a ocorrência não está associada a uma área protegida ou quando essa informação não está disponível. |
| `RNMPF` | Texto | Nome da mata nacional ou do perímetro florestal associado à ocorrência (rede de matas nacionais e perímetros florestais). Fica vazio quando não existe associação ou informação disponível. A coluna contém algumas anomalias históricas de formatação no ficheiro de origem. |

## Coordenadas do ponto de início

| Coluna | Tipo/unidade | Descrição |
|---|---|---|
| `X_Militar` | Decimal, metros | Coordenada X (este) do ponto de início no antigo sistema de coordenadas militares portuguesas, baseado no Datum Lisboa/Hayford-Gauss. |
| `Y_Militar` | Decimal, metros | Coordenada Y (norte) do ponto de início no antigo sistema de coordenadas militares portuguesas, baseado no Datum Lisboa/Hayford-Gauss. |
| `Latitude` | Decimal, graus | Latitude geográfica do ponto de início, em graus decimais; valores positivos indicam norte. |
| `Longitude` | Decimal, graus | Longitude geográfica do ponto de início, em graus decimais; em Portugal continental os valores são normalmente negativos, indicando oeste. |
| `X_ETRS89` | Decimal, metros | Coordenada X (este) no sistema ETRS89 / PT-TM06, EPSG:3763. |
| `Y_ETRS89` | Decimal, metros | Coordenada Y (norte) no sistema ETRS89 / PT-TM06, EPSG:3763. |

## Índices meteorológicos de perigo de incêndio

Estes campos pertencem ao *Canadian Forest Fire Weather Index System*. São
índices adimensionais associados às condições meteorológicas da ocorrência;
valores mais elevados traduzem, em geral, condições mais favoráveis à ignição,
propagação ou dificuldade de supressão. Podem existir valores em falta.

| Coluna | Tipo/unidade | Descrição |
|---|---|---|
| `DSR` | Decimal, índice | *Daily Severity Rating* (Índice de Severidade Diário), derivado do FWI. Representa a dificuldade esperada de controlo e o esforço de supressão do incêndio. |
| `FWI` | Decimal, índice | *Fire Weather Index* (Índice Meteorológico de Perigo de Incêndio). Indicador geral da intensidade potencial do fogo, calculado a partir do ISI e do BUI. |
| `ISI` | Decimal, índice | *Initial Spread Index* (Índice de Propagação Inicial). Estima a rapidez inicial de propagação do fogo, combinando o efeito do vento e o teor de humidade dos combustíveis finos. |
| `DC` | Decimal, índice | *Drought Code* (Código de Seca). Indicador da humidade das camadas orgânicas profundas e dos combustíveis de grande dimensão, refletindo efeitos de seca de longo prazo. |
| `DMC` | Decimal, índice | *Duff Moisture Code* (Código de Humidade da Matéria Orgânica). Indicador da humidade das camadas orgânicas moderadamente profundas e dos combustíveis médios. |
| `FFMC` | Decimal, índice | *Fine Fuel Moisture Code* (Código de Humidade dos Combustíveis Finos). Indicador da humidade dos combustíveis finos superficiais e da facilidade de ignição. |
| `BUI` | Decimal, índice | *Build Up Index* (Índice de Combustível Disponível). Combina DMC e DC para representar a quantidade de combustível disponível para combustão. |

## Causa e origem do alerta

| Coluna | Tipo/unidade | Descrição |
|---|---|---|
| `CodCausa` | Inteiro/código | Código atribuído à causa apurada da ocorrência. Deve ser interpretado em conjunto com `TipoCausa`, `GrupoCausa` e `DescricaoCausa`; pode estar em falta quando a investigação não produziu uma classificação. |
| `TipoCausa` | Categoria | Classificação de nível superior da causa. Os valores observados são `Natural`, `Negligente`, `Intencional`, `Reacendimento` e `Desconhecida`. |
| `GrupoCausa` | Categoria | Grupo intermédio que organiza causas semelhantes, por exemplo uso do fogo, causas acidentais ou causas estruturais. |
| `DescricaoCausa` | Texto/categoria | Descrição detalhada da causa apurada, correspondente ao código de causa. |
| `FonteAlerta` | Texto/categoria | Entidade, serviço ou meio através do qual o alerta foi comunicado, por exemplo `112`, bombeiros, GNR, populares ou sapadores. Pode estar em falta. |

## Notas de utilização

- Os valores vazios significam informação não registada ou não aplicável; não
  devem ser automaticamente interpretados como zero ou como ausência do
  fenómeno.
- `Codigo_SGIF`, `Codigo_ANEPC`, `DTCCFR` e `CodCausa` são identificadores ou
  códigos. Mesmo quando são armazenados como inteiros, não representam
  quantidades.
- As colunas de texto agregam dados de 2001 a 2025 e podem conter diferenças de
  maiúsculas, acentuação, grafia e nomenclatura administrativa entre períodos.
- Os índices meteorológicos não são probabilidades nem percentagens e não devem
  ser comparados como se usassem essas unidades.

## Fontes de referência

- [ICNF — Estatísticas de incêndios rurais](https://www.icnf.pt/florestas/gfr/gfrgestaoinformacao/estatisticas)
- [ICNF — Índice Meteorológico de Perigo de Incêndio Florestal do Sistema Canadiano](https://fogos.icnf.pt/localizador/faztablefwidiario.asp)
- [Direção-Geral do Território — DICOFRE](https://www.dgterritorio.gov.pt/recart/v_1_1_2/UNIDADES%20ADMINISTRATIVAS/Freguesia.html)
- [ICNF — Rede Nacional de Áreas Protegidas](https://sig.icnf.pt/portal/home/item.html?id=9b09821ee9c441b29a26863ae5651b96)
