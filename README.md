# ManusBridge

Ponte HTTP diretto tra **Manus AI** (o qualsiasi client) e **Blender 3D**, pensato per l'automazione remota tramite tunnel ngrok. Include l'addon per Blender e la skill `blender-manager` che insegna a Manus come comunicare con l'istanza locale.

> ⚠️ **Avviso di sicurezza — leggi prima di usare.** Questo addon avvia un server HTTP che esegue **codice Python arbitrario** inviato via richiesta `POST`. Se lo esponi con ngrok, *chiunque* abbia l'URL può eseguire codice sulla tua macchina con i permessi di Blender. Vedi la sezione [Sicurezza](#sicurezza).

> 📖 **Guida completa passo-passo:** [`docs/GUIDA.md`](docs/GUIDA.md) — installazione, ngrok, skill, esempi e troubleshooting.

---

## Architettura

```
┌──────────┐    HTTPS    ┌────────┐   HTTP :9999   ┌──────────────────┐
│ Manus AI │ ──────────► │ ngrok  │ ─────────────► │ Blender          │
│ (client) │             │ tunnel │                │ + addon ManusBridge
└──────────┘             └────────┘                └──────────────────┘
                                                            │
                                          coda → bpy.app.timers (main thread)
```

I comandi inviati al server HTTP vengono accodati e poi eseguiti nel **main thread** di Blender tramite `bpy.app.timers`. Questo è essenziale: le API `bpy.*` non sono thread-safe e chiamarle direttamente dal thread del server causa crash (`EXCEPTION_ACCESS_VIOLATION`).

---

## Componenti

| Componente | Descrizione |
|------------|-------------|
| `manus_bridge/__init__.py` | Addon Blender: server HTTP su porta `9999`, esecuzione comandi nel main thread, pannello nella N-sidebar. |
| `blender-manager.skill` | Skill per Manus: protocollo di comunicazione, workflow di automazione Blender, integrazione Ollama. |

---

## Requisiti

- **Blender** 3.0+ (testato su 5.1.2)
- **ngrok** (o tunnel equivalente) per esporre la porta `9999`
- *(opzionale)* **Ollama** in ascolto su `11434` per LLM locali
- Lato client: Python con `requests` per inviare i comandi

---

## Installazione

### 1. Addon Blender

1. Comprimi la cartella `manus_bridge/` in uno zip (deve contenere `__init__.py` al suo interno).
2. In Blender: **Edit → Preferences → Add-ons → Install…** e seleziona lo zip.
3. Abilita **ManusBridge** dalla lista.
4. Nella vista 3D apri la N-sidebar (tasto `N`) → scheda **Manus** → **Avvia ManusBridge**.

Lo stato passa a *Connesso (Porta 9999)*.

### 2. Tunnel ngrok

```bash
ngrok http 9999
```

Copia l'URL pubblico (es. `https://xxxx.ngrok-free.app`) e passalo a Manus.

### 3. Skill (lato Manus)

Carica `blender-manager.skill` tra le skill di Manus. Indica nelle istruzioni di progetto l'URL del tunnel.

---

## Utilizzo

Esempio di invio comando dal client:

```python
import requests

def send_command(url, command):
    headers = {"ngrok-skip-browser-warning": "true"}
    payload = {"command": command}
    return requests.post(url, json=payload, headers=headers).json()

send_command(
    "https://xxxx.ngrok-free.app",
    "bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))"
)
```

### Endpoint

| Metodo | Path | Descrizione |
|--------|------|-------------|
| `GET`  | `/`  | Health check — risponde `ManusBridge is active!` |
| `POST` | `/`  | Esegue il comando nel campo JSON `command`. Risposta: `{"status": "success"\|"error", "message": "..."}` |

Gli errori Python nei comandi vengono **catturati e restituiti** nella risposta HTTP (status `error`), non fanno più crashare Blender.

---

## Sicurezza

Questo strumento è pensato per **uso locale/personale e ambienti fidati**. Rischi e mitigazioni:

- **Esecuzione di codice arbitrario**: l'endpoint `POST` fa `exec()` del comando ricevuto. Non esiste autenticazione.
- **Esposizione pubblica**: con ngrok l'URL è raggiungibile da Internet. Usa la funzione di autenticazione di ngrok (es. `ngrok http 9999 --basic-auth user:pass`) o un IP allow-list.
- **Non esporre mai questo server su una macchina con dati sensibili** senza un layer di autenticazione davanti.
- Spegni il tunnel quando non ti serve.

---

## Troubleshooting

| Problema | Soluzione |
|----------|-----------|
| **Connection Refused** | Verifica di aver premuto *Avvia ManusBridge* nel pannello Manus. |
| **Timeout** | Controlla che ngrok sia attivo e l'URL sia quello corrente (cambia a ogni riavvio nel piano free). |
| **Blender crasha durante i comandi** | Assicurati di usare la v1.1+ dell'addon (esecuzione nel main thread). Verifica in console: `import manus_bridge; print(hasattr(manus_bridge, '_process_command_queue'))` deve dare `True`. |
| **`register_class già registrato` al disabilitare l'addon** | Bug presente fino alla v1.0; risolto in v1.1. Chiudi e riapri Blender, poi reinstalla. |

---

## Changelog

### v1.1
- **Fix crash critico**: i comandi `bpy.*` ora vengono eseguiti nel main thread tramite `bpy.app.timers` + coda, invece che nel thread del server HTTP (causa di `EXCEPTION_ACCESS_VIOLATION` nel depsgraph).
- **Fix `unregister()`**: chiamava erroneamente `register_class` invece di `unregister_class`, impedendo di disabilitare/riabilitare l'addon pulito.
- Deregistrazione corretta del timer in `unregister()`.
- Soppressi i log HTTP nella console di Blender.
- Aggiunto timeout di 30s lato server per evitare client appesi.

### v1.0
- Versione iniziale (Manus AI).

---

## Licenza

Specifica una licenza prima di pubblicare (es. MIT). Crea un file `LICENSE` nella root.
