# Traficom WMTS → KAP -muunnin

*[Read in English / Lue englanniksi →](README.md)*

Lataa Traficomin julkiset merikartta-WMTS-laatat erissä ja pakkaa ne
BSB/KAP-rasterikartoiksi, jotka voi ladata suoraan OpenCPN:ään, SeaCleariin
ja muihin BSB-yhteensopiviin karttaplottereihin.

> ⚠️ **Ei navigointikäyttöön.** Tällä työkalulla tuotetut kartat on johdettu
> julkisista rasterilaatoista, eivätkä ne sovellu varsinaiseen
> meriliikenteen navigointiin. Käytä navigointiin aina virallisia,
> ajantasaisia karttoja ja julkaisuja. Katso [Vastuuvapauslauseke](#vastuuvapauslauseke)
> alempaa.

---

## Mitä tämä tekee

- Hakee karttalaattoja Traficomin julkisesta WMTS-palvelusta halutulle
  karttalehden alueelle ja zoom-tasolle
- Yhdistää ja pelkistää laatat väripaletilliseksi rasteriksi
- Kirjoittaa kelvollisen BSB/KAP-otsikon (kalibrointipisteet, alueen
  ääriviivat, projektio, kartan nimi) ja koodaa rasterin standardin
  BSB-pätkäkoodauksella (run-length encoding)
- Voi käsitellä koko karttalehtiluettelon yhdellä ajolla
- Antaa hallita kartan nimeä ja karttaplotterin listassa näkyvää nimellistä
  mittakaavaa, riippumatta siitä millä WMTS-zoom-tasolla rasteri on haettu

Mukana on kaksi skriptiä:

| Skripti | Tarkoitus |
|---|---|
| `traficom_kap.py` | Muuntaa **yhden** rajausalueen yhdeksi KAP-tiedostoksi |
| `make_sheets.py` | Käsittelee koko karttalehtiluettelon (kutsuu `traficom_kap.py`:tä + `imgkap.exe`:tä jokaiselle lehdelle) |

Lisäksi mukana on kolme apuskriptiä Windows-käyttäjille, jotka eivät halua
käyttää komentoriviä:

| Tiedosto | Tarkoitus |
|---|---|
| `install.bat` | Kertaluontoinen asennus: tarkistaa Pythonin, asentaa riippuvuudet, tarkistaa `imgkap.exe`:n |
| `run_50k.bat` | Luo koko 1:50 000 -karttasarjan tiedostosta `sheets_scaindex.txt` |
| `run_20k.bat` | Luo koko 1:20 000 -karttasarjan tiedostosta `sheets_subs.txt` |

---

## Oman karttalehtiluettelon (catalog-tiedoston) luominen

Luettelotiedosto (`sheets_scaindex.txt`, `sheets_subs.txt`, tai mikä nimi
tahansa) on tavallinen tekstitiedosto, joka listaa haluamasi karttalehdet
yksi rivi kerrallaan. Sen voi luoda tai muokata vaikka Muistiolla — erikoisia
työkaluja ei tarvita.

### Muoto

```
LEHTITUNNUS; LUOTEISKULMA; KAAKKOISKULMA; TASO
```

Kentät erotetaan puolipisteellä (`;`). **Kolme ensimmäistä kenttää ovat
pakollisia**, neljäs on valinnainen.

| Kenttä | Merkitys | Esimerkki |
|---|---|---|
| 1. Lehtitunnus | Käytetään tiedostonimenä ja (yhdessä `--prefix`/`--info`-valitsimien kanssa) kartan nimenä | `B626` |
| 2. Luoteiskulma | Alueen luoteiskulma: **leveysaste ensin, sitten pituusaste**, välilyönnillä erotettuna | `60N13.0 24E48.0` |
| 3. Kaakkoiskulma | Alueen kaakkoiskulma: **leveysaste ensin, sitten pituusaste**, välilyönnillä erotettuna | `60N01.2 25E06.2` |
| 4. Taso *(valinnainen)* | Nimenomainen WMTS-tason nimi, jos et halua sen päättyvän automaattisesti lehtitunnuksen kirjaimen perusteella | `Traficom:Merikarttasarja B public` |

Tyhjät rivit ja `#`-merkillä alkavat rivit ohitetaan, joten `#`:llä voi
lisätä kommentteja tai poistaa lehden tilapäisesti käytöstä.

### Hyväksytyt koordinaattimuodot

Jokainen koordinaatti tulee kirjoittaa muodossa **asteet, sitten
pallonpuoliskon kirjain, sitten desimaaliminuutit** — vain valinnaisilla
välilyönneillä väliin (ei `°`- tai `'`-merkkejä):

- `60N13.0` tai `60 N 13.0` → 60°13,0' pohjoista
- `24E48.0` tai `24 E 48.0` → 24°48,0' itää
- `60S01.2`, `25W06.2` eteläisille/läntisille pallonpuoliskoille

Vaihtoehtoisesti voi käyttää **pelkkiä desimaaliasteita ilman kirjainta** —
tällöin etelä ja länsi kirjoitetaan **negatiivisina lukuina**:

- `60.2167` (pohjoinen, positiivinen)
- `-24.8000` (läntinen, negatiivinen)

Älä sekoita näitä kahta tyyliä saman koordinaatin sisällä.

### Esimerkkitiedosto

```
# Traficom-karttaluettelo - 1:50 000 -sarja
# tunnus; luoteiskulma;    kaakkoiskulma;    taso (valinnainen)
B626;   60N13.0 24E48.0; 60N01.2 25E06.2
B627;   60N13.0 25E05.0; 60N01.2 25E23.0
C104;   60N30.0 22E30.0; 60N18.0 22E50.0; Traficom:Merikarttasarja C public
```

### Mistä kulmakoordinaatit löytyvät?

Tarvitset kunkin karttalehden kattaman suorakulmion **luoteis-** ja
**kaakkoiskulman**. Muutamia käytännön tapoja hankkia ne:

1. **Virallisesta karttalehtijaosta** — Traficom (tai oman maasi
   merenkulkuviranomainen) julkaisee yleensä lehtijaon, josta näkyy
   karttalehtien rajat; lue kulmakoordinaatit siitä.
2. **Karttatyökalusta** — napsauta hiiren oikealla pistettä Google
   Mapsissa, OpenStreetMapissa tai GIS-työkalussa saadaksesi sen
   koordinaatit, ja muunna tarvittaessa asteiksi ja minuuteiksi (useimmat
   karttatyökalut näyttävät suoraan desimaaliasteet, joita tämä muoto myös
   hyväksyy).
3. **Olemassa olevasta KAP-tiedostosta**, johon jo luotat — sen
   `PLY/`-riveillä on kartan neljä kulmapistettä; käytä niistä
   luoteisinta ja kaakkoisinta pistettä.

### Tasonimen tarkistaminen

Jos kenttä 4 jätetään pois, skripti arvaa WMTS-tason lehtitunnuksen
ensimmäisen kirjaimen perusteella (esim. `B`-alkuinen tunnus etsii tasoa
`Traficom:Merikarttasarja B public`). Nähdäksesi kaikki palvelimella
saatavilla olevat tasot:

```bat
py traficom_kap.py --list-layers
```

Jos lehtitunnuksesi kirjain ei vastaa mitään saatavilla olevaa tasoa,
skripti pysähtyy ja tulostaa listan kelvollisista tasonimistä — kopioi
oikea nimi kyseisen lehden kenttään 4.

### Uuden luettelon testaaminen ennen täyttä ajoa

Ennen kuin sitoudut lataamaan suuren erän, tee kuivaharjoitus, joka
näyttää lehtien koot ja laattamäärät ilman latauksen vahvistamista:

```bat
py make_sheets.py oma_uusi_luettelo.txt --only "B6*"
```

Skripti tulostaa lehtikohtaisen koko-/laattamäärätaulukon ja kysyy
**"Proceed? [y/N]"** — vastaa `N`, jos haluat vain tarkistaa luvut
ensin (esim. huomataksesi vahingossa vaihdetut luoteis-/kaakkoiskulmat,
mikä näkyy yleensä kohtuuttoman suurena pikselikokona tai
`bbox outside tile matrix` -virheenä).

---

## Asennusohje (vaihe vaiheelta)

Ei vaadi ohjelmointiosaamista. Kolme asiaa tulee samaan kansioon: tämän
projektin tiedostot, Python ja `imgkap.exe`.

### Vaihe 1 — Lataa projekti

Siirry **[Releases](../../releases)**-sivulle, lataa uusin
`traficom-kap-vX.X.X.zip` ja pura se haluamaasi kansioon, esim.
`C:\TraficomKAP\`.

*(Eikö Releases-pakettia vielä ole? Käytä sen sijaan vihreää
"Code → Download ZIP" -painiketta repon pääsivulla ja pura se samalla
tavalla.)*

### Vaihe 2 — Asenna Python (ohita, jos sinulla on se jo)

1. Siirry osoitteeseen <https://www.python.org/downloads/> ja lataa uusin
   Python 3 -asennusohjelma Windowsille.
2. Käynnistä asennusohjelma. **Ensimmäisellä ruudulla rastita "Add
   python.exe to PATH"** ennen Install-painiketta — tämä vaihe unohtuu
   helposti, mutta se on välttämätön skriptien toimimiseksi.
3. Viimeistele asennus.

### Vaihe 3 — Hanki `imgkap.exe`

Ei sisälly tähän repositorioon (katso [Tietoa imgkap.exe:stä](#tietoa-imgkapexestä)).
Lataa se erikseen ja aseta `imgkap.exe` suoraan samaan kansioon kuin
`make_sheets.py` (esim. `C:\TraficomKAP\imgkap.exe`).

### Vaihe 4 — Aja asennusskripti

Kaksoisnapsauta **`install.bat`** projektikansiossa. Se:
- tarkistaa, että Python on asennettu oikein
- asentaa tarvittavat Python-paketit (`requests`, `pillow`, `pyproj`)
- tarkistaa, että `imgkap.exe` on paikallaan, ja varoittaa jos ei ole

Jos se ilmoittaa virheistä, lue ikkunan viesti — se kertoo tarkalleen mitä
pitää korjata (yleensä: asenna Python uudelleen oikein, tai lisää puuttuva
`imgkap.exe`).

### Vaihe 5 — Luo kartat

Kaksoisnapsauta:
- **`run_50k.bat`** — luo koko 1:50 000 -karttasarjan tiedostosta
  `sheets_scaindex.txt`
- **`run_20k.bat`** — luo koko 1:20 000 -karttasarjan tiedostosta
  `sheets_subs.txt`

Musta komentoikkuna avautuu ja näyttää etenemisen (laattojen lataus,
koodaus jne.). Tämä voi kestää tovin suurilla luetteloilla — se on
normaalia. Kun se on valmis, paina mitä tahansa näppäintä sulkeaksesi
ikkunan.

### Vaihe 6 — Lataa kartat karttaplotteriin

Valmiit `.kap`-tiedostot löytyvät `sheets_out\`-kansiosta. Kopioi ne
karttaplotterisi karttakansioon (esim. OpenCPN:n karttakansioon) ja
päivitä kartat kyseisestä ohjelmasta.

---

## Yksittäisten lehtien ajaminen tai omat valitsimet (edistyneille)

Kun `install.bat` on ajettu kerran, voit myös avata komentokehotteen
projektikansiossa ja ajaa jompaakumpaa skriptiä omilla valitsimilla:

```bat
:: yksi lehti, oma mittakaava/nimi
py traficom_kap.py --west 24.8008 --south 60.0200 --east 25.1032 --north 60.2183 ^
    --zoom 13 --scale 50000 --out B626.kap

:: vain yksi lehti luettelosta, jokerimerkeillä
py make_sheets.py sheets_scaindex.txt --only "B6*" --zoom 12 --scale 50000 --prefix FIN

:: oma nimen lisäosa
py make_sheets.py sheets_scaindex.txt --only B626 --zoom 12 --scale 50000 --prefix FIN --info "(Mean)"
```

Katso [`make_sheets.py`-käyttö](#make_sheetspy-käyttö) alempaa kaikki
valitsimet.

### Ajaminen lähdekoodista macOS/Linuxilla

`.bat`-tiedostot toimivat vain Windowsilla, mutta itse skriptit toimivat
kaikkialla missä Python toimii:

```bash
pip install requests pillow pyproj
python make_sheets.py sheets_scaindex.txt --zoom 12 --scale 50000 --prefix FIN
```

(tarvitset Linux/macOS-version `imgkap`:sta, tai aja se Wine:n kautta,
`make_sheets.py`:n eräajoputkea varten — pelkkä `traficom_kap.py` ei
tarvitse sitä)

---

## `make_sheets.py`-käyttö

```
py make_sheets.py <luettelo.txt> [valitsimet]
```

| Valitsin | Kuvaus |
|---|---|
| `--only TUNNUS [TUNNUS ...]` | Käsittele vain vastaavat lehtitunnukset. Tukee jokerimerkkejä (`*`, `?`), esim. `--only "B6*"` |
| `--zoom N` | Ladattava WMTS-zoom-taso (määrää rasterin tarkkuuden) |
| `--scale N` | KAP-otsikkoon kirjoitettava ja karttaplotterin listassa näkyvä nimellinen mittakaava, esim. `--scale 50000` mittakaavalle 1:50 000. Riippumaton `--zoom`-valitsimesta. |
| `--prefix TEKSTI` | Kartan nimeen lisättävä etuliite, esim. `FIN` |
| `--info TEKSTI` | Kartan nimeen lisättävä lisäteksti, esim. `N2000` |
| `--layer NIMI` | Ylikirjoita WMTS-taso kaikille lehdille |
| `--imgkap POLKU` | Polku `imgkap.exe`:hen (oletus: `imgkap.exe` työkansiossa) |
| `--outdir KANSIO` | Kansio valmiille KAP-tiedostoille (oletus: `sheets_out`) |
| `--workers N` | Rinnakkaisten lataussäikeiden määrä (oletus: 4) |
| `--keep` | Säilytä väliaikaiset PNG/otsikkotiedostot poistamisen sijaan |
| `-y`, `--yes` | Ohita vahvistuskysymys |

**Esimerkki kartan nimestä:**

```
py make_sheets.py sheets_scaindex.txt --only B626 --zoom 12 --scale 50000 --prefix FIN --info "(Mean)"
```

tuottaa kartan, joka näkyy muodossa **`FIN, B626, (Mean)`** mittakaavalla
**1:50000** karttaplotterin karttalistassa.

> **Huom:** `--scale` koskee kaikkia yhden ajon lehtiä. Jos luettelossasi on
> eri nimellisiä mittakaavoja tarvitsevia lehtiä, aja `make_sheets.py`
> erikseen kunkin mittakaavaryhmän kohdalla `--only`-valitsimella (esim.
> kerran 1:50 000 -lehdille, kerran 1:20 000 -lehdille).

---

## Luettelotiedoston muoto (`sheets_scaindex.txt`, `sheets_subs.txt`, ...)

Puolipisteellä eroteltu tekstitiedosto, yksi lehti per rivi:

```
LEHTITUNNUS; LUOTEISKULMA; KAAKKOISKULMA; [valinnainen taso]
```

- Kenttä 1: lehtitunnus (käytetään KAP-tiedostonimenä ja kartan nimenä)
- Kenttä 2: luoteiskulma (`lev pit`, katso [koordinaattimuodot](#hyväksytyt-koordinaattimuodot))
- Kenttä 3: kaakkoiskulma (`lev pit`)
- Kenttä 4 (valinnainen): nimenomainen WMTS-tason nimi, muuten pääteltynä
  automaattisesti lehtitunnuksen alkukirjaimesta
- `#`-merkillä alkavat rivit ovat kommentteja ja ohitetaan

---

## Vianetsintä

**"Python was not found on this computer" ajettaessa `install.bat`:tia**
Pythonia ei ole asennettu, tai sitä ei lisätty PATH-muuttujaan. Asenna
uudelleen osoitteesta <https://www.python.org/downloads/> ja muista
rastittaa "Add python.exe to PATH" asennuksen aikana, aja sitten
`install.bat` uudelleen.

**`install.bat` onnistuu, mutta `run_50k.bat`/`run_20k.bat` epäonnistuu
heti viestillä `imgkap.exe not found`**
Lataa `imgkap.exe` ja aseta se suoraan samaan kansioon kuin
`make_sheets.py` — ei alikansioon.

**Komentoikkuna välähtää ja sulkeutuu heti**
Älä kaksoisnapsauta `make_sheets.py`- tai `traficom_kap.py`-tiedostoja
suoraan — käytä aina `.bat`-tiedostoja tai avointa komentokehotetta, jotta
mahdollinen virheviesti jää näkyviin.

**Kartta latautuu, mutta mittakaava tai geometria on väärä**
Tarkista, että `--scale`-arvo vastaa lehden todellista nimellistä
mittakaavaa, äläkä muokkaa `KNP/SC=`-arvoa käsin valmiiseen
`.kap`-tiedostoon — luo se sen sijaan uudelleen oikealla
`--scale`-valitsimella, sillä mittakaavakentän ja rasterin todellisen
kalibroinnin täytyy pysyä yhteensopivina.

**Lataus on hyvin hidas tai aikakatkeaa usein**
Traficomin WMTS-palvelin saattaa rajoittaa pyyntöjä. Kokeile pienempää
`--workers`-arvoa (esim. `--workers 2`) tai pientä `--delay`-viivettä
laattapyyntöjen väliin.

**Ongelma jatkuu?**
Avaa [issue](../../issues) tarkalla virheviestillä ja komennolla tai
`.bat`-tiedostolla, jota ajoit.

---

## Tietoa imgkap.exe:stä

`make_sheets.py` kutsuu `imgkap.exe`:tä koostaakseen lopullisen
KAP-tiedoston ladatusta rasterista ja luodusta otsikosta. Sitä **ei
toimiteta mukana** tässä repositoriossa tai sen julkaisuissa — hanki se
erikseen (katso OpenCPN-projektin dokumentaatiota/wikiä) ja tarkista sen
lisenssiehdot ennen kuin jaat sitä itse eteenpäin.

---

## Vastuuvapauslauseke

Tämä projekti on riippumaton, henkilökohtaiseen käyttöön tarkoitettu
työkalu, eikä se ole Traficomin sponsoroima tai hyväksymä. Karttadata
haetaan Traficomin julkisesta WMTS-palvelusta; palvelun käyttö on
Traficomin omien käyttöehtojen alaista. Tällä työkalulla tuotetut kartat
on tarkoitettu **vain viitteelliseen ja harrastekäyttöön**, eikä niihin
saa **luottaa** varsinaisessa meriliikenteen navigoinnissa.

---

## Lisenssi

Katso [LICENSE](LICENSE) tämän projektin oman koodin lisenssistä. Tämä ei
kata `imgkap.exe`:tä eikä Traficomin karttadataa, jotka ovat omien
lisenssiensä/ehtojensa alaisia.
