# 🧺 उधारी खाते – Grocery Shop Credit Manager (मराठी PWA)

Flask + PostgreSQL (Supabase) वर चालणारे, पूर्णपणे मराठी, mobile-first अ‍ॅप. फोनवर "Add to Home Screen" करून अ‍ॅपसारखे वापरता येते.

## काय काय आहे
- 🔐 अ‍ॅडमिन लॉगिन + पासवर्ड बदला (लॉगिन प्रयत्नांवर मर्यादा, CSRF संरक्षण)
- 👥 ग्राहक **जोडा / बदला / काढा**, नाव किंवा मोबाईलने शोध, "बाकी असलेले" फिल्टर
- 📞 मोबाईल नंबर **आवश्यक, फक्त १० अंकी आणि प्रत्येक ग्राहकाचा वेगळा** (डुप्लिकेट आल्यास कोणत्या ग्राहकाकडे आहे ते सांगतो; DB unique index ने देखील अडवले जाते)
- 🎙️ **बोलून नाव टाका** (मराठी voice input) – फक्त ग्राहकाच्या नावासाठी. Android Chrome / Edge वर चालते, इंटरनेट + माइक परवानगी लागते. iPhone Safari वर ही सुविधा विश्वासार्ह नसते – तेथे नाव टाईप करावे लागते.
- 🧾 **उधार दिले** आणि **जमा झाले** नोंदी – जोडा / बदला / काढा
- 📒 रुळ्यांच्या वहीसारखी खातेवही (प्रत्येक ओळीनंतर चालू बाकी), प्रिंट सुविधा
- 💬 WhatsApp वर पैसे मागण्याची तयार मराठी आठवण
- ⬇️ बाकी यादी Excel (CSV) मध्ये डाउनलोड
- 📲 PWA: होम स्क्रीनवर इन्स्टॉल, वेगवान लोडिंग, इंटरनेट नसल्यास "इंटरनेट नाही" पान
- रक्कम paise मध्ये साठवली जाते (दशांश चुका नाहीत), भारतीय पद्धतीने ₹1,23,456 दिसते

## ⚠️ महत्त्वाचे: "SQLite on Supabase" बद्दल
Supabase मध्ये **PostgreSQL** असते, SQLite नाही. Render च्या free सर्व्हरवरील फाइल्स प्रत्येक deploy/restart ला पुसल्या जातात, म्हणून SQLite फाइल तेथे वापरली तर ग्राहकांचा डेटा जाईल.
म्हणून हे अ‍ॅप `DATABASE_URL` असेल तर **Supabase Postgres** वापरते, आणि नसेल तर फक्त लोकल टेस्टिंगसाठी SQLite वापरते. कोड तोच, काही बदलायची गरज नाही.

## लोकल चालवा
```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py                                         # http://localhost:5000
```
लोकलला लॉगिन: `admin` / `admin123` (लगेच पासवर्ड बदला). PWA/service worker `localhost` वर चालतो; खऱ्या फोनवर HTTPS (Render) लागते.

## Deploy – पायरी १: Supabase डेटाबेस
1. [supabase.com](https://supabase.com) → New project (Region: **Mumbai / ap-south-1** निवडा).
2. Database password नीट सेव्ह करा. त्यात `@ : / # ?` सारखी चिन्हे असतील तर URL मध्ये **%-encode** करावी लागतील (सोपे: फक्त अक्षरे व अंकांचा पासवर्ड ठेवा).
3. प्रोजेक्टमध्ये वर **Connect** दाबा → **Session pooler** ची connection string कॉपी करा. ती अशी दिसते:
   `postgresql://postgres.<project-ref>:<PASSWORD>@aws-0-<region>.pooler.supabase.com:5432/postgres`
4. **Direct connection (db.xxx.supabase.co) वापरू नका** – ती IPv6 वर असते, Render free IPv4 वर चालते आणि कनेक्ट होत नाही. Pooler वापरा.
5. टेबल्स मॅन्युअली बनवायची गरज नाही – अ‍ॅप पहिल्या स्टार्टला स्वतः बनवते.

## Deploy – पायरी २: Render
1. हा फोल्डर GitHub वर push करा.
2. Render → **New → Blueprint** → तुमची repo निवडा (`render.yaml` आपोआप वाचला जातो).
   (किंवा New → Web Service: Build `pip install -r requirements.txt`, Start `gunicorn app:app --workers 1 --threads 4 --timeout 60 --bind 0.0.0.0:$PORT`)
3. Environment variables:

| Key | Value |
|---|---|
| `DATABASE_URL` | Supabase Session pooler string (पायरी १.३) |
| `ADMIN_USERNAME` | उदा. `admin` |
| `ADMIN_PASSWORD` | पहिला पासवर्ड (किमान ६ अक्षरे) |
| `SHOP_NAME` | उदा. `श्री गणेश किराणा स्टोअर्स` |
| `SECRET_KEY` | Blueprint आपोआप बनवतो; manual असल्यास लांब random string |

4. Deploy झाल्यावर `https://<नाव>.onrender.com` उघडा → लॉगिन → **पासवर्ड** मेनूमधून पासवर्ड बदला.
   `ADMIN_PASSWORD` फक्त पहिल्यांदा (admin तयार होताना) वापरला जातो; नंतर पासवर्ड DB मध्ये असतो.
5. आरोग्य तपासणी: `/healthz` → `{"status":"ok"}` म्हणजे DB कनेक्ट आहे.

## फोनवर इन्स्टॉल (ग्राहकाला सांगा)
- **Android Chrome:** पानाच्या तळाशी "📲 अ‍ॅप इन्स्टॉल करा" बटण, किंवा ⋮ मेनू → *Install app / Add to Home screen*.
- **iPhone Safari:** Share → *Add to Home Screen*.

## फाइल रचना
```
app.py                 सर्व routes, models, पहिला admin
templates/             मराठी पाने (base, login, dashboard, customers, ...)
static/css/style.css   किराणा थीम (चांदवा, वही-कागद, हिरवा/हळदी)
static/js/app.js       confirm, install बटण, चिप्स
static/js/sw.js        service worker (/sw.js वरून serve होतो)
static/icons/          PWA आयकॉन्स
render.yaml            Render Blueprint
requirements.txt
```

## सानुकूल बदल
- दुकानाचे नाव: `SHOP_NAME` env variable.
- रंग: `static/css/style.css` च्या सुरुवातीचे `:root` variables.
- CSS/JS बदलल्यावर फोनवर लगेच दिसण्यासाठी `app.py` मधील `ASSET_VERSION` वाढवा.
- आयकॉन बदलायचे असल्यास `static/icons/` मधील PNG बदला (192, 512, maskable-512, apple-touch-icon 180, favicon 32).

## मर्यादा (तुम्ही क्लायंटला सांगावे)
- नोंदी जतन करायला इंटरनेट लागते (ऑफलाइन फक्त अ‍ॅपचे शेल उघडते). ऑफलाइन-लिखाण हवे असल्यास वेगळे काम (IndexedDB + sync) लागेल.
- Render free सर्व्हर काही वेळ वापर नसल्यास झोपतो – पहिले पान उघडायला ~३० सेकंद लागू शकतात. Supabase free प्रोजेक्ट बराच काळ वापर नसेल तर pause होऊ शकतो. प्रत्यक्ष दुकानात वापरासाठी paid Render plan आणि Supabase backups विचारात घ्या.
- एकच admin (दुकानदार) आहे; वेगवेगळे वापरकर्ते/रोल्स नाहीत.
- लॉगिन प्रयत्नांची मर्यादा सर्व्हर-मेमरीत आहे (restart ला रीसेट होते).
