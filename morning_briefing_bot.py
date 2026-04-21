#!/usr/bin/env python3
"""
Morning Briefing Bot — version enrichie
Sections : Marchés, Monde, FMCG, Tech/IA, Outil, Impression 3D,
           Activité enfants, Podcast, Vidéo YouTube, Article, Citation
Envoi : Telegram + Email Gmail
"""

import os
import json
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "6327266038")
GMAIL_USER         = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
EMAIL_TO           = os.environ.get("EMAIL_TO", "")
TELEGRAM_LIMIT     = 4000

# ─────────────────────────────────────────────
# PROMPT CLAUDE
# ─────────────────────────────────────────────

PROMPT_TEMPLATE = """Tu es un assistant de veille quotidienne pour un père de famille français actif et curieux.
Il s'intéresse aux marchés financiers, à la tech, au FMCG/retail, à l'impression 3D, et cherche des idées d'activités avec ses enfants.
Date du jour : {today}

Réponds UNIQUEMENT avec un objet JSON brut valide. Pas de texte avant, pas de texte après, pas de backticks.
Commence par {{ et termine par }}.

Pour chaque item avec un champ "url", fournis un vrai lien URL complet et fonctionnel (commence par https://).
Si tu n'as pas de lien certain, utilise null.

Structure JSON exacte :

{{
  "headline": "phrase de 10 mots max résumant le thème dominant du jour",

  "markets": [
    {{"s":"BTC",    "p":"$84000", "c": 1.2,  "note":"observation 5 mots"}},
    {{"s":"ETH",    "p":"$1600",  "c":-0.8,  "note":"observation 5 mots"}},
    {{"s":"CAC40",  "p":"7800",   "c": 0.4,  "note":"observation 5 mots"}},
    {{"s":"SP500",  "p":"5200",   "c": 0.5,  "note":"observation 5 mots"}},
    {{"s":"Or",     "p":"$2300",  "c": 0.2,  "note":"observation 5 mots"}},
    {{"s":"EUR/USD","p":"1.082",  "c":-0.1,  "note":"observation 5 mots"}}
  ],

  "macro_signal": {{
    "title": "Signal macro du jour en 6 mots",
    "summary": "Une phrase expliquant l'impact pour un investisseur.",
    "url": null
  }},

  "news": [
    {{
      "cat": "monde",
      "title": "titre 5-6 mots",
      "src": "Reuters",
      "summary": "Une phrase. Pourquoi c'est important.",
      "url": "https://..."
    }},
    {{
      "cat": "fmcg",
      "title": "titre 5-6 mots",
      "src": "LSA",
      "summary": "Une phrase sur l'innovation ou tendance consommation.",
      "url": "https://..."
    }},
    {{
      "cat": "tech",
      "title": "titre 5-6 mots",
      "src": "TechCrunch",
      "summary": "Une phrase sur la nouveauté tech ou IA.",
      "url": "https://..."
    }}
  ],

  "outil_du_jour": {{
    "name": "Nom de l'outil",
    "category": "IA | productivité | design | no-code | autre",
    "description": "Une phrase : ce que ça fait et pourquoi c'est utile.",
    "url": "https://..."
  }},

  "impression_3d": {{
    "title": "Nom du modèle ou projet",
    "description": "Une phrase : ce que c'est, difficulté, durée estimée.",
    "url": "https://www.printables.com/..."
  }},

  "activite_enfant": {{
    "title": "Nom de l'activité",
    "age": "ex: 4-10 ans",
    "duree": "ex: 1h",
    "description": "Une phrase : ce qu'on fait et pourquoi c'est bien.",
    "url": "https://..."
  }},

  "podcast": {{
    "name": "Nom du podcast",
    "episode": "Titre de l'épisode",
    "duration": "45 min",
    "description": "Une phrase : de quoi ça parle.",
    "url": "https://open.spotify.com/... ou https://podcasts.apple.com/..."
  }},

  "video": {{
    "title": "Titre de la vidéo",
    "channel": "Nom de la chaîne",
    "duration": "12 min",
    "description": "Une phrase : pourquoi regarder ça aujourd'hui.",
    "url": "https://www.youtube.com/watch?v=..."
  }},

  "article": {{
    "title": "Titre de l'article de fond",
    "src": "The Economist",
    "read_time": "8 min",
    "summary": "Deux phrases : de quoi ça parle et pourquoi le lire.",
    "url": "https://..."
  }},

  "quote": "Citation courte et percutante pour bien démarrer la journée."
}}"""


# ─────────────────────────────────────────────
# GÉNÉRATION VIA CLAUDE
# ─────────────────────────────────────────────

def extract_json(text):
    text = text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start != -1 and end > 0:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    decoder = json.JSONDecoder()
    for i in range(len(text)):
        if text[i] == "{":
            try:
                obj, _ = decoder.raw_decode(text, i)
                return obj
            except json.JSONDecodeError:
                continue
    raise ValueError("Aucun JSON valide. Reponse : " + text[:400])


def generate_briefing():
    today  = datetime.now().strftime("%A %d %B %Y")
    prompt = PROMPT_TEMPLATE.format(today=today)

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key":         ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        },
        json={
            "model":      "claude-sonnet-4-6",
            "max_tokens": 2000,
            "messages":   [{"role": "user", "content": prompt}],
        },
        timeout=90,
    )

    if resp.status_code != 200:
        print("Erreur API " + str(resp.status_code) + " : " + resp.text[:300])
        resp.raise_for_status()

    raw = ""
    for block in resp.json().get("content", []):
        if block.get("type") == "text":
            raw += block["text"]

    print("Reponse Claude : " + str(len(raw)) + " chars")
    return extract_json(raw)


# ─────────────────────────────────────────────
# FORMATAGE TELEGRAM
# ─────────────────────────────────────────────

CAT_EMOJI = {
    "monde":      "🌍",
    "fmcg":       "🛒",
    "tech":       "🔵",
    "crypto":     "🟡",
    "macro":      "🟢",
    "regulation": "🔴",
}

def esc(v):
    s = str(v) if v else ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def link(label, url):
    if url and url != "null" and str(url).startswith("http"):
        return ' <a href="' + esc(url) + '">' + label + '</a>'
    return ""

def build_telegram_parts(b):
    """Retourne une liste de messages Telegram (découpés par section)."""
    today = datetime.now().strftime("%d/%m/%Y")
    parts = []

    # ── PARTIE 1 : En-tête + Marchés + Macro ──
    L = []
    L.append("☀️ <b>MORNING BRIEFING — " + today + "</b>")
    if b.get("headline"):
        L.append("<i>" + esc(b["headline"]) + "</i>")
    L.append("")

    markets = b.get("markets", [])
    if markets:
        L.append("📊 <b>MARCHÉS</b>")
        for m in markets:
            c    = float(m.get("c", 0))
            arr  = "▲" if c >= 0 else "▼"
            sign = "+" if c >= 0 else ""
            note = "  <i>" + esc(m["note"]) + "</i>" if m.get("note") else ""
            L.append("<code>" + esc(m.get("s","")).ljust(7) + "</code> " + esc(m.get("p","")) + "  " + arr + " " + sign + str(c) + "%" + note)
        L.append("")

    macro = b.get("macro_signal")
    if macro:
        L.append("📡 <b>SIGNAL MACRO</b>")
        L.append("<b>" + esc(macro.get("title","")) + "</b>")
        L.append(esc(macro.get("summary","")) + link("En savoir plus", macro.get("url")))
        L.append("")

    parts.append("\n".join(L))

    # ── PARTIE 2 : News ──
    L = []
    news = b.get("news", [])
    if news:
        L.append("📰 <b>ACTUALITÉS</b>")
        for n in news:
            e = CAT_EMOJI.get(n.get("cat",""), "⚪")
            L.append(e + " <b>" + esc(n.get("title","")) + "</b> — <i>" + esc(n.get("src","")) + "</i>")
            L.append(esc(n.get("summary","")) + link("Lire →", n.get("url")))
            L.append("")
    parts.append("\n".join(L))

    # ── PARTIE 3 : Outil + Impression 3D + Activité enfant ──
    L = []
    outil = b.get("outil_du_jour")
    if outil:
        L.append("🛠 <b>OUTIL DU JOUR</b>")
        L.append("<b>" + esc(outil.get("name","")) + "</b> — <i>" + esc(outil.get("category","")) + "</i>")
        L.append(esc(outil.get("description","")) + link("Essayer →", outil.get("url")))
        L.append("")

    p3d = b.get("impression_3d")
    if p3d:
        L.append("🖨 <b>IMPRESSION 3D</b>")
        L.append("<b>" + esc(p3d.get("title","")) + "</b>")
        L.append(esc(p3d.get("description","")) + link("Télécharger →", p3d.get("url")))
        L.append("")

    act = b.get("activite_enfant")
    if act:
        L.append("👨‍👧 <b>ACTIVITÉ ENFANTS</b>")
        age  = " (" + esc(act.get("age","")) + ")" if act.get("age") else ""
        dur  = " · " + esc(act.get("duree","")) if act.get("duree") else ""
        L.append("<b>" + esc(act.get("title","")) + "</b>" + age + dur)
        L.append(esc(act.get("description","")) + link("Voir →", act.get("url")))
        L.append("")

    parts.append("\n".join(L))

    # ── PARTIE 4 : Podcast + Vidéo + Article + Citation ──
    L = []
    pod = b.get("podcast")
    if pod:
        L.append("🎙 <b>PODCAST</b>")
        dur = " (" + esc(pod.get("duration","")) + ")" if pod.get("duration") else ""
        L.append("<b>" + esc(pod.get("name","")) + "</b>" + dur)
        L.append("<i>" + esc(pod.get("episode","")) + "</i>")
        L.append(esc(pod.get("description","")) + link("Écouter →", pod.get("url")))
        L.append("")

    vid = b.get("video")
    if vid:
        L.append("▶️ <b>VIDÉO</b>")
        dur = " (" + esc(vid.get("duration","")) + ")" if vid.get("duration") else ""
        L.append("<b>" + esc(vid.get("title","")) + "</b> — <i>" + esc(vid.get("channel","")) + "</i>" + dur)
        L.append(esc(vid.get("description","")) + link("Regarder →", vid.get("url")))
        L.append("")

    art = b.get("article")
    if art:
        L.append("📖 <b>ARTICLE DU JOUR</b>")
        rt = " · " + esc(art.get("read_time","")) if art.get("read_time") else ""
        L.append("<b>" + esc(art.get("title","")) + "</b> — <i>" + esc(art.get("src","")) + "</i>" + rt)
        L.append(esc(art.get("summary","")) + link("Lire →", art.get("url")))
        L.append("")

    if b.get("quote"):
        L.append("💬 <i>" + esc(b["quote"]) + "</i>")
    L.append("")
    L.append("<i>Morning Briefing Bot</i>")

    parts.append("\n".join(L))
    return [p for p in parts if p.strip()]


# ─────────────────────────────────────────────
# FORMATAGE EMAIL HTML
# ─────────────────────────────────────────────

def build_email_html(b):
    today = datetime.now().strftime("%d %B %Y")

    def row(label, value, url=None):
        link_html = ""
        if url and str(url).startswith("http"):
            link_html = ' <a href="' + esc(url) + '" style="color:#3b82f6;font-size:12px;margin-left:8px;">Voir →</a>'
        return ('<tr><td style="color:#999;font-size:12px;padding:6px 0 6px 0;width:110px;vertical-align:top">'
                + label + '</td><td style="font-size:13px;padding:6px 0;color:#1a1a1a">'
                + esc(value) + link_html + '</td></tr>')

    def section(icon, title, content_html):
        return ('<div style="margin:0 0 24px">'
                '<div style="font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#999;'
                'border-bottom:1px solid #eee;padding-bottom:6px;margin-bottom:12px">'
                + icon + ' ' + title + '</div>'
                + content_html + '</div>')

    def news_card(n):
        cat_colors = {"monde":"#3b82f6","fmcg":"#10b981","tech":"#8b5cf6","crypto":"#f59e0b","regulation":"#ef4444"}
        color = cat_colors.get(n.get("cat",""), "#9ca3af")
        url   = n.get("url","")
        lnk   = ('<a href="' + esc(url) + '" style="color:#3b82f6;font-size:12px;text-decoration:none">Lire l\'article →</a>'
                 if url and str(url).startswith("http") else "")
        return ('<div style="border-left:3px solid ' + color + ';padding:8px 12px;margin-bottom:12px;background:#fafafa;border-radius:0 6px 6px 0">'
                '<div style="font-weight:bold;font-size:14px;color:#1a1a1a">' + esc(n.get("title","")) + '</div>'
                '<div style="font-size:11px;color:#999;margin:2px 0">' + esc(n.get("src","")) + '</div>'
                '<div style="font-size:13px;color:#444;line-height:1.5">' + esc(n.get("summary","")) + '</div>'
                + ('<div style="margin-top:6px">' + lnk + '</div>' if lnk else '') +
                '</div>')

    def btn(label, url):
        if not url or not str(url).startswith("http"):
            return ""
        return ('<a href="' + esc(url) + '" style="display:inline-block;margin-top:8px;padding:6px 14px;'
                'background:#1a1a1a;color:#fff;font-size:12px;text-decoration:none;border-radius:4px">'
                + label + '</a>')

    # ── CONSTRUCTION HTML ──
    html = ('<!DOCTYPE html><html><head><meta charset="utf-8"></head>'
            '<body style="background:#f3f4f6;font-family:Georgia,serif;margin:0;padding:20px">'
            '<div style="max-width:620px;margin:0 auto;background:#fff;border-radius:10px;padding:32px">')

    html += ('<h1 style="font-size:24px;margin:0 0 4px">☀️ Morning Briefing</h1>'
             '<div style="color:#999;font-size:13px;margin-bottom:24px">' + today + '</div>')
    if b.get("headline"):
        html += '<p style="font-style:italic;color:#555;margin-bottom:24px">' + esc(b["headline"]) + '</p>'

    # Marchés
    markets = b.get("markets", [])
    if markets:
        grid = '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:8px">'
        for m in markets:
            c    = float(m.get("c", 0))
            col  = "#16a34a" if c >= 0 else "#dc2626"
            sign = "+" if c >= 0 else ""
            grid += ('<div style="background:#f9f9f7;border-radius:6px;padding:10px;text-align:center">'
                     '<div style="font-size:11px;color:#999">' + esc(m.get("s","")) + '</div>'
                     '<div style="font-size:14px;font-weight:bold">' + esc(m.get("p","")) + '</div>'
                     '<div style="font-size:12px;color:' + col + '">' + sign + str(c) + '%</div>'
                     + ('<div style="font-size:10px;color:#bbb;margin-top:2px">' + esc(m.get("note","")) + '</div>' if m.get("note") else '') +
                     '</div>')
        grid += '</div>'
        html += section("📊", "Marchés", grid)

    # Macro
    macro = b.get("macro_signal")
    if macro:
        mc = ('<p style="font-size:14px;margin:0;color:#444">'
              '<b>' + esc(macro.get("title","")) + '</b><br>'
              + esc(macro.get("summary","")) + '</p>'
              + btn("En savoir plus", macro.get("url")))
        html += section("📡", "Signal Macro", mc)

    # News
    news = b.get("news", [])
    if news:
        nc = "".join(news_card(n) for n in news)
        html += section("📰", "Actualités", nc)

    # Outil
    outil = b.get("outil_du_jour")
    if outil:
        oc = ('<p style="margin:0;font-size:14px"><b>' + esc(outil.get("name","")) + '</b>'
              + (' <span style="color:#999;font-size:12px">— ' + esc(outil.get("category","")) + '</span>' if outil.get("category") else '') + '</p>'
              '<p style="font-size:13px;color:#444;margin:6px 0">' + esc(outil.get("description","")) + '</p>'
              + btn("Essayer →", outil.get("url")))
        html += section("🛠", "Outil du jour", oc)

    # Impression 3D
    p3d = b.get("impression_3d")
    if p3d:
        pc = ('<p style="margin:0;font-size:14px"><b>' + esc(p3d.get("title","")) + '</b></p>'
              '<p style="font-size:13px;color:#444;margin:6px 0">' + esc(p3d.get("description","")) + '</p>'
              + btn("Télécharger le modèle →", p3d.get("url")))
        html += section("🖨", "Impression 3D", pc)

    # Activité enfant
    act = b.get("activite_enfant")
    if act:
        meta = ""
        if act.get("age"):
            meta += '<span style="background:#fef9c3;color:#854d0e;font-size:11px;padding:2px 8px;border-radius:10px;margin-right:6px">' + esc(act["age"]) + '</span>'
        if act.get("duree"):
            meta += '<span style="background:#e0f2fe;color:#0369a1;font-size:11px;padding:2px 8px;border-radius:10px">' + esc(act["duree"]) + '</span>'
        ac = (('<div style="margin-bottom:8px">' + meta + '</div>' if meta else '') +
              '<p style="margin:0;font-size:14px"><b>' + esc(act.get("title","")) + '</b></p>'
              '<p style="font-size:13px;color:#444;margin:6px 0">' + esc(act.get("description","")) + '</p>'
              + btn("Voir l\'activité →", act.get("url")))
        html += section("👨‍👧", "Activité avec tes enfants", ac)

    # Podcast
    pod = b.get("podcast")
    if pod:
        pc = ('<p style="margin:0;font-size:14px"><b>' + esc(pod.get("name","")) + '</b>'
              + (' <span style="color:#999;font-size:12px">(' + esc(pod.get("duration","")) + ')</span>' if pod.get("duration") else '') + '</p>'
              '<p style="font-style:italic;font-size:13px;color:#555;margin:4px 0">' + esc(pod.get("episode","")) + '</p>'
              '<p style="font-size:13px;color:#444;margin:4px 0">' + esc(pod.get("description","")) + '</p>'
              + btn("🎧 Écouter →", pod.get("url")))
        html += section("🎙", "Podcast", pc)

    # Vidéo
    vid = b.get("video")
    if vid:
        vc = ('<p style="margin:0;font-size:14px"><b>' + esc(vid.get("title","")) + '</b>'
              + (' <span style="color:#999;font-size:12px">(' + esc(vid.get("duration","")) + ')</span>' if vid.get("duration") else '') + '</p>'
              '<p style="font-size:12px;color:#999;margin:3px 0">' + esc(vid.get("channel","")) + '</p>'
              '<p style="font-size:13px;color:#444;margin:6px 0">' + esc(vid.get("description","")) + '</p>'
              + btn("▶️ Regarder →", vid.get("url")))
        html += section("▶️", "Vidéo YouTube", vc)

    # Article
    art = b.get("article")
    if art:
        ac = ('<p style="margin:0;font-size:14px"><b>' + esc(art.get("title","")) + '</b>'
              + (' <span style="color:#999;font-size:12px">· ' + esc(art.get("read_time","")) + '</span>' if art.get("read_time") else '') + '</p>'
              '<p style="font-size:12px;color:#999;margin:3px 0">' + esc(art.get("src","")) + '</p>'
              '<p style="font-size:13px;color:#444;line-height:1.5;margin:6px 0">' + esc(art.get("summary","")) + '</p>'
              + btn("📖 Lire l\'article →", art.get("url")))
        html += section("📖", "Article du jour", ac)

    # Citation
    if b.get("quote"):
        html += ('<div style="border-left:3px solid #e5e7eb;padding:8px 16px;margin:16px 0">'
                 '<p style="font-style:italic;color:#666;margin:0;font-size:15px">' + esc(b["quote"]) + '</p>'
                 '</div>')

    html += ('<div style="text-align:center;font-size:11px;color:#d1d5db;margin-top:24px;padding-top:16px;border-top:1px solid #f3f4f6">'
             'Morning Briefing Bot — généré automatiquement</div>')
    html += '</div></body></html>'
    return html


# ─────────────────────────────────────────────
# ENVOI TELEGRAM
# ─────────────────────────────────────────────

def tg_send_one(text):
    url  = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage"
    resp = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID, "text": text,
        "parse_mode": "HTML", "disable_web_page_preview": False,
    }, timeout=30)
    if resp.status_code != 200:
        print("Erreur Telegram : " + resp.text[:200])
        resp.raise_for_status()
    return resp.json().get("ok", False)


def send_telegram(b):
    parts = build_telegram_parts(b)
    ok = True
    for i, part in enumerate(parts):
        if not part.strip():
            continue
        if len(part) > TELEGRAM_LIMIT:
            # Découpage d'urgence ligne par ligne
            cur = ""
            for line in part.split("\n"):
                if len(cur + line + "\n") > TELEGRAM_LIMIT and cur.strip():
                    tg_send_one(cur.strip())
                    cur = line + "\n"
                else:
                    cur += line + "\n"
            if cur.strip():
                ok = tg_send_one(cur.strip()) and ok
        else:
            ok = tg_send_one(part) and ok
    return ok


# ─────────────────────────────────────────────
# ENVOI EMAIL
# ─────────────────────────────────────────────

def send_email(html_body):
    today = datetime.now().strftime("%d/%m/%Y")
    msg   = MIMEMultipart("alternative")
    msg["Subject"] = "☀️ Morning Briefing — " + today
    msg["From"]    = GMAIL_USER
    msg["To"]      = EMAIL_TO
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        s.sendmail(GMAIL_USER, EMAIL_TO, msg.as_string())
    return True


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    ts = "[" + datetime.now().strftime("%H:%M:%S") + "] "
    print(ts + "Demarrage Morning Briefing Bot")

    if not ANTHROPIC_API_KEY:
        print("ERREUR : ANTHROPIC_API_KEY manquante")
        return

    use_tg    = bool(TELEGRAM_BOT_TOKEN)
    use_email = bool(GMAIL_USER and GMAIL_APP_PASSWORD and EMAIL_TO)

    if not use_tg and not use_email:
        print("ERREUR : aucun canal configure")
        return

    print(ts + "Canaux : " + ("Telegram " if use_tg else "") + ("Email" if use_email else ""))
    print(ts + "Appel Claude...")

    try:
        briefing = generate_briefing()
        print(ts + "Briefing genere OK")

        if use_tg:
            ok = send_telegram(briefing)
            print(ts + ("✓ Telegram envoye" if ok else "✗ Telegram echec"))

        if use_email:
            html = build_email_html(briefing)
            send_email(html)
            print(ts + "✓ Email envoye vers " + EMAIL_TO)

    except requests.exceptions.HTTPError as e:
        print(ts + "Erreur HTTP : " + str(e))
    except requests.exceptions.Timeout:
        print(ts + "Timeout 90s")
    except json.JSONDecodeError as e:
        print(ts + "Erreur JSON : " + str(e))
    except Exception as e:
        print(ts + "Erreur : " + str(e))
        raise


if __name__ == "__main__":
    main()
