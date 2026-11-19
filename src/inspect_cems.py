"""Mostra a estrutura de um ficheiro NetCDF do CEMS para conferir o descarregamento.

Uso:  python src/inspect_cems.py data/raw/cems/cems_fire_2017-08_test.nc
"""
from __future__ import annotations

import sys

import numpy as np
import xarray as xr


def main(path: str) -> None:
    with xr.open_dataset(path) as ds:
        print("== Dimensões ==", dict(ds.sizes))
        print("== Coordenadas ==")
        for name, c in ds.coords.items():
            v = c.values
            rng = f"{v.min()} .. {v.max()}" if v.size else "vazio"
            print(f"  {name:14s} n={v.size:<5} {rng}")
        print("== Variáveis ==")
        for name, v in ds.data_vars.items():
            arr = v.values.astype("float64")
            ok = arr[~np.isnan(arr)]
            stats = f"min={ok.min():.2f} max={ok.max():.2f}" if ok.size else "sem valores"
            print(f"  {name:32s} unidades={v.attrs.get('units', '-'):6s} "
                  f"nulos={int(np.isnan(arr).sum())}/{arr.size}  {stats}")
        time_name = next((n for n in ("time", "valid_time") if n in ds.coords), None)
        if time_name:
            t = ds[time_name].values
            print(f"== Instantes == {t[0]} .. {t[-1]}  (primeiros 3: {[str(x) for x in t[:3]]})")
        print("== Atributos globais ==")
        for k, val in ds.attrs.items():
            print(f"  {k}: {str(val)[:110]}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/raw/cems/cems_fire_2017-08_test.nc")
