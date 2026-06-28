# Guida all'uso di ManusBridge

Guida completa e passo-passo per installare e utilizzare **ManusBridge**: l'addon
per Blender e la skill `blender-manager` per Manus AI. Questo documento è pensato
sia per chi parte da zero, sia come riferimento per la risoluzione dei problemi.

---

## Indice

1. [Introduzione](#1-introduzione)
2. [Come funziona](#2-come-funziona)
3. [Requisiti](#3-requisiti)
4. [Parte 1 — Installazione dell'addon in Blender](#4-parte-1--installazione-delladdon-in-blender)
5. [Parte 2 — Avvio del server e del tunnel ngrok](#5-parte-2--avvio-del-server-e-del-tunnel-ngrok)
6. [Parte 3 — Configurazione della skill su Manus](#6-parte-3--configurazione-della-skill-su-manus)
7. [Parte 4 — Invio dei comandi e primi esempi](#7-parte-4--invio-dei-comandi-e-primi-esempi)
8. [Parte 5 — Integrazione con Ollama (opzionale)](#8-parte-5--integrazione-con-ollama-opzionale)
9. [Sicurezza](#9-sicurezza)
10. [Risoluzione dei problemi](#10-risoluzione-dei-problemi)
11. [Disinstallazione](#11-disinstallazione)

---

## 1. Introduzione

ManusBridge permette a Manus AI (o a qualsiasi altro client) di **controllare Blender
da remoto**, inviando comandi Python che vengono eseguiti all'interno della scena 3D.
La comunicazione avviene tramite un semplice server HTTP esposto su Internet con un
tunnel (ngrok), evitando le complessità di autenticazione dei protocolli più strutturati.

Il progetto è composto da due parti:

| Parte | Cosa fa | Dove gira |
|-------|---------|-----------|
| **Addon** (`manus_bridge`) | Avvia un server HTTP che riceve ed esegue i comandi. | Dentro Blender, sul tuo PC. |
| **Skill** (`blender-manager`) | Insegna a Manus il protocollo per comunicare con l'addon. | Su Manus AI. |

---

## 2. Come funziona

```
┌──────────┐    HTTPS    ┌────────┐   HTTP :9999   ┌────────────────────────┐
│ Manus AI │ ──────────► │ ngrok  │ ─────────────► │ Blender + addon        │
│ (client) │             │ tunnel │                │ ManusBridge            │
└──────────┘             └────────┘                └────────────────────────┘
                                                              │
                                            coda → bpy.app.timers (main thread)
```

1. Manus invia una richiesta HTTP `POST` contenente un comando Python.
2. La richiesta passa attraverso il tunnel ngrok e raggiunge il server locale sulla porta `9999`.
3. L'addon **non** esegue subito il comando: lo mette in una coda.
4. Un timer interno di Blender (`bpy.app.timers`) preleva il comando dalla coda e lo
   esegue nel **thread principale** di Blender. Questo passaggio è fondamentale: le API
   di Blender non sono thread-safe ed eseguirle dal thread del server provocherebbe il
   crash dell'applicazione.
5. L'addon restituisce a Manus l'esito (`success` oppure `error` con messaggio).

---

## 3. Requisiti

- **Blender** 3.0 o superiore (testato su 5.1.2).
- **ngrok** installato e configurato con un account gratuito ([ngrok.com](https://ngrok.com)).
- *(Facoltativo)* **Ollama** in esecuzione su `localhost:11434` per usare LLM locali.
- Una connessione a Internet attiva.

---

## 4. Parte 1 — Installazione dell'addon in Blender

1. Scarica il repository:
   - dal pulsante verde **Code → Download ZIP**, oppure
   - con `git clone https://github.com/Glitch371/manus-bridge.git`.
2. Dalla cartella scaricata, individua la sottocartella `manus_bridge` (quella che
   contiene `__init__.py`) e **comprimila in un file `.zip`**.
   > L'addon va installato come zip che contiene la cartella `manus_bridge`, non il
   > singolo file `__init__.py`.
3. Apri Blender e vai su **Edit → Preferences → Add-ons**.
4. Clicca **Install…** (in alto a destra) e seleziona il file `.zip`.
5. Nella lista degli addon cerca **ManusBridge** e attiva la casella per abilitarlo.
6. Chiudi le Preferenze.

Per verificare che sia attivo: nella vista 3D premi `N` per aprire la barra laterale
(N-panel) e controlla che sia presente la scheda **Manus**.

---

## 5. Parte 2 — Avvio del server e del tunnel ngrok

### 5.1 Avvio del server in Blender

1. Nella vista 3D, apri la N-panel (tasto `N`) e seleziona la scheda **Manus**.
2. Clicca **Avvia ManusBridge**.
3. Lo stato deve passare a **Connesso (Porta 9999)**.

### 5.2 Avvio del tunnel ngrok

Apri un terminale ed esegui:

```bash
ngrok http 9999
```

ngrok mostrerà un URL pubblico simile a:

```
Forwarding   https://1a2b-3c4d.ngrok-free.app -> http://localhost:9999
```

Copia quell'URL (`https://1a2b-3c4d.ngrok-free.app`): è l'indirizzo che dovrai
comunicare a Manus.

> **Nota:** con il piano gratuito di ngrok l'URL **cambia a ogni riavvio**. Se riavvii
> ngrok, dovrai aggiornare l'URL su Manus.

### 5.3 Verifica rapida

Apri l'URL di ngrok nel browser. Se vedi il messaggio `ManusBridge is active!`,
il server e il tunnel funzionano correttamente.

---

## 6. Parte 3 — Configurazione della skill su Manus

1. Carica il file `blender-manager.skill` (lo trovi nella cartella `skill/` del
   repository, oppure riconfezionato come `.skill`) tra le skill del tuo agente Manus.
2. Nelle istruzioni di progetto o nel primo messaggio della sessione, **comunica a
   Manus l'URL del tunnel ngrok**. Esempio:

   > L'istanza di Blender è raggiungibile a `https://1a2b-3c4d.ngrok-free.app`
   > (porta 9999). Usa la skill blender-manager per inviare i comandi.

3. Da questo momento Manus saprà come inviare comandi Python a Blender.

---

## 7. Parte 4 — Invio dei comandi e primi esempi

I comandi sono normale codice Python che usa l'API `bpy` di Blender. Manus li invierà
automaticamente; di seguito alcuni esempi del codice che viene eseguito.

### Esempio di richiesta (lato client)

```python
import requests

def send_command(url, command):
    headers = {"ngrok-skip-browser-warning": "true"}
    payload = {"command": command}
    return requests.post(url, json=payload, headers=headers).json()

# Aggiunge un cubo all'origine
send_command(
    "https://1a2b-3c4d.ngrok-free.app",
    "bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))"
)
```

### Esempi di comandi utili

```python
# Creare un piano
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))

# Creare una sfera
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 2))

# Eliminare tutti gli oggetti selezionati
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Applicare un materiale rosso all'oggetto attivo
mat = bpy.data.materials.new(name="Rosso")
mat.diffuse_color = (1, 0, 0, 1)
bpy.context.active_object.data.materials.append(mat)
```

### Formato della risposta

```json
{ "status": "success", "message": "Comando eseguito" }
```

In caso di errore nel comando:

```json
{ "status": "error", "message": "descrizione dell'errore Python" }
```

> Gli errori nei comandi vengono **catturati e restituiti** nella risposta: non fanno
> più crashare Blender. Se Manus riceve uno `status: error`, leggi il messaggio per
> capire cosa correggere nel comando.

---

## 8. Parte 5 — Integrazione con Ollama (opzionale)

Se hai Ollama in esecuzione, la skill può interrogare modelli LLM locali.

```python
# Elenco dei modelli disponibili
GET http://localhost:11434/api/tags

# Generazione di testo
POST http://localhost:11434/api/generate
{ "model": "llama3", "prompt": "..." }
```

Usa i modelli locali per le elaborazioni che richiedono riservatezza.

---

## 9. Sicurezza

> ⚠️ **Leggi attentamente.** Questo strumento esegue codice Python arbitrario ricevuto
> via HTTP, senza autenticazione integrata.

- **Non esiste autenticazione** sull'endpoint: chiunque conosca l'URL ngrok può
  eseguire codice sul tuo PC con i permessi di Blender.
- **Proteggi il tunnel.** Aggiungi un'autenticazione di base a ngrok:
  ```bash
  ngrok http 9999 --basic-auth "utente:password"
  ```
- **Spegni il tunnel** quando hai finito di lavorare.
- **Non usare** questo strumento su una macchina con dati sensibili senza un livello di
  protezione davanti.
- Trattandosi di uno strumento pensato per l'uso personale e per ambienti fidati,
  evita di pubblicare l'URL del tunnel.

---

## 10. Risoluzione dei problemi

| Problema | Causa probabile | Soluzione |
|----------|-----------------|-----------|
| **Connection Refused** | Il server non è avviato. | Premi *Avvia ManusBridge* nella N-panel → scheda Manus. |
| **Timeout** | ngrok spento o URL non aggiornato. | Verifica che ngrok sia attivo; aggiorna l'URL su Manus (cambia a ogni riavvio). |
| **Blender crasha durante i comandi** | Versione vecchia dell'addon (esecuzione fuori dal main thread). | Usa la v1.1 o superiore. Verifica nella console Python: `import manus_bridge; print(hasattr(manus_bridge, '_process_command_queue'))` deve restituire `True`. |
| **`register_class(...): already registered`** | Bug della v1.0 nella funzione di disattivazione. | Risolto in v1.1. Chiudi e riapri Blender, poi reinstalla l'addon aggiornato. |
| **La scheda "Manus" non compare** | Addon non abilitato. | Edit → Preferences → Add-ons → cerca ManusBridge e abilitalo. |
| **`status: error` nella risposta** | Errore nel comando Python inviato. | Comportamento corretto (non è un crash): leggi il messaggio e correggi il comando. |

### Verifica diagnostica nella console Python di Blender

Apri la **console Python interattiva** (area in basso a sinistra, prompt `>>>`) e
incolla:

```python
import manus_bridge
print(manus_bridge.__file__)
print(hasattr(manus_bridge, "_process_command_queue"))  # deve stampare True
```

> Nota: i `print()` di uno *script* lanciato con il pulsante "Run Script" finiscono nella
> **console di sistema** (Window → Toggle System Console), non nella console interattiva.
> Per una verifica veloce, usa la console interattiva come sopra.

---

## 11. Disinstallazione

1. In Blender: **Edit → Preferences → Add-ons**, cerca **ManusBridge** e disabilitalo,
   poi clicca **Remove** per rimuoverlo.
2. Chiudi il tunnel ngrok (`Ctrl+C` nel terminale).

---

*Per una panoramica rapida del progetto consulta il [README](../README.md).*
