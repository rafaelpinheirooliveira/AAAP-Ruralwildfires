# Auditoria da disponibilidade temporal das features SGIF

## Objetivo

Esta auditoria verifica se a combinação dos ficheiros SGIF por períodos pode ter
provocado a perda de colunas ou de valores e identifica as features cuja
disponibilidade varia ao longo de 2001–2025.

A análise foi realizada em setembro de 2026 sobre os seguintes ficheiros:

- `Registos_Incendios_SGIF_2001_2010.xlsx`;
- `Registos_Incendios_SGIF_2011_2020.xlsx`;
- `Registos_Incendios_SGIF_2021_2025.xlsx`;
- `data/Combined_Registos_Incendios_SGIF_2001_2025.xlsx`.

## Como é feita a combinação

Não é feito um *join* por `Codigo_SGIF` ou por qualquer outra chave. Assim, o
processo não procura correspondências entre ocorrências: limita-se a colocar as
linhas dos três períodos umas depois das outras.

### Reconciliação dos ficheiros

| Origem | Linhas | Colunas |
|---|---:|---:|
| 2001–2010 | 279 743 | 41 |
| 2011–2020 | 177 129 | 41 |
| 2021–2025 | 40 606 | 41 |
| **Soma / ficheiro combinado** | **497 478** | **41** |

Os três ficheiros têm os mesmos nomes de coluna. Tanto a união como a
interseção dos esquemas contêm 41 colunas, pelo que, na versão auditada:

- não foi descartada nenhuma coluna;
- o combinado contém exatamente a soma das linhas das três origens;
- não há indícios de que a concatenação tenha criado os vazios observados.

## Método de medição

A cobertura foi calculada por ano como:

```text
número de registos com valor / número total de registos do ano
```

Foram considerados em falta os valores nulos, `NaN` e textos vazios depois de
remover espaços. O valor numérico zero foi considerado preenchido, porque pode
ser um valor legítimo, nomeadamente nas áreas ardidas e em indicadores.

Esta medição avalia a presença de valores, mas não prova que estes sejam
corretos, comparáveis entre anos ou conhecidos no instante de previsão.

## Resultados principais

### Features com variações temporais relevantes

| Feature | Resultado |
|---|---|
| `DataHora_PrimeiraIntervencao` | 0% em 2001–2005; 0,2% em 2006; 0% em 2007; 84,6% em 2008; 86,4% em 2009; pelo menos 91% desde 2010 e aproximadamente 98–100% nos anos recentes. |
| `CodCausa` | Entre 7,7% e 12,7% em 2001–2006; 38,0% em 2007; 51,6% em 2008; 49,4% em 2009; aumenta gradualmente e atinge 99,8% em 2025. |
| `TipoCausa` | Tem a mesma cobertura anual de `CodCausa`. |
| `GrupoCausa` | Tem a mesma cobertura anual de `CodCausa`. |
| `DescricaoCausa` | Tem a mesma cobertura anual de `CodCausa`. |
| `FonteAlerta` | 100% em 2001–2022; 99,8% em 2023; 81,2% em 2024; 78,1% em 2025. |
| `RNAP` | Cobertura entre 2,5% e 4,4%, dependendo do ano. |
| `RNMPF` | Cobertura entre 0,9% e 6,3%, dependendo do ano. |

As ausências em `RNAP` e `RNMPF` não devem ser interpretadas automaticamente
como falhas de recolha. Um valor vazio também pode significar que a ocorrência
não pertence a uma área protegida, mata nacional ou perímetro florestal. A
fonte não permite distinguir inequivocamente “não se aplica” de “não
registado”.

### Features com cobertura elevada

- `Latitude`, `Longitude`, `X_ETRS89`, `Y_ETRS89`, `X_Militar` e
  `Y_Militar` aparecem preenchidas em todos os anos.
- `DataHora_Extincao` e `Duracao_Horas` apresentam geralmente entre 98,8% e
  100% de cobertura, com pequenas exceções anuais.
- `Codigo_ANEPC` está praticamente completo; o mínimo observado foi 99,7% em
  2002.
- Os índices `DSR`, `FWI`, `ISI`, `DC`, `DMC`, `FFMC` e `BUI` têm o mesmo
  padrão de cobertura: 100% em 2001–2011 e aproximadamente 98,6–100% entre
  2012 e 2025.

Ter um valor preenchido não significa que a feature estivesse disponível antes
ou durante o incêndio. Por exemplo, a área total, a duração, a causa apurada e
a hora de extinção são informação posterior à ocorrência ou ao seu desfecho.

## Cobertura anual das features mais sensíveis

Os valores seguintes estão arredondados a uma casa decimal. A coluna “Causa”
representa `CodCausa`, `TipoCausa`, `GrupoCausa` e `DescricaoCausa`, que têm a
mesma disponibilidade.

| Ano | Registos | Primeira intervenção | Causa | Fonte de alerta | RNAP | RNMPF | Índices FWI |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2001 | 28 915 | 0,0% | 7,9% | 100,0% | 3,8% | 2,5% | 100,0% |
| 2002 | 28 993 | 0,0% | 9,2% | 100,0% | 2,8% | 1,3% | 100,0% |
| 2003 | 28 087 | 0,0% | 8,4% | 100,0% | 2,7% | 0,9% | 100,0% |
| 2004 | 27 829 | 0,0% | 7,7% | 100,0% | 3,1% | 1,1% | 100,0% |
| 2005 | 41 689 | 0,0% | 8,3% | 100,0% | 2,5% | 1,2% | 100,0% |
| 2006 | 24 243 | 0,2% | 12,7% | 100,0% | 3,2% | 1,1% | 100,0% |
| 2007 | 25 132 | 0,0% | 38,0% | 100,0% | 3,7% | 1,5% | 100,0% |
| 2008 | 18 959 | 84,6% | 51,6% | 100,0% | 3,6% | 1,4% | 100,0% |
| 2009 | 29 783 | 86,4% | 49,4% | 100,0% | 3,4% | 2,0% | 100,0% |
| 2010 | 26 113 | 91,0% | 64,4% | 100,0% | 3,2% | 1,7% | 100,0% |
| 2011 | 29 782 | 99,2% | 69,8% | 100,0% | 3,7% | 1,7% | 100,0% |
| 2012 | 25 352 | 100,0% | 75,2% | 100,0% | 3,2% | 2,1% | 99,4% |
| 2013 | 23 129 | 100,0% | 77,1% | 100,0% | 2,6% | 2,6% | 99,7% |
| 2014 | 9 388 | 100,0% | 86,6% | 100,0% | 4,2% | 2,2% | 99,6% |
| 2015 | 19 643 | 100,0% | 82,7% | 100,0% | 4,3% | 3,3% | 99,9% |
| 2016 | 16 104 | 100,0% | 79,4% | 100,0% | 3,6% | 3,6% | 99,9% |
| 2017 | 21 006 | 100,0% | 82,2% | 100,0% | 3,5% | 4,0% | 99,9% |
| 2018 | 12 274 | 100,0% | 83,7% | 100,0% | 3,8% | 3,3% | 100,0% |
| 2019 | 10 832 | 100,0% | 91,5% | 100,0% | 4,0% | 3,9% | 98,8% |
| 2020 | 9 619 | 99,8% | 90,6% | 100,0% | 3,3% | 4,2% | 99,7% |
| 2021 | 8 186 | 99,8% | 97,0% | 100,0% | 4,1% | 6,3% | 100,0% |
| 2022 | 10 390 | 99,6% | 96,7% | 100,0% | 3,8% | 5,5% | 99,8% |
| 2023 | 7 523 | 99,9% | 96,5% | 99,8% | 4,4% | 5,7% | 98,6% |
| 2024 | 6 255 | 97,9% | 98,5% | 81,2% | 3,7% | 5,3% | 100,0% |
| 2025 | 8 252 | 98,1% | 99,8% | 78,1% | 4,1% | 4,8% | 100,0% |

## Implicações para os modelos

1. A validação deve ser temporal, por exemplo treinando em anos anteriores e
   validando nos seguintes. Uma divisão aleatória pode esconder alterações no
   processo de recolha.
2. `DataHora_PrimeiraIntervencao` não deve ser usada num modelo uniforme desde
   2001 sem uma política explícita para a ausência estrutural nos anos antigos.
3. As features de causa estão fortemente associadas ao período histórico e só
   ficam disponíveis depois da investigação. Não são apropriadas para prever o
   risco antes da ocorrência.
4. `FonteAlerta` exige cautela nos dados de 2024–2025 devido à quebra de
   cobertura e também não existe antes de o alerta ser comunicado.
5. Para features incompletas pode ser útil acrescentar indicadores binários de
   disponibilidade, mas estes indicadores também podem revelar o ano ou uma
   mudança administrativa e induzir *dataset shift*.
6. Deve distinguir-se sempre disponibilidade no ficheiro final de
   disponibilidade no instante de inferência. Esta distinção está aprofundada
   em `docs/estudo_features_temporais_modelos_incendio_pt.md`.


## Conclusão

Na versão auditada, a combinação não eliminou features nem registos. As
diferenças temporais relevantes já existem nas fontes e refletem sobretudo
mudanças na recolha de primeira intervenção, investigação das causas e origem
do alerta. Estas diferenças devem ser tratadas como parte do desenho temporal
dos datasets de modelação, e não apenas como um problema genérico de imputação.
