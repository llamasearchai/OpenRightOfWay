from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pyproj import CRS, Transformer
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Point, Polygon, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from openrightofway.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Corridor:
    geometry: BaseGeometry


def _to_geometry(geom: BaseGeometry) -> BaseGeometry:
    if isinstance(geom, LineString | MultiLineString | Polygon | MultiPolygon):
        return geom
    raise TypeError("Unsupported geometry type for corridor")


def load_corridor(geojson_path: str) -> Corridor:
    import json

    p = Path(geojson_path)
    if not p.exists():
        raise FileNotFoundError(f"Corridor file not found: {geojson_path}")

    data = json.loads(p.read_text(encoding="utf-8"))
    geoms = []
    if data.get("type") == "FeatureCollection":
        for feat in data.get("features", []):
            geoms.append(shape(feat.get("geometry")))
    elif data.get("type") in {"Feature", "LineString", "MultiLineString", "Polygon", "MultiPolygon"}:
        geom = shape(data.get("geometry")) if data.get("type") == "Feature" else shape(data)
        geoms.append(geom)
    else:
        raise ValueError("Unsupported GeoJSON structure")

    merged = unary_union(geoms)
    return Corridor(geometry=_to_geometry(merged))


def _utm_crs_for_lonlat(lon: float, lat: float) -> CRS:
    zone = int((lon + 180) / 6) + 1
    is_north = lat >= 0
    epsg = 32600 + zone if is_north else 32700 + zone
    return CRS.from_epsg(epsg)


def _build_transformers(sample_lon: float, sample_lat: float) -> tuple[Transformer, Transformer]:
    src = CRS.from_epsg(4326)
    dst = _utm_crs_for_lonlat(sample_lon, sample_lat)
    fwd = Transformer.from_crs(src, dst, always_xy=True)
    inv = Transformer.from_crs(dst, src, always_xy=True)
    return fwd, inv


def distance_to_corridor_meters(lon: float, lat: float, corridor: Corridor) -> float:
    """Approximate geodesic distance by local UTM projection."""
    fwd, _ = _build_transformers(lon, lat)
    x, y = fwd.transform(lon, lat)

    # project corridor
    if corridor.geometry.is_empty:
        return float("inf")

    # Transform each coordinate of the geometry to projected space
    def _transform_geom(geom: BaseGeometry) -> BaseGeometry:
        def _tx(xy):
            return fwd.transform(xy[0], xy[1])

        return shapely_transform_coords(geom, _tx)

    proj_geom = _transform_geom(corridor.geometry)
    return float(proj_geom.distance(Point(x, y)))


def point_in_corridor_buffer(lon: float, lat: float, corridor: Corridor, buffer_meters: float) -> bool:
    fwd, _ = _build_transformers(lon, lat)
    x, y = fwd.transform(lon, lat)

    proj_geom = shapely_transform_coords(corridor.geometry, lambda xy: fwd.transform(xy[0], xy[1]))
    return bool(proj_geom.buffer(buffer_meters).contains(Point(x, y)))


def shapely_transform_coords(geom: BaseGeometry, tx_fn):
    """Transform coordinates of a shapely geometry using tx_fn(xy)->(x,y)."""

    def _recurse(g):
        if g.geom_type == "Point":
            x, y = tx_fn((g.x, g.y))
            return Point(x, y)
        elif g.geom_type == "LineString":
            return LineString([tx_fn(xy) for xy in g.coords])
        elif g.geom_type == "LinearRing":
            from shapely.geometry import LinearRing
            return LinearRing([tx_fn(xy) for xy in g.coords])
        elif g.geom_type == "Polygon":
            return Polygon([tx_fn(xy) for xy in g.exterior.coords],
                           [ [tx_fn(xy) for xy in ring.coords] for ring in g.interiors ])
        elif g.geom_type == "MultiLineString":
            return MultiLineString([_recurse(p) for p in g.geoms])
        elif g.geom_type == "MultiPolygon":
            return MultiPolygon([_recurse(p) for p in g.geoms])
        else:
            return g

    return _recurse(geom)

