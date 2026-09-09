#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_catalog.py - Auto-generate a make_sheets.py catalog file by dividing
   a WMTS layer's geographic bounding box into a regular grid of sheet tiles.

   Useful when you don't have pre-defined sheet corner coordinates - the
   script reads the layer's own WGS84BoundingBox from the WMTS capabilities
   and divides it into tiles of a given size in degrees.

   Usage:
     py make_catalog.py --layer "Traficom:Yleiskartat 250k public" ^
         --dlat 1.5 --dlon 3.0 --prefix YK250 --out sheets_yleiskartat.txt

     py make_catalog.py --layer "Traficom:Merikarttasarja A public" ^
         --dlat 0.5 --dlon 1.0 --prefix A --out sheets_A.txt
     
     Then:
        py make_catalog.py --layer "Traficom:Yleiskartat 250k public" ^
    --dlat 1.5 --dlon 3.0 --prefix YK250 --zoom 10 --overlap 0.05 ^
    --out sheets_yleiskartat.txt
"""
import argparse, sys
import requests
import traficom_kap as tk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--layer', required=True,
                     help='Exact WMTS layer identifier')
    ap.add_argument('--dlat', type=float, default=1.5,
                     help='Sheet height in degrees latitude (default 1.5)')
    ap.add_argument('--dlon', type=float, default=3.0,
                     help='Sheet width in degrees longitude (default 3.0)')
    ap.add_argument('--prefix', default='SHEET',
                     help='Sheet ID prefix, e.g. YK250 -> YK250_001')
    ap.add_argument('--out', default='sheets_auto.txt',
                     help='Output catalog filename')
    ap.add_argument('--overlap', type=float, default=0.05,
                    help='Fractional overlap between adjacent sheets (default 0.05 = 5%%)')
    ap.add_argument('--zoom', type=int, default=None,
                    help='Optional: verify sheet pixel size at this zoom level')
    ap.add_argument('--tms', default=tk.TMS_ID)
    args = ap.parse_args()

    session = requests.Session()
    session.headers.update({'User-Agent': tk.UA})

    print('Fetching GetCapabilities ...')
    root = tk.fetch_capabilities(session)

    # Find bounding box for the requested layer
    layers = tk.parse_layers(root)
    bbox = None
    for entry in layers:
        # handle both 2-tuple (old) and 3-tuple (new) parse_layers output
        if len(entry) == 3:
            ident, title, bb = entry
        else:
            ident, bb = entry
        if ident == args.layer and bb is not None:
            bbox = bb
            break
    if bbox is None:
        # Try again ignoring bbox=None entries (container layers)
        for entry in layers:
            ident = entry[0]
            if ident == args.layer:
                print(f'WARNING: layer found but has no WGS84BoundingBox in capabilities.')
                print(f'Falling back to approximate Finnish coastal extent.')
                bbox = (19.0, 59.5, 31.5, 70.5)
                break
        else:
            sys.exit(f'Layer "{args.layer}" not found in capabilities.\n'
                     f'Run list_layers.py to see exact identifiers.')

    w, s, e, n = bbox
    print(f'Layer bbox : {s:.4f}N {w:.4f}E  ->  {n:.4f}N {e:.4f}E')
    print(f'Sheet size : {args.dlat}° lat x {args.dlon}° lon')

    # Optionally show pixel size per sheet at a given zoom
    if args.zoom is not None:
        matrices = tk.parse_tilematrixset(root, args.tms)
        if not 0 <= args.zoom < len(matrices):
            sys.exit(f'--zoom must be 0..{len(matrices) - 1}')
        from pyproj import Transformer
        import math
        m = matrices[args.zoom]
        res = m['scale'] * tk.OGC_M_PER_PX
        fwd = Transformer.from_crs('EPSG:4326', 'EPSG:3067', always_xy=True)
        cx, cy_mid = (w + e) / 2, (s + n) / 2
        e0, n0 = fwd.transform(cx - args.dlon / 2, cy_mid)
        e1, n1 = fwd.transform(cx + args.dlon / 2, cy_mid)
        _, n_top = fwd.transform(cx, cy_mid + args.dlat / 2)
        _, n_bot = fwd.transform(cx, cy_mid - args.dlat / 2)
        W = int(round((e1 - e0) / res))
        H = int(round((n_top - n_bot) / res))
        tiles = math.ceil(W / m['tw']) * math.ceil(H / m['th'])
        print(f'At zoom {args.zoom} (~{res:g} m/px): ~{W}x{H} px per sheet, '
              f'~{tiles} tiles, ~{W*H/1e6:.0f} Mpx')

    # Generate grid with overlap
    OVERLAP = args.overlap
    olat = args.dlat * OVERLAP
    olon = args.dlon * OVERLAP
    sheets = []
    row = col = 0
    lat = s
    while lat < n - 1e-6:
        lat_n = min(lat + args.dlat, n)
        lon = w
        col = 0
        while lon < e - 1e-6:
            lon_e = min(lon + args.dlon, e)
            # expand by overlap (clamped to layer bbox)
            sheet_n = min(lat_n + olat, n)
            sheet_s = max(lat   - olat, s)
            sheet_w = max(lon   - olon, w)
            sheet_e = min(lon_e + olon, e)
            sheet_id = f'{args.prefix}_{row:02d}{col:02d}'
            sheets.append((sheet_id, sheet_n, sheet_w, sheet_s, sheet_e))
            lon = lon_e
            col += 1
        lat = lat_n
        row += 1

    print(f'Grid       : {row} rows x {col} cols = {len(sheets)} sheets')
    print(f'Writing    : {args.out}')

    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(f'# Auto-generated catalog for {args.layer}\n')
        f.write(f'# Sheet size: {args.dlat}° lat x {args.dlon}° lon, {args.overlap*100:.0f}% overlap\n')
        f.write(f'# Format: id; NW corner (lat lon); SE corner (lat lon); layer\n')
        f.write('#\n')
        for sheet_id, sn, sw, ss, se in sheets:
            f.write(f'{sheet_id}; {sheet_n:.6f} {sheet_w:.6f}; {sheet_s:.6f} {sheet_e:.6f}; {args.layer}\n')

    print(f'Done: {len(sheets)} sheets written to {args.out}')
    print()
    print('Next step:')
    print(f'  py make_sheets.py {args.out} --zoom 10 --scale 250000 --prefix YK250')


if __name__ == '__main__':
    main()
