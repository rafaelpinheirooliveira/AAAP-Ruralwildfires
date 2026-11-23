"""Descarrega os índices de perigo de incêndio do CEMS (reanálise, sistema canadiano).

Dataset : cems-fire-historical-v1 (CEMS Early Warning Data Store, Copernicus)
Saída   : data/raw/cems/cems_fire_<ano>.nc   (um ficheiro por ano; fora do Git)

Uso:
    python src/download_cems.py --test       # só agosto de 2017 (pedido de teste)
    python src/download_cems.py              # todos os anos do período de estudo
    python src/download_cems.py --year 2003  # só um ano
    python src/download_cems.py --dry-run    # mostra os pedidos sem descarregar

Credenciais: o `cdsapi` lê o url e a chave de ~/.cdsapirc (fora do repositório).
O portal mostra os valores a usar na página de ajuda da API, depois do login.
Os anos já descarregados são saltados, por isso o script pode ser repetido.

Cada pedido é de um ano, para manter os ficheiros manejáveis e permitir retomar
o descarregamento sem repetir anos concluídos.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/raw/cems"
CONFIG = ROOT / "configs/config.yaml"

DATASET = "cems-fire-historical-v1"
VARIABLES = [  # sistema canadiano: as mesmas sete colunas do ficheiro do ICNF
    "build_up_index",
    "drought_code",
    "duff_moisture_code",
    "fine_fuel_moisture_code",
    "fire_daily_severity_rating",
    "fire_weather_index",
    "initial_fire_spread_index",
]
# Norte, Oeste, Sul, Este (graus): Portugal continental com margem de 0,25 a 0,5 graus.
AREA = [42.5, -10, 36.5, -5.5]
DAYS = [f"{d:02d}" for d in range(1, 32)]
MONTHS = [f"{m:02d}" for m in range(1, 13)]


def build_request(year: int, months: list[str] | None = None) -> dict:
    return {
        "product_type": "reanalysis",
        "variable": VARIABLES,
        "dataset_type": "consolidated_dataset",
        "system_version": ["4_1"],
        "year": [str(year)],
        "month": months or MONTHS,
        "day": DAYS,
        "grid": "0.25/0.25",
        "data_format": "netcdf",
        "area": AREA,
    }


def download(
    client, request: dict, target: Path, retries: int, wait_seconds: int
) -> bool:
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(".part")
    for attempt in range(1, retries + 1):
        part.unlink(missing_ok=True)
        remote = None
        try:
            remote = client.retrieve(DATASET, request)
            deadline = time.monotonic() + wait_seconds
            while remote.reply.get("state") != "completed":
                state = remote.reply.get("state", "unknown")
                if state == "failed":
                    error = remote.reply.get("error", {})
                    raise RuntimeError(
                        f"pedido falhou: {error.get('message', 'sem mensagem')} "
                        f"{error.get('reason', '')}".strip()
                    )
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    remote.delete()
                    print(
                        f"  tentativa {attempt}/{retries}: estado {state!r} "
                        f"após {wait_seconds}s; cancelamento pedido.",
                        flush=True,
                    )
                    break
                time.sleep(min(5, remaining))
                remote.update()
            else:
                remote.download(str(part))
                part.replace(target)  # só aparece com o nome final após a descarga completa
                return True
        except Exception as exc:  # erros de rede ou de fila do portal
            if remote is not None and remote.reply.get("state") != "completed":
                remote.delete()
            part.unlink(missing_ok=True)
            print(f"  tentativa {attempt}/{retries} falhou: {exc!r}", flush=True)
            if attempt < retries:
                time.sleep(10 * attempt)
            continue
        if remote.reply.get("state") != "completed":
            part.unlink(missing_ok=True)
    return False


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("tem de ser um inteiro positivo") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("tem de ser um inteiro positivo")
    return number


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--test", action="store_true", help="só agosto de 2017")
    p.add_argument("--year", type=int, help="descarrega apenas este ano do período de estudo")
    p.add_argument("--dry-run", action="store_true", help="mostra os pedidos e termina")
    p.add_argument("--retries", type=positive_int, default=2, help="número de tentativas por ano")
    p.add_argument(
        "--wait-seconds", type=positive_int, default=30,
        help="tempo máximo de espera por tentativa antes de cancelar o pedido",
    )
    a = p.parse_args()

    if a.test and a.year is not None:
        p.error("--test e --year não podem ser usados ao mesmo tempo")
    if a.test:
        jobs = [(OUT_DIR / "cems_fire_2017-08_test.nc", build_request(2017, ["08"]))]
    else:
        cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
        y0, y1 = cfg["study_period"]["start"].year, cfg["study_period"]["end"].year
        if a.year is not None:
            if not y0 <= a.year <= y1:
                p.error(f"--year tem de estar entre {y0} e {y1}")
            years = [a.year]
        else:
            years = range(y0, y1 + 1)
        jobs = [(OUT_DIR / f"cems_fire_{year}.nc", build_request(year)) for year in years]

    todo = [(t, r) for t, r in jobs if not t.exists()]
    print(f"{len(jobs)} pedidos, {len(jobs) - len(todo)} já descarregados, {len(todo)} por fazer.")
    if not todo:
        print("Nada por descarregar.")
        return
    if a.dry_run:
        for t, r in todo[:2]:
            print(t.name, json.dumps(r, ensure_ascii=False)[:400], "...")
        return

    import cdsapi  # importado aqui para o --dry-run funcionar sem o pacote

    client = cdsapi.Client(wait_until_complete=False)
    failed = []
    for i, (target, request) in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {target.name}", flush=True)
        if not download(client, request, target, a.retries, a.wait_seconds):
            failed.append(target.name)
    if failed:
        print(f"Falharam: {failed}. Corrigir o problema e repetir o script.")
        raise SystemExit(1)
    print("Concluído.")


if __name__ == "__main__":
    main()
