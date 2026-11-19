"""Mostra a estrutura de um ficheiro NetCDF do CEMS para conferir o descarregamento.

Uso:  python src/inspect_cems.py data/raw/cems/cems_fire_2017-08_test.nc
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset, num2date


def main(path: str) -> None:
    resolved = Path(path).resolve()
    try:
        # netCDF4's Windows native library fails on absolute paths with accents.
        open_path = os.path.relpath(resolved, Path.cwd())
    except ValueError:
        open_path = str(resolved)

    with Dataset(open_path) as ds:
        print("== Dimensões ==", {name: len(dim) for name, dim in ds.dimensions.items()})
        print("== Coordenadas ==")
        coord_names = set(ds.dimensions)
        for variable in ds.variables.values():
            coord_names.update(str(getattr(variable, "coordinates", "")).split())
        coord_names.intersection_update(ds.variables)
        for name in ds.variables:
            if name not in coord_names:
                continue
            variable = ds.variables[name]
            values = np.ma.filled(variable[...], np.nan)
            if name in ("time", "valid_time") and "units" in variable.ncattrs():
                dates = num2date(
                    values,
                    units=variable.getncattr("units"),
                    calendar=getattr(variable, "calendar", "standard"),
                    only_use_cftime_datetimes=False,
                    only_use_python_datetimes=True,
                )
                rng = f"{dates.min()} .. {dates.max()}" if values.size else "vazio"
            else:
                rng = f"{np.nanmin(values)} .. {np.nanmax(values)}" if values.size else "vazio"
            print(f"  {name:14s} n={values.size:<5} {rng}")
        print("== Variáveis ==")
        for name, variable in ds.variables.items():
            if name in coord_names:
                continue
            arr = np.ma.filled(variable[...], np.nan).astype("float64")
            ok = arr[~np.isnan(arr)]
            stats = f"min={ok.min():.2f} max={ok.max():.2f}" if ok.size else "sem valores"
            units = str(getattr(variable, "units", "-"))
            print(f"  {name:32s} unidades={units:6s} "
                  f"nulos={int(np.isnan(arr).sum())}/{arr.size}  {stats}")
        time_name = next((n for n in ("time", "valid_time") if n in ds.variables), None)
        if time_name:
            variable = ds.variables[time_name]
            t = num2date(
                variable[:],
                units=variable.getncattr("units"),
                calendar=getattr(variable, "calendar", "standard"),
                only_use_cftime_datetimes=False,
                only_use_python_datetimes=True,
            )
            print(f"== Instantes == {t[0]} .. {t[-1]}  (primeiros 3: {[str(x) for x in t[:3]]})")
        print("== Atributos globais ==")
        for name in ds.ncattrs():
            print(f"  {name}: {str(ds.getncattr(name))[:110]}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/raw/cems/cems_fire_2017-08_test.nc")
