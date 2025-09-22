# Web Sandbox (React) - Bootstrap

> Stato: BOOTSTRAP (directory creata, implementazione non ancora avviata)

Questa cartella ospiterà la **Sandbox Web** per:
- Validare query e mutation GraphQL in sviluppo
- Ispezionare rapidamente differenze schema tra versioni
- Testare recommendation engine (futuro) con pannelli diagnostici

## Obiettivi Iniziali
| Step | Descrizione | Stato |
|------|-------------|-------|
| 1 | Scaffold Vite + React + TypeScript | TODO |
| 2 | Setup Apollo Client (link + cache) | TODO |
| 3 | Script fetch schema dal backend (o mirror root) | TODO |
| 4 | Query Explorer minimale (product) | TODO |
| 5 | Mutation Panel (logMeal) | TODO |
| 6 | Diff viewer schema (prev vs current) | TODO |
| 7 | Catalogo query salvate (.graphql) | TODO |

## Stack Previsto
- Vite + React 18 + TypeScript
- Apollo Client (cache normalized, possibile estensione reactive vars)
- Tailwind CSS (rapida prototipazione) oppure minimal CSS Modules
- msw (Mock Service Worker) per isolare UI da backend durante prototipi

## Directory (target futura)
```
web/
  src/
    apollo/
    components/
    pages/
    graphql/ (fragments + operazioni)
    hooks/
    utils/
  public/
  scripts/
  tests/
```

## Versioning
Tag dedicati: `web-vX.Y.Z`.

## Note
La sandbox non è pensata per utenti finali: può includere strumenti diagnostici pesanti / non ottimizzati.
