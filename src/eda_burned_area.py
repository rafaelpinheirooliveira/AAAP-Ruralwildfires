"""EDA da área ardida e justificação do Amin (Milestone 1).

Entrada : data/processed/occurrences.parquet e territory_day.parquet
Saída   : results/figures/*.png e results/amin_candidates.md
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "results/figures"
CFG = yaml.safe_load((ROOT / "configs/config.yaml").read_text(encoding="utf-8"))
AMIN = CFG["amin_main"]
CANDIDATES = [5, 10, 20, 50, 100]
COL = {"main": "#c0392b", "other": "#7f8c8d", "bar": "#2e86ab"}
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False})


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    occ = pd.read_parquet(ROOT / "data/processed/occurrences.parquet",
                          columns=["ano", "target_only_final_burned_area_ha"])
    a = occ["target_only_final_burned_area_ha"]
    td = pd.read_parquet(ROOT / "data/processed/territory_day.parquet",
                         columns=["date", "cod_distrito", "target_only_area_max_ha"])
    td["ano"] = td["date"].dt.year
    m = td["target_only_area_max_ha"]

    # 1) Distribuição da área (escala logarítmica) -------------------------------
    # Áreas < 0,001 ha (10 m2) incluem valores residuais como 1e-12; ficam fora do gráfico.
    shown = a[a >= 0.001]
    n_out = int((a < 0.001).sum())
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.hist(np.log10(shown), bins=np.linspace(-3, 5, 81), color=COL["bar"], alpha=.85)
    top = ax.get_ylim()[1]
    for i, c in enumerate(CANDIDATES):
        main_c = c == AMIN
        color = COL["main" if main_c else "other"]
        ax.axvline(np.log10(c), color=color, ls="-" if main_c else "--", lw=2 if main_c else 1)
        ax.text(np.log10(c) + .04, top * (.93 - .09 * (i % 3)), f"{c} ha", fontsize=8, color=color,
                fontweight="bold" if main_c else "normal")
    ticks = [0.001, 0.01, 0.1, 1, 10, 100, 1000, 10000, 100000]
    ax.set_xticks(np.log10(ticks)); ax.set_xticklabels([f"{t:g}" for t in ticks], fontsize=8)
    ax.set_xlim(-3, 4.9)
    ax.set_xlabel("Área ardida final (ha, escala logarítmica)")
    ax.set_ylabel("Número de ocorrências")
    ax.set_title("Distribuição da área ardida")
    n_shown = f"{len(shown):,}".replace(",", " ")
    n_omit = f"{n_out:,}".replace(",", " ")
    ax.text(.99, .62, f"{n_shown} ocorrências representadas\n{n_omit} com área < 0,001 ha omitidas",
            transform=ax.transAxes, ha="right", fontsize=8, color="#555")
    fig.tight_layout(); fig.savefig(FIG / "01_distribuicao_area.png"); plt.close(fig)

    # 2) Prevalência por candidato de Amin, nas duas populações -------------------
    p3 = [100 * (a >= c).mean() for c in CANDIDATES]
    p2 = [100 * (m >= c).mean() for c in CANDIDATES]
    x = np.arange(len(CANDIDATES)); w = .38
    fig, ax = plt.subplots(figsize=(8, 4.2))
    b3 = ax.bar(x - w / 2, p3, w, label="Tarefa 3 (ocorrências)", color=COL["bar"])
    b2 = ax.bar(x + w / 2, p2, w, label="Tarefa 2 (concelho × dia)", color="#e0a030")
    ax.set_yscale("log")
    ax.set_yticks([0.1, 0.3, 1, 3, 10]); ax.set_yticklabels(["0,1", "0,3", "1", "3", "10"])
    ax.set_ylim(0.08, 8); ax.set_xticks(x); ax.set_xticklabels([f"{c} ha" for c in CANDIDATES])
    ax.set_ylabel("% de positivos (escala log)"); ax.set_xlabel("Amin candidato")
    for bars, vals in ((b3, p3), (b2, p2)):
        for r, v in zip(bars, vals):
            ax.text(r.get_x() + r.get_width() / 2, v * 1.12, f"{v:.2f}".replace(".", ",") + "%", ha="center", fontsize=8)
    ax.legend(frameon=False); ax.set_title("Desbalanceamento de classes por valor de Amin")
    fig.tight_layout(); fig.savefig(FIG / "02_prevalencia_por_amin.png"); plt.close(fig)

    # 3) Positivos da Tarefa 2 por ano (Amin principal e 20) ----------------------
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for c, color, ls in ((AMIN, COL["main"], "-"), (20, COL["other"], "--")):
        y = (m >= c).groupby(td["ano"]).sum()
        ax.plot(y.index, y.values, ls, marker="o", ms=3, color=color, label=f"Amin = {c} ha")
    ax.axvspan(2020.5, 2025.5, color="#dddddd", alpha=.5, lw=0)
    ax.text(2023, ax.get_ylim()[1] * .92, "2021–2025:\nexemplo de teste temporal", ha="center", fontsize=8)
    ax.set_xlabel("Ano"); ax.set_ylabel("Concelhos-dia com incêndio significativo")
    ax.set_title("Positivos da Tarefa 2 por ano"); ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(FIG / "03_positivos_por_ano.png"); plt.close(fig)

    # Tabela de candidatos ---------------------------------------------------------
    rows = []
    for c in CANDIDATES:
        t2 = m >= c
        per_dist = t2.groupby(td["cod_distrito"]).sum()
        rows.append((c, int((a >= c).sum()), 100 * (a >= c).mean(), int(t2.sum()), 100 * t2.mean(),
                     int(t2[td["ano"] >= 2021].sum()), int(per_dist.min())))
    md = ["| Amin (ha) | Tarefa 3: positivos | % | Tarefa 2: positivos | % | T2 em 2021–2025 | T2: mínimo por distrito |",
          "|---:|---:|---:|---:|---:|---:|---:|"]
    md += [f"| {r[0]} | {r[1]:,} | {r[2]:.2f} | {r[3]:,} | {r[4]:.3f} | {r[5]:,} | {r[6]} |".replace(",", " ")
           for r in rows]
    (ROOT / "results/amin_candidates.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
