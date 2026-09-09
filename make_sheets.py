r"""make_sheets.py - batch-produce full chart sheets as KAP files.
Usage:
  py make_sheets.py sheets.txt --only B626 --zoom 13
  py make_sheets.py sheets.txt --zoom 12 -y
"""
import fnmatch  # add to imports at top
import argparse, os, re, subprocess, sys
from pyproj import Transformer
import traficom_kap as tk

COORD = re.compile(r'^\s*(\d+(?:\.\d+)?)\s*([NSEWnsew])\s*(\d+(?:\.\d+)?)\s*$')


def parse_coord(tok):
    m = COORD.match(tok)
    if m:
        val = float(m.group(1)) + float(m.group(3)) / 60.0
        return -val if m.group(2).upper() in 'SW' else val
    return float(tok)


def load_catalog(path):
    sheets = []
    for raw in open(path, encoding='utf-8-sig'):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        parts = [p.strip() for p in line.split(';')]
        if len(parts) < 3:
            print(f'SKIP (need 3 fields): {line}')
            continue
        nw, se = parts[1].split(), parts[2].split()
        if len(nw) != 2 or len(se) != 2:
            print(f'SKIP (bad coords): {line}')
            continue
        sheets.append(dict(id=parts[0],
                           north=parse_coord(nw[0]), west=parse_coord(nw[1]),
                           south=parse_coord(se[0]), east=parse_coord(se[1]),
                           layer=parts[3] if len(parts) > 3 else None))
    return sheets


def derive_layer(sid, available, override):
    if override:
        return override
    letter = next((c for c in sid.upper() if c.isalpha()), '?')
    for cand in (f'Traficom:Merikarttasarja {letter} public',
                 f'Traficom:Merikarttasarja {letter}'):
        if cand in available:
            return cand
    sys.exit(f'{sid}: no layer candidate found. Available layers:\n  '
             + '\n  '.join(sorted(available)))


def header_for(kap_path, txt_path, sid, prefix=None, info=None):
    data = open(kap_path, 'rb').read()
    hdr = data[:data.find(b'\x1a')].decode('ascii', 'replace')
    name_parts = [p for p in (prefix, sid, info) if p]
    name = ', '.join(name_parts)
    out, has_ifm = [], False
    for l in hdr.split('\n'):
        l = l.rstrip('\r')
        if not l.strip():
            continue
        if l.startswith('BSB/'):
            l = re.sub(r'BSB/NA=\S*\s*NU=', f'BSB/NA={name},NU=', l)
        elif l.startswith('IFM/'):
            l, has_ifm = 'IFM/1', True
        out.append(l)
    if not has_ifm:
        i = next(i for i, l in enumerate(out) if l.startswith('OST/'))
        out.insert(i + 1, 'IFM/1')
    out.append('EOD')
    open(txt_path, 'w', encoding='ascii', errors='replace').write('\n'.join(out) + '\n')
    

def process(sheet, layer, args):
    sid = sheet['id']
    tmp_kap, png, pgw = f'_tmp_{sid}.kap', f'_tmp_{sid}.png', f'_tmp_{sid}.pgw'
    hf, final = f'{sid}_header.txt', os.path.join(args.outdir, f'{sid}.kap')
    cmd = [sys.executable, 'traficom_kap.py',
           '--west', f"{sheet['west']:.6f}", '--south', f"{sheet['south']:.6f}",
           '--east', f"{sheet['east']:.6f}", '--north', f"{sheet['north']:.6f}",
           '--layer', layer, '--zoom', str(args.zoom),
           '--save-png', '-y', '--out', tmp_kap,
           '--workers', str(args.workers)]
    if args.delay:
        cmd += ['--delay', str(args.delay)]
    if args.scale:
        cmd += ['--scale', str(args.scale)]
    print(f'\n=== {sid}  ({layer}) ===\n>> {" ".join(cmd)}')
    if subprocess.run(cmd).returncode != 0:
        return 'traficom_kap.py failed'
    header_for(tmp_kap, hf, sid, prefix=args.prefix, info=args.info)
    cmd = [args.imgkap, png, hf, final]
    print('>>', ' '.join(cmd))
    if subprocess.run(cmd).returncode != 0:
        return 'imgkap failed'
    if not args.keep:
        for f in (tmp_kap, png, pgw, hf):
            try:
                os.remove(f)
            except OSError:
                pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('catalog')
    ap.add_argument('--only', nargs='+', help='process just these sheet IDs')
    ap.add_argument('--zoom', type=int, default=13)
    ap.add_argument('--layer', help='override layer for ALL sheets')
    ap.add_argument('--imgkap', default='imgkap.exe')
    ap.add_argument('--outdir', default='sheets_out')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--delay', type=float, default=0.0)
    ap.add_argument('--keep', action='store_true', help='keep temp PNG/header files')
    ap.add_argument('-y', '--yes', action='store_true')
    ap.add_argument('--scale', type=int, default=None,
                 help='Nominal chart scale to write into KNP/SC for ALL sheets (e.g. 50000)')
    ap.add_argument('--prefix', default=None, help='Prefix for chart name, e.g. FIN')
    ap.add_argument('--info', default=None, help='Extra info appended to chart name, e.g. N2000')
    args = ap.parse_args()

    sheets = load_catalog(args.catalog)
    if not sheets:
        sys.exit('Catalog is empty.')
    if args.only:
        patterns = [s.upper() for s in args.only]
        sheets = [s for s in sheets
              if any(fnmatch.fnmatch(s['id'].upper(), p) for p in patterns)]
    if not sheets:
        sys.exit(f'None matching {patterns} found in catalog.')

    session_cwd = os.path.dirname(os.path.abspath('traficom_kap.py'))
    os.chdir(session_cwd)                      # ensure traficom_kap.py is importable/found
    os.makedirs(args.outdir, exist_ok=True)

    print('Fetching GetCapabilities ...')
    s = __import__('requests').Session()
    s.headers['User-Agent'] = tk.UA
    root = tk.fetch_capabilities(s)
    matrices = tk.parse_tilematrixset(root, tk.TMS_ID)
    available = {ident for ident, *_ in tk.parse_layers(root)}
    fwd = Transformer.from_crs('EPSG:4326', 'EPSG:3067', always_xy=True)

    print(f'\n{"Sheet":8s} {"Layer":42s} {"px":>14s} {"Mpx":>6s} {"tiles":>7s}')
    total_tiles = total_mpx = 0
    for sh in sheets:
        sh['layer'] = sh['layer'] or derive_layer(sh['id'], available, args.layer)
        m = matrices[args.zoom]
        res = m['scale'] * tk.OGC_M_PER_PX
        es, ns = [], []
        for la in (sh['south'], sh['north']):
            for lo in (sh['west'], sh['east']):
                e, n = fwd.transform(lo, la)
                es.append(e); ns.append(n)
        W = round((max(es) - min(es)) / res)
        H = round((max(ns) - min(ns)) / res)
        t = -(-W // 256) * -(-H // 256)
        sh['tiles'], sh['mpx'] = t, W * H / 1e6
        total_tiles += t; total_mpx += W * H / 1e6
        print(f'{sh["id"]:8s} {sh["layer"]:42s} {W}x{H:<7d} {W * H / 1e6:6.0f} {t:7d}')
    print(f'\nTotal: {len(sheets)} sheets, {total_mpx:.0f} Mpx, '
          f'{total_tiles} tiles, ~{total_tiles * 25e-3:.0f} MB downloads, '
          f'~{total_mpx * 1e-3:.2f} GB of KAPs')
    if not args.yes and input('Proceed? [y/N] ').strip().lower() != 'y':
        sys.exit('Aborted.')

    failed = []
    for sh in sheets:
        err = process(sh, sh['layer'], args)
        if err:
            print(f'!! {sh["id"]}: {err}')
            failed.append(sh['id'])
        else:
            print(f'OK: {sh["id"]} -> {args.outdir}/{sh["id"]}.kap')

    print(f'\nDone. {len(sheets) - len(failed)}/{len(sheets)} sheets written to {args.outdir}\\')
    if failed:
        print('Failed: ' + ', '.join(failed))


if __name__ == '__main__':
    main()