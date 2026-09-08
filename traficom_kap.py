#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Traficom WMTS -> BSB/KAP converter (VER/2.0, sequential RLL, no table).
   pip install requests pillow pyproj"""

import argparse, datetime, io, math, os, re, sys, time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import requests
from PIL import Image
from pyproj import Transformer

Image.MAX_IMAGE_PIXELS = None

CAPS_URL     = "https://julkinen.traficom.fi/rasteripalvelu/wmts?request=GetCapabilities"
TMS_ID       = "ETRS89_TM35-FIN"
OGC_M_PER_PX = 0.00028
MAX_COLORS   = 63
UA           = "traficom-wmts-kap-converter/1.0 (personal use; non-navigational)"


def _local(tag):
    return tag.rsplit('}', 1)[-1]


def fetch_capabilities(session):
    r = session.get(CAPS_URL, timeout=60)
    r.raise_for_status()
    return ET.fromstring(r.content)


def parse_tilematrixset(root, tms_id):
    found = []
    for el in root.iter():
        if _local(el.tag) != 'TileMatrixSet':
            continue
        ident, mats = '', []
        for ch in el:
            name = _local(ch.tag)
            if name == 'Identifier':
                ident = (ch.text or '').strip()
            elif name == 'TileMatrix':
                mats.append({_local(g.tag): (g.text or '').strip() for g in ch})
        if ident != tms_id:
            continue
        for m in mats:
            e0, n0 = m['TopLeftCorner'].split()
            found.append({'id': m['Identifier'], 'scale': float(m['ScaleDenominator']),
                          'e0': float(e0), 'n0': float(n0),
                          'mx': int(m['MatrixWidth']), 'my': int(m['MatrixHeight']),
                          'tw': int(m.get('TileWidth', 256)), 'th': int(m.get('TileHeight', 256))})
        break
    if not found:
        sys.exit(f"ERROR: TileMatrixSet '{tms_id}' not found.")
    found.sort(key=lambda d: -d['scale'])
    return found


def parse_tile_template(root, layer):
    for el in root.iter():
        if _local(el.tag) != 'Layer':
            continue
        ident, tmpl = None, None
        for ch in el:
            name = _local(ch.tag)
            if name == 'Identifier' and ident is None:
                ident = (ch.text or '').strip()
            elif name == 'ResourceURL' and ch.get('resourceType') == 'tile':
                tmpl = ch.get('template')
        if ident == layer and tmpl:
            return tmpl
    return None


def tile_url(template, base, layer, style, tms_id, matrix_id, x, y):
    if template:
        u = template
        u = re.sub(r'\{style\}', style, u, flags=re.I)
        u = re.sub(r'\{tilematrixset\}', tms_id, u, flags=re.I)
        u = re.sub(r'\{tilematrix\}', matrix_id, u, flags=re.I)
        u = re.sub(r'\{tilerow\}', str(y), u, flags=re.I)
        u = re.sub(r'\{tilecol\}', str(x), u, flags=re.I)
        if layer in u:
            u = u.replace(layer, quote(layer, safe=':'))
        return u
    return (f"{base}/rest/{quote(layer, safe=':')}/{quote(style)}/"
            f"{quote(tms_id)}/{matrix_id}/{y}/{x}?format=image/png")


def download_tile(session, url, cache_path, tries=5):
    if cache_path and os.path.exists(cache_path):
        try:
            with open(cache_path, 'rb') as f:
                return f.read() or None
        except OSError:
            pass
    delay = 1.0
    for _ in range(tries):
        try:
            r = session.get(url, timeout=60)
            if r.status_code == 200 and r.content[:8] == b'\x89PNG\r\n\x1a\n':
                if cache_path:
                    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                    with open(cache_path + '.part', 'wb') as f:
                        f.write(r.content)
                    os.replace(cache_path + '.part', cache_path)
                return r.content
            if r.status_code == 404:
                return None
        except requests.RequestException:
            pass
        time.sleep(delay)
        delay = min(delay * 2, 30)
    return None


# ---------------------------------------------------------------- BSB encoder

def encode_row(row):
    """Canonical BSB v2 RLL: byte < 0x80 = single pixel;
       (0x80|n), color = run of n pixels (n stored DIRECTLY, 1..127);
       row terminated with 0x00 after exactly w pixels."""
    out = bytearray()
    i, w = 0, len(row)
    while i < w:
        c = row[i]
        j = i + 1
        while j < w and row[j] == c:
            j += 1
        n = j - i
        i = j
        c &= 0x7F
        while n > 127:
            out += bytes((0xFF, c))
            n -= 127
        if n > 1:
            out += bytes((0x80 | n, c))
        else:
            out.append(c)
    out.append(0x00)
    return bytes(out)


def decode_row(buf, start, w):
    """Round-trip decoder with terminator semantics (like OpenCPN/libbsb)."""
    out = bytearray()
    p = start
    while True:
        c = buf[p]; p += 1
        if c == 0x00:
            break
        if c < 0x80:
            out.append(c)
        else:
            cnt = c & 0x7F
            if cnt == 0:
                cnt = (buf[p] << 8) | buf[p + 1]; p += 2
            out += bytes([buf[p]]) * cnt
            p += 1
    if len(out) != w:
        raise ValueError(f'row decoded to {len(out)} px, expected {w}')
    return bytes(out), p


def write_kap(path, name, w, h, palette, indices, refs, ply, res, nominal_scale=None):
    DU = 72
    sc = nominal_scale if nominal_scale else max(1, int(round(res / OGC_M_PER_PX)))
    today = datetime.date.today().strftime('%Y%m%d')
    L = ['VER/2.0',
         f'BSB/NA={name}    NU=,RA={w},{h},DU={DU}',
         f'KNP/SC={sc},GD=WGS84,PR=MERCATOR',
         '    PP=0,PI=UNKNOWN,SP=UNKNOWN,SK=0.0',
         '    UN=METERS,SD=LAT,DX=000,DY=000',
         f'CED/SE=,RE=1,ED={today}',
         'OST/1']
    for i, (x, y, la, lo) in enumerate(refs, 1):
        L.append(f'REF/{i},{x},{y},{la:.7f},{lo:.7f}')
    for i, (la, lo) in enumerate(ply, 1):
        L.append(f'PLY/{i},{la:.7f},{lo:.7f}')
    L += ['DTM/0.00,0.00', 'IFM/7']
    for i, (r, g, b) in enumerate(palette, 1):
        L.append(f'RGB/{i},{r},{g},{b}')
    text = ('\n'.join(L) + '\n').encode('ascii', 'replace')

    print('Encoding rows (with per-row round-trip check) ...')
    with open(path, 'wb') as f:
        f.write(text)
        f.write(bytes([0x1A, (w >> 8) & 0xFF, w & 0xFF, (h >> 8) & 0xFF, h & 0xFF])) 
        f.write(b'\x1a')
        for y in range(h):
            pix = bytes(b + 1 for b in indices[y * w:(y + 1) * w])
            enc = encode_row(pix)
            dec, _ = decode_row(enc, 0, w)
            if dec != pix:
                sys.exit(f'INTERNAL ERROR: row {y} failed round-trip verification')
            f.write(enc)
            if (y + 1) % 2000 == 0:
                print(f'  {y + 1}/{h} rows')


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--west', type=float); ap.add_argument('--south', type=float)
    ap.add_argument('--east', type=float); ap.add_argument('--north', type=float)
    ap.add_argument('--layer', default='Traficom:Merikarttasarja A public')
    ap.add_argument('--style', default='default')
    ap.add_argument('--tms', default=TMS_ID)
    ap.add_argument('--zoom', type=int, default=13)
    ap.add_argument('--out', default=None)
    ap.add_argument('--cache', default='tilecache')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--save-png', action='store_true')
    ap.add_argument('-y', '--yes', action='store_true')
    ap.add_argument('--list-layers', action='store_true')
    ap.add_argument('--scale', type=int, default=None,
                 help='Nominal chart scale to write into KNP/SC (e.g. 50000). '
                      'Overrides the value derived from the WMTS zoom level.')
    args = ap.parse_args()

    session = requests.Session()
    session.headers.update({'User-Agent': UA})

    print('Fetching GetCapabilities ...')
    root = fetch_capabilities(session)
    matrices = parse_tilematrixset(root, args.tms)

    if args.list_layers:
        for m in matrices:
            print(f'  {m["id"]}  {m["scale"] * OGC_M_PER_PX:g} m/px')
        return

    if None in (args.west, args.south, args.east, args.north):
        ap.error('--west/--south/--east/--north required')
    if not (args.west < args.east and args.south < args.north):
        sys.exit('ERROR: need west<east and south<north')

    z = args.zoom
    if not 0 <= z < len(matrices):
        sys.exit(f'ERROR: zoom must be 0..{len(matrices) - 1}')
    m = matrices[z]
    res = m['scale'] * OGC_M_PER_PX
    tw, th = m['tw'], m['th']

    template = parse_tile_template(root, args.layer)
    base = CAPS_URL.split('?')[0]

    fwd = Transformer.from_crs('EPSG:4326', 'EPSG:3067', always_xy=True)
    inv = Transformer.from_crs('EPSG:3067', 'EPSG:4326', always_xy=True)

    lons = [args.west + (args.east - args.west) * i / 16 for i in range(17)]
    lats = [args.south + (args.north - args.south) * i / 16 for i in range(17)]
    es, ns = [], []
    for lo in lons:
        for la in lats:
            e, n = fwd.transform(lo, la)
            es.append(e); ns.append(n)
    emin, emax, nmin, nmax = min(es), max(es), min(ns), max(ns)

    px0 = (emin - m['e0']) / res
    px1 = (emax - m['e0']) / res
    py0 = (m['n0'] - nmax) / res
    py1 = (m['n0'] - nmin) / res
    tx0, ty0 = int(math.floor(px0 / tw)), int(math.floor(py0 / th))
    tx1, ty1 = int(math.floor((px1 - 1e-9) / tw)), int(math.floor((py1 - 1e-9) / th))
    if tx0 < 0 or ty0 < 0 or tx1 >= m['mx'] or ty1 >= m['my']:
        sys.exit('ERROR: bbox outside tile matrix.')

    W, H = int(round(px1 - px0)), int(round(py1 - py0))
    if W > 65535 or H > 65535:
        sys.exit('ERROR: side exceeds 65535 px; lower --zoom or split area.')
    ncols, nrows = tx1 - tx0 + 1, ty1 - ty0 + 1

    print(f'Layer    : {args.layer}')
    print(f'Matrix   : {m["id"]}  ({res:g} m/px)')
    print(f'Area     : {W} x {H} px')
    print(f'Tiles    : {ncols} x {nrows} = {ncols * nrows}')
    if ncols * nrows > 4000 or W * H > 3.0e8:
        if not args.yes and input('Big job. Continue? [y/N] ').strip().lower() != 'y':
            sys.exit('Aborted.')

    jobs = [(tx, ty) for ty in range(ty0, ty1 + 1) for tx in range(tx0, tx1 + 1)]
    slug = ''.join(c if c.isalnum() else '_' for c in args.layer)
    mslug = ''.join(c if c.isalnum() else '_' for c in m['id'])
    mosaic = Image.new('RGB', (ncols * tw, nrows * th), (255, 255, 255))
    missing = done = 0

    def job(item):
        tx, ty = item
        url = tile_url(template, base, args.layer, args.style, args.tms, m['id'], tx, ty)
        cache = os.path.join(args.cache, slug, mslug, f'{tx}_{ty}.png')
        return tx, ty, download_tile(session, url, cache)

    print('Downloading ...')
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for tx, ty, data in ex.map(job, jobs):
            done += 1
            if data:
                tile = Image.open(io.BytesIO(data)).convert('RGBA')
                mosaic.paste(tile, ((tx - tx0) * tw, (ty - ty0) * th), tile)
            else:
                missing += 1
            if done % 100 == 0 or done == ncols * nrows:
                print(f'  {done}/{ncols * nrows} tiles')
    if missing:
        print(f'WARNING: {missing} tiles had no coverage (left white).')

    cx0, cy0 = int(math.floor(px0)), int(math.floor(py0))
    img = mosaic.crop((cx0 - tx0 * tw, cy0 - ty0 * th,
                       cx0 - tx0 * tw + W, cy0 - ty0 * th + H))
    del mosaic
    gx0, gy0 = cx0, cy0

    out = args.out or f'traficom_{args.west:.4f}_{args.south:.4f}_{args.east:.4f}_{args.north:.4f}.kap'
    name = os.path.splitext(os.path.basename(out))[0]

    print('Quantizing ...')
    try:
        p = img.quantize(colors=MAX_COLORS, method=Image.MEDIANCUT, dither=Image.Dither.NONE)
    except (AttributeError, TypeError):
        p = img.quantize(colors=MAX_COLORS, method=Image.MEDIANCUT)

    if args.save_png:
        p.save(name + '.png')
        with open(name + '.pgw', 'w') as f:
            f.write(f'{res}\n0\n0\n{-res}\n'
                    f"{m['e0'] + (gx0 + 0.5) * res}\n{m['n0'] - (gy0 + 0.5) * res}\n")
    indices = p.tobytes()
    raw = list(p.getpalette() or [])
    palette = [(tuple(raw[i * 3:i * 3 + 3]) if 3 * i + 2 < len(raw) else (0, 0, 0))
               for i in range(MAX_COLORS)]

    refs = []
    for fy in (0.0, 0.5, 1.0):
        for fx in (0.0, 0.5, 1.0):
            x = min(W - 1, int(round(fx * (W - 1))))
            y = min(H - 1, int(round(fy * (H - 1))))
            e = m['e0'] + (gx0 + x + 0.5) * res
            n = m['n0'] - (gy0 + y + 0.5) * res
            lon, lat = inv.transform(e, n)
            refs.append((x, y, lat, lon))

    def wgs(e, n):
        lo, la = inv.transform(e, n)
        return la, lo

    eL = m['e0'] + gx0 * res
    eR = m['e0'] + (gx0 + W) * res
    nT = m['n0'] - gy0 * res
    nB = m['n0'] - (gy0 + H) * res
    ply = [wgs(eL, nT), wgs(eR, nT), wgs(eR, nB), wgs(eL, nB)]

    print(f'Writing {out} ...')
    write_kap(out, name, W, H, palette, indices, refs, ply, res, nominal_scale=args.scale)
    print(f'Done: {os.path.getsize(out) / 1e6:.1f} MB, {W}x{H} px, '
        f'{len(refs)} REF points, nominal scale 1:{args.scale if args.scale else max(1, int(round(res / OGC_M_PER_PX)))}')

if __name__ == '__main__':
    main()
    


def parse_layers(root):
    """[(identifier, (w, s, e, n) or None)] for every Layer in capabilities."""
    out = []
    for el in root.iter():
        if _local(el.tag) != 'Layer':
            continue
        ident, bbox = None, None
        for ch in el:
            name = _local(ch.tag)
            if name == 'Identifier' and ident is None:
                ident = (ch.text or '').strip()
            elif name == 'WGS84BoundingBox':
                lo = up = None
                for g in ch:
                    if _local(g.tag) == 'LowerCorner':
                        lo = g.text.split()
                    if _local(g.tag) == 'UpperCorner':
                        up = g.text.split()
                if lo and up:
                    bbox = (float(lo[0]), float(lo[1]), float(up[0]), float(up[1]))
        if ident:
            out.append((ident, bbox))
    return out    