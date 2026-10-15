# Open items for the app library

Fill in what you can, in any order, and save. Leave anything you're unsure of as it is. When you're done (or partly done), tell me and I'll apply it to the catalog.

---

## 1. Titles for hymns that only have a Coptic title

These are my drafts, already applied to the hymns. Correct any title here and I'll update it.

| Folder | Coptic title | English title | Arabic title |
|---|---|---|---|
| `arihouo-gasf-third-hoos` | Ⲁⲣⲓϩⲟⲩⲟ Ϭⲁⲥϥ from 3rd Hoos | Aree Hoo Ou Chasf (Third Canticle) | اري هوؤو تشاسف (الهوس الثالث) |
| `aripalin` | Ⲁⲣⲓⲯⲁⲗⲓⲛ | Aripsalin | اريبصالين |
| `christos-analympsis` | ⲭ̀ⲣⲓⲥⲧⲟⲥ ⲁ̀ⲛⲁⲗⲩⲙⲯⲓⲥ | Christos Analimpsis (Christ Ascended) | اخرستوس أناليم ابسيس |
| `ethbe-ti-anastasis` | Ⲉⲑⲃⲉ Ϯⲁⲛⲁⲥⲧⲁⲥⲓⲥ | Ethve Ti Anastasis (For the Resurrection of the Dead) | إثفي تي أنسطاسيس |
| `fai-etafenf` | Ⲫⲁⲓ Ⲉⲧⲁϥⲉⲛϥ | Fai Etaf Enf (This Is He Who Offered Himself) | فاي إيتاف إنف |
| `joyful-agios-major` | Joyful Ⲁⲅⲓⲟⲥ, Major | Joyful Agios, Major | آجيوس الفرايحي (كبير) |
| `kata-ni-khoros` | Ⲕⲁⲧⲁ Ⲛⲓⲭⲟⲣⲟⲥ | Kata Ni Khoros (All the Choirs) | كاطا ني خوروس |
| `ke-ypertou` | Ⲕⲉ Ⲩ̀ⲡⲉⲣⲧⲟⲩ | Ke Ypertou | كي إبرتو |
| `onim-nai-symfonia` | Ⲱ̀ⲛⲓⲙ Ⲛⲁⲓ Ⲥⲩⲙⲫⲱⲛⲓⲁ | Oonim Nai Symphonia (What Are These?) | أونيم ناي سيمفونيا |
| `ou-katikisis` | Ⲟⲩⲕⲁⲧⲏⲭⲏⲥⲓⲥ | Ou Katikisis (A Homily) | أوكاتي شيسيس |
| `pi-christos-aftonf` | Ⲡⲓⲭⲣⲓⲥⲧⲟⲥ Ⲁϥⲧⲟⲛϥ | Pikhristos Aftonf (Christ Is Risen) | بي إخرستوس آفتونف |
| `pi-oik` | Ⲡⲓⲱⲓⲕ | Pi Oik (The Bread of Life) | بي أويك |
| `pi-pnevma` | ⲡⲓⲡ̀ⲛⲉⲩⲙⲁ | Pi Pnevma (The Spirit of Comfort) | بي إبنفما |
| `ten-thinou` | Ⲧⲉⲛ Ⲑⲏⲛⲟⲩ | Ten Theeno (Arise, O Children of the Light) | تين ثينو |
| `tenoue-n-khok` | Ⲧⲉⲛⲟⲩⲉϩ Ⲛ̀ⲥⲱⲕ | Tenoueh Ensok (We Follow You) | تين أوويه إنسوك |
| `ton-syna` | ⲧⲟⲛ ⲥⲩⲛⲁ | Ton Sinanarkhon (We the Believers) | طون سينانارخون |
| `tou-lithou` | Ⲧⲟⲩ Ⲗⲓⲑⲟⲩ | Tou Lithou (When the Stone Was Sealed) | طو ليثو |

---

## 2. Library names

Correct any name, add missing ones, or delete ones that don't belong. Arabic names are my drafts.

**Seasons** (each has Raising of Incense, Liturgy, Special hymns; all but Annual also have Midnight Praises)
- Annual · السنوي
- Nyrouz - النيروز (راس السنة القبطية)
- Kiahk · كيهك
- Nativity · الميلاد
- Theophany · الغطاس
- Great Lent · الصوم الكبير
- Palm Sunday · أحد الشعانين
- Resurrection · القيامة
- Ascension · الصعود
- Pentecost · العنصرة
- Apostles Fast - صوم الرسل

**Services inside a season**
- Midnight Praises · التسبحة
- Raising of Incense · رفع البخور
- Liturgy · القداس
- Special hymns · ألحان خاصة

**Praises** (its own group): Vesper Praises · تسبحة عشية, Midnight Praises · تسبحة نصف الليل, Morning Praises · تسبحة باكر

**Special seasons**: Holy Week · أسبوع الآلام (by day: Palm Sunday evening, Monday … Good Friday), Bright Saturday · سبت الفرح

**Common hymns** · ألحان عامة

**Occasions**: Veneration · تمجيد
- (add more occasions here, e.g. Funeral, Wedding, Consecration…)

**Questions**
- Should feasts have their own entries in the library, like the other apps (Coptic New Year, Feast of the Cross, Circumcision, Wedding at Cana, Presentation, Lazarus Saturday, Jonah's Fast…)? yes but these are the seasons or we can group them under Feasts, Fasts
- Kiahk has its own praises. Keep them under the Kiahk season, or move them to the Praises group? either is fine.

---

## 3–5. Hymn details: add them to each hymn as you go

No need to fill a big table. Whenever you work on a hymn, open its `info.json` (in its folder under `content/`) and add any of these lines. Then tell me, or run `python3 tools/build_catalog.py`, which reports typos.

```json
{
  "title": "…",
  "places": ["resurrection/liturgy", "annual/raising-of-incense"],
  "kind": "melismatic",
  "style": "major",
  "mode": "festal",
  "text": "verse-cymbals-resurrection",
  "lyricsSource": "https://tasbeha.org/hymn_library/view/…"
}
```

| Line | What it does |
|---|---|
| `places` | Where the hymn appears in the library. List as many as apply. |
| `kind` | `recital` or `melismatic` |
| `style` | `major`, `medium` or `minor` |
| `mode` | `annual`, `festal`, `lenten`, `joyful`… |
| `text` | Only for a second tune of another hymn: that hymn's folder name. Its lyrics are then shared, not copied. |
| `lyricsSource` | Where to find the words, for hymns that don't have them yet |

Keep the existing lines (`title`, `youtube`, `titles`) as they are.

### Places you can use

**Seasons**
- Annual: `annual/raising-of-incense`, `annual/liturgy`, `annual/special`
- Nayrouz (Coptic New Year): `nayrouz/midnight-praises`, `nayrouz/raising-of-incense`, `nayrouz/liturgy`, `nayrouz/special`
- Kiahk: `kiahk/midnight-praises`, `kiahk/raising-of-incense`, `kiahk/liturgy`, `kiahk/special`

**Feasts**
- Feast of the Cross: `feast-of-the-cross/midnight-praises`, `feast-of-the-cross/raising-of-incense`, `feast-of-the-cross/liturgy`, `feast-of-the-cross/special`
- Nativity: `nativity/midnight-praises`, `nativity/raising-of-incense`, `nativity/liturgy`, `nativity/special`
- Circumcision: `circumcision/midnight-praises`, `circumcision/raising-of-incense`, `circumcision/liturgy`, `circumcision/special`
- Theophany: `theophany/midnight-praises`, `theophany/raising-of-incense`, `theophany/liturgy`, `theophany/special`
- Wedding at Cana: `wedding-at-cana/midnight-praises`, `wedding-at-cana/raising-of-incense`, `wedding-at-cana/liturgy`, `wedding-at-cana/special`
- Presentation of the Lord: `presentation/midnight-praises`, `presentation/raising-of-incense`, `presentation/liturgy`, `presentation/special`
- Lazarus Saturday: `lazarus-saturday/midnight-praises`, `lazarus-saturday/raising-of-incense`, `lazarus-saturday/liturgy`, `lazarus-saturday/special`
- Palm Sunday: `palm-sunday/midnight-praises`, `palm-sunday/raising-of-incense`, `palm-sunday/liturgy`, `palm-sunday/special`
- Resurrection: `resurrection/midnight-praises`, `resurrection/raising-of-incense`, `resurrection/liturgy`, `resurrection/special`
- Ascension: `ascension/midnight-praises`, `ascension/raising-of-incense`, `ascension/liturgy`, `ascension/special`
- Pentecost: `pentecost/midnight-praises`, `pentecost/raising-of-incense`, `pentecost/liturgy`, `pentecost/special`

**Fasts**
- Advent Fast: `advent/midnight-praises`, `advent/raising-of-incense`, `advent/liturgy`, `advent/special`
- Jonah's Fast: `jonahs-fast/midnight-praises`, `jonahs-fast/raising-of-incense`, `jonahs-fast/liturgy`, `jonahs-fast/special`
- Great Lent: `great-lent/midnight-praises`, `great-lent/raising-of-incense`, `great-lent/liturgy`, `great-lent/special`
- Apostles' Fast: `apostles-fast/midnight-praises`, `apostles-fast/raising-of-incense`, `apostles-fast/liturgy`, `apostles-fast/special`

**Praises**
- Praises (Psalmody): `praises/vesper-praises`, `praises/midnight-praises`, `praises/morning-praises`

**Special seasons**
- Holy Week: `holy-week/palm-sunday-evening`, `holy-week/monday`, `holy-week/tuesday`, `holy-week/wednesday`, `holy-week/thursday`, `holy-week/friday`
- Bright Saturday: `bright-saturday/hymns`

**Common hymns**
- Common hymns: `common-hymns/midnight-praises`, `common-hymns/raising-of-incense`, `common-hymns/liturgy`, `common-hymns/special`

**Occasions**
- Veneration: `veneration/hymns`

### Still to do, when you get to them

- Tune pair to check: `verse-cymbals-resurrection` (3:32) and `verses-cymbals-resurrection` (2:18). If they're the same words, add `"text": "verse-cymbals-resurrection"` to the second one.
- Hymns with audio but no lyrics: `conclusion-canon-resurrection`, `ke-ypertou`, `verses-cymbals-resurrection`.
