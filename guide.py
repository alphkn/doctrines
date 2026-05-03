import pyttsx3

# Ses motorunu başlat
engine = pyttsx3.init()

# Türkçe ve ciddi bir erkek sesi bulmaya çalış
for voice in engine.getProperty('voices'):
    if 'tr' in voice.languages[0].decode() and ('male' in voice.name.lower() or 'erkek' in voice.name.lower()):
        engine.setProperty('voice', voice.id)
        break

# Ses hızı ve tonlaması
engine.setProperty('rate', 145)  # Konuşma hızı
engine.setProperty('volume', 1.0)  # Ses yüksekliği

# Metin
metin = """
Gün başladı. Koştun. Terledin. Şimdi zihin sırada. Dik dur.

Omuzlarını geriye al. Burnundan derin bir nefes çek.
Bu senin bedenin. Bu senin zihnin. Kontrol sende.

Bugün seni zorlayabilecek ne var?
Baskı olacak. Karar alman gerekecek. Sınırını test edecekler.

Zorlandığında nasıl tepki vereceksin?
Sert olacağım. Sağlam duracağım. Kendimi ezdirmeyeceğim.

Günün sonunda nasıl bir adam olarak günü bitirmek istiyorsun?
Dik duran, sakin kalan, kontrolü bırakmayan bir adam. Söze gerek bırakmayan biri.

Nefes al. 4 saniye. Tut. 4 saniye. Ver. 6 saniye.
Son nefesin sonunda sadece bunu söyle:
Bugün hiçbir şey beni benden alamaz.

Şimdi suyunu iç. Küçük bir hamle. Netliği başlatır.
Bugün ezmen gerekirse ez, susman gerekirse sus.
Ama kendine karşı ne ezil, ne sus.
İnsanları sesinle değil, zihninle yöneteceksin.
Sert değil savruk, yumuşak değil zayıf olmayacaksın.

Zihin hizada. Beden hazır.
Gün seni şekillendirmeyecek. Sen günü yöneteceksin.
Karar sende. Kontrol sende.
Sen günün üzerindesin.
"""

# MP3 olarak kaydet
engine.save_to_file(metin, 'sabah_komuta_al.mp3')
engine.runAndWait()

print("✔️ Ses kaydedildi: sabah_komuta_al.mp3")
