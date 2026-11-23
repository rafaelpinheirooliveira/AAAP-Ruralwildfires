"""Aggregate CEMS grid cells to CAOP2025 municipalities.

Usage:
    python src/integrate_cems.py --test
    python src/integrate_cems.py
    python src/integrate_cems.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

import numpy as np
import pandas as pd
import yaml
from netCDF4 import Dataset, num2date
from pyproj import Transformer
from shapely import STRtree, from_wkb, transform as transform_geometry
from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[1]
CEMS_DIR = ROOT / "data/raw/cems"
CAOP_ZIP = ROOT / "data/raw/caop/CAOP_Continente_2025-gpkg.zip"
OUT_DIR = ROOT / "data/processed/cems_by_municipality"
CONFIG = ROOT / "configs/config.yaml"

NETCDF_VARIABLES = {
    "feat_cems_bui": "fbupinx",
    "feat_cems_dc": "drtcode",
    "feat_cems_dmc": "dufmcode",
    "feat_cems_ffmc": "ffmcode",
    "feat_cems_dsr": "fdsrte",
    "feat_cems_fwi": "fwinx",
    "feat_cems_isi": "infsinx",
}
GPKG_ENVELOPE_BYTES = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}


def _gpkg_wkb(blob: bytes) -> bytes:
    if len(blob) < 8 or blob[:2] != b"GP":
        raise ValueError("Geometria CAOP sem cabeçalho GeoPackage válido.")
    envelope_code = (blob[3] >> 1) & 0x07
    try:
        envelope_bytes = GPKG_ENVELOPE_BYTES[envelope_code]
    except KeyError as exc:
        raise ValueError(f"Código de envelope GeoPackage não suportado: {envelope_code}") from exc
    return blob[8 + envelope_bytes:]


def load_municipalities() -> tuple[list[str], list]:
    if not CAOP_ZIP.is_file():
        raise FileNotFoundError(f"GeoPackage CAOP não encontrado: {CAOP_ZIP}")

    with ZipFile(CAOP_ZIP) as archive:
        members = [
            name for name in archive.namelist()
            if PurePosixPath(name).name == "Continente_CAOP2025.gpkg"
        ]
        if len(members) != 1:
            raise ValueError(f"Esperava um GeoPackage CAOP no ZIP; encontrei {len(members)}.")

        with tempfile.TemporaryDirectory(prefix="caop_cems_") as temp_dir:
            gpkg_path = Path(temp_dir) / "Continente_CAOP2025.gpkg"
            with archive.open(members[0]) as source, gpkg_path.open("wb") as target:
                shutil.copyfileobj(source, target)

            connection = sqlite3.connect(gpkg_path)
            try:
                metadata = connection.execute(
                    "SELECT srs_id FROM gpkg_geometry_columns "
                    "WHERE table_name = ? AND column_name = ?",
                    ("cont_municipios", "geom"),
                ).fetchone()
                if metadata is None or metadata[0] != 3763:
                    raise ValueError("A camada cont_municipios não está identificada em EPSG:3763.")
                rows = connection.execute(
                    "SELECT dtmn, geom FROM cont_municipios ORDER BY dtmn"
                ).fetchall()
            finally:
                connection.close()

    codes = [str(code).zfill(4) for code, _ in rows]
    geometries = [from_wkb(_gpkg_wkb(blob)) for _, blob in rows]
    if len(codes) != 278 or len(set(codes)) != 278:
        raise ValueError(f"Esperava 278 códigos municipais únicos; encontrei {len(set(codes))}.")
    invalid = [code for code, geom in zip(codes, geometries)
               if geom.is_empty or not geom.is_valid or geom.area <= 0]
    if invalid:
        raise ValueError(f"Geometrias municipais inválidas: {invalid[:10]}")
    return codes, geometries


def _cell_edges(centres: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ordered = np.sort(np.asarray(centres, dtype="float64"))
    if ordered.size < 2 or np.any(np.diff(ordered) <= 0):
        raise ValueError("A grelha precisa de pelo menos dois centros distintos por eixo.")
    edges = np.empty(ordered.size + 1, dtype="float64")
    edges[1:-1] = (ordered[:-1] + ordered[1:]) / 2
    edges[0] = ordered[0] - (ordered[1] - ordered[0]) / 2
    edges[-1] = ordered[-1] + (ordered[-1] - ordered[-2]) / 2
    return ordered, edges


def build_area_weights(
    codes: list[str], municipalities: list, latitudes: np.ndarray, longitudes: np.ndarray
) -> tuple[np.ndarray, dict]:
    latitudes = np.asarray(latitudes, dtype="float64")
    longitudes = np.asarray(longitudes, dtype="float64")
    signed_longitudes = np.where(longitudes > 180, longitudes - 360, longitudes)
    sorted_lats, lat_edges = _cell_edges(latitudes)
    sorted_lons, lon_edges = _cell_edges(signed_longitudes)
    lat_positions = {value: index for index, value in enumerate(sorted_lats)}
    lon_positions = {value: index for index, value in enumerate(sorted_lons)}

    to_pt = Transformer.from_crs("EPSG:4326", "EPSG:3763", always_xy=True)
    cells = []
    for latitude in latitudes:
        lat_index = lat_positions[float(latitude)]
        south, north = lat_edges[lat_index:lat_index + 2]
        for longitude in signed_longitudes:
            lon_index = lon_positions[float(longitude)]
            west, east = lon_edges[lon_index:lon_index + 2]
            cells.append(
                transform_geometry(
                    box(west, south, east, north), to_pt.transform, interleaved=False
                )
            )

    tree = STRtree(cells)
    weights = np.zeros((len(municipalities), len(cells)), dtype="float64")
    area_coverage = np.empty(len(municipalities), dtype="float64")
    for row, municipality in enumerate(municipalities):
        for cell_index in tree.query(municipality, predicate="intersects"):
            index = int(cell_index)
            area = municipality.intersection(cells[index]).area
            if area > 0:
                weights[row, index] = area
        area_coverage[row] = weights[row].sum() / municipality.area

    if np.any(weights.sum(axis=1) == 0):
        missing = [codes[i] for i in np.flatnonzero(weights.sum(axis=1) == 0)]
        raise ValueError(f"Sem interseção da grelha com concelhos: {missing}")
    return weights, {
        "municipalities": len(codes),
        "grid_cells": len(cells),
        "min_grid_area_coverage": float(area_coverage.min()),
        "max_grid_area_coverage": float(area_coverage.max()),
        "grid_longitude_range_west_east": [
            float(signed_longitudes.min()), float(signed_longitudes.max())
        ],
    }


def _native_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return os.path.relpath(resolved, Path.cwd())
    except ValueError:
        return str(resolved)


def aggregate_file(
    source: Path, target: Path, codes: list[str], weights: np.ndarray, force: bool
) -> dict:
    if target.exists() and not force:
        return {"source": source.name, "output": target.name, "status": "já existe"}

    with Dataset(_native_path(source)) as dataset:
        time_name = next((name for name in ("valid_time", "time") if name in dataset.variables), None)
        if time_name is None:
            raise ValueError(f"{source.name}: não encontrei a coordenada temporal.")
        time_variable = dataset.variables[time_name]
        times = num2date(
            time_variable[:],
            units=time_variable.getncattr("units"),
            calendar=getattr(time_variable, "calendar", "standard"),
            only_use_cftime_datetimes=False,
            only_use_python_datetimes=True,
        )
        time_strings = [str(value) for value in times]
        times_utc = pd.to_datetime(time_strings, utc=True)
        valid_time_utc = times_utc.tz_localize(None).to_numpy()
        dates = times_utc.tz_localize(None).normalize().to_numpy()

        latitude_name = "latitude" if "latitude" in dataset.variables else "lat"
        longitude_name = "longitude" if "longitude" in dataset.variables else "lon"
        latitude = np.asarray(dataset.variables[latitude_name][:], dtype="float64")
        longitude = np.asarray(dataset.variables[longitude_name][:], dtype="float64")
        if latitude.ndim != 1 or longitude.ndim != 1:
            raise ValueError(f"{source.name}: esperava coordenadas 1D de latitude e longitude.")
        if weights.shape[1] != latitude.size * longitude.size:
            raise ValueError(f"{source.name}: dimensão da grelha mudou face aos pesos espaciais.")

        row_count = len(times) * len(codes)
        data: dict[str, np.ndarray] = {
            "date": np.repeat(dates, len(codes)),
            "valid_time_utc": np.repeat(valid_time_utc, len(codes)),
            "cod_concelho": np.tile(codes, len(times)),
        }
        missing_by_variable = {}
        for feature, variable_name in NETCDF_VARIABLES.items():
            if variable_name not in dataset.variables:
                raise ValueError(f"{source.name}: variável NetCDF em falta: {variable_name}")
            variable = dataset.variables[variable_name]
            if variable.dimensions != (time_name, latitude_name, longitude_name):
                raise ValueError(
                    f"{source.name}: dimensões inesperadas em {variable_name}: "
                    f"{variable.dimensions}"
                )
            values = np.ma.filled(variable[:], np.nan).astype("float64")
            values = values.reshape(len(times), -1)
            valid = np.isfinite(values)
            numerator = weights @ np.where(valid, values, 0.0).T
            denominator = weights @ valid.astype("float64").T
            aggregated = np.full(numerator.shape, np.nan, dtype="float64")
            np.divide(numerator, denominator, out=aggregated, where=denominator > 0)
            data[feature] = aggregated.T.reshape(row_count)
            missing_by_variable[feature] = int(np.isnan(aggregated).sum())

        global_attributes = {
            name: str(dataset.getncattr(name))
            for name in ("GRIB_centre", "Conventions")
            if name in dataset.ncattrs()
        }

    output = pd.DataFrame(data)
    if output.duplicated(["date", "cod_concelho"]).any():
        raise ValueError(f"{source.name}: datas ou códigos municipais duplicados.")
    target.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(target, index=False)
    report = {
        "source": source.name,
        "rows": len(output),
        "date_start": str(output["date"].min()),
        "date_end": str(output["date"].max()),
        "municipalities": output["cod_concelho"].nunique(),
        "valid_time_utc_start": str(output["valid_time_utc"].min()),
        "valid_time_utc_end": str(output["valid_time_utc"].max()),
        "missing_values_by_feature": missing_by_variable,
        "global_attributes": global_attributes,
    }
    target.with_suffix(".json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {"source": source.name, "output": target.name, "status": "agregado", **report}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="processa o NetCDF de agosto de 2017")
    parser.add_argument("--dry-run", action="store_true", help="mostra os ficheiros sem processar")
    parser.add_argument("--force", action="store_true", help="substitui agregações já existentes")
    args = parser.parse_args()

    if args.test:
        inputs = [CEMS_DIR / "cems_fire_2017-08_test.nc"]
    else:
        config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
        start = config["study_period"]["start"].year
        end = config["study_period"]["end"].year
        inputs = [CEMS_DIR / f"cems_fire_{year}.nc" for year in range(start, end + 1)]
        missing = [path.name for path in inputs if not path.is_file()]
        if missing and not args.dry_run:
            raise SystemExit(f"Faltam ficheiros CEMS anuais: {', '.join(missing)}")
        if missing:
            print(f"Faltam {len(missing)} ficheiros: {', '.join(missing)}")
            return

    if any(not path.is_file() for path in inputs):
        missing = [path.name for path in inputs if not path.is_file()]
        raise SystemExit(f"Ficheiros CEMS não encontrados: {', '.join(missing)}")

    outputs = [
        OUT_DIR / f"{source.stem}_municipalities.parquet"
        for source in inputs
    ]
    for source, output in zip(inputs, outputs):
        print(f"{source.name} -> {output.relative_to(ROOT)}")
    if args.dry_run:
        return

    todo = [
        (source, output) for source, output in zip(inputs, outputs)
        if args.force or not output.exists()
    ]
    if not todo:
        print("Todas as agregações já existem.")
        return

    codes, geometries = load_municipalities()
    with Dataset(_native_path(todo[0][0])) as sample:
        lat_name = "latitude" if "latitude" in sample.variables else "lat"
        lon_name = "longitude" if "longitude" in sample.variables else "lon"
        weights, spatial_report = build_area_weights(
            codes,
            geometries,
            sample.variables[lat_name][:],
            sample.variables[lon_name][:],
        )
    print("Pesos espaciais:", json.dumps(spatial_report, ensure_ascii=False))

    for index, (source, output) in enumerate(todo, 1):
        print(f"[{index}/{len(todo)}] {source.name}", flush=True)
        report = aggregate_file(source, output, codes, weights, args.force)
        print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
