import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Personvern - ShiftSync',
  description: 'Personvernerkl\u00e6ring for ShiftSync. Les om hvordan vi behandler data og beskytter ditt personvern.',
}

export default function PersonvernPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Personvernerkl&aelig;ring</h1>

      <div className="prose prose-gray max-w-none space-y-8">
        <p className="text-gray-600">
          Sist oppdatert: 14. februar 2026
        </p>

        <section>
          <h2 className="text-xl font-semibold text-gray-900">1. Behandlingsansvarlig</h2>
          <p className="text-gray-600">
            ShiftSync er ansvarlig for behandlingen av data i tjenesten. Kontakt oss
            p&aring; <a href="mailto:kontakt@shiftsync.no" className="text-sky-600 hover:text-sky-700">kontakt@shiftsync.no</a> ved
            sp&oslash;rsm&aring;l om personvern.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900">2. Hvilke data behandler vi</h2>
          <p className="text-gray-600">
            ShiftSync er designet for &aring; minimere datainnsamling. Vi behandler f&oslash;lgende:
          </p>
          <ul className="list-disc pl-6 text-gray-600 space-y-2">
            <li>
              <strong>Opplastede bilder:</strong> Bilder av vaktplaner du laster opp for konvertering.
              Disse slettes automatisk etter 24 timer.
            </li>
            <li>
              <strong>Anonyme &oslash;kttokens:</strong> En anonym informasjonskapsel for &aring; holde styr p&aring;
              din sesjon og kvote. Denne inneholder ingen personlige opplysninger.
            </li>
            <li>
              <strong>Anonymisert bruksstatistikk:</strong> Aggregert informasjon om bruk av tjenesten
              (antall konverteringer, OCR-metode valgt, osv.). IP-adresser blir hashet og kan ikke spores tilbake.
            </li>
            <li>
              <strong>Tilbakemeldinger:</strong> Dersom du sender inn korreksjoner p&aring; OCR-resultater,
              lagres disse anonymisert for &aring; forbedre tjenesten.
            </li>
          </ul>
          <p className="text-gray-600 mt-4">
            Vi lagrer <strong>ingen</strong> brukerkontoer, e-postadresser, navn, eller andre
            personopplysninger.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900">3. Form&aring;l med behandlingen</h2>
          <ul className="list-disc pl-6 text-gray-600 space-y-2">
            <li>Konvertere vaktplanbilder til kalenderfiler (kjernetjenesten)</li>
            <li>H&aring;ndtere betalinger via Stripe for premium-funksjoner</li>
            <li>Forbedre OCR-kvaliteten basert p&aring; anonymiserte tilbakemeldinger</li>
            <li>Forst&aring; brukem&oslash;nstre for &aring; forbedre tjenesten</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900">4. Rettslig grunnlag</h2>
          <p className="text-gray-600">
            Behandlingen baseres p&aring; GDPR artikkel 6(1)(b) &mdash; oppfyllelse av avtale (levering av tjenesten)
            og artikkel 6(1)(f) &mdash; berettiget interesse (anonymisert bruksstatistikk for tjenesteforbedring).
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900">5. Tredjeparter og databehandlere</h2>
          <ul className="list-disc pl-6 text-gray-600 space-y-2">
            <li><strong>Microsoft Azure:</strong> Lagring av filer og hosting av backend (EU-region)</li>
            <li><strong>Vercel:</strong> Hosting av frontend (global CDN)</li>
            <li><strong>Stripe:</strong> Betalingsbehandling &mdash; vi ser aldri dine kortdetaljer</li>
            <li><strong>OpenAI:</strong> AI-basert OCR (kun n&aring;r du velger &laquo;AI-metode&raquo;) &mdash; bildet sendes til OpenAI for prosessering</li>
            <li><strong>Sentry:</strong> Feilsporing (ingen persondata, kun tekniske feilmeldinger)</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900">6. Lagring og sletting</h2>
          <p className="text-gray-600">
            Opplastede bilder og genererte kalenderfiler slettes automatisk etter <strong>24 timer</strong>.
            Anonymisert bruksstatistikk og tilbakemeldinger lagres p&aring; ubestemt tid, men inneholder
            ingen personopplysninger.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900">7. Informasjonskapsler (cookies)</h2>
          <p className="text-gray-600">
            Vi bruker kun funksjonelle informasjonskapsler som er n&oslash;dvendige for &aring; levere tjenesten:
          </p>
          <ul className="list-disc pl-6 text-gray-600 space-y-2">
            <li><strong>Sesjons-cookie:</strong> Holder styr p&aring; din anonyme sesjon og kvote. HttpOnly, SameSite=Lax, Secure.</li>
            <li><strong>Cookie-samtykke:</strong> Husker ditt valg for informasjonskapsler.</li>
          </ul>
          <p className="text-gray-600 mt-4">
            Vi bruker ingen sporingscookies, reklamecookies, eller tredjeparts analyseverkt&oslash;y som samler persondata.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900">8. Dine rettigheter</h2>
          <p className="text-gray-600">
            Siden vi ikke lagrer personopplysninger, er de fleste GDPR-rettigheter (innsyn, retting, sletting)
            ikke relevante. Dersom du mener vi behandler dine data, kan du kontakte oss p&aring;{' '}
            <a href="mailto:kontakt@shiftsync.no" className="text-sky-600 hover:text-sky-700">kontakt@shiftsync.no</a>.
          </p>
          <p className="text-gray-600 mt-4">
            Du har rett til &aring; klage til Datatilsynet dersom du mener vi behandler personopplysninger i strid med regelverket.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900">9. Endringer</h2>
          <p className="text-gray-600">
            Vi kan oppdatere denne erkl&aelig;ringen ved behov. Vesentlige endringer vil bli varslet p&aring; nettsiden.
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
