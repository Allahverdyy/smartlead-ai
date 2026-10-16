/**
 * Wix Velo — Backend Web Module (sunucu tarafı)
 * Wix'teki yeri: Code → Backend → smartlead.web.js
 *
 * Neden backend?
 *   ADMIN_KEY tarayıcıya hiç inmez. Anahtar Wix Secrets Manager'da durur ("SMARTLEAD_ADMIN_KEY"),
 *   istek Wix sunucusundan Render'a gider. Permissions.Admin sayesinde bu fonksiyonları
 *   yalnızca site yöneticisi çağırabilir; ziyaretçi sayfayı bulsa bile veri alamaz.
 */
import { Permissions, webMethod } from 'wix-web-module';
import { fetch } from 'wix-fetch';
import { getSecret } from 'wix-secrets-backend';

const API_ADRESI = 'https://smartlead-ai-dse5.onrender.com';

async function getir(yol) {
    const anahtar = await getSecret('SMARTLEAD_ADMIN_KEY');
    let yanit;
    try {
        yanit = await fetch(API_ADRESI + yol, { method: 'GET', headers: { 'X-Admin-Key': anahtar } });
    } catch (e) {
        // Render ücretsiz planda 15 dk boşta kalınca uyur; ilk istek zaman aşımına düşebilir
        throw new Error('UYANIYOR');
    }
    if (yanit.status === 401) throw new Error('Yönetici anahtarı hatalı (Secrets Manager ile Render aynı olmalı).');
    if (!yanit.ok) throw new Error('UYANIYOR');
    const veri = await yanit.json();
    if (!veri.basari) throw new Error(veri.hata || 'Veri alınamadı.');
    return veri;
}

/** GET /api/leads → potansiyel müşteriler (en yeni üstte) */
export const leadleriGetir = webMethod(Permissions.Admin, async () => {
    const veri = await getir('/api/leads');
    return veri.leadler;
});

/** GET /api/sohbetler → form doldurulmasa da kaydedilen tüm sohbetler */
export const sohbetleriGetir = webMethod(Permissions.Admin, async () => {
    const veri = await getir('/api/sohbetler');
    return veri.sohbetler;
});

/** Sunucuyu uyandırmak için hafif istek (anahtar gerekmez) */
export const sunucuyuUyandir = webMethod(Permissions.Admin, async () => {
    try {
        const yanit = await fetch(API_ADRESI + '/health', { method: 'GET' });
        return yanit.ok;
    } catch (e) {
        return false;
    }
});
