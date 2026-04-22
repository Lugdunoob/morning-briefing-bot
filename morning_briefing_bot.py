#!/usr/bin/env python3
"""
Morning Briefing Bot — v4 (Morning Brew style)
- Web search activé : vrais articles du jour précédent
- 3 articles par section
- Activité enfants + Impression 3D : toutes les 2 semaines
- Inspiré de Morning Brew / 1440 / Chartr
"""

import os
import json
import smtplib
import requests
from datetime import datetime, timedelta
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

def is_biweekly_week():
    """Retourne True les semaines paires → sections enfants/3D actives."""
    return datetime.now().isocalendar()[1] % 2 == 0


# ─────────────────────────────────────────────
# PROMPT — avec web search, style Morning Brew
# ─────────────────────────────────────────────

def build_prompt(include_special):
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d %B %Y")
    today     = datetime.now().strftime("%A %d %B %Y")

    special_block = ""
    if include_special:
        special_block = """
  "impression_3d": {
    "title": "Nom du modèle à imprimer",
    "description": "Ce que c'est, niveau de difficulté, durée estimée. 1 phrase.",
    "url": "URL Printables ou Makerworld (https://www.printables.com/...)"
  },
  "activite_enfant": {
    "title": "Nom de l'activité",
    "age": "ex: 5-10 ans",
    "duree": "ex: 1h30",
    "description": "Ce qu'on fait et pourquoi c'est bien. 1 phrase.",
    "url": "URL vers le tuto ou la ressource"
  },"""

    return f"""Tu es un assistant de veille pour un père de famille français actif et curieux.
Il s'intéresse aux marchés financiers, à la tech/IA, au FMCG/retail, à l'impression 3D, aux activités avec ses enfants, et aux nouvelles découvertes.
Aujourd'hui : {today}. Les articles doivent dater du {yesterday} au maximum.

UTILISE LA RECHERCHE WEB pour trouver de vrais articles récents avec de vrais liens fonctionnels.
Pour chaque article/lien : vérifie que l'URL existe vraiment avant de l'inclure.
Si tu n'es pas certain d'un lien, mets null plutôt qu'un faux lien.

Réponds UNIQUEMENT avec un objet JSON brut. Pas de texte avant ni après. Commence par {{ et termine par }}.

Inspire-toi du style Morning Brew / 1440 : chaque brief a un titre accrocheur, 2 phrases max, et un angle "pourquoi c'est important".

Structure JSON :
{{
  "headline": "L'insight dominant du jour en 10 mots — percutant comme Morning Brew",
  "date": "{yesterday}",

  "markets": [
    {{"s":"BTC","p":"$84000","c":1.2,"note":"5 mots"}},
    {{"s":"ETH","p":"$1600","c":-0.8,"note":"5 mots"}},
    {{"s":"CAC40","p":"7800","c":0.4,"note":"5 mots"}},
    {{"s":"SP500","p":"5200","c":0.5,"note":"5 mots"}},
    {{"s":"Or","p":"$2300","c":0.2,"note":"5 mots"}},
    {{"s":"EUR/USD","p":"1.082","c":-0.1,"note":"5 mots"}}
  ],

  "macro_signal": {{
    "title": "Signal du jour en 6 mots",
    "body": "Ce qui se passe + pourquoi ça compte pour un investisseur. 2 phrases.",
    "url": "vrai lien ou null"
  }},

  "news_monde": [
    {{"title":"Titre accrocheur 5 mots","src":"Reuters","body":"2 phrases : fait + why it matters.","url":"https://..."}},
    {{"title":"Titre accrocheur 5 mots","src":"Le Monde","body":"2 phrases.","url":"https://..."}},
    {{"title":"Titre accrocheur 5 mots","src":"BBC","body":"2 phrases.","url":"https://..."}}
  ],

  "news_tech": [
    {{"title":"Titre accrocheur 5 mots","src":"TechCrunch","body":"2 phrases : nouveauté + impact concret.","url":"https://..."}},
    {{"title":"Titre accrocheur 5 mots","src":"Wired","body":"2 phrases.","url":"https://..."}},
    {{"title":"Titre accrocheur 5 mots","src":"MIT Tech Review","body":"2 phrases.","url":"https://..."}}
  ],

  "news_fmcg": [
    {{"title":"Titre accrocheur 5 mots","src":"LSA","body":"2 phrases : tendance consommation + implication marché.","url":"https://..."}},
    {{"title":"Titre accrocheur 5 mots","src":"Linéaires","body":"2 phrases.","url":"https://..."}},
    {{"title":"Titre accrocheur 5 mots","src":"Nielsen","body":"2 phrases.","url":"https://..."}}
  ],

  "outils": [
    {{"name":"Nom","category":"IA | productivité | design","description":"Ce que ça fait en 1 phrase. Cas d'usage concret.","url":"https://..."}},
    {{"name":"Nom","category":"IA | no-code | autre","description":"Ce que ça fait en 1 phrase.","url":"https://..."}},
    {{"name":"Nom","category":"IA | créativité | autre","description":"Ce que ça fait en 1 phrase.","url":"https://..."}}
  ],
{special_block}
  "podcasts": [
    {{"name":"Nom","episode":"Titre épisode récent","duration":"45 min","body":"De quoi ça parle en 1 phrase.","url":"https://open.spotify.com/... ou https://podcasts.apple.com/..."}},
    {{"name":"Nom","episode":"Titre épisode récent","duration":"30 min","body":"De quoi ça parle.","url":"https://..."}},
    {{"name":"Nom","episode":"Titre épisode récent","duration":"60 min","body":"De quoi ça parle.","url":"https://..."}}
  ],

  "videos": [
    {{"title":"Titre","channel":"Nom chaîne","duration":"15 min","body":"Pourquoi regarder. 1 phrase.","url":"https://www.youtube.com/watch?v=..."}},
    {{"title":"Titre","channel":"Nom chaîne","duration":"10 min","body":"Pourquoi regarder.","url":"https://www.youtube.com/watch?v=..."}},
    {{"title":"Titre","channel":"Nom chaîne","duration":"20 min","body":"Pourquoi regarder.","url":"https://www.youtube.com/watch?v=..."}}
  ],

  "articles_fond": [
    {{"title":"Titre","src":"The Economist","read_time":"8 min","body":"Sujet + pourquoi le lire. 2 phrases.","url":"https://..."}},
    {{"title":"Titre","src":"Wired","read_time":"6 min","body":"Sujet + angle original.","url":"https://..."}},
    {{"title":"Titre","src":"Substack","read_time":"10 min","body":"Sujet + insight clé.","url":"https://"}}
  ],

  "stat_du_jour": {{
    "number": "ex: 73%",
    "context": "Phrase expliquant ce chiffre et pourquoi il est surprenant. Source incluse."
  }},

  "quote": "Citation courte et percutante — style Morning Brew."
}}"""


# ─────────────────────────────────────────────
# GÉNÉRATION VIA CLAUDE + WEB SEARCH
# ─────────────────────────────────────────────

def extract_json(text):
    text = text.strip().replace("```json", "").replace("```", "").strip()
    for attempt in [
        lambda t: json.loads(t),
        lambda t: json.loads(t[t.find("{"):t.rfind("}")+1]),
        lambda t: json.JSONDecoder().raw_decode(t, t.find("{"))[0],
    ]:
        try:
            return attempt(text)
        except Exception:
            continue
    raise ValueError("Aucun JSON valide. Début : " + text[:300])


def generate_briefing():
    include_special = is_biweekly_week()
    prompt = build_prompt(include_special)
    print("Sections spéciales (enfants/3D) : " + ("OUI" if include_special else "NON (semaine impaire)"))

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key":         ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        },
        json={
            "model":      "claude-sonnet-4-6",
            "max_tokens": 4000,
            "tools":      [{"type": "web_search_20250305", "name": "web_search"}],
            "messages":   [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )

    if resp.status_code != 200:
        print("Erreur API " + str(resp.status_code) + " : " + resp.text[:300])
        resp.raise_for_status()

    raw = ""
    for block in resp.json().get("content", []):
        if block.get("type") == "text":
            raw += block["text"]

    print("Réponse Claude : " + str(len(raw)) + " chars")
    briefing = extract_json(raw)
    briefing["_include_special"] = include_special
    return briefing


# ─────────────────────────────────────────────
# HELPERS FORMATAGE
# ─────────────────────────────────────────────

def esc(v):
    s = str(v) if v else ""
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def valid_url(u):
    return bool(u and str(u).startswith("http"))

def tg_link(label, url):
    return (' <a href="' + esc(url) + '">' + label + '</a>') if valid_url(url) else ""


# ─────────────────────────────────────────────
# FORMATAGE TELEGRAM — 1 message par section
# ─────────────────────────────────────────────

def build_telegram_parts(b):
    parts = []
    date  = b.get("date", datetime.now().strftime("%d/%m/%Y"))

    # ── 1. En-tête + Marchés + Macro ──
    L = []
    L.append("☀️ <b>MORNING BRIEFING — " + date + "</b>")
    if b.get("headline"):
        L.append("<i>" + esc(b["headline"]) + "</i>")
    L.append("")

    if b.get("markets"):
        L.append("📊 <b>MARCHÉS</b>")
        for m in b["markets"]:
            c    = float(m.get("c", 0))
            arr  = "▲" if c >= 0 else "▼"
            sign = "+" if c >= 0 else ""
            note = "  <i>" + esc(m["note"]) + "</i>" if m.get("note") else ""
            L.append("<code>" + esc(m.get("s","")).ljust(7) + "</code> "
                     + esc(m.get("p","")) + "  " + arr + " " + sign + str(c) + "%" + note)
        L.append("")

    macro = b.get("macro_signal")
    if macro:
        L.append("📡 <b>SIGNAL MACRO</b> — <b>" + esc(macro.get("title","")) + "</b>")
        L.append(esc(macro.get("body","")) + tg_link(" En savoir +", macro.get("url")))
    parts.append("\n".join(L))

    # ── 2. News Monde ──
    news_monde = b.get("news_monde", [])
    if news_monde:
        L = ["🌍 <b>MONDE</b>"]
        for n in news_monde:
            L.append("")
            L.append("▸ <b>" + esc(n.get("title","")) + "</b> — <i>" + esc(n.get("src","")) + "</i>")
            L.append(esc(n.get("body","")) + tg_link(" Lire →", n.get("url")))
        parts.append("\n".join(L))

    # ── 3. News Tech + FMCG ──
    L = []
    news_tech = b.get("news_tech", [])
    if news_tech:
        L.append("💻 <b>TECH & IA</b>")
        for n in news_tech:
            L.append("")
            L.append("▸ <b>" + esc(n.get("title","")) + "</b> — <i>" + esc(n.get("src","")) + "</i>")
            L.append(esc(n.get("body","")) + tg_link(" Lire →", n.get("url")))
    L.append("")
    news_fmcg = b.get("news_fmcg", [])
    if news_fmcg:
        L.append("🛒 <b>FMCG & RETAIL</b>")
        for n in news_fmcg:
            L.append("")
            L.append("▸ <b>" + esc(n.get("title","")) + "</b> — <i>" + esc(n.get("src","")) + "</i>")
            L.append(esc(n.get("body","")) + tg_link(" Lire →", n.get("url")))
    if L:
        parts.append("\n".join(L))

    # ── 4. Outils ──
    outils = b.get("outils", [])
    if outils:
        L = ["🛠 <b>OUTILS DU JOUR</b>"]
        for o in outils:
            L.append("")
            L.append("▸ <b>" + esc(o.get("name","")) + "</b>"
                     + (" <i>[" + esc(o.get("category","")) + "]</i>" if o.get("category") else ""))
            L.append(esc(o.get("description","")) + tg_link(" Essayer →", o.get("url")))
        parts.append("\n".join(L))

    # ── 5. Sections spéciales (toutes les 2 semaines) ──
    if b.get("_include_special"):
        L = []
        p3d = b.get("impression_3d")
        if p3d:
            L.append("🖨 <b>IMPRESSION 3D</b>")
            L.append("<b>" + esc(p3d.get("title","")) + "</b>")
            L.append(esc(p3d.get("description","")) + tg_link(" Télécharger →", p3d.get("url")))
            L.append("")
        act = b.get("activite_enfant")
        if act:
            L.append("👨‍👧 <b>ACTIVITÉ ENFANTS</b>")
            meta = ""
            if act.get("age"):  meta += "[" + esc(act["age"]) + "] "
            if act.get("duree"): meta += "[" + esc(act["duree"]) + "]"
            L.append("<b>" + esc(act.get("title","")) + "</b> " + meta)
            L.append(esc(act.get("description","")) + tg_link(" Voir →", act.get("url")))
        if L:
            parts.append("\n".join(L))

    # ── 6. Podcasts + Vidéos ──
    L = []
    podcasts = b.get("podcasts", [])
    if podcasts:
        L.append("🎙 <b>PODCASTS</b>")
        for p in podcasts:
            dur = " (" + esc(p.get("duration","")) + ")" if p.get("duration") else ""
            L.append("")
            L.append("▸ <b>" + esc(p.get("name","")) + "</b>" + dur + " — <i>" + esc(p.get("episode","")) + "</i>")
            L.append(esc(p.get("body","")) + tg_link(" Écouter →", p.get("url")))
    L.append("")
    videos = b.get("videos", [])
    if videos:
        L.append("▶️ <b>VIDÉOS YOUTUBE</b>")
        for v in videos:
            dur = " (" + esc(v.get("duration","")) + ")" if v.get("duration") else ""
            L.append("")
            L.append("▸ <b>" + esc(v.get("title","")) + "</b>" + dur + " — <i>" + esc(v.get("channel","")) + "</i>")
            L.append(esc(v.get("body","")) + tg_link(" Regarder →", v.get("url")))
    if L:
        parts.append("\n".join(L))

    # ── 7. Articles de fond + Stat + Citation ──
    L = []
    articles = b.get("articles_fond", [])
    if articles:
        L.append("📖 <b>ARTICLES DE FOND</b>")
        for a in articles:
            rt = " · " + esc(a.get("read_time","")) if a.get("read_time") else ""
            L.append("")
            L.append("▸ <b>" + esc(a.get("title","")) + "</b> — <i>" + esc(a.get("src","")) + "</i>" + rt)
            L.append(esc(a.get("body","")) + tg_link(" Lire →", a.get("url")))
    stat = b.get("stat_du_jour")
    if stat:
        L.append("")
        L.append("📊 <b>" + esc(stat.get("number","")) + "</b> — " + esc(stat.get("context","")))
    if b.get("quote"):
        L.append("")
        L.append("💬 <i>" + esc(b["quote"]) + "</i>")
    L.append("")
    L.append("<i>Morning Briefing Bot</i>")
    parts.append("\n".join(L))

    return [p for p in parts if p.strip()]


# ─────────────────────────────────────────────
# FORMATAGE EMAIL HTML — style Morning Brew
# ─────────────────────────────────────────────

def build_email_html(b):
    date = b.get("date", datetime.now().strftime("%d %B %Y"))

    def esc_h(v):
        return esc(v)

    def btn(label, url, color="#111"):
        if not valid_url(url): return ""
        return ('<a href="' + esc(url) + '" style="display:inline-block;margin-top:10px;padding:7px 16px;'
                'background:' + color + ';color:#fff;font-size:12px;text-decoration:none;'
                'border-radius:4px;font-family:Arial,sans-serif">' + label + '</a>')

    def section_title(icon, title):
        return ('<div style="display:flex;align-items:center;gap:8px;margin:28px 0 14px">'
                '<span style="font-size:16px">' + icon + '</span>'
                '<span style="font-size:10px;letter-spacing:2.5px;text-transform:uppercase;'
                'font-family:Arial,sans-serif;color:#999;font-weight:600">' + title + '</span>'
                '<div style="flex:1;height:1px;background:#f0f0f0;margin-left:8px"></div>'
                '</div>')

    def news_card(n, accent="#3b82f6"):
        url = n.get("url","")
        lnk = ('<a href="' + esc(url) + '" style="font-size:11px;color:' + accent + ';text-decoration:none;font-family:Arial,sans-serif">Lire l\'article →</a>'
               if valid_url(url) else "")
        return ('<div style="border-left:3px solid ' + accent + ';padding:10px 14px;'
                'margin-bottom:10px;background:#fafafa;border-radius:0 6px 6px 0">'
                '<div style="font-weight:700;font-size:14px;color:#111;margin-bottom:3px;'
                'font-family:Georgia,serif">' + esc_h(n.get("title","")) + '</div>'
                '<div style="font-size:11px;color:#aaa;margin-bottom:5px;font-family:Arial,sans-serif">'
                + esc_h(n.get("src","")) + '</div>'
                '<div style="font-size:13px;color:#444;line-height:1.6;font-family:Arial,sans-serif">'
                + esc_h(n.get("body","")) + '</div>'
                + ('<div style="margin-top:7px">' + lnk + '</div>' if lnk else '')
                + '</div>')

    def tool_card(o):
        return ('<div style="background:#f9f9f9;border-radius:6px;padding:12px;margin-bottom:8px">'
                '<div style="font-weight:700;font-size:13px;color:#111;font-family:Arial,sans-serif">'
                + esc_h(o.get("name",""))
                + (' <span style="background:#e5e7eb;color:#6b7280;font-size:10px;padding:2px 7px;border-radius:10px">'
                   + esc_h(o.get("category","")) + '</span>' if o.get("category") else "")
                + '</div>'
                '<div style="font-size:13px;color:#555;margin-top:4px;font-family:Arial,sans-serif">'
                + esc_h(o.get("description","")) + '</div>'
                + btn("Essayer →", o.get("url"), "#111")
                + '</div>')

    def media_card(item, icon="🎙"):
        title = item.get("title", item.get("name", ""))
        sub   = item.get("channel", item.get("episode", ""))
        dur   = (' <span style="color:#aaa;font-size:11px">(' + esc_h(item.get("duration","")) + ')</span>'
                 if item.get("duration") else "")
        return ('<div style="padding:10px 0;border-bottom:1px solid #f5f5f5">'
                '<div style="font-weight:700;font-size:13px;color:#111;font-family:Arial,sans-serif">'
                + icon + ' ' + esc_h(title) + dur + '</div>'
                + ('<div style="font-size:11px;color:#aaa;font-family:Arial,sans-serif">' + esc_h(sub) + '</div>' if sub else "")
                + '<div style="font-size:13px;color:#555;margin-top:4px;font-family:Arial,sans-serif">'
                + esc_h(item.get("body","")) + '</div>'
                + btn("→ Accéder", item.get("url"), "#374151")
                + '</div>')

    def article_card(a):
        rt = (' <span style="color:#aaa">· ' + esc_h(a.get("read_time","")) + '</span>'
              if a.get("read_time") else "")
        return ('<div style="padding:10px 0;border-bottom:1px solid #f5f5f5">'
                '<div style="font-weight:700;font-size:14px;color:#111;font-family:Georgia,serif">'
                + esc_h(a.get("title","")) + rt + '</div>'
                '<div style="font-size:11px;color:#aaa;margin:3px 0;font-family:Arial,sans-serif">'
                + esc_h(a.get("src","")) + '</div>'
                '<div style="font-size:13px;color:#555;line-height:1.6;font-family:Arial,sans-serif">'
                + esc_h(a.get("body","")) + '</div>'
                + btn("Lire l'article →", a.get("url"), "#1d4ed8")
                + '</div>')

    # ── BUILD ──
    H = ('<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
         '<title>Morning Briefing</title></head>'
         '<body style="background:#f3f4f6;margin:0;padding:20px 0">')
    H += '<div style="max-width:640px;margin:0 auto">'

    # Header — style Morning Brew
    H += ('<div style="background:#111;padding:24px 32px;border-radius:10px 10px 0 0">'
          '<div style="font-family:Georgia,serif;font-size:26px;font-weight:700;color:#fff;letter-spacing:-0.5px">'
          '☀️ Morning Briefing</div>'
          '<div style="font-size:12px;color:#888;margin-top:4px;font-family:Arial,sans-serif">' + date + '</div>'
          + ('<div style="font-style:italic;color:#ccc;font-size:14px;margin-top:10px;font-family:Georgia,serif">'
             + esc_h(b.get("headline","")) + '</div>' if b.get("headline") else "")
          + '</div>')

    H += '<div style="background:#fff;padding:24px 32px;border-radius:0 0 10px 10px">'

    # Marchés
    markets = b.get("markets", [])
    if markets:
        H += section_title("📊", "Marchés")
        H += '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">'
        for m in markets:
            c    = float(m.get("c", 0))
            col  = "#16a34a" if c >= 0 else "#dc2626"
            sign = "+" if c >= 0 else ""
            H += ('<div style="background:#f9f9f9;border-radius:6px;padding:10px;text-align:center">'
                  '<div style="font-size:10px;color:#aaa;font-family:Arial,sans-serif">' + esc_h(m.get("s","")) + '</div>'
                  '<div style="font-size:15px;font-weight:700;color:#111;font-family:Arial,sans-serif">' + esc_h(m.get("p","")) + '</div>'
                  '<div style="font-size:12px;color:' + col + ';font-family:Arial,sans-serif">' + sign + str(c) + '%</div>'
                  + ('<div style="font-size:10px;color:#bbb;margin-top:2px;font-family:Arial,sans-serif">' + esc_h(m.get("note","")) + '</div>' if m.get("note") else "")
                  + '</div>')
        H += '</div>'

    # Macro
    macro = b.get("macro_signal")
    if macro:
        H += section_title("📡", "Signal Macro")
        H += ('<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:6px;padding:14px">'
              '<div style="font-weight:700;font-size:14px;color:#111;font-family:Georgia,serif">'
              + esc_h(macro.get("title","")) + '</div>'
              '<div style="font-size:13px;color:#555;margin-top:6px;line-height:1.6;font-family:Arial,sans-serif">'
              + esc_h(macro.get("body","")) + '</div>'
              + btn("En savoir plus", macro.get("url"), "#92400e")
              + '</div>')

    # News Monde
    if b.get("news_monde"):
        H += section_title("🌍", "Monde")
        for n in b["news_monde"]:
            H += news_card(n, "#3b82f6")

    # News Tech
    if b.get("news_tech"):
        H += section_title("💻", "Tech & IA")
        for n in b["news_tech"]:
            H += news_card(n, "#8b5cf6")

    # News FMCG
    if b.get("news_fmcg"):
        H += section_title("🛒", "FMCG & Retail")
        for n in b["news_fmcg"]:
            H += news_card(n, "#10b981")

    # Outils
    if b.get("outils"):
        H += section_title("🛠", "Outils du jour")
        for o in b["outils"]:
            H += tool_card(o)

    # Sections spéciales (toutes les 2 semaines)
    if b.get("_include_special"):
        p3d = b.get("impression_3d")
        if p3d:
            H += section_title("🖨", "Impression 3D")
            H += ('<div style="background:#f0f9ff;border-radius:6px;padding:14px">'
                  '<div style="font-weight:700;font-size:14px;color:#111;font-family:Georgia,serif">'
                  + esc_h(p3d.get("title","")) + '</div>'
                  '<div style="font-size:13px;color:#555;margin-top:6px;font-family:Arial,sans-serif">'
                  + esc_h(p3d.get("description","")) + '</div>'
                  + btn("Télécharger le modèle →", p3d.get("url"), "#0369a1")
                  + '</div>')
        act = b.get("activite_enfant")
        if act:
            H += section_title("👨‍👧", "Activité Enfants")
            meta = ""
            if act.get("age"):   meta += '<span style="background:#fef9c3;color:#854d0e;font-size:11px;padding:2px 8px;border-radius:10px;margin-right:6px;font-family:Arial,sans-serif">' + esc_h(act["age"]) + '</span>'
            if act.get("duree"): meta += '<span style="background:#e0f2fe;color:#0369a1;font-size:11px;padding:2px 8px;border-radius:10px;font-family:Arial,sans-serif">' + esc_h(act["duree"]) + '</span>'
            H += ('<div style="background:#fafff4;border-radius:6px;padding:14px">'
                  + ('<div style="margin-bottom:8px">' + meta + '</div>' if meta else "")
                  + '<div style="font-weight:700;font-size:14px;color:#111;font-family:Georgia,serif">'
                  + esc_h(act.get("title","")) + '</div>'
                  '<div style="font-size:13px;color:#555;margin-top:6px;font-family:Arial,sans-serif">'
                  + esc_h(act.get("description","")) + '</div>'
                  + btn("Voir l'activité →", act.get("url"), "#15803d")
                  + '</div>')

    # Podcasts
    if b.get("podcasts"):
        H += section_title("🎙", "Podcasts")
        for p in b["podcasts"]:
            H += media_card(p, "🎙")

    # Vidéos
    if b.get("videos"):
        H += section_title("▶️", "Vidéos YouTube")
        for v in b["videos"]:
            H += media_card(v, "▶️")

    # Articles de fond
    if b.get("articles_fond"):
        H += section_title("📖", "Articles de fond")
        for a in b["articles_fond"]:
            H += article_card(a)

    # Stat du jour
    stat = b.get("stat_du_jour")
    if stat:
        H += ('<div style="background:#111;border-radius:8px;padding:16px 20px;margin:20px 0;text-align:center">'
              '<div style="font-size:32px;font-weight:700;color:#fff;font-family:Georgia,serif">'
              + esc_h(stat.get("number","")) + '</div>'
              '<div style="font-size:13px;color:#aaa;margin-top:6px;font-family:Arial,sans-serif">'
              + esc_h(stat.get("context","")) + '</div>'
              '</div>')

    # Citation
    if b.get("quote"):
        H += ('<div style="border-left:3px solid #e5e7eb;padding:10px 16px;margin:20px 0">'
              '<p style="font-style:italic;color:#666;margin:0;font-size:15px;font-family:Georgia,serif">'
              + esc_h(b["quote"]) + '</p></div>')

    # Footer
    H += ('<div style="text-align:center;font-size:11px;color:#d1d5db;margin-top:24px;padding-top:16px;'
          'border-top:1px solid #f3f4f6;font-family:Arial,sans-serif">'
          'Morning Briefing Bot — généré automatiquement</div>')

    H += '</div></div></body></html>'
    return H


# ─────────────────────────────────────────────
# ENVOI TELEGRAM
# ─────────────────────────────────────────────

def tg_send_one(text):
    resp = requests.post(
        "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text,
              "parse_mode": "HTML", "disable_web_page_preview": False},
        timeout=30,
    )
    if resp.status_code != 200:
        print("Erreur Telegram : " + resp.text[:200])
        resp.raise_for_status()
    return resp.json().get("ok", False)

def send_telegram(briefing):
    parts = build_telegram_parts(briefing)
    ok = True
    for i, part in enumerate(parts):
        if not part.strip(): continue
        # Découpage d'urgence si une partie est encore trop longue
        if len(part) > TELEGRAM_LIMIT:
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
    print(ts + "Morning Briefing Bot v4 — démarrage")

    if not ANTHROPIC_API_KEY:
        print("ERREUR : ANTHROPIC_API_KEY manquante"); return

    use_tg    = bool(TELEGRAM_BOT_TOKEN)
    use_email = bool(GMAIL_USER and GMAIL_APP_PASSWORD and EMAIL_TO)

    if not use_tg and not use_email:
        print("ERREUR : aucun canal configuré"); return

    print(ts + "Canaux : " + ("Telegram " if use_tg else "") + ("Email" if use_email else ""))
    print(ts + "Appel Claude avec web search...")

    try:
        briefing = generate_briefing()
        print(ts + "Briefing généré OK")

        if use_tg:
            ok = send_telegram(briefing)
            print(ts + ("✓ Telegram OK" if ok else "✗ Telegram ECHEC"))

        if use_email:
            html = build_email_html(briefing)
            send_email(html)
            print(ts + "✓ Email envoyé → " + EMAIL_TO)

    except requests.exceptions.HTTPError as e:
        print(ts + "Erreur HTTP : " + str(e))
    except requests.exceptions.Timeout:
        print(ts + "Timeout 120s")
    except json.JSONDecodeError as e:
        print(ts + "Erreur JSON : " + str(e))
    except Exception as e:
        print(ts + "Erreur : " + str(e))
        raise


if __name__ == "__main__":
    main()
