# OCR Kalender - Vaktplan Konverter

**Prosjekttype:** Produktiserbar løsning for konvertering av vaktplan-bilder til kalenderfiler  
**Målgruppe:** Bedrifter og individer som ønsker å digitalisere papirbaserte vaktplaner  
**Teknologi:** Python, OCR (Tesseract), iCalendar

---

## 📋 Prosjektstatus

### ✅ Implementert
- OCR-lesing av vaktplan-bilder (JPEG, PNG)
- Bildeforbedring for bedre OCR-nøyaktighet (gråskala, kontrast)
- Ekstraksjon av dato og klokkeslett fra norsk tekst
- Automatisk deteksjon av vakttype (tidlig/mellom/sent) basert på klokkeslett
- Generering av iCalendar (.ics) filer
- Samling av alle vakter i én kalenderfil

### 🔄 Pågående
- Ingen aktive utviklingsoppgaver

### ❌ Kjente problemer og begrensninger
- **Python 3.13 advarsel**: "Could not find platform independent libraries" vises, men programmet fungerer likevel
- **Fast varighet**: Alle vakter antas å vare i 8 timer (konfigurerbart via .env) - ideelt sett burde slutt-tid leses fra bildet
- **Encoding**: Windows PowerShell har problemer med emojis (løst ved å bruke tekstbaserte tags som [OK], [FEIL], etc.)
- **OCR-nøyaktighet**: Avhengig av bildekvalitet - dårlige bilder kan gi feil resultater

### 📝 Planlagte forbedringer
- Automatisk lesing av faktisk slutt-tid fra vaktplan (istedenfor fast varighet)
- Støtte for flere vaktplan-formater og layouts
- Web-grensesnitt for opplasting og konvertering
- REST API for integrasjon med andre systemer
- Batch-prosessering av flere måneder samtidig
- Forbedret OCR med maskinlæring for bedre nøyaktighet

---

## 🏗️ Arkitektur

### Filstruktur
```
OCR - Kalender/
├── vaktplan_konverter.py    # Hovedprogram
├── requirements.txt          # Python-avhengigheter
├── README.md                 # Brukerinstruksjoner
├── ocr-kalender.md          # Prosjektdokumentasjon (denne filen)
├── Bilder/                   # Input: Vaktplan-bilder
│   └── signal-2025-11-13-*.jpeg
└── KalenderFiler/           # Output: Genererte .ics filer
    └── alle_vakter.ics
```

### Avhengigheter
- **Pillow 10.2.0**: Bildebehandling og forbedring
- **pytesseract 0.3.10**: Python-wrapper for Tesseract OCR
- **icalendar 5.0.11**: Generering av iCalendar-filer
- **Tesseract OCR** (ekstern): Må installeres separat

---

## 🔧 Business Logic

### Hovedprosess (hovedfunksjon)
1. Skann `Bilder/`-mappen for JPEG/PNG-filer
2. For hvert bilde:
   - Forbedre bildekvalitet
   - Utfør OCR med norsk språkmodell
   - Ekstraher vaktinformasjon
   - Opprett kalenderhendelse
3. Lagre alle hendelser i én `.ics` fil

### Bildeforbedring (forbedre_bilde)
- Konvertering til gråskala
- Øke kontrast (threshold ved 128)
- Gjør tekst mer lesbar for OCR

### Dato/tid-ekstraksjon (ekstraher_dato_og_tid)
**Input**: OCR-tekst  
**Output**: Liste av (dato, klokkeslett)-tupler  

**Mønster for måned og år:**
```regex
(mai|juni|juli|august|september|oktober|november|desember) (\d{4})
```

**Mønster for vaktlinjer:**
```regex
(?:mandag|tirsdag|onsdag|torsdag|fredag|lørdag|søndag)\s+(\d{1,2}):(\d{2})\s*-\s*\d{1,2}:\d{2}\s*\n\s*(\d{1,2})
```

### Vakttype-klassifisering (bestem_vakttype)
- **Tidlig**: 06:00 - 11:59
- **Mellom**: 11:00 - 15:59  
- **Sent**: 16:00 - 05:59

### Kalenderhendelse (lag_kalenderhendelse)
- **Summary**: "Cathrine jobber {vakttype}"  
- **Start**: Ekstraherert dato + klokkeslett  
- **Slutt**: Start + 8 timer (hardkodet)  
- **Format**: iCalendar standard

---

## ⚡ Kjøring

### Krav
1. Python 3.8+ installert
2. Tesseract OCR installert på `C:\Program Files\Tesseract-OCR\tesseract.exe`
3. Python-pakker installert: `py -m pip install -r requirements.txt`

### Kommando
```powershell
py vaktplan_konverter.py
```

### Forventet output
```
Behandler bilde: signal-2025-11-13-214513.jpeg
OCR resultat: [tekst fra bilde]
Funnet vakt: 13.11.2025 07:00
La til vakt: 13.11.2025 07:00 (tidlig)
...
Genererte kalenderfil med 12 vakter: alle_vakter.ics
```

---

## 🔐 Sikkerhet

### Nåværende tilstand
- Ingen autentisering (lokalt script)
- Ingen sensitive data behandles utover vaktplan-info
- Ingen nettverkskommunikasjon
- Lokal filbehandling

### Fremtidige sikkerhetstiltak (ved produktisering)
- Input-validering for bildestørrelser
- Sanitering av OCR-output før parsing
- Rate limiting hvis det blir web-API
- Kryptering av lagrede kalenderfiler
- Brukerautentisering og autorisasjon
- HTTPS for alle API-kall

---

## 📊 Dataformat

### Input (OCR-tekst eksempel)
```
mai 2025
mandag 07:00 - 15:00
5
tirsdag 11:00 - 19:00
6
```

### Output (iCalendar)
```ics
BEGIN:VCALENDAR
BEGIN:VEVENT
SUMMARY:Cathrine jobber tidlig
DTSTART:20250505T070000
DTEND:20250505T150000
END:VEVENT
END:VCALENDAR
```

---

**Sist oppdatert:** 2025-11-17  
**Versjon:** 1.1
**Status:** ✅ Fullt funksjonell med .env-konfigurasjon, validering, og full månedsstøtte

