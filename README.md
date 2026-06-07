# Rotaka — Çevrimiçi Çok Oyunculu Kurulum Rehberi

Bu klasör, iki oyuncunun aynı bağlantı üzerinden gerçek zamanlı olarak Rotaka oynayabileceği **Flask-SocketIO sunucusunu** içerir.

---

## Nasıl Çalışır?

```
Oyuncu A (Beyaz)           Sunucu (Render.com)          Oyuncu B (Siyah)
     │                           │                              │
     │──── Oda Oluştur ─────────►│                              │
     │◄─── Oda Kodu: "ABC123" ───│                              │
     │                           │                              │
     │                           │◄──── Odaya Katıl (ABC123) ───│
     │◄─── Oyun Başladı ─────────│────► Oyun Başladı ───────────│
     │                           │                              │
     │──── Hamle (e9→e8) ───────►│──────────────────────────────►│
     │◄────────────────── Rakip hamlesi (e8→e7) ────────────────│
```

Sunucu hiçbir oyun mantığı çalıştırmaz — yalnızca iki oyuncu arasında mesajları iletir. Oyun mantığı tamamen tarayıcıda (JavaScript) çalışır; her iki istemci aynı kodu çalıştırır ve pozisyon senkronize kalır.

---

## Klasör Yapısı

```
server/
├── rotaka_server.py   ← Flask-SocketIO sunucu
├── rotaka.html        ← Çok oyunculu istemci (oyun + lobi)
├── icons/             ← Taş görselleri buraya kopyalanmalı!
├── requirements.txt   ← Python bağımlılıkları
├── render.yaml        ← Render.com otomatik dağıtım yapılandırması
└── README.md          ← Bu dosya
```

---

## Kurulum — Yerel (Test Amaçlı)

### 1. Python Kurulu Olduğundan Emin Ol

Python 3.10 veya üzeri gereklidir.

```bash
python --version
```

### 2. Bağımlılıkları Yükle

```bash
cd server
pip install -r requirements.txt
```

### 3. Icons Klasörünü Kopyala

Taş görsellerini kopyala:

```bash
# Windows
xcopy ..\icons icons\ /E /I

# macOS / Linux
cp -r ../icons ./icons
```

### 4. Sunucuyu Başlat

```bash
python rotaka_server.py
```

Çıktı şuna benzemelidir:

```
 * Running on http://0.0.0.0:5000
```

### 5. Tarayıcıda Aç

İki ayrı tarayıcı sekmesi aç:

- `http://localhost:5000` — Oyuncu A (Beyaz)
- `http://localhost:5000` — Oyuncu B (Siyah)

Oyuncu A **"Oda Oluştur"** düğmesine tıklar. Ekranda bir oda kodu belirir (örn. `ABC123`). Bu kodu Oyuncu B'ye gönder. Oyuncu B kodu girerek **"Katıl"**'a tıklar. Oyun başlar.

---

## Dağıtım — Render.com (Ücretsiz, Canlı Bağlantı)

Bu yöntem, **herhangi bir bilgisayardan erişilebilen** gerçek bir bağlantı oluşturur.

### Adım 1 — GitHub'a Yükle

```bash
git init
git add .
git commit -m "Rotaka multiplayer server"
git remote add origin https://github.com/KULLANICI_ADI/rotaka-server.git
git push -u origin main
```

> Not: Reponun tüm içeriğinin `server/` klasörünün içinden değil, doğrudan kökünden `rotaka_server.py` dosyası görünecek şekilde olması gerekir. Yani `server/` klasörünü ayrı bir repo olarak push et (içindeyken `git init` yap).

### Adım 2 — Render.com'a Git

1. [render.com](https://render.com) adresinde hesap oluştur (ücretsiz)
2. **"New +"** → **"Web Service"** seç
3. GitHub reposunu bağla
4. Aşağıdaki ayarları gir (ya da `render.yaml` otomatik doldurur):

| Alan | Değer |
|------|-------|
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT rotaka_server:app` |
| Plan | Free |

5. **"Create Web Service"** tıkla — Render otomatik olarak derleme ve başlatma yapacak.

### Adım 3 — Bağlantıyı Paylaş

Render size şuna benzer bir URL verir:

```
https://rotaka-server.onrender.com
```

Bu URL'yi arkadaşınla paylaş. İkiniz de bu adrese girip lobi ekranından oda oluşturabilir/katılabilirsiniz.

---

## Önemli Notlar

### Free Tier Uyku Modu

Render.com ücretsiz planında sunucu **15 dakika kullanılmazsa uyku moduna** girer. İlk istek geldiğinde ~30 saniye başlangıç süresi olabilir. Çözüm: bir request yapıp ~1 dakika bekle.

### WebSocket Desteği

Render.com ücretsiz planı WebSocket'i destekler. Herhangi bir ek yapılandırma gerekmez.

### Sunucu Güvenilirliği

Bu sunucu relay-only (yalnızca iletim) çalışır. Sunucu çökerse veya yeniden başlarsa mevcut oyun kaybolur. Bu, yerel ve küçük ölçekli oyunlar için yeterlidir.

---

## Oyun Akışı

```
LOBI
  └─ Oda Oluştur (Beyaz) → Oda kodu al → Paylaş
  └─ Oda Katıl (Siyah)  → Kod gir → Katıl

OYUN BAŞLADI
  ├─ Beyaz hamle yapar
  ├─ Pie Rule (Siyah karar verir: Kal / Swap)
  │   └─ Swap → Siyah Beyaz olur, Rebound Boost alır
  └─ Normal oyun akışı…
      ├─ 3-Tekrar → Beraberlik
      ├─ 50 Eylemsiz Hamle → Beraberlik
      ├─ 5 Ev İşgali → Kazanç
      └─ Tüm Taşlar İmha → Kazanç
```

---

## Sorun Giderme

**"Oda bulunamadı" hatası:** Oda kodunu büyük harfle girdiğinden emin ol (otomatik dönüştürülür).

**Bağlantı kurulamıyor (yerel):** `requirements.txt` kurulu mu? `pip install -r requirements.txt` tekrar çalıştır.

**Render'da "Application failed to start":** Start command'in tam olarak şu şekilde olduğunu kontrol et:
```
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT rotaka_server:app
```

**Taşlar görünmüyor:** `icons/` klasörünün `server/` içinde olduğundan emin ol.

**Oyun senkronize değil (iki tarafta farklı pozisyon):** Sayfa yenilemek (`F5`) gerekebilir. Her iki taraf da aynı deterministik JavaScript kodunu çalıştırır; teorik olarak her zaman senkronize olmalı.
