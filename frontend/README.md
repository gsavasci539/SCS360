# Okul360 Frontend

Material Dashboard veya hazır admin tema kullanmadan geliştirilmiş React + TypeScript yönetim panelidir. FastAPI backend'inin `/api` sözleşmesine bağlıdır.

## Yerel geliştirme

```bash
cp .env.example .env
npm install
npm run dev
```

Varsayılan arayüz `http://localhost:5173`, backend ise `http://localhost:5006/api` adresindedir.

## Komutlar

- `npm run dev`: geliştirme sunucusu
- `npm run build`: TypeScript kontrolü ve production build
- `npm run lint`: kod kalitesi kontrolü
- `npm run test`: Vitest testleri

## Demo hesabı

- E-posta: `admin@demo.com`
- Şifre: `Admin123*`

Roller ve izinler backend'den alınır; kullanıcıya kapalı modüller menüde gösterilmez.
