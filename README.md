# Traficom WMTS → KAP Converter

*[Lue suomeksi / Read in Finnish →](README.fi.md)*

Batch-download Traficom's public nautical-chart WMTS tiles and package them as
BSB/KAP raster charts, ready to load into OpenCPN, SeaClear, and other
BSB-compatible chart plotters.

> ⚠️ **Non-navigational use only.** Charts produced by this tool are derived
> from public raster tiles and are **not** suitable for actual marine
> navigation. Always use official, up-to-date charts and publications for
> navigation. See [Disclaimer](#disclaimer) below.

---

## What this does

- Fetches map tiles from Traficom's public WMTS service for a given sheet
  area and zoom level
- Mosaics and quantizes them into a paletted raster
- Writes a valid BSB/KAP header (calibration points, polygon, projection,
  chart name) and encodes the raster using standard BSB run-length encoding
- Can batch-process an entire catalog of chart sheets in one run
- Lets you control the chart name and the nominal scale shown in chart-plotter
  chart lists, independent of the WMTS zoom level used to fetch the raster

Two scripts are involved:

| Script | Purpose |
|---|---|
| `traficom_kap.py` | Converts **one** bounding box into a single KAP file |
| `make_sheets.py` | Batch-processes a catalog of sheets (calls `traficom_kap.py` + `imgkap.exe` per sheet) |

Plus three helper scripts for Windows users who don't want to touch a
command line:

| File | Purpose |
|---|---|
| `install.bat` | One-time setup: checks Python, installs dependencies, checks for `imgkap.exe` |
| `run_50k.bat` | Builds the full 1:50,000 chart set from `sheets_scaindex.txt` |
| `run_20k.bat` | Builds the full 1:20,000 chart set from `sheets_subs.txt` |

---

## Creating your own catalog file

A catalog file (`sheets_scaindex.txt`, `sheets_subs.txt`, or any name you
choose) is just a plain text file listing the chart sheets you want to
generate, one per line. You can create or edit it with Notepad — no special
tools needed.

### Format

```
SHEET_ID; NW_CORNER; SE_CORNER; LAYER
```

Fields are separated by semicolons (`;`). The **first three fields are
required**; the fourth is optional.

| Field | Meaning | Example |
|---|---|---|
| 1. Sheet ID | Name used for the output filename and (with `--prefix`/`--info`) the chart title | `B626` |
| 2. NW corner | North-west corner: **latitude then longitude**, space-separated | `60N13.0 24E48.0` |
| 3. SE corner | South-east corner: **latitude then longitude**, space-separated | `60N01.2 25E06.2` |
| 4. Layer *(optional)* | Explicit WMTS layer name, if you don't want it auto-detected from the sheet ID's letter | `Traficom:Merikarttasarja B public` |

Blank lines and lines starting with `#` are ignored, so you can use `#` to
add comments or temporarily disable a sheet.

### Coordinate formats accepted

Each coordinate token must be written as **degrees, then the hemisphere
letter, then decimal minutes** — with only optional spaces between them (no
`°` or `'` symbols):

- `60N13.0` or `60 N 13.0` → 60°13.0' North
- `24E48.0` or `24 E 48.0` → 24°48.0' East
- `60S01.2`, `25W06.2` for southern/western hemispheres

Or, alternatively, **plain decimal degrees with no letter** — south and west
must then be written as **negative numbers**:

- `60.2167` (north, positive)
- `-24.8000` (west, negative)

Don't mix the two styles within one coordinate.

### Example file

```
# Traficom sheet catalog - 1:50,000 series
# id;   NW corner;      SE corner;       layer (optional)
B626;   60N13.0 24E48.0; 60N01.2 25E06.2
B627;   60N13.0 25E05.0; 60N01.2 25E23.0
C104;   60N30.0 22E30.0; 60N18.0 22E50.0; Traficom:Merikarttasarja C public
```

### Where do the corner coordinates come from?

You need the **north-west** and **south-east** corners of the rectangular
area you want each chart sheet to cover. A few practical ways to get them:

1. **From an official chart index/grid** — Traficom (or your national
   hydrographic authority) usually publishes a sheet index showing chart
   boundaries; read the corner coordinates off that.
2. **From a map tool** — right-click a point on Google Maps, OpenStreetMap,
   or a GIS tool to get its lat/lon, then convert to degrees+minutes if
   needed (most map tools show decimal degrees directly, which this format
   also accepts).
3. **From an existing KAP file** you already trust — its `PLY/` lines list
   the four corner coordinates of that chart's coverage; use the
   north-west-most and south-east-most of those four points.

### Checking the layer name

If field 4 is omitted, the script guesses the WMTS layer from the first
letter in your sheet ID (e.g. an ID starting with `B` looks for
`Traficom:Merikarttasarja B public`). To see all available layers on the
server:

```bat
py traficom_kap.py --list-layers
```

If your sheet ID's letter doesn't match an available layer, the script will
stop and print the full list of valid layer names — copy the correct one
into field 4 for that sheet.

### Testing a new catalog before a full run

Before committing to downloading a large batch, do a dry run to check sheet
sizes and tile counts without confirming the download:

```bat
py make_sheets.py my_new_sheets.txt --only "B6*"
```

The script prints a per-sheet size/tile table and asks **"Proceed? [y/N]"**
— answer `N` if you just want to sanity-check the numbers first (e.g.
catching a badly swapped NW/SE corner, which usually shows up as an
unreasonably huge pixel size or a `bbox outside tile matrix` error).

---

## Installation guide (step by step)

No programming knowledge needed. Three things go in one folder: this
project's files, Python, and `imgkap.exe`.

### Step 1 — Download this project

Go to the **[Releases](../../releases)** page, download the latest
`traficom-kap-vX.X.X.zip`, and extract it to a folder of your choice, e.g.
`C:\TraficomKAP\`.

*(Don't have a Releases zip yet? Use the green "Code → Download ZIP" button
on the repo's main page instead, then extract it the same way.)*

### Step 2 — Install Python (skip if you already have it)

1. Go to <https://www.python.org/downloads/> and download the latest
   Python 3 installer for Windows.
2. Run the installer. **On the first screen, tick the box "Add python.exe
   to PATH"** before clicking Install — this step is easy to miss and is
   required for the scripts to work.
3. Finish the installer.

### Step 3 — Get `imgkap.exe`

Not included in this repository (see [About imgkap.exe](#about-imgkapexe)).
Download it separately and place `imgkap.exe` directly inside the same
folder as `make_sheets.py` (e.g. `C:\TraficomKAP\imgkap.exe`).

### Step 4 — Run the setup script

Double-click **`install.bat`** in the project folder. It will:
- check Python is installed correctly
- install the required Python packages (`requests`, `pillow`, `pyproj`)
- check that `imgkap.exe` is present and warn you if it isn't

If it reports any errors, read the message in the window — it tells you
exactly what to fix (usually: install Python properly, or add the missing
`imgkap.exe`).

### Step 5 — Build your charts

Double-click:
- **`run_50k.bat`** — builds the full 1:50,000 chart set from
  `sheets_scaindex.txt`
- **`run_20k.bat`** — builds the full 1:20,000 chart set from
  `sheets_subs.txt`

A black command window will open and show progress (downloading tiles,
encoding, etc.). This can take a while for large catalogs — that's normal.
When it finishes, press any key to close the window.

### Step 6 — Load the charts

Finished `.kap` files are in the `sheets_out\` folder. Copy them into your
chart plotter's chart directory (e.g. OpenCPN's chart folder) and rescan
charts from within that program.

---

## Running individual sheets or custom options (advanced)

Once `install.bat` has been run once, you can also open a command prompt in
the project folder and run either script directly with custom options:

```bat
:: single sheet, custom scale/name
py traficom_kap.py --west 24.8008 --south 60.0200 --east 25.1032 --north 60.2183 ^
    --zoom 13 --scale 50000 --out B626.kap

:: just one sheet from the catalog, with wildcard matching
py make_sheets.py sheets_scaindex.txt --only "B6*" --zoom 12 --scale 50000 --prefix FIN

:: custom name suffix
py make_sheets.py sheets_scaindex.txt --only B626 --zoom 12 --scale 50000 --prefix FIN --info "(Mean)"
```

See [`make_sheets.py` usage](#make_sheetspy-usage) below for the full option
reference.

### Running from source on macOS/Linux

The `.bat` files are Windows-only, but the underlying scripts run anywhere
Python does:

```bash
pip install requests pillow pyproj
python make_sheets.py sheets_scaindex.txt --zoom 12 --scale 50000 --prefix FIN
```

(you'll need a Linux/macOS build of `imgkap`, or run it via Wine, for the
`make_sheets.py` batch pipeline — `traficom_kap.py` alone has no such
dependency)

---

## `make_sheets.py` usage

```
py make_sheets.py <catalog.txt> [options]
```

| Option | Description |
|---|---|
| `--only ID [ID ...]` | Process only matching sheet IDs. Supports wildcards (`*`, `?`), e.g. `--only "B6*"` |
| `--zoom N` | WMTS zoom level to download (controls raster detail/resolution) |
| `--scale N` | Nominal chart scale written into the KAP header and shown in chart-plotter chart lists, e.g. `--scale 50000` for 1:50,000. Independent of `--zoom`. |
| `--prefix TEXT` | Prefix added to the chart name, e.g. `FIN` |
| `--info TEXT` | Extra text appended to the chart name, e.g. `N2000` |
| `--layer NAME` | Override the WMTS layer for all sheets |
| `--imgkap PATH` | Path to `imgkap.exe` (default: `imgkap.exe` in the working folder) |
| `--outdir DIR` | Output folder for finished KAP files (default: `sheets_out`) |
| `--workers N` | Parallel tile-download threads (default: 4) |
| `--keep` | Keep temporary PNG/header files instead of deleting them |
| `-y`, `--yes` | Skip the confirmation prompt |

**Chart name example:**

```
py make_sheets.py sheets_scaindex.txt --only B626 --zoom 12 --scale 50000 --prefix FIN --info "(Mean)"
```

produces a chart that displays as **`FIN, B626, (Mean)`** with scale
**1:50000** in the chart-plotter chart list.

> **Note:** `--scale` applies to every sheet in a given run. If your catalog
> mixes sheets that need different nominal scales, run `make_sheets.py`
> separately per scale group using `--only` (e.g. once for the 1:50,000
> sheets, once for the 1:20,000 sheets).

---

## Catalog file format (`sheets_scaindex.txt`, `sheets_subs.txt`, ...)

Semicolon-separated text file, one sheet per line:

```
SHEET_ID; NW_CORNER; SE_CORNER; [optional layer override]
```

- Field 1: sheet ID (used as the KAP filename and chart name)
- Field 2: north-west corner (`lat lon`, see [coordinate formats](#coordinate-formats-accepted))
- Field 3: south-east corner (`lat lon`)
- Field 4 (optional): explicit WMTS layer name, otherwise auto-derived from
  the sheet ID's letter prefix
- Lines starting with `#` are comments and are skipped

---

## Troubleshooting

**"Python was not found on this computer" when running `install.bat`**
Python isn't installed, or wasn't added to PATH. Reinstall from
<https://www.python.org/downloads/> and make sure to tick "Add python.exe
to PATH" during setup, then run `install.bat` again.

**`install.bat` succeeds but `run_50k.bat`/`run_20k.bat` fail immediately
with an `imgkap.exe not found` message**
Download `imgkap.exe` and place it directly in the same folder as
`make_sheets.py` — not in a subfolder.

**The command window flashes and closes instantly**
Don't double-click `make_sheets.py` or `traficom_kap.py` directly — always
run them through the `.bat` files, or from an open command prompt, so any
error message stays visible.

**Chart loads but shows the wrong scale, or geometry looks wrong**
Check the `--scale` value matches the sheet's real nominal scale, and don't
hand-edit `KNP/SC=` in a finished `.kap` file — regenerate it with the
correct `--scale` option instead, since the scale field and the raster's
actual calibration need to stay consistent.

**Download seems very slow or times out often**
Traficom's WMTS server may be rate-limiting. Try lowering `--workers` (e.g.
`--workers 2`) or adding a small `--delay` between tile requests.

**Still stuck?**
Open an [issue](../../issues) with the exact error message and the command
or `.bat` file you ran.

---

## About `imgkap.exe`

`make_sheets.py` shells out to `imgkap.exe` to assemble the final KAP file
from the downloaded raster and generated header. It is **not bundled** in
this repository or its releases — please obtain it separately (see the
OpenCPN project's documentation/wiki) and check its license terms before
redistributing it yourself.

---

## Disclaimer

This project is an independent, personal-use tool and is not affiliated
with or endorsed by Traficom. Chart data is fetched from Traficom's public
WMTS service; use of that service is subject to Traficom's own terms of use.
Charts produced by this tool are for **reference and hobby use only** and
must **not** be relied upon for actual marine navigation.

---

## License

See [LICENSE](LICENSE) for this project's own code license. This does not
cover `imgkap.exe` or Traficom's chart data, which remain subject to their
own respective licenses/terms.
