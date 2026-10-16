/**
 * Wix Velo — Yönetim Paneli (B2B) sayfa kodu
 * Wix'teki yeri: "Yönetim" sayfasının kodu (sayfa menüde gizli)
 *
 * UX: F-Pattern — üstte tam genişlik başlık + KPI kartları, altında soldan okunan liste.
 * En önemli bilgi (isim) satırın solunda.
 *
 * Mimari akış:
 *   Wix sayfası → backend/smartlead.web.js (Secrets Manager'daki anahtarla)
 *   → wix-fetch GET /api/leads, /api/sohbetler → Python (Flask) → SQLite → JSON → Repeater
 *
 * Sayfadaki bileşenler (Properties panelinden ID verilir):
 *   #btnSekmeLead, #btnSekmeSohbet   Sekme butonları: "Potansiyel müşteriler" / "Tüm sohbetler"
 *   #txtToplam, #txtBugun, #txtHafta KPI sayıları   (#txtHaftaEtiket: üçüncü kartın başlığı)
 *   #inputArama                      Arama kutusu
 *   #btnYenile                       Yenile butonu
 *   #txtDurum                        Durum / hata yazısı
 *   #repeaterLeads                   Repeater; her öğede:
 *       #txtIsim, #txtIletisim, #txtOnizleme, #txtTarih, #btnSohbet,
 *       #boxSohbet (Container, başta daraltılmış) → içinde #txtSohbet
 */
import { leadleriGetir, sohbetleriGetir, sunucuyuUyandir } from 'backend/smartlead.web';

let veriler = { leadler: [], sohbetler: [] };
let sekme = 'leadler';

// Opsiyonel bileşen sayfada yoksa kod durmasın
function yaz(id, metin) {
    try { $w(id).text = String(metin); } catch (e) { /* bileşen yok */ }
}

$w.onReady(async function () {
    $w('#repeaterLeads').data = [];
    $w('#repeaterLeads').onItemReady(satiriDoldur);

    $w('#btnYenile').onClick(() => yukle());
    $w('#inputArama').onInput(() => goster());
    try { $w('#btnSekmeLead').onClick(() => sekmeSec('leadler')); } catch (e) {}
    try { $w('#btnSekmeSohbet').onClick(() => sekmeSec('sohbetler')); } catch (e) {}

    await yukle();
});


// ---------------- Veri yükleme ----------------

async function yukle(deneme = 1) {
    yaz('#txtDurum', deneme === 1 ? '⏳ Veriler yükleniyor…' : `⏳ Sunucu uyanıyor, tekrar deneniyor (${deneme}/4)…`);
    try {
        const [leadler, sohbetler] = await Promise.all([leadleriGetir(), sohbetleriGetir()]);
        veriler = { leadler, sohbetler };
        yaz('#txtDurum', `✓ Güncellendi · ${new Date().toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })}`);
        kpiGuncelle();
        goster();
    } catch (hata) {
        const mesaj = String(hata && hata.message || hata);
        const kucuk = mesaj.toLowerCase();
        const yetkiHatasi = kucuk.includes('permission') || kucuk.includes('forbidden');
        const anahtarHatasi = mesaj.includes('anahtarı');
        if (!yetkiHatasi && !anahtarHatasi) {
            // Uyku, zaman aşımı veya geçici ağ hatası
            // Render uykudaysa ilk açılış ~1 dk sürer: uyandır, 15 sn bekle, en fazla 4 kez dene
            if (deneme < 4) {
                sunucuyuUyandir();
                setTimeout(() => yukle(deneme + 1), 15000);
                return;
            }
            yaz('#txtDurum', '⚠️ Sunucuya ulaşılamadı. Biraz sonra Yenile\'ye basın.');
        } else if (yetkiHatasi) {
            yaz('#txtDurum', '🔒 Bu sayfayı yalnızca site yöneticisi görebilir.');
        } else {
            yaz('#txtDurum', '⚠️ ' + mesaj);
        }
    }
}


// ---------------- Sekme, KPI, arama ----------------

function sekmeSec(yeni) {
    sekme = yeni;
    kpiGuncelle();
    goster();
}

const tarihNesnesi = (t) => new Date(String(t || '').replace(' ', 'T'));
const tarihYaz = (t) => {
    const d = tarihNesnesi(t);
    return isNaN(d) ? (t || '') : d.toLocaleString('tr-TR', { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' });
};

function kpiGuncelle() {
    const simdi = new Date();
    const bugun = simdi.toDateString();
    try {
        $w('#btnSekmeLead').label = `Potansiyel müşteriler (${veriler.leadler.length})`;
        $w('#btnSekmeSohbet').label = `Tüm sohbetler (${veriler.sohbetler.length})`;
    } catch (e) {}

    if (sekme === 'leadler') {
        const L = veriler.leadler;
        yaz('#txtToplam', L.length);
        yaz('#txtBugun', L.filter(l => tarihNesnesi(l.tarih).toDateString() === bugun).length);
        yaz('#txtHafta', L.filter(l => simdi - tarihNesnesi(l.tarih) < 7 * 864e5).length);
        yaz('#txtHaftaEtiket', 'Son 7 gün');
    } else {
        const S = veriler.sohbetler;
        const donusen = S.filter(s => s.lead_id).length;
        yaz('#txtToplam', S.length);
        yaz('#txtBugun', S.filter(s => tarihNesnesi(s.son_tarih).toDateString() === bugun).length);
        yaz('#txtHafta', S.length ? `${donusen} (%${Math.round(100 * donusen / S.length)})` : '0');
        yaz('#txtHaftaEtiket', 'Lead\'e dönüşen');
    }
}

/** Lead ve sohbet kayıtlarını Repeater'ın beklediği tek biçime çevirir. Repeater her öğede _id ister. */
function kayitlar() {
    const ham = veriler[sekme];
    return ham.map((r, i) => {
        if (sekme === 'leadler') {
            return { _id: 'lead-' + r.id, isim: r.isim, telefon: r.telefon, eposta: r.eposta,
                     etsy: r.etsy_magaza, dokum: r.mesaj, tarih: r.tarih, lead: true };
        }
        const isim = r.isim || r.z_isim;
        return { _id: 'sohbet-' + r.oturum, isim: isim || `Ziyaretçi #${ham.length - i}`, telefon: r.telefon,
                 eposta: r.eposta || r.z_eposta, dokum: r.dokum, tarih: r.son_tarih, lead: !!r.lead_id };
    });
}

function goster() {
    const q = ($w('#inputArama').value || '').toLocaleLowerCase('tr').trim();
    const liste = kayitlar().filter(k => !q ||
        [k.isim, k.telefon, k.eposta, k.etsy, k.dokum].join(' ').toLocaleLowerCase('tr').includes(q));
    $w('#repeaterLeads').data = liste;
    if (!liste.length) yaz('#txtDurum', q ? 'Aramaya uyan kayıt yok.' : 'Henüz kayıt yok.');
}


// ---------------- Repeater satırı ----------------

/** "Ziyaretçi: ..." / "Asistan: ..." satırlarını mesajlara ayırır; öneksiz satır öncekinin devamıdır. */
function sohbetiAyristir(metin) {
    const mesajlar = [];
    for (const satir of String(metin || '').split('\n')) {
        const m = satir.match(/^(Ziyaretçi|Asistan):\s?(.*)$/);
        if (m) mesajlar.push({ kim: m[1], metin: m[2] });
        else if (mesajlar.length) mesajlar[mesajlar.length - 1].metin += '\n' + satir;
        else if (satir.trim()) mesajlar.push({ kim: 'Ziyaretçi', metin: satir.trim() });
    }
    return mesajlar;
}

// Kullanıcı metni HTML olarak basılmadan önce kaçırılır (XSS'e karşı)
const kacir = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');

function sohbetHtml(mesajlar) {
    if (!mesajlar.length) return '<p style="color:#4A5468">Bu kayıtta sohbet yok.</p>';
    return mesajlar.map(m => {
        const renk = m.kim === 'Asistan' ? '#0F1B33' : '#FF6B4A';
        return `<p style="margin-bottom:8px"><span style="color:${renk};font-weight:bold">${m.kim}</span>` +
               `<span style="color:#4A5468">: ${kacir(m.metin)}</span></p>`;
    }).join('');
}

function satiriDoldur($item, k) {
    const mesajlar = sohbetiAyristir(k.dokum);
    const iletisim = [k.telefon, k.eposta, k.etsy ? '🛍 ' + k.etsy : ''].filter(Boolean).join('  ·  ');
    const sonZiyaretci = [...mesajlar].reverse().find(m => m.kim === 'Ziyaretçi');

    $item('#txtIsim').text = k.isim + (sekme === 'sohbetler' && k.lead ? '  •  Lead' : '');
    $item('#txtIletisim').text = iletisim || 'İletişim bilgisi bırakmadı';
    $item('#txtOnizleme').text = sonZiyaretci ? `“${sonZiyaretci.metin.slice(0, 120)}”` : 'Sohbet kaydı yok';
    $item('#txtTarih').text = `${tarihYaz(k.tarih)}  ·  ${mesajlar.length} mesaj`;

    $item('#txtSohbet').html = sohbetHtml(mesajlar);
    $item('#boxSohbet').collapse();
    $item('#btnSohbet').label = 'Sohbeti göster ▾';
    $item('#btnSohbet').onClick(() => {
        const kutu = $item('#boxSohbet');
        if (kutu.collapsed) { kutu.expand(); $item('#btnSohbet').label = 'Gizle ▴'; }
        else { kutu.collapse(); $item('#btnSohbet').label = 'Sohbeti göster ▾'; }
    });
}
