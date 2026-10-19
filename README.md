# yakup-gunduz.com kişisel site

Yakup Gündüz'ün Türkçe/İngilizce kişisel sitesi. Statik sayfalar Python (yalnız standart kütüphane) ile üretilir ve Vercel üzerinden yayınlanır.

## Dosyalar

- `site.html`: tek kaynak şablon. Üst kısım `<!-- BODY -->` işaretine kadar head içeriği, sonrası gövde.
- `build.py`: Türkçe ve İngilizce statik sayfaları `dist/` altında üretir; canonical, hreflang, yapılandırılmış veri, sitemap ve llms.txt burada oluşturulur.
- `src/content.json`, `src/projects.json`: biyografi ve proje içerikleri.
- `src/app.js`: sayfalara gömülen istemci betiği.
- `src/robots.txt`, `src/llms.txt`, `src/indexnow.key`: `dist/` için kaynak dosyalar.
- `assets/`: görseller, logolar, fontlar, favicon'lar.
- `vercel.json`: derleme komutu, yönlendirmeler ve güvenlik başlıkları.
- `tests/test_site.py`: her sayfada başlık, açıklama, canonical, hreflang, OG, JSON-LD ve sitemap kontrolü.

## Yerel önizleme

```bash
python3 -m unittest discover -s tests -v
python3 build.py
python3 -m http.server 4175 --directory dist
```

## Yayına alma (Vercel)

1. Depoyu GitHub'a gönderin.
2. Vercel'de **Add New → Project** ile depoyu içe aktarın. Ayarlar `vercel.json`'dan okunur (Framework: *Other*, Build: `python3 build.py`, Output: `dist`).
3. Bundan sonra `main` dalına yapılan her push otomatik olarak yayına alınır; diğer dallar önizleme adresi alır.

`dist/` depoya eklenmez, her dağıtımda Vercel tarafından yeniden üretilir.

İletişim formu bir sunucuya gönderim yapmaz, ziyaretçinin e-posta uygulamasında hazır mesaj açar.
