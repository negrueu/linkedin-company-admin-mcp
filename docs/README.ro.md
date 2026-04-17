# linkedin-company-admin-mcp (RO)

> **Limba:** [English](../README.md) - Romana

[![PyPI](https://img.shields.io/pypi/v/linkedin-company-admin-mcp.svg)](https://pypi.org/project/linkedin-company-admin-mcp/)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE)
[![CI](https://github.com/negrueu/linkedin-company-admin-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/negrueu/linkedin-company-admin-mcp/actions/workflows/ci.yml)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

**Server MCP pentru administrarea Paginii de Companie LinkedIn.** Citeste analytics, gestioneaza postari, editeaza detaliile paginii, atrage urmaritori si foloseste profilul personal ca punte in workflow-urile de employee advocacy.

> **Complementar cu [stickerdaniel/linkedin-mcp-server](https://github.com/stickerdaniel/linkedin-mcp-server).** Proiectul stickerdaniel acopera cazurile de utilizare pe LinkedIn personal (feed, mesagerie, cautare). Proiectul acesta umple o nisa pe care nu o acopera nimeni: **control administrativ complet asupra Paginii de Companie LinkedIn**, plus un set mic de tool-uri bridge pentru profilul personal, dedicate exclusiv flow-urilor de employee advocacy.

> 🛇 **Termenii LinkedIn si risc de restrictie cont.** [User Agreement](https://www.linkedin.com/legal/user-agreement) de la LinkedIn interzice explicit accesul automatizat la platforma. Acest server actioneaza prin browser real in numele tau iar LinkedIn poate detecta, limita sau restrictiona permanent conturile care il folosesc - inclusiv cu pierderea accesului la Pagina de Companie. **Folosire pe risc propriu.** Nu folosi acest MCP pe un cont personal sau de business pe care nu iti permiti sa-l pierzi. Autorii NU pot recupera un cont restrictionat. Alternativa oficiala: [Community Management API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/), daca te califici.

> 🔐 **Nota de securitate - directorul de profil = credentiale.** "Fara credentiale stocate" inseamna ca serverul nu cere parola si nu o scrie intr-un fisier de configurare. NU inseamna ca directorul de profil e sigur de partajat. Dupa login, `~/.linkedin-company-admin/profile` contine cookie-urile de sesiune LinkedIn, echivalente functional cu parola + 2FA combinate. Oricine citeste acest director obtine acces admin complet la contul si pagina ta. In particular: **nu sincroniza acest director pe OneDrive / iCloud / Dropbox / alt backup in cloud.** Pastreaza-l strict pe disk local, pe un calculator in care ai incredere.

## De ce acest proiect

Community Management API de la LinkedIn este doar pe invitatie. Scraping-ul profilelor personale e deja bine acoperit. Ce lipsea: un MCP stabil, bazat pe browser, care permite unui administrator de pagina (sau LLM-ului sau asistent) sa citeasca analytics, sa pregateasca postari, sa editeze sectiunea about, sa invite urmaritori si sa taggheze pagina dintr-o postare personala - fara ca vreo parola sa fie stocata vreodata.

## Caracteristici pe scurt

- **24 de tool-uri MCP** in 6 categorii - vezi [Referinta tool-uri](#referinta-tool-uri) mai jos.
- **Zero credentiale** pe disk. Login interactiv intr-o fereastra Chromium vizibila; sesiunea este pastrata intr-un director de profil persistent (chmod 0o700 pe Unix).
- **Chromium stealth** prin [Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python) (fork anti-detectie peste Playwright).
- **Provider abstraction** (`AdminProvider`, `PostsProvider`) astfel incat un backend viitor pe Community Management API sa se integreze fara rescrierea tool-urilor.
- **Rate limiting** chiar aplicat (nu doar importat) - fiecare tool de scriere are un cap orar conservator.
- **Selectori doar pe aria-label / role / innerText** - fara clase CSS ofuscate. Cand LinkedIn schimba UI, se atinge doar `selectors/__init__.py`.
- **Fara god-files** (max ~300 LOC per fisier), type-check cu mypy, lint cu ruff.

## Instalare

### Optiunea 1: uvx (recomandat)

Publicat pe PyPI ca [`linkedin-company-admin-mcp`](https://pypi.org/project/linkedin-company-admin-mcp/).

```bash
uvx linkedin-company-admin-mcp@latest --login
```

Apoi adauga in config Claude Desktop (`~/.config/Claude/claude_desktop_config.json` sau echivalentul de platforma):

```json
{
  "mcpServers": {
    "linkedin-company-admin": {
      "command": "uvx",
      "args": ["linkedin-company-admin-mcp@latest"]
    }
  }
}
```

### Optiunea 2: Dezvoltare locala

```bash
git clone https://github.com/negrueu/linkedin-company-admin-mcp.git
cd linkedin-company-admin-mcp
uv sync
uv run linkedin-company-admin-mcp --login
```

### Optiunea 3: Docker

```bash
docker build -t linkedin-company-admin-mcp .
docker run --rm -it \
  -v linkedin_profile:/home/mcp/.linkedin-company-admin \
  linkedin-company-admin-mcp --login
```

## Login la prima rulare

**Credentialele nu sunt stocate niciodata in server.** Login-ul este interactiv:

```bash
uvx linkedin-company-admin-mcp --login
```

Se deschide o fereastra Chromium vizibila. Autentifica-te pe LinkedIn normal (inclusiv 2FA). Profilul persistent este salvat in `~/.linkedin-company-admin/profile` (chmod 0o700 pe Unix). Toate apelurile MCP ulterioare reutilizeaza aceasta sesiune automat.

Pentru logout: `uvx linkedin-company-admin-mcp --logout` (sterge directorul de profil).

## Referinta tool-uri

Lista completa de argumente si exemple se afla in [docs/TOOL_REFERENCE.md](TOOL_REFERENCE.md). Sumar:

### Session (3)

| Tool | Scop |
|---|---|
| `session_status` | Este profilul persistent viu si logat? |
| `session_warmup` | Preincarca browser-ul + `/feed/` pentru a reduce latenta primului apel. |
| `session_logout` | Inchide browser-ul si sterge directorul de profil. |

### Company read (6)

| Tool | Scop |
|---|---|
| `company_read_page` | Nume, tagline, followers, about, industrie, website. |
| `company_list_posts` | Postari recente cu URN, text, reactii, comentarii. |
| `company_list_followers` | Lista urmaritori (doar admin; paginata). |
| `company_list_mentions` | Postari care au mentionat pagina (notificari admin). |
| `company_manage_admins` | Listeaza administratorii si rolurile lor. |
| `company_analytics` | Metrici followers / postari pentru fereastra 7d / 28d / 90d. |

### Company admin write (3)

| Tool | Scop |
|---|---|
| `company_edit_about` | Actualizeaza sectiunea About (cu fallback pe tagline). |
| `company_edit_logo` | Incarca un logo nou (si optional un banner). |
| `company_update_details` | Website, industrie, marime, specializari. |

### Company content (6)

| Tool | Scop |
|---|---|
| `company_create_post` | Publica o postare text (optional link / imagine). |
| `company_edit_post` | Inlocuieste corpul unei postari existente. |
| `company_delete_post` | Stergere permanenta - vezi [docs/RCA_DELETE_POST.md](RCA_DELETE_POST.md). |
| `company_schedule_post` | Publica la un datetime ISO-8601 viitor. |
| `company_reply_comment` | Raspunde ca pagina la un comentariu pe una din postarile tale. |
| `company_reshare_post` | Repostare ca pagina, cu comentariu optional. |

### Company growth (2)

| Tool | Scop |
|---|---|
| `company_invite_to_follow` | Trimite invitatii de follow catre conexiuni de gradul 1 (LinkedIn impune cap 250/luna). |
| `company_list_scheduled` | Listeaza postarile in asteptare pentru publicare viitoare. |

### Personal -> Company bridge (4)

| Tool | Scop |
|---|---|
| `personal_tag_company` | Publica o postare personala care @-mentioneaza pagina. |
| `personal_reshare_company_post` | Repostare a unei postari de pagina pe profilul personal. |
| `personal_comment_as_admin` | Comenteaza pe o postare de pagina ca pagina (sau ca tine). |
| `personal_read_company_mentions` | Scaneaza activitatea recenta dupa postari care taggheaza pagina. |

## Model de securitate

- **Fara gestionare email/parola.** Credentialele nu ating codul.
- **Starea sesiunii** traieste intr-un director de profil persistent, izolat per utilizator OS, in afara repo-ului.
- **`.env`** contine doar configurari (log level, transport, tool timeout). Fara secrete.
- Directorul de profil este chmod 0o700 la primul login (Unix).
- **Rate limiting** se aplica per tool; cap-urile sunt conservative prin design, calibrate dupa ce tolereaza LinkedIn, nu ce permite tehnic.

## Workflow-uri suportate

- Pregateste, revizuieste si publica o postare pe pagina ta de companie din Claude.
- Taggheaza pagina dintr-o postare personala si urmareste cum reactioneaza comunitatea.
- Auditeaza cine a postat despre pagina ta saptamana aceasta (mentions admin).
- Invita un batch de conexiuni de gradul 1 sa urmareasca pagina, oprindu-te la quota lunara LinkedIn.
- Ruleaza un CRUD complet pe postarile programate inainte de un lansament.

Vezi [docs/TOOL_REFERENCE.md](TOOL_REFERENCE.md) pentru exemple end-to-end.

## Depanare

Selector drift, captcha, rate limits, expirare cookies si probleme de lansare Chromium sunt acoperite in [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Contributii

Contributiile sunt binevenite. Vezi [docs/CONTRIBUTING.md](CONTRIBUTING.md) pentru setup local, layout de teste si workflow-ul pentru adaugarea unui tool nou.

## Status

In dezvoltare activa. Vezi [CHANGELOG.md](../CHANGELOG.md) pentru istoricul versiunilor si [issues](https://github.com/negrueu/linkedin-company-admin-mcp/issues) pentru roadmap.

## Licenta

[MIT](../LICENSE)
