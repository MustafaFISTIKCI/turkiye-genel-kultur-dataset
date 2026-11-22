# Türkiye Genel Kültür Görsel Veri Seti

Türkiye'nin **81 iline** ait **tarihi yapılar**, **doğal güzellikler** ve **yöresel lezzetler** ile **255 ülke/bölge bayrağını** içeren açık kaynaklı, ticari kullanıma uygun görsel veri seti.

## Klasör Yapısı

```text
turkiye-genel-kultur-dataset/
├── bayrak/                         # 255 ülke/bölge bayrağı (turkiye_tr.svg, almanya_de.svg ...)
├── turkiye_gorselleri/
│   ├── doga/                       # 81 il doğal güzellik görseli (01_adana_kapikaya_kanyonu.webp ...)
│   ├── tarihi_yapi/                # 81 il tarihi yapı görseli (01_adana_taskopru.webp ...)
│   └── yemek/                      # 81 il yöresel lezzet görseli (01_adana_adana_kebabi.webp ...)
├── data/
│   ├── turkiye_81_il.json          # 243 konumun adı, ili, bölgesi, ipucu, lisans ve atıf bilgisi
│   ├── bayraklar.json              # 255 bayrağın Türkçe adı, başkenti, kıtası ve dosya yolu
│   └── seed_locations.json         # Tohum arama listesi
├── scripts/
│   ├── build_seed.py               # 81 il tohum veri üreticisi
│   └── fetch_images.py             # Wikimedia Commons API lisans filtreli indirici
├── CREDITS.md                      # Tüm görseller için yazar, lisans ve kaynak tablosu
├── LICENSE                         # Kod için MIT; görseller için kendi açık lisansları
└── requirements.txt
```

## Veri Formatları

### `data/turkiye_81_il.json`
```json
{
  "id": "01_tarihi_yapi",
  "plate": "01",
  "city": "Adana",
  "region": "Akdeniz",
  "category": "tarihi_yapi",
  "name": "Taşköprü",
  "hint": "Roma döneminden kalma, Seyhan Nehri üzerindeki tarihi taş köprü.",
  "imagePath": "turkiye_gorselleri/tarihi_yapi/01_adana_taskopru.webp",
  "width": 1200,
  "height": 799,
  "author": "Mesutdemirrci",
  "license": "CC BY-SA 4.0",
  "attribution": "Fotoğraf: Mesutdemirrci (CC BY-SA 4.0)",
  "sourceUrl": "https://commons.wikimedia.org/wiki/File:..."
}
```

### `data/bayraklar.json`
```json
{
  "countryCode": "tr",
  "countryName": "Türkiye",
  "capital": "Ankara",
  "continent": "Avrupa / Asya",
  "flagPath": "bayrak/turkiye_tr.svg"
}
```

## Lisans ve Atıf
* **Kod ve Scriptler:** MIT Lisansı.
* **Bayraklar (`bayrak/`):** [hampusborgos/country-flags](https://github.com/hampusborgos/country-flags) kaynaklıdır (**Public Domain**).
* **Türkiye Görselleri (`turkiye_gorselleri/`):** Wikimedia Commons üzerinden yalnızca ticari kullanıma ve türev çalışmalara izin veren (`CC0`, `Public Domain`, `CC BY`, `CC BY-SA`) lisanslarla seçilmiştir. `NC` (ticari olmayan) ve `ND` (türetilemez) lisanslı görseller filtrelenmiştir. `CC BY` / `CC BY-SA` görselleri kullanırken `attribution` ve `sourceUrl` bilgilerini göstermeniz yeterlidir (tam tablo için `CREDITS.md` dosyasına bakın).
