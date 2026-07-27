# LinkedIn Posts - Angelo Falci

Raccolta dei miei post pubblicati su LinkedIn.

Ogni post è salvato come file `.txt` con formato `YYYYMMDD-titolo-breve.txt`.

## Import draft nel blog

Lo script `publish_new_blog_drafts.py` crea draft nel blog del sito personale a partire dai file locali piu recenti del post pubblicato piu nuovo presente su Firestore.

Se esiste un file `.env` nella root di questa cartella, lo script lo carica automaticamente prima di leggere gli argomenti CLI.

Prerequisiti:
- Python 3.10+
- `pip install firebase-admin`
- un service account Firebase del progetto `angelo-falci`

Configurazione minima:
- nel file `.env` basta impostare `GOOGLE_APPLICATION_CREDENTIALS` con il path reale del service account JSON
- `project id`, collection, locale e tag hanno gia default coerenti con il tuo sito

Esempi:
- `python publish_new_blog_drafts.py --dry-run` se hai gia configurato `.env`
- `python publish_new_blog_drafts.py --credentials C:\path\service-account.json --dry-run`
- `python publish_new_blog_drafts.py --credentials C:\path\service-account.json`
- `python publish_new_blog_drafts.py --cutoff-date 2026-05-27 --dry-run`

Note:
- legge i file `YYYYMMDD-*.txt` nella root di questa cartella
- crea documenti nella collection `posts` con `status = draft`
- se un post con lo stesso `slug` esiste gia, lo salta
- unica variabile realmente necessaria nel `.env`: `GOOGLE_APPLICATION_CREDENTIALS`
- variabili opzionali supportate nel `.env`: `LINKEDIN_SOURCE_DIR`, `BLOG_FIRESTORE_PROJECT_ID`, `BLOG_FIRESTORE_COLLECTION`, `BLOG_POST_LOCALE`, `BLOG_POST_TAGS`, `BLOG_CUTOFF_DATE`
