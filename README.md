# 📅 Vaktplan OCR - Kalendergenerator

Konverter bilder av vaktplaner til iCalendar-filer (`.ics`) ved hjelp av OCR-teknologi!

Dette programmet leser norske vaktplaner fra bilder og genererer kalenderfiler som kan importeres i Outlook, Google Calendar, Apple Calendar, og andre kalenderapplikasjoner.

---

## 🚀 Kom i gang

### 1. Forutsetninger

- **Python 3.8+** (anbefalt: 3.11 eller 3.12)
- **Tesseract OCR** med norsk språkpakke

#### Installer Tesseract OCR:
- **Windows**: [Last ned installer](https://github.com/UB-Mannheim/tesseract/wiki) (velg "Norwegian" under installasjon)
- **Linux**: `sudo apt-get install tesseract-ocr tesseract-ocr-nor`
- **Mac**: `brew install tesseract tesseract-lang`

### 2. Installer Python-pakker

```powershell
py -m pip install -r requirements.txt
```

### 3. Konfigurer programmet

Kopier `.env.example` til `.env` og tilpass om nødvendig:

```powershell
Copy-Item .env.example .env
```

Standard-innstillinger:
- Tesseract-sti: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- Input-mappe: `Bilder/`
- Output-mappe: `KalenderFiler/`
- Vaktvarighet: 8 timer

### 4. Legg til vaktplan-bilder

Plasser bilder av vaktplanene i `Bilder/`-mappen. Støttede formater:
- `.jpg` / `.jpeg`
- `.png`

### 5. Kjør programmet

```powershell
py vaktplan_konverter.py
```

---

## 📸 Tips for beste OCR-resultater

✅ **Gjør:**
- Bruk klare, velbelyste bilder
- Ta bilder rett forfra (unngå skrå vinkler)
- Sørg for at teksten er skarp og lesbar
- Ta bilder med høy oppløsning

❌ **Unngå:**
- Refleksjoner og skygger
- Uskarpe eller kornete bilder
- Skråstilt tekst eller perspektivforvrengning
- For lav oppløsning

---

## 📂 Filstruktur

```
OCR - Kalender/
├── vaktplan_konverter.py    # Hovedprogram
├── requirements.txt          # Python-avhengigheter
├── .env                      # Konfigurasjon (opprett fra .env.example)
├── .env.example             # Mal for konfigurasjon
├── ocr-kalender.md          # Detaljert prosjektdokumentasjon
├── Bilder/                   # Legg vaktplan-bilder her (INPUT)
└── KalenderFiler/           # Genererte .ics filer (OUTPUT)
    └── alle_vakter.ics      # Kalender med alle vakter
```

---

## 🛠️ Støttede formater

### Vaktplan-format
Programmet forventer norske vaktplaner med følgende format:

```
[måned] [år]
[ukedag] [HH:MM] - [HH:MM]
[dag i måneden]
```

**Eksempel:**
```
november 2025
mandag 07:00 - 15:00
18
tirsdag 14:00 - 22:00
19
```

### Støttede måneder
Alle 12 måneder: januar, februar, mars, april, mai, juni, juli, august, september, oktober, november, desember

### Vakttyper
Programmet kategoriserer vakter automatisk:
- **Tidlig**: 06:00 - 11:59
- **Mellom**: 11:00 - 15:59
- **Sent**: 16:00 - 05:59

---

## 🎯 Output

### iCalendar-format (.ics)
Genererte kalenderfiler er i standard iCalendar-format og kan importeres i:
- Microsoft Outlook
- Google Calendar
- Apple Calendar
- Mozilla Thunderbird
- De fleste andre kalenderapplikasjoner

### Importer kalenderfilen
1. Åpne `KalenderFiler/alle_vakter.ics`
2. Dobbeltklikk filen, eller importer manuelt i kalenderappen din

---

## 🔧 Tilpasning

Rediger `.env` for å tilpasse:

```env
# Endre navn på vaktinnehaver
SHIFT_OWNER_NAME=Ditt Navn

# Endre standard vaktlengde (timer)
DEFAULT_SHIFT_DURATION_HOURS=7.5

# Endre Tesseract-sti hvis installert annet sted
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```

---

## 📄 Dokumentasjon

For detaljert teknisk dokumentasjon, arkitektur og business logic, se: **[ocr-kalender.md](ocr-kalender.md)**

---

## 🐛 Feilsøking

### "Tesseract OCR ikke funnet"
- Sjekk at Tesseract er installert
- Verifiser stien i `.env`-filen

### "Ingen vakter funnet"
- Sjekk at bildene er klare nok
- Verifiser at vaktplanen følger forventet format
- Sjekk at norsk språkpakke er installert for Tesseract

### Python-feil: "No module named..."
```powershell
py -m pip install -r requirements.txt
```

---

## 💡 Fremtidige forbedringer

- [ ] Web-grensesnitt for opplasting
- [ ] Support for flere vaktplan-formater
- [ ] Automatisk lesing av slutt-tid (istedenfor fast varighet)
- [ ] Bulk-import fra flere kilder
- [ ] REST API for integrasjon

---

**Utviklet som en produktiserbar løsning for digitalisering av vaktplaner** 🚀 