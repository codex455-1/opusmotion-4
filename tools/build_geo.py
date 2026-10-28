"""Bake geographic assets from OpenStreetMap (BBBike / Geofabrik extracts) and Natural Earth.

Outputs in build/cache/:
  moscow_map.png + moscow_map.json      dark Moscow street map (river, parks, road hierarchy, MKAD)
  london_wide.png + london_wide.json    Greater London (Thames, major roads, rail, parks)
  london_core.png + london_core.json    central London ground texture for the 3D city
  london_bldg.npz                       extruded building mesh (pos, nrm, col) for central London
Map data © OpenStreetMap contributors (ODbL). Natural Earth is public domain.
"""
import json, math, pathlib, sys
import numpy as np
import shapefile
import skia
import mapbox_earcut as earcut

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEO = ROOT / "assets/geo"
OUT = ROOT / "build/cache"
OUT.mkdir(parents=True, exist_ok=True)


class Proj:
    def __init__(self, lon0, lat0, lon_min, lat_min, lon_max, lat_max, width):
        self.lon0, self.lat0 = lon0, lat0
        self.kx = math.cos(math.radians(lat0)) * 111.32
        self.ky = 111.2
        x0, y1 = self.km(lon_min, lat_min)
        x1, y0 = self.km(lon_max, lat_max)
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.w = width
        self.h = int(round(width * (y1 - y0) / (x1 - x0)))
        self.ppk = width / (x1 - x0)  # pixels per km
        self.bbox = (lon_min, lat_min, lon_max, lat_max)

    def km(self, lon, lat):
        return (lon - self.lon0) * self.kx, -(lat - self.lat0) * self.ky

    def px(self, lon, lat):
        x, y = self.km(lon, lat)
        return (x - self.x0) * self.ppk, (y - self.y0) * self.ppk

    def meta(self):
        return dict(lon0=self.lon0, lat0=self.lat0, kx=self.kx, ky=self.ky, x0=self.x0, y0=self.y0,
                    ppk=self.ppk, w=self.w, h=self.h, bbox=self.bbox)


def col(r, g, b, a=1.0):
    return skia.Color4f(r, g, b, a)


def paint(c, stroke=None, aa=True):
    p = skia.Paint(AntiAlias=aa, Color4f=c)
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    return p


def iter_layer(path, bbox, fields=None):
    r = shapefile.Reader(str(path), encoding="utf-8")
    names = [f[0] for f in r.fields[1:]]
    it = r.iterShapeRecords(bbox=bbox) if "bbox" in r.iterShapeRecords.__code__.co_varnames else r.iterShapeRecords()
    for sr in it:
        try:
            sh = sr.shape
            if not sh.points:
                continue
            b = sh.bbox if len(sh.points) > 1 else (sh.points[0][0], sh.points[0][1]) * 2
        except Exception:
            continue
        if b[2] < bbox[0] or b[0] > bbox[2] or b[3] < bbox[1] or b[1] > bbox[3]:
            continue
        yield sh, dict(zip(names, sr.record))


def shape_path(proj, sh, closed):
    p = skia.Path()
    parts = list(sh.parts) + [len(sh.points)]
    for a, b in zip(parts[:-1], parts[1:]):
        pts = sh.points[a:b]
        if len(pts) < 2:
            continue
        x, y = proj.px(*pts[0])
        p.moveTo(x, y)
        for q in pts[1:]:
            p.lineTo(*proj.px(*q))
        if closed:
            p.close()
    if closed:
        p.setFillType(skia.PathFillType.kEvenOdd)
    return p


def save(surf, name, meta):
    img = surf.makeImageSnapshot()
    img.save(str(OUT / f"{name}.png"), skia.kPNG)
    (OUT / f"{name}.json").write_text(json.dumps(meta, indent=1))
    print("wrote", name, meta.get("w"), meta.get("h"), flush=True)


# ---------------------------------------------------------------------------------------------
def moscow():
    pr = Proj(37.60, 55.75, 37.32, 55.57, 37.88, 55.92, 4096)
    s = skia.Surface(pr.w, pr.h)
    c = s.getCanvas()
    c.clear(col(0.030, 0.036, 0.044))
    d = GEO / "moscow"
    for sh, rec in iter_layer(d / "landuse", pr.bbox):
        if rec["type"] in ("residential", "commercial", "retail", "industrial"):
            c.drawPath(shape_path(pr, sh, True), paint(col(0.045, 0.050, 0.058)))
    for sh, rec in iter_layer(d / "natural", pr.bbox):
        if rec["type"] in ("forest", "park"):
            c.drawPath(shape_path(pr, sh, True), paint(col(0.040, 0.058, 0.054)))
    water = skia.Path()
    for sh, rec in iter_layer(d / "natural", pr.bbox):
        if rec["type"] == "water":
            water.addPath(shape_path(pr, sh, True))
    for sh, rec in iter_layer(d / "waterways", pr.bbox):
        if rec["type"] in ("river", "canal"):
            c.drawPath(shape_path(pr, sh, False), paint(col(0.09, 0.18, 0.21), stroke=3.0))
    c.drawPath(water, paint(col(0.085, 0.175, 0.205)))
    c.drawPath(water, paint(col(0.20, 0.36, 0.40, 0.8), stroke=1.6))
    style = {"tertiary": (0.085, 1.1), "secondary": (0.13, 1.7), "primary": (0.20, 2.6), "trunk": (0.30, 3.6),
             "motorway": (0.34, 4.0)}
    mkad = []
    roads = {k: skia.Path() for k in style}
    for sh, rec in iter_layer(d / "roads", pr.bbox):
        t = rec["type"]
        if t in style:
            roads[t].addPath(shape_path(pr, sh, False))
        nm = (rec.get("name") or "") + " " + (rec.get("ref") or "")
        if "МКАД" in nm or "Московская кольцевая автомобильная" in nm:
            mkad.append([list(map(float, pr.px(*q))) for q in sh.points[::3]])
    for k in ("tertiary", "secondary", "primary", "trunk", "motorway"):
        v, wdt = style[k]
        c.drawPath(roads[k], paint(col(v, v * 0.98, v * 0.94), stroke=wdt))
    pts = {"lubyanka": pr.px(37.6268, 55.7596), "yasenevo": pr.px(37.5206, 55.5842), "kremlin": pr.px(37.6175, 55.7520)}
    meta = pr.meta()
    meta.update(points={k: list(map(float, v)) for k, v in pts.items()})
    save(s, "moscow_map", meta)
    # MKAD ring as its own transparent overlay (highlighted live, same projection)
    o = skia.Surface(pr.w, pr.h)
    oc = o.getCanvas()
    oc.clear(skia.Color4f(0, 0, 0, 0))
    ring = skia.Path()
    for sh, rec in iter_layer(d / "roads", pr.bbox):
        nm = (rec.get("name") or "") + " " + (rec.get("ref") or "")
        if rec["type"] in ("motorway", "trunk") and ("МКАД" in nm or "Московская кольцевая автомобильная" in nm):
            parts = list(sh.parts) + [len(sh.points)]
            for a, b in zip(parts[:-1], parts[1:]):
                prev = None
                for q in sh.points[a:b]:
                    x, y = pr.px(*q)
                    # break the stroke on long jumps (clipped / spur geometry)
                    if prev is None or (x - prev[0]) ** 2 + (y - prev[1]) ** 2 > (0.6 * pr.ppk) ** 2:
                        ring.moveTo(x, y)
                    else:
                        ring.lineTo(x, y)
                    prev = (x, y)
    oc.drawPath(ring, paint(col(1, 1, 1, 0.35), stroke=22))
    oc.drawPath(ring, paint(col(1, 1, 1, 1), stroke=5))
    save(o, "moscow_mkad", meta)


def london_wide():
    pr = Proj(-0.03, 51.48, -0.32, 51.36, 0.26, 51.60, 4096)
    s = skia.Surface(pr.w, pr.h)
    c = s.getCanvas()
    c.clear(col(0.028, 0.036, 0.046))
    d = GEO / "london"
    for sh, rec in iter_layer(d / "gis_osm_landuse_a_free_1", pr.bbox):
        if rec["fclass"] in ("park", "forest", "nature_reserve", "recreation_ground", "cemetery", "meadow"):
            c.drawPath(shape_path(pr, sh, True), paint(col(0.036, 0.054, 0.052)))
        elif rec["fclass"] in ("residential",):
            c.drawPath(shape_path(pr, sh, True), paint(col(0.040, 0.047, 0.057)))
    water = skia.Path()
    for sh, rec in iter_layer(d / "gis_osm_water_a_free_1", pr.bbox):
        water.addPath(shape_path(pr, sh, True))
    c.drawPath(water, paint(col(0.09, 0.19, 0.23)))
    c.drawPath(water, paint(col(0.22, 0.40, 0.45, 0.8), stroke=1.4))
    rail = skia.Path()
    for sh, rec in iter_layer(d / "gis_osm_railways_free_1", pr.bbox):
        if rec["fclass"] == "rail":
            rail.addPath(shape_path(pr, sh, False))
    c.drawPath(rail, paint(col(0.11, 0.12, 0.14), stroke=1.0))
    style = {"tertiary": (0.075, 0.9), "secondary": (0.12, 1.4), "primary": (0.19, 2.2), "trunk": (0.27, 3.0),
             "motorway": (0.32, 3.6)}
    roads = {k: skia.Path() for k in style}
    for sh, rec in iter_layer(d / "gis_osm_roads_free_1", pr.bbox):
        t = rec["fclass"]
        if t in style:
            roads[t].addPath(shape_path(pr, sh, False))
    for k in ("tertiary", "secondary", "primary", "trunk", "motorway"):
        v, wdt = style[k]
        c.drawPath(roads[k], paint(col(v, v * 0.98, v * 0.93), stroke=wdt))
    pts = {"century": pr.px(-0.1108, 51.4987), "bexleyheath": pr.px(0.1440, 51.4570),
           "westminster": pr.px(-0.1246, 51.5007), "city": pr.px(-0.0900, 51.5130)}
    meta = pr.meta()
    meta.update(points={k: list(map(float, v)) for k, v in pts.items()})
    save(s, "london_wide", meta)


def london_core():
    bbox = (-0.150, 51.488, -0.075, 51.516)
    pr = Proj(-0.1108, 51.4987, *bbox, 4096)
    s = skia.Surface(pr.w, pr.h)
    c = s.getCanvas()
    c.clear(col(0.035, 0.040, 0.050))
    d = GEO / "london"
    for sh, rec in iter_layer(d / "gis_osm_landuse_a_free_1", bbox):
        if rec["fclass"] in ("park", "forest", "grass", "recreation_ground", "cemetery"):
            c.drawPath(shape_path(pr, sh, True), paint(col(0.040, 0.060, 0.055)))
    water = skia.Path()
    for sh, rec in iter_layer(d / "gis_osm_water_a_free_1", bbox):
        water.addPath(shape_path(pr, sh, True))
    c.drawPath(water, paint(col(0.07, 0.16, 0.20)))
    c.drawPath(water, paint(col(0.30, 0.50, 0.55, 0.9), stroke=2.0))
    style = {"residential": (0.10, 2.0), "tertiary": (0.15, 3.0), "secondary": (0.22, 4.5), "primary": (0.30, 6.0),
             "trunk": (0.36, 7.0)}
    roads = {k: skia.Path() for k in style}
    for sh, rec in iter_layer(d / "gis_osm_roads_free_1", bbox):
        t = rec["fclass"]
        if t in style and rec.get("tunnel") != "T":
            roads[t].addPath(shape_path(pr, sh, False))
    for k in ("residential", "tertiary", "secondary", "primary", "trunk"):
        v, wdt = style[k]
        c.drawPath(roads[k], paint(col(v * 1.15, v * 1.0, v * 0.80), stroke=wdt))
    meta = pr.meta()
    meta.update(points={"century": list(map(float, pr.px(-0.1108, 51.4987)))})
    save(s, "london_core", meta)

    # ---- buildings -> extruded mesh in km units (x east, y north, z up) --------------------
    rng = np.random.default_rng(3)
    P, N, C = [], [], []
    cen = pr.km(-0.1108, 51.4987)
    count = 0
    for sh, rec in iter_layer(d / "gis_osm_buildings_a_free_1", bbox):
        pts = np.array(sh.points, np.float64)
        if len(pts) < 4:
            continue
        xy = np.stack([(pts[:, 0] - pr.lon0) * pr.kx, (pts[:, 1] - pr.lat0) * pr.ky], 1)  # y north
        parts = list(sh.parts) + [len(pts)]
        ring = xy[parts[0]:parts[1]]
        if len(ring) < 4:
            continue
        ring = ring[:-1] if np.allclose(ring[0], ring[-1]) else ring
        area = 0.5 * abs(np.dot(ring[:, 0], np.roll(ring[:, 1], 1)) - np.dot(ring[:, 1], np.roll(ring[:, 0], 1)))
        area_m2 = area * 1e6
        if area_m2 < 25:
            continue
        cx, cy = ring.mean(0)
        dist_c = math.hypot(cx - cen[0], cy + cen[1])
        base_h = 9 + 7 * rng.random() + min(area_m2, 6000) ** 0.42 * 0.55 * rng.random()
        if rng.random() < 0.06:
            base_h *= 1.8
        h = min(base_h, 70) / 1000.0
        if dist_c < 0.035 and area_m2 > 2000:
            h = 0.075  # Century House (22 storeys)
        # roof
        tri = earcut.triangulate_float64(ring, np.array([len(ring)], np.uint32))
        tone = 0.13 + 0.06 * rng.random()
        seed = rng.random()
        for k in tri:
            P.append((ring[k, 0], ring[k, 1], h))
            N.append((0, 0, 1))
            C.append((tone * 0.9, tone * 0.92, tone, seed))
        # walls
        sgn = 1.0 if np.dot(ring[:, 0], np.roll(ring[:, 1], -1)) - np.dot(ring[:, 1], np.roll(ring[:, 0], -1)) > 0 else -1.0
        for i in range(len(ring)):
            a, b = ring[i], ring[(i + 1) % len(ring)]
            e = b - a
            L = math.hypot(*e)
            if L < 1e-6:
                continue
            n = (e[1] / L * sgn, -e[0] / L * sgn, 0.0)
            quad = [(a[0], a[1], 0), (b[0], b[1], 0), (b[0], b[1], h), (a[0], a[1], h)]
            for q in (0, 1, 2, 0, 2, 3):
                P.append(quad[q])
                N.append(n)
                C.append((tone * 0.75, tone * 0.78, tone * 0.85, seed))
        count += 1
    np.savez_compressed(OUT / "london_bldg.npz", pos=np.array(P, np.float32), nrm=np.array(N, np.float32),
                        col=np.array(C, np.float32), centre=np.array(cen, np.float32))
    print("buildings", count, "triangles", len(P) // 3, flush=True)


def europe():
    """Dark Europe/Baltic map + live polygons for the 15 Soviet republics (for the 1991 break-up)."""
    from shapely.geometry import shape as shp_shape, mapping
    from shapely.ops import unary_union
    pr = Proj(22.0, 55.0, -14.0, 36.0, 64.0, 70.5, 4096)
    feats = json.loads((GEO / "ne_50m_admin_0_countries.geojson").read_text())["features"]
    s = skia.Surface(pr.w, pr.h)
    c = s.getCanvas()
    c.clear(col(0.020, 0.030, 0.042))
    grat = paint(col(0.10, 0.14, 0.18, 0.5), stroke=1.0)
    for lon in range(-20, 70, 5):
        a, b = pr.px(lon, 30), pr.px(lon, 72)
        c.drawLine(*a, *b, grat)
    for lat in range(35, 72, 5):
        pth = skia.Path()
        pth.moveTo(*pr.px(-20, lat))
        for lon in range(-20, 71, 2):
            pth.lineTo(*pr.px(lon, lat))
        c.drawPath(pth, grat)

    def geom_path(g):
        p = skia.Path()
        polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
        for poly in polys:
            for ring in [poly.exterior] + list(poly.interiors):
                pts = list(ring.coords)
                p.moveTo(*pr.px(*pts[0]))
                for q in pts[1:]:
                    p.lineTo(*pr.px(*q))
                p.close()
        p.setFillType(skia.PathFillType.kEvenOdd)
        return p

    soviet = {"RUS", "UKR", "BLR", "EST", "LVA", "LTU", "MDA", "GEO", "ARM", "AZE", "KAZ", "UZB", "TKM", "KGZ", "TJK"}
    live = {}
    land = skia.Path()
    for f in feats:
        g = shp_shape(f["geometry"])
        iso = f["properties"].get("ADM0_A3") or f["properties"].get("ISO_A3")
        p = geom_path(g)
        land.addPath(p)
        c.drawPath(p, paint(col(0.105, 0.118, 0.130)))
        c.drawPath(p, paint(col(0.26, 0.30, 0.33, 0.9), stroke=1.8))
        if iso in soviet:
            gs = g.simplify(0.03, preserve_topology=True)
            polys = [gs] if gs.geom_type == "Polygon" else list(gs.geoms)
            live[iso] = [[list(map(float, pr.px(*q))) for q in poly.exterior.coords] for poly in polys]
    c.drawPath(land, paint(col(0.38, 0.48, 0.54, 0.65), stroke=2.6))
    union = unary_union([shp_shape(f["geometry"]) for f in feats
                         if (f["properties"].get("ADM0_A3") or f["properties"].get("ISO_A3")) in soviet]).simplify(0.03)
    upolys = [union] if union.geom_type == "Polygon" else list(union.geoms)
    meta = pr.meta()
    cities = {"moscow": (37.6173, 55.7558), "riga": (24.1052, 56.9496), "vilnius": (25.2797, 54.6872),
              "klaipeda": (21.1443, 55.7033), "london": (-0.1278, 51.5074), "sea": (17.2, 55.7), "tallinn": (24.7536, 59.437)}
    meta.update(soviet=live, ussr=[[list(map(float, pr.px(*q))) for q in poly.exterior.coords] for poly in upolys],
                cities={k: list(map(float, pr.px(*v))) for k, v in cities.items()})
    save(s, "europe", meta)


if __name__ == "__main__":
    which = sys.argv[1:] or ["moscow", "london_wide", "london_core", "europe"]
    for w in which:
        globals()[w]()
