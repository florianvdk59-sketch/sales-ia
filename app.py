
import os, sqlite3, csv, io
from datetime import datetime, date, timedelta
import streamlit as st


load_dotenv()
DB_PATH = os.getenv("SALES_AI_DB", "sales_ai.db")

st.set_page_config(page_title="SALES AI", page_icon="🎯", layout="wide")

def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("""
    CREATE TABLE IF NOT EXISTS prospects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company TEXT NOT NULL,
        website TEXT DEFAULT '',
        sector TEXT DEFAULT '',
        city TEXT DEFAULT '',
        contact_name TEXT DEFAULT '',
        email TEXT DEFAULT '',
        source TEXT DEFAULT '',
        need TEXT DEFAULT '',
        score INTEGER DEFAULT 0,
        status TEXT DEFAULT 'À qualifier',
        last_contact TEXT DEFAULT '',
        next_action TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )""")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prospect_id INTEGER,
        activity_type TEXT NOT NULL,
        content TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )""")
    conn.commit()
    return conn

conn = db()

def add_activity(pid, typ, content=""):
    conn.execute("INSERT INTO activities(prospect_id,activity_type,content,created_at) VALUES(?,?,?,?)",
                 (pid, typ, content, datetime.now().isoformat(timespec="minutes")))
    conn.commit()

def score_prospect(row):
    score = 0
    if row.get("website"): score += 10
    if row.get("email"): score += 15
    if row.get("contact_name"): score += 10
    if row.get("sector"): score += 10
    if row.get("need"): score += 25
    if row.get("city"): score += 5
    need = (row.get("need") or "").lower()
    triggers = ["recrute", "nouveau", "développement", "commercial", "prospect", "croissance", "client", "devis"]
    score += min(25, sum(5 for x in triggers if x in need))
    return min(100, score)

def generate_copy(prospect, offer, tone):
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            prompt = f"""Tu es un assistant commercial B2B français. Rédige un premier email de prospection personnalisé,
court (80 à 120 mots), honnête et sans promesse garantie.
Entreprise prospectée : {prospect['company']}
Secteur : {prospect['sector']}
Ville : {prospect['city']}
Site : {prospect['website']}
Besoin/élément connu : {prospect['need']}
Offre SALES AI : {offer}
Ton : {tone}
Ne prétends pas avoir analysé des informations qui ne sont pas fournies. Termine par une question simple.
Ajoute un objet. Mentionne clairement l'identité de l'expéditeur à compléter et une possibilité simple de ne plus être contacté."""
            response = client.responses.create(model=os.getenv("OPENAI_MODEL", "gpt-5-mini"), input=prompt)
            return response.output_text
        except Exception as e:
            return f"Erreur IA : {e}\n\n" + fallback_copy(prospect, offer)
    return fallback_copy(prospect, offer)

def fallback_copy(p, offer):
    return f"""Objet : Une piste pour développer {p['company']}

Bonjour,

Je me permets de vous contacter car {p['company']} évolue dans le secteur {p['sector'] or 'des services'}.
Chez SALES AI, nous aidons les entreprises à structurer leur prospection et à identifier de nouvelles opportunités commerciales grâce à des outils assistés par IA.

Notre approche : ciblage pertinent, messages personnalisés et suivi des échanges, avec validation humaine avant envoi.

Est-ce un sujet que vous cherchez à développer actuellement ?

Bien cordialement,
[Prénom / SALES AI]
[Coordonnées]

Si vous ne souhaitez plus recevoir de message de notre part, dites-le-moi simplement et nous ne vous recontacterons pas."""

st.title("🎯 SALES AI")
st.caption("Espace de pilotage de la prospection B2B — version MVP")

with st.sidebar:
    st.header("Configuration")
    st.write("Offre commerciale")
    offer = st.text_area("Votre offre", value="Nous aidons les entreprises à générer des opportunités commerciales grâce à une prospection B2B ciblée, personnalisée et suivie.", height=110)
    tone = st.selectbox("Ton des messages", ["Professionnel et direct", "Chaleureux et humain", "Court et premium"])
    st.divider()
    st.caption("IA connectée" if os.getenv("OPENAI_API_KEY") else "Mode sans clé IA : modèles de messages intégrés")
    st.caption("Aucun email n'est envoyé automatiquement dans cette version.")

tabs = st.tabs(["Vue d'ensemble", "Prospects", "Ajouter / importer", "Campagnes & messages", "Conformité"])

with tabs[0]:
    rows = conn.execute("SELECT * FROM prospects").fetchall()
    total = len(rows)
    qualified = sum(1 for r in rows if r["score"] >= 50)
    contacted = sum(1 for r in rows if r["status"] in ("Contacté", "Réponse reçue", "Rendez-vous", "Client"))
    meetings = sum(1 for r in rows if r["status"] == "Rendez-vous")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Prospects", total)
    c2.metric("Prospects qualifiés", qualified)
    c3.metric("Contactés", contacted)
    c4.metric("Rendez-vous", meetings)
    st.subheader("Derniers prospects")
    if rows:
        st.dataframe([dict(r) for r in rows[-10:]], use_container_width=True, hide_index=True)
    else:
        st.info("Ajoutez vos premiers prospects ou importez un fichier CSV pour commencer.")

with tabs[1]:
    rows = conn.execute("SELECT * FROM prospects ORDER BY score DESC, created_at DESC").fetchall()
    if rows:
        search = st.text_input("Rechercher une entreprise")
        status_filter = st.multiselect("Filtrer par statut", ["À qualifier","Qualifié","À valider","Contacté","Réponse reçue","Rendez-vous","Client","Non intéressé","Ne plus contacter"])
        filtered = [dict(r) for r in rows if (search.lower() in r["company"].lower() if search else True) and (not status_filter or r["status"] in status_filter)]
        st.dataframe(filtered, use_container_width=True, hide_index=True)
        names = {f"{r['company']} — #{r['id']}": r for r in rows}
        selected = st.selectbox("Ouvrir un prospect", list(names.keys()))
        p = names[selected]
        with st.form("edit_prospect"):
            a,b,c = st.columns(3)
            company = a.text_input("Entreprise", p["company"])
            sector = b.text_input("Secteur", p["sector"])
            city = c.text_input("Ville", p["city"])
            website = a.text_input("Site web", p["website"])
            email = b.text_input("Email professionnel", p["email"])
            contact_name = c.text_input("Contact", p["contact_name"])
            need = st.text_area("Besoin / signal observé (source à noter)", p["need"])
            status = st.selectbox("Statut", ["À qualifier","Qualifié","À valider","Contacté","Réponse reçue","Rendez-vous","Client","Non intéressé","Ne plus contacter"], index=["À qualifier","Qualifié","À valider","Contacté","Réponse reçue","Rendez-vous","Client","Non intéressé","Ne plus contacter"].index(p["status"]))
            notes = st.text_area("Notes", p["notes"])
            save = st.form_submit_button("Enregistrer les modifications")
        if save:
            score = score_prospect({"website":website,"email":email,"contact_name":contact_name,"sector":sector,"city":city,"need":need})
            conn.execute("""UPDATE prospects SET company=?,sector=?,city=?,website=?,email=?,contact_name=?,need=?,status=?,notes=?,score=? WHERE id=?""",
                         (company,sector,city,website,email,contact_name,need,status,notes,score,p["id"]))
            conn.commit()
            st.success("Prospect mis à jour.")
            st.rerun()
        if st.button("Enregistrer une relance / interaction"):
            add_activity(p["id"], "Suivi", "Interaction enregistrée manuellement")
            conn.execute("UPDATE prospects SET last_contact=? WHERE id=?", (date.today().isoformat(), p["id"]))
            conn.commit()
            st.success("Suivi enregistré.")
    else:
        st.info("Aucun prospect pour le moment.")

with tabs[2]:
    st.subheader("Ajouter un prospect")
    with st.form("new_prospect"):
        a,b = st.columns(2)
        company = a.text_input("Nom de l'entreprise *")
        sector = b.text_input("Secteur")
        website = a.text_input("Site web")
        city = b.text_input("Ville")
        contact_name = a.text_input("Nom du contact")
        email = b.text_input("Email professionnel")
        need = st.text_area("Besoin ou signal commercial observé")
        source = st.text_input("Source de l'information (URL, annuaire, recommandation...)")
        submitted = st.form_submit_button("Ajouter le prospect")
    if submitted:
        if not company.strip():
            st.error("Le nom de l'entreprise est obligatoire.")
        else:
            data = {"website":website,"email":email,"contact_name":contact_name,"sector":sector,"city":city,"need":need}
            score = score_prospect(data)
            cur = conn.execute("""INSERT INTO prospects(company,website,sector,city,contact_name,email,source,need,score,created_at)
                               VALUES(?,?,?,?,?,?,?,?,?,?)""",
                               (company,website,sector,city,contact_name,email,source,need,score,datetime.now().isoformat(timespec="minutes")))
            conn.commit()
            add_activity(cur.lastrowid, "Création", "Prospect ajouté")
            st.success(f"Prospect ajouté — score indicatif : {score}/100")
    st.divider()
    st.subheader("Importer un CSV")
    st.write("Colonnes acceptées : company, website, sector, city, contact_name, email, source, need")
    upload = st.file_uploader("Choisir un fichier CSV", type=["csv"])
    if upload and st.button("Importer les entreprises"):
        content = upload.getvalue().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content))
        count = 0
        for r in reader:
            company = (r.get("company") or "").strip()
            if not company: continue
            score = score_prospect(r)
            conn.execute("""INSERT INTO prospects(company,website,sector,city,contact_name,email,source,need,score,created_at)
                          VALUES(?,?,?,?,?,?,?,?,?,?)""",
                         (company,r.get("website",""),r.get("sector",""),r.get("city",""),r.get("contact_name",""),r.get("email",""),r.get("source",""),r.get("need",""),score,datetime.now().isoformat(timespec="minutes")))
            count += 1
        conn.commit()
        st.success(f"{count} prospect(s) importé(s).")

with tabs[3]:
    rows = conn.execute("SELECT * FROM prospects WHERE status != 'Ne plus contacter' ORDER BY score DESC").fetchall()
    if rows:
        opts = {f"{r['company']} — score {r['score']}/100": dict(r) for r in rows}
        selected = st.selectbox("Choisir un prospect pour préparer un message", list(opts.keys()))
        p = opts[selected]
        st.write(f"**Entreprise :** {p['company']}  |  **Secteur :** {p['sector'] or 'Non renseigné'}  |  **Email :** {p['email'] or 'Non renseigné'}")
        if st.button("Générer un message personnalisé"):
            st.session_state["draft"] = generate_copy(p, offer, tone)
            st.session_state["draft_pid"] = p["id"]
        draft = st.text_area("Brouillon à vérifier avant envoi", value=st.session_state.get("draft",""), height=300)
        if draft and st.button("Enregistrer comme brouillon validé"):
            add_activity(p["id"], "Brouillon préparé", draft)
            conn.execute("UPDATE prospects SET status='À valider' WHERE id=?", (p["id"],))
            conn.commit()
            st.success("Brouillon enregistré dans l'historique. Copiez-le dans votre messagerie après vérification.")
        if st.button("Marquer comme contacté (après envoi réel)"):
            conn.execute("UPDATE prospects SET status='Contacté', last_contact=? WHERE id=?", (date.today().isoformat(), p["id"]))
            conn.commit()
            add_activity(p["id"], "Contacté", "Marqué comme contacté après envoi manuel")
            st.success("Statut mis à jour.")
    else:
        st.info("Ajoutez d'abord des prospects.")

with tabs[4]:
    st.subheader("Prospection responsable")
    st.markdown("""
- Ciblez des contacts professionnels pertinents et en lien avec votre offre.
- Utilisez des données obtenues légalement et conservez la source de chaque contact.
- Identifiez clairement l'expéditeur et l'objet commercial du message.
- Donnez un moyen simple de s'opposer aux sollicitations et respectez immédiatement toute opposition.
- N'utilisez jamais de listes achetées ou aspirées sans vérifier leur origine, les droits d'utilisation et les règles applicables.
- En France/UE, vérifiez les exigences RGPD et les règles de prospection électronique B2B avant toute campagne.
- Cette version ne collecte pas automatiquement des données sur le web et n'envoie aucun email. Chaque message doit être vérifié et envoyé manuellement.
""")
    st.caption("Conseil : faites valider votre processus de prospection et vos mentions de confidentialité avant une campagne à grande échelle.")

st.divider()
st.caption("SALES AI MVP • Les scores sont indicatifs et doivent être vérifiés par un humain.")
