# SALES AI — MVP de prospection B2B

Une première application locale pour gérer des prospects, les qualifier, préparer des messages personnalisés et suivre les campagnes.

## Ce que fait cette version
- Tableau de bord et indicateurs
- Base prospects SQLite
- Ajout manuel et import CSV
- Score indicatif de qualification
- Génération de brouillons avec OpenAI si une clé API est configurée
- Modèles de messages sans clé API
- Historique et suivi manuel
- Aucun envoi automatique d'emails

## Installation sur Mac

1. Installe Python 3.10 ou plus récent si nécessaire.
2. Décompresse le dossier SALES_AI.
3. Ouvre Terminal dans le dossier SALES_AI.
4. Exécute :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

L'application s'ouvrira dans ton navigateur. Elle tourne localement sur ton Mac.

## Activer la génération IA
- Crée une clé API OpenAI depuis ton compte développeur.
- Ajoute-la dans le fichier `.env` après `OPENAI_API_KEY=`.
- Ne partage jamais cette clé et ne la mets pas dans un fichier public.
- Vérifie les tarifs API avant utilisation : l'abonnement ChatGPT ne comprend pas automatiquement les crédits API.

## Import CSV
Colonnes attendues :
`company,website,sector,city,contact_name,email,source,need`

Un modèle `prospects_exemple.csv` est fourni.

## Limites et prochaine étape
Cette version est un MVP : elle ne recherche pas encore des entreprises sur Internet, ne vérifie pas les adresses email et n'envoie pas de messages. Il faut ajouter des sources de données autorisées, une validation de conformité, puis connecter une messagerie avec confirmation explicite avant les envois.
