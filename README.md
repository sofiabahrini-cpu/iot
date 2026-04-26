# ⚡ IoT Energy Dashboard — ESP32 + Flask + Streamlit

Dashboard de surveillance énergétique et environnementale pour ESP32 (BME280 + INA219).

## Architecture

```
ESP32 ──HTTP POST──► Flask server.py ──► SQLite (iot_data.db) ──► Streamlit app.py
```

## Installation

```bash
pip install -r requirements.txt
```

## Lancement (en local)

### 1. Démarrer le serveur Flask (reçoit l'ESP32)

```bash
python server.py
```

Le serveur écoute sur `http://0.0.0.0:5000`.  
L'ESP32 le trouve automatiquement via mDNS (`mon-pc-iot.local`).

### 2. Lancer le dashboard Streamlit

```bash
streamlit run app.py
```

Ouvre `http://localhost:8501` dans ton navigateur.

## Configuration ESP32

Dans le code Arduino, assure-toi que :
- `serverHostname` correspond au nom mDNS de ton PC
- `securityKey` correspond à `SECURITY_KEY` dans `server.py` (défaut: `"123456"`)

Pour activer mDNS sur ton PC :
- **Windows** : installe [Bonjour](https://support.apple.com/downloads/bonjour)
- **Linux** : `sudo apt install avahi-daemon`
- **macOS** : natif, rien à faire

## Déploiement Streamlit Cloud (optionnel)

Pour un dashboard accessible depuis internet, remplace SQLite par [Supabase](https://supabase.com) (gratuit) :

1. Crée un projet Supabase → récupère l'URL et la clé API
2. Dans `server.py`, remplace les appels SQLite par `supabase-py`
3. Dans `app.py`, lis depuis Supabase avec `st.secrets`
4. Pousse sur GitHub → connecte sur [share.streamlit.io](https://share.streamlit.io)

## Fonctionnalités du dashboard

- Métriques temps réel : Température, Humidité, Tension, Courant, Batterie %
- Jauges animées avec seuils visuels
- Graphes historiques (fenêtre configurable de 1h à 7 jours)
- Courbe de santé batterie avec seuil critique à 20%
- Statistiques (min/max/moyenne)
- Export CSV
- Auto-refresh toutes les 10 secondes
- Indicateur en ligne / hors ligne basé sur l'âge de la dernière mesure

## Structure des fichiers

```
iot-dashboard/
├── server.py          ← Serveur Flask (port 5000)
├── app.py             ← Dashboard Streamlit
├── requirements.txt
├── README.md
└── iot_data.db        ← Créé automatiquement au premier démarrage
```
