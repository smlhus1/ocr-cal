import os
import sys
from PIL import Image
import pytesseract
from datetime import datetime, timedelta
from icalendar import Calendar, Event
import re
from dotenv import load_dotenv
from pathlib import Path

# Last inn miljøvariabler fra .env fil
load_dotenv()

# Konfigurer pytesseract med sti fra .env eller standard
TESSERACT_PATH = os.getenv('TESSERACT_PATH', r'C:\Program Files\Tesseract-OCR\tesseract.exe')
OCR_LANGUAGE = os.getenv('OCR_LANGUAGE', 'nor')
INPUT_FOLDER = os.getenv('INPUT_FOLDER', 'Bilder')
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER', 'KalenderFiler')
SHIFT_DURATION = int(os.getenv('DEFAULT_SHIFT_DURATION_HOURS', '8'))
SHIFT_OWNER = os.getenv('SHIFT_OWNER_NAME', 'Cathrine')

# Valider at Tesseract er installert
if not Path(TESSERACT_PATH).exists():
    print(f"[FEIL] Tesseract OCR ikke funnet paa: {TESSERACT_PATH}")
    print("[INFO] Last ned og installer Tesseract fra:")
    print("   https://github.com/UB-Mannheim/tesseract/wiki")
    print("\n[TIP] Eller oppdater TESSERACT_PATH i .env filen")
    sys.exit(1)

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
print(f"[OK] Tesseract funnet: {TESSERACT_PATH}")

def forbedre_bilde(bilde_sti):
    """Forbedrer bildekvaliteten for bedre OCR-resultater."""
    bilde = Image.open(bilde_sti)
    # Konverter til gråskala
    bilde = bilde.convert('L')
    # Øk kontrasten
    bilde = bilde.point(lambda x: 0 if x < 128 else 255, '1')
    return bilde

def ekstraher_dato_og_tid(tekst):
    """Ekstraherer dato og klokkeslett fra OCR-tekst."""
    print("[OCR] Resultat:", tekst[:200], "..." if len(tekst) > 200 else "")  # Vis første 200 tegn
    
    # Finn måned og år (alle 12 måneder)
    måned_år_mønster = r'(januar|februar|mars|april|mai|juni|juli|august|september|oktober|november|desember) (\d{4})'
    måned_år = re.search(måned_år_mønster, tekst.lower())
    
    # Finn vaktlinjer med både start- og slutt-tid (forbedret mønster)
    # Håndterer nå også mellomrom i dagnummer (f.eks. "2 3" → 23)
    # Tillater tekst/whitespace mellom tid og dag (greedy men begrenset til 30 tegn)
    # VIKTIG: \d\s+\d må komme FØRST i alternativet, ellers matcher \d{1,2} bare første siffer!
    vakt_mønster = r'(?:mandag|tirsdag|onsdag|torsdag|fredag|l.rdag|.rdag|søndag|s.ndag)\s+(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*[^\d]{0,30}?(\d\s+\d|\d{1,2})'
    vakter = re.finditer(vakt_mønster, tekst.lower())
    
    resultater = []
    funnet_vakter = set()  # For å unngå duplikater
    
    if måned_år:
        måned_navn, år = måned_år.groups()
        måneder = {
            'januar': 1, 'februar': 2, 'mars': 3, 'april': 4,
            'mai': 5, 'juni': 6, 'juli': 7, 'august': 8,
            'september': 9, 'oktober': 10, 'november': 11, 'desember': 12
        }
        måned_nummer = måneder.get(måned_navn.lower())
        
        if måned_nummer:
            for vakt in vakter:
                start_time, start_min, slutt_time, slutt_min, dag = vakt.groups()
                
                # Debug: Vis rå-match
                print(f"[DEBUG] Match: {start_time}:{start_min}-{slutt_time}:{slutt_min}, dag='{dag}'")
                
                # Fjern mellomrom fra dag (f.eks. "2 3" → "23")
                dag = dag.replace(' ', '')
                
                # Valider at dagen er rimelig (1-31)
                try:
                    dag_int = int(dag)
                    if dag_int < 1 or dag_int > 31:
                        print(f"[DEBUG] Ugyldig dag funnet: {dag} - hopper over")
                        continue
                except ValueError:
                    print(f"[DEBUG] Kunne ikke parse dag: {dag} - hopper over")
                    continue
                
                # Lag en unik nøkkel for denne vakten
                dato = f"{dag.zfill(2)}.{str(måned_nummer).zfill(2)}.{år}"
                start_tid = f"{start_time.zfill(2)}:{start_min}"
                slutt_tid = f"{slutt_time.zfill(2)}:{slutt_min}"
                vakt_nøkkel = f"{dato}_{start_tid}_{slutt_tid}"
                
                # Sjekk om vi allerede har lagt til denne vakten
                if vakt_nøkkel in funnet_vakter:
                    print(f"[DEBUG] Duplikat hopper over: {dato} {start_tid}-{slutt_tid}")
                    continue
                
                funnet_vakter.add(vakt_nøkkel)
                print(f"[+] Funnet vakt: {dato} {start_tid}-{slutt_tid}")
                resultater.append((dato, start_tid, slutt_tid))
        else:
            print(f"[ADVARSEL] Ukjent maaned: {måned_navn}")
    else:
        print("[ADVARSEL] Ingen maaned/aar funnet i OCR-teksten")
    
    return resultater

def bestem_vakttype(start_klokkeslett, slutt_klokkeslett=None):
    """Bestemmer vakttype basert på start- og slutt-klokkeslett."""
    start_time = int(start_klokkeslett.split(':')[0])
    
    # Hvis vi har slutt-tid, sjekk om det er nattevakt (går over midnatt)
    if slutt_klokkeslett:
        slutt_time = int(slutt_klokkeslett.split(':')[0])
        # Nattevakt hvis den starter sent og slutter tidlig (går over midnatt)
        if start_time >= 20 or start_time < 6:
            if slutt_time <= 10:  # Slutter på morgenen
                return "natt"
    
    # Standard klassifisering basert på start-tid
    if 6 <= start_time < 12:
        return "tidlig"
    elif 12 <= start_time < 16:
        return "mellom"
    elif 16 <= start_time < 22:
        return "kveld"
    else:
        return "natt"  # 22:00-06:00

def lag_kalenderhendelse(kalender, dato, start_klokkeslett, slutt_klokkeslett, vakttype):
    """Legger til en kalenderhendelse i den eksisterende kalenderen."""
    try:
        # Sørg for at klokkeslettene har riktig format (HH:MM)
        if len(start_klokkeslett.split(':')[0]) == 1:
            start_klokkeslett = f"0{start_klokkeslett}"
        if len(slutt_klokkeslett.split(':')[0]) == 1:
            slutt_klokkeslett = f"0{slutt_klokkeslett}"
        
        # Konverter start dato og tid til datetime-objekt
        start_dato_tid = datetime.strptime(f"{dato} {start_klokkeslett}", "%d.%m.%Y %H:%M")
        
        # Parse slutt-tid
        slutt_time_obj = datetime.strptime(slutt_klokkeslett, "%H:%M")
        
        # Beregn slutt-dato/tid
        # Hvis slutt-time er mindre enn start-time, går vakten over midnatt
        if slutt_time_obj.hour < start_dato_tid.hour or (slutt_time_obj.hour == start_dato_tid.hour and slutt_time_obj.minute < start_dato_tid.minute):
            # Vakt går over midnatt - legg til 1 dag
            slutt_dato_tid = start_dato_tid + timedelta(days=1)
            slutt_dato_tid = slutt_dato_tid.replace(hour=slutt_time_obj.hour, minute=slutt_time_obj.minute)
        else:
            # Vanlig vakt samme dag
            slutt_dato_tid = start_dato_tid.replace(hour=slutt_time_obj.hour, minute=slutt_time_obj.minute)
        
        # Opprett hendelse
        hendelse = Event()
        hendelse.add('summary', f"{SHIFT_OWNER} jobber {vakttype}")
        hendelse.add('dtstart', start_dato_tid)
        hendelse.add('dtend', slutt_dato_tid)
        hendelse.add('description', f'Vakt importert fra vaktplan-bilde via OCR\n{start_klokkeslett} - {slutt_klokkeslett}')
        
        # Legg til hendelsen i kalenderen
        kalender.add_component(hendelse)
        print(f"[OK] La til vakt: {dato} {start_klokkeslett}-{slutt_klokkeslett} ({vakttype})")
        return True
    except ValueError as e:
        print(f"[FEIL] Feil ved oppretting av kalenderhendelse: {e}")
        return False
    except Exception as e:
        print(f"[FEIL] Uventet feil: {e}")
        return False

def hovedfunksjon():
    """Hovedfunksjon som prosesserer alle vaktplan-bilder."""
    print("\n>>> Starter vaktplan-konvertering...\n")
    
    # Bruk konfigurasjonsverdier
    bilde_mappe = INPUT_FOLDER
    kalender_mappe = OUTPUT_FOLDER

    # Sjekk at mappene eksisterer
    if not os.path.exists(bilde_mappe):
        print(f"[FEIL] Mappen '{bilde_mappe}' eksisterer ikke!")
        print(f"[TIP] Opprett mappen og legg til vaktplan-bilder der.")
        return
    
    # Tell antall bilder
    bilde_filer = [f for f in os.listdir(bilde_mappe) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not bilde_filer:
        print(f"[ADVARSEL] Ingen bildefiler funnet i '{bilde_mappe}'-mappen")
        print(f"[TIP] Stoettede formater: .png, .jpg, .jpeg")
        return
    
    print(f"[INFO] Funnet {len(bilde_filer)} bilde(r) i '{bilde_mappe}'\n")
    
    if not os.path.exists(kalender_mappe):
        os.makedirs(kalender_mappe)
        print(f"[INFO] Opprettet output-mappe: {kalender_mappe}\n")

    # Opprett én kalender for alle vakter
    kalender = Calendar()
    kalender.add('prodid', '-//Vaktplan Konverter//OCR til iCal//NO')
    kalender.add('version', '2.0')
    antall_vakter = 0
    antall_feilet = 0

    # Behandle hvert bilde
    for idx, bilde_fil in enumerate(bilde_filer, 1):
        bilde_sti = os.path.join(bilde_mappe, bilde_fil)
        print(f"[{idx}/{len(bilde_filer)}] Behandler: {bilde_fil}")
        
        try:
            # Forbedre bilde og utfør OCR
            bilde = forbedre_bilde(bilde_sti)
            tekst = pytesseract.image_to_string(bilde, lang=OCR_LANGUAGE)
            
            # Ekstraher alle vakter fra bildet
            vakter = ekstraher_dato_og_tid(tekst)
            if vakter:
                for dato, start_klokkeslett, slutt_klokkeslett in vakter:
                    # Bestem vakttype basert på start- og slutt-tid
                    vakttype = bestem_vakttype(start_klokkeslett, slutt_klokkeslett)
                    
                    # Legg til hendelsen i kalenderen
                    if lag_kalenderhendelse(kalender, dato, start_klokkeslett, slutt_klokkeslett, vakttype):
                        antall_vakter += 1
            else:
                print(f"[ADVARSEL] Ingen vakter funnet i {bilde_fil}")
                antall_feilet += 1
        
        except Exception as e:
            print(f"[FEIL] Feil ved behandling av {bilde_fil}: {e}")
            antall_feilet += 1
        
        print()  # Blank linje mellom bilder

    # Lagre alle vakter i én fil
    print("="*60)
    if antall_vakter > 0:
        kalender_sti = os.path.join(kalender_mappe, "alle_vakter.ics")
        with open(kalender_sti, 'wb') as f:
            f.write(kalender.to_ical())
        print(f"[SUKSESS] Genererte kalenderfil: {kalender_sti}")
        print(f"[INFO] Totalt {antall_vakter} vakt(er) lagt til")
        if antall_feilet > 0:
            print(f"[ADVARSEL] {antall_feilet} bilde(r) feilet eller hadde ingen vakter")
    else:
        print("[FEIL] Ingen vakter ble funnet i bildene.")
        print("[TIP] Tips:")
        print("   - Sjekk at bildene er klare og lesbare")
        print("   - Sjekk at datoformat er stoettet (maaned + aar)")
        print("   - Sjekk at vakter har format: 'ukedag HH:MM - HH:MM'")
    print("="*60)

if __name__ == "__main__":
    hovedfunksjon() 