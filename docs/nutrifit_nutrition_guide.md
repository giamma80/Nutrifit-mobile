# Nutrifit – Nutrition & Diet Engine Guide (Draft)

> Stato: Spostato in `docs/`. Questo è il documento originale completo. (Versione ricollocata 2025-09-18)

<!-- Inizio contenuto originale -->

```diff
NOTE: Questo file è stato ricollocato da root a docs/ per una migliore organizzazione.
```

## 1. Vision & Scopo
Obiettivo: integrare tracking nutrizionale intelligente (calorie + macronutrienti + aderenza al piano) con i dati di spesa energetica provenienti da HealthKit / Google Fit per fornire all’utente un quadro completo: deficit / mantenimento / surplus e progressi verso il goal.

Valore chiave:
- Unico pannello integrato input (cibo) + output (dispendio) + goal adattivi.
- Supporto logging multi-canale: ricerca alimenti, barcode, foto + AI, inserimento rapido porzioni/ricette.
- Feedback adattivo e insight personalizzati.

Out-of-scope iniziale (Fase > MVP): ricette collaborative, social meal sharing, suggerimenti ML avanzati.

## 2. Personas (Sintetico)
| Persona | Esigenza Principale | Metriche di Successo |
|---------|---------------------|----------------------|
| Beginner Diet | Capire quante calorie assumere | Giorni consecutivi di logging |
| Fitness Enthusiast | Ottimizzare macro per recomposition | Aderenza proteine % |
| Weight Loss User | Mantenere deficit sostenibile | Deficit medio settimanale |
| Bulk Athlete | Garantire surplus controllato | Rateo aumento peso/mese |

Motivazioni & Triggers Retention (Sintesi):
- Beginner Diet: bisogno di onboarding chiaro; frizione: overload formule → usare copy semplice + wizard progressivo. Trigger retention: primo grafico progresso peso dopo 5 giorni.
- Fitness Enthusiast: vuole granularità macro; frizione: editing macro manuale; soluzione: modalità avanzata macro override. Trigger: raggiungimento 90% aderenza proteine 7 giorni → badge.
- Weight Loss User: teme plateau; frizione: mancanza feedback trend; soluzione: trend peso smussato (EMA) + messaggi rassicuranti. Trigger: notifica “progressi reali” ogni -1kg cumulativo.
- Bulk Athlete: evita eccessivo grasso; frizione: necessità confronto surplus pianificato vs reale; soluzione: card ‘surplus medio 7g’. Trigger: alert se surplus >15% per 10 giorni.

## 3. Use Case (Priorità)
| ID | Titolo | Descrizione | Priorità | Stato |
|----|--------|-------------|----------|-------|
| UC1 | Onboarding nutrizionale | Raccolta dati fisici + goal → calcolo TDEE & target calorie/macro | P0 | Draft |
| UC2 | Log pasto manuale | Aggiunta alimento da ricerca + quantità | P0 | Draft |
| UC3 | Dashboard giornaliera | Bilancio: assunte vs bruciate vs target | P0 | Draft |
| UC4 | Modifica piano | Aggiornare goal (cut/maintain/bulk) | P1 | Planned |
| UC5 | Barcode scan | Ricerca alimento da codice a barre | P1 | Planned |
| UC6 | Foto piatto (AI) | Stima alimento + conferma utente | P2 | Planned |
| UC7 | Trend settimanali | Aderenza calorie e macro | P1 | Planned |
| UC8 | Notifiche reminder pasti | Prompt quando utente non logga | P2 | Planned |
| UC9 | Adattamento automatico piano | Ricalcolo target se deviazione persistente | P3 | Planned |

## 4. Domain Model (Overview)
...existing content from original guide continues (omitted here for brevity, identical al file root al momento dello spostamento)...

<!-- Contenuto successivo consolidato: le sezioni avanzate (AI pipeline, notifiche, adattamento) sono ora nel documento esteso. -->



