# AFFiNE MCP Server - Oppsett og Dokumentasjon

Dokumentasjon for vår integrasjon med [AFFiNE MCP Server](https://github.com/DAWNCR0W/affine-mcp-server).

## Oversikt

Vi har satt opp en MCP-server (Model Context Protocol) som lar AI-assistenter (som Claude/Cursor) kommunisere direkte med AFFiNE-workspacen vår. Dette muliggjør lesing, søking og manipulering av dokumenter uten å forlate IDE-en.

## Installasjon

```bash
npm install -g affine-mcp-server
```

## Konfigurasjon

Konfigurasjonen ligger i `C:\Users\StianMelhus\.cursor\mcp.json`:

```json
{
  "mcpServers": {
    "affine": {
      "command": "affine-mcp",
      "env": {
        "AFFINE_BASE_URL": "https://affine.sinter.ai/",
        "AFFINE_EMAIL": "din-epost@example.com",
        "AFFINE_PASSWORD": "ditt-passord",
        "AFFINE_LOGIN_AT_START": "async"
      }
    }
  }
}
```

### Autentiseringsmetoder (prioritert rekkefølge)

1. `AFFINE_API_TOKEN` - Personal Access Token (anbefalt for sikkerhet)
2. `AFFINE_COOKIE` - Session cookie fra nettleser
3. `AFFINE_EMAIL` + `AFFINE_PASSWORD` - E-post og passord

> **Sikkerhetsanbefaling:** Bruk `AFFINE_API_TOKEN` i stedet for passord i klartekst. Generer token i AFFiNE-innstillingene.

## Tilgjengelige Verktøy

### Workspace
| Verktøy | Beskrivelse |
|---------|-------------|
| `list_workspaces` | List alle workspaces |
| `get_workspace` | Hent workspace-detaljer |
| `create_workspace` | Opprett workspace med initialt dokument |
| `update_workspace` | Oppdater workspace-innstillinger |
| `delete_workspace` | Slett workspace permanent |

### Dokumenter
| Verktøy | Beskrivelse |
|---------|-------------|
| `list_docs` | List dokumenter med paginering |
| `get_doc` | Hent dokumentmetadata |
| `search_docs` | Søk i dokumenter etter nøkkelord |
| `recent_docs` | List nylig oppdaterte dokumenter |
| `publish_doc` | Gjør dokument offentlig |
| `revoke_doc` | Fjern offentlig tilgang |
| `create_doc` | Opprett nytt dokument (WebSocket) |
| `append_paragraph` | Legg til avsnitt (WebSocket) |
| `delete_doc` | Slett dokument (WebSocket) |

### Kommentarer
| Verktøy | Beskrivelse |
|---------|-------------|
| `list_comments` | List kommentarer på dokument |
| `create_comment` | Opprett kommentar |
| `update_comment` | Oppdater kommentar |
| `delete_comment` | Slett kommentar |
| `resolve_comment` | Merk kommentar som løst |

### Versjonshistorikk
| Verktøy | Beskrivelse |
|---------|-------------|
| `list_histories` | List dokumenthistorikk |
| `recover_doc` | Gjenopprett til tidligere versjon |

### Brukere og Tokens
| Verktøy | Beskrivelse |
|---------|-------------|
| `current_user` | Hent innlogget bruker |
| `sign_in` | Logg inn |
| `update_profile` | Oppdater profil |
| `update_settings` | Oppdater innstillinger |
| `list_access_tokens` | List access tokens |
| `generate_access_token` | Generer ny token |
| `revoke_access_token` | Tilbakekall token |

### Varsler
| Verktøy | Beskrivelse |
|---------|-------------|
| `list_notifications` | Hent varsler |
| `read_notification` | Merk varsel som lest |
| `read_all_notifications` | Merk alle varsler som lest |

### Blob Storage
| Verktøy | Beskrivelse |
|---------|-------------|
| `upload_blob` | Last opp fil |
| `delete_blob` | Slett fil |
| `cleanup_blobs` | Rydd opp i slettede filer |

### Avansert
| Verktøy | Beskrivelse |
|---------|-------------|
| `apply_doc_updates` | Bruk CRDT-oppdateringer på dokumenter |

## Test-resultater (16. januar 2026)

### Hva som fungerer
- [x] MCP-tilkobling til AFFiNE
- [x] `list_workspaces` - Fant 1 workspace
- [x] `list_docs` - Fant 104 dokumenter
- [x] `recent_docs` - Henter nylige dokumenter
- [x] `get_doc` - Henter dokumentmetadata med tittel og sammendrag

### Begrensninger oppdaget
- [ ] `search_docs` - Returnerer tomme resultater selv for ord som burde matche
- [ ] Dokumenttitler vises som `null` i list-operasjoner, men hentes korrekt via `get_doc`

### Dokumenter funnet i workspacen
Eksempler på dokumenter:
- **How to AI** - AI-dokumentasjon
- **Gaussian Splatting** - 3D-teknologi, GPU setup
- **AFFiNE - MCP Server Dev Log** - MCP-serverutvikling
- **Knowledge and Relations Management** - Private cloud
- **Twenty Object Model** - CRM/datamodellering
- **GA4 + GTM + Cookiebot + Site Kit Oppsett** - Analytics-oppsett

## Bruksregler (fra .cursorrules)

Vi har definert følgende regler for sikker bruk:

1. **Ingen destruktive handlinger uten eksplisitt instruksjon**
   - Aldri slett dokumenter, workspaces, eller blobs uten bekreftelse

2. **Minimal-endring prinsipp**
   - Kun gjør strengt nødvendige endringer

3. **Les-før-skriv**
   - Alltid inspiser nåværende tilstand før endringer

4. **Sikre standardvalg**
   - Ved usikkerhet, velg read-only operasjoner

## Feilsøking

### MCP-serveren starter ikke
1. Sjekk at `affine-mcp` er installert: `affine-mcp --version`
2. Restart Cursor etter konfigurasjon
3. Sjekk MCP-status i Cursor Settings → Features → MCP

### Autentiseringsfeil
1. Verifiser at `AFFINE_BASE_URL` er tilgjengelig
2. Sjekk at e-post/passord er korrekt
3. Prøv å generere en API-token i AFFiNE og bruk den i stedet

### Søk fungerer ikke
- Søkefunksjonen har begrensninger i API-et
- Bruk `get_doc` på spesifikke dokumenter i stedet
- Eller naviger manuelt via `list_docs` og `recent_docs`

## Lenker

- [AFFiNE MCP Server GitHub](https://github.com/DAWNCR0W/affine-mcp-server)
- [AFFiNE Dokumentasjon](https://docs.affine.pro)
- [MCP Protocol Spesifikasjon](https://modelcontextprotocol.io)

---

*Sist oppdatert: 16. januar 2026*
