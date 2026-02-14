import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Bruksvilk\u00e5r - ShiftSync',
  description: 'Bruksvilk\u00e5r for ShiftSync. Les om vilk\u00e5rene for bruk av tjenesten.',
}

export default function VilkarPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Bruksvilk&aring;r</h1>

      <div className="prose prose-gray max-w-none space-y-8">
        <p className="text-gray-600">
          Sist oppdatert: 14. februar 2026
        </p>

        <section>
          <h2 className="text-xl font-semibold text-gray-900">1. Om tjenesten</h2>
          <p className="text-gray-600">
            ShiftSync (&laquo;tjenesten&raquo;) er en nettbasert l&oslash;sning for &aring; konvertere bilder av
            vaktplaner til kalenderfiler (.ics) ved hjelp av OCR-teknologi. Tjenesten leveres
            av ShiftSync, org.nr. [kommer ved registrering].
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900">2. Bruk av tjenesten</h2>
          <p className="text-gray-600">
            Ved &aring; bruke ShiftSync godtar du disse vilk&aring;rene. Tjenesten kan brukes uten opprettelse
            av brukerkonto. Du f&aring;r et begrenset antall gratis konverteringer per m&aring;ned, og kan
            kj&oslash;pe ekstra kreditter for utvidet bruk.
          </p>
          <p className="text-gray-600 mt-4">
            Du er ansvarlig for &aring;:
          </p>
          <ul className="list-disc pl-6 text-gray-600 space-y-2">
            <li>Kun laste opp bilder du har rett til &aring; bruke</li>
            <li>Ikke misbruke tjenesten (automatisert massebruk, fors&oslash;k p&aring; &aring; omg&aring; kvotegrenser, osv.)</li>
            <li>Selv verifisere at OCR-resultatene er korrekte f&oslash;r du bruker kalenderfilen</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900">3. OCR-n&oslash;yaktighet</h2>
          <p className="text-gray-600">
            OCR-teknologi er ikke feilfri. ShiftSync gj&oslash;r sitt beste for &aring; levere n&oslash;yaktige resultater,
            men <strong>garanterer ikke 100 % korrekthet</strong>. Du b&oslash;r alltid kontrollere de genererte
            vaktene f&oslash;r du importerer dem i kalenderen din. ShiftSync er ikke ansvarlig for
            konsekvenser av feil i OCR-resultater.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900">4. Betaling og kreditter</h2>
          <p className="text-gray-600">
            Betalinger h&aring;ndteres av Stripe. Ved kj&oslash;p av kreditter gjelder f&oslash;lgende:
          </p>
          <ul className="list-disc pl-6 text-gray-600 space-y-2">
            <li>Kreditter er ikke-refunderbare etter bruk</li>
            <li>Ubrukte kreditter utl&oslash;per ikke</li>
            <li>Priser oppgis i NOK inkludert mva.</li>
          </ul>
          <p className="text-gray-600 mt-4">
            For sp&oslash;rsm&aring;l om betaling, kontakt{' '}
            <a href="mailto:kontakt@shiftsync.no" className="text-sky-600 hover:text-sky-700">kontakt@shiftsync.no</a>.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900">5. Opplastede filer</h2>
          <p className="text-gray-600">
            Bilder du laster opp behandles kun for &aring; utf&oslash;re konverteringen og slettes automatisk
            etter 24 timer. Vi forbeholder oss ikke noen rettigheter til innholdet i dine bilder.
            Se v&aring;r <Link href="/personvern" className="text-sky-600 hover:text-sky-700">personvernerkl&aelig;ring</Link> for
            mer informasjon om databehandling.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900">6. Tilgjengelighet</h2>
          <p className="text-gray-600">
            Vi tilstreber h&oslash;y oppetid, men garanterer ikke uavbrutt tilgang til tjenesten.
            Planlagt vedlikehold vil normalt varsles p&aring; forh&aring;nd. ShiftSync er ikke ansvarlig
            for tap som f&oslash;lge av nedetid.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900">7. Ansvarsbegrensning</h2>
          <p className="text-gray-600">
            ShiftSync leveres &laquo;som den er&raquo;. Vi er ikke ansvarlige for indirekte tap,
            f&oslash;lgetap, eller tap som skyldes feil i OCR-resultater. V&aring;rt maksimale
            erstatningsansvar er begrenset til bel&oslash;pet du har betalt for tjenesten de siste 12 m&aring;nedene.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900">8. Immaterielle rettigheter</h2>
          <p className="text-gray-600">
            ShiftSync, inkludert kode, design og varemerke, tilh&oslash;rer ShiftSync.
            Du f&aring;r en begrenset, ikke-eksklusiv rett til &aring; bruke tjenesten i henhold til disse vilk&aring;rene.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900">9. Endringer i vilk&aring;rene</h2>
          <p className="text-gray-600">
            Vi kan oppdatere disse vilk&aring;rene ved behov. Vesentlige endringer vil bli varslet p&aring; nettsiden.
            Fortsatt bruk av tjenesten etter endringer anses som aksept av de nye vilk&aring;rene.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900">10. Lovvalg og tvister</h2>
          <p className="text-gray-600">
            Disse vilk&aring;rene er underlagt norsk lov. Eventuelle tvister skal s&oslash;kes l&oslash;st i minnelighet
            f&oslash;rst. Dersom det ikke oppn&aring;s enighet, avgj&oslash;res tvisten av norske domstoler.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900">11. Kontakt</h2>
          <p className="text-gray-600">
            Sp&oslash;rsm&aring;l om vilk&aring;rene? Kontakt oss p&aring;{' '}
            <a href="mailto:kontakt@shiftsync.no" className="text-sky-600 hover:text-sky-700">kontakt@shiftsync.no</a>.
          </p>
        </section>

        <div className="mt-8 pt-6 border-t border-gray-200">
          <Link href="/" className="text-sky-600 hover:text-sky-700 focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 rounded">
            &larr; Tilbake til forsiden
          </Link>
        </div>
      </div>
    </div>
  )
}
