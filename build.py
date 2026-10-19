#!/usr/bin/env python3
"""Build yakup-gunduz.com.

site.html is the single source (it also works as a single-page preview with client-side i18n).
This script turns it into a static, crawlable site in dist/:
  /            /hakkimda/   /iletisim/      (Turkish)
  /en/         /en/about/   /en/contact/    (English)
plus 404 pages, robots.txt, sitemap.xml, llms.txt, llms-full.txt and JSON-LD on every page.
"""
import html
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
SRC = (ROOT / "site.html").read_text(encoding="utf-8")
CONTENT = json.loads((ROOT / "src" / "content.json").read_text(encoding="utf-8"))
APP_JS = (ROOT / "src" / "app.js").read_text(encoding="utf-8")
DIST = ROOT / "dist"
BASE = "https://yakup-gunduz.com"
MODIFIED = CONTENT.get("dateModified") or datetime.now().astimezone().isoformat(timespec="seconds")
TODAY = MODIFIED[:10]

PAGES = {
    "home": {"tr": "/", "en": "/en/"},
    "about": {"tr": "/hakkimda/", "en": "/en/about/"},
    "contact": {"tr": "/iletisim/", "en": "/en/contact/"},
}

# Project pages: /projeler/<slug>/ and /en/projects/<slug>/, built from src/projects.json
PROJECTS = json.loads((ROOT / "src" / "projects.json").read_text(encoding="utf-8"))
PAGES["projects"] = {"tr": "/projeler/", "en": "/en/projects/"}
CONTENT["pages"]["projects"] = {
    lang: {"title": v["title"], "description": v["description"], "og": v["description"], "og_alt": CONTENT["pages"]["about"][lang]["og_alt"], "crumb": v["crumb"]}
    for lang, v in PROJECTS["index"].items()
}
for _p in PROJECTS["projects"]:
    PAGES["p:" + _p["slug"]] = {"tr": f"/projeler/{_p['slug']}/", "en": f"/en/projects/{_p['slug']}/"}
    CONTENT["pages"]["p:" + _p["slug"]] = {
        lang: {"title": _p[lang]["title"], "description": _p[lang]["description"], "og": _p[lang]["description"], "og_alt": CONTENT["pages"]["about"][lang]["og_alt"], "crumb": _p[lang]["name"]}
        for lang in ("tr", "en")
    }
PROJECT_BY_PAGE = {"p:" + _p["slug"]: _p for _p in PROJECTS["projects"]}

# ---------------------------------------------------------------- source parts
head_src, body_src = SRC.split("<!-- BODY -->", 1)
CSS = re.search(r"<style>(.*?)</style>", head_src, re.S).group(1)


def block(pattern, text=body_src):
    m = re.search(pattern, text, re.S)
    if not m:
        raise SystemExit(f"missing block: {pattern}")
    return m.group(0)


SPRITE = block(r'<svg width="0".*?</svg>')
HEADER = block(r'<header class="nav".*?</header>')
MENU = block(r'<nav class="menu" id="menu".*?\n</nav>')
MAINS = {
    "home": block(r'<main class="view" id="view-home".*?</main>'),
    "about": block(r'<main class="view" id="view-about".*?</main>'),
    "contact": block(r'<main class="view" id="view-contact".*?</main>'),
}
FOOTER = block(r'<footer class="footer.*?</footer>')

script_src = block(r"<script>.*?</script>")
EN = json.loads("{" + re.search(r"var EN = \{(.*?)\n\s*\};", script_src, re.S).group(1) + "}")
TR_EXTRA = json.loads("{" + re.search(r"var TR_EXTRA = \{(.*?)\n\s*\};", script_src, re.S).group(1) + "}")

MONTHS = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "tr": ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"],
}

# ---------------------------------------------------------------- transforms
LEAF = re.compile(r'(<(\w+)\b[^>]*?\sdata-i18n="([^"]+)"[^>]*>)(.*?)(</\2>)', re.S)
RICH = re.compile(r'(<(\w+)\b[^>]*?\sdata-i18n-html="([^"]+)"[^>]*>)(.*?)(</\2>)', re.S)
ATTRS = re.compile(r'\sdata-i18n-attr="([^"]+)"')


def tr_text(lang, key, fallback):
    if lang == "en":
        if key not in EN:
            raise SystemExit(f"missing EN key {key}")
        return EN[key]
    return TR_EXTRA.get(key, fallback)


def translate(markup, lang):
    if lang == "en":
        markup = LEAF.sub(lambda m: m.group(1) + html.escape(EN[m.group(3)], quote=False) + m.group(5), markup)
        markup = RICH.sub(lambda m: m.group(1) + EN[m.group(3)] + m.group(5), markup)

        def attr_sub(tag_match):
            tag = tag_match.group(0)
            spec = ATTRS.search(tag)
            if not spec:
                return tag
            for pair in spec.group(1).split(","):
                attr, key = [x.strip() for x in pair.split(":")]
                value = html.escape(EN[key], quote=True)
                tag, n = re.subn(r'(\s%s=")[^"]*(")' % re.escape(attr), lambda mm: mm.group(1) + value + mm.group(2), tag, count=1)
                if not n:
                    raise SystemExit(f"attr {attr} missing for {key}")
            return tag

        markup = re.sub(r"<[^>]+data-i18n-attr=[^>]+>", attr_sub, markup)
    months = MONTHS[lang]
    markup = re.sub(r'(data-date="(\d{4})-(\d{2})">)[^<]*', lambda m: m.group(1) + f"{months[int(m.group(3)) - 1]} {m.group(2)}", markup)
    # drop the i18n plumbing from production markup
    markup = re.sub(r'\sdata-i18n(?:-html|-attr)?="[^"]*"', "", markup)
    markup = re.sub(r'\sdata-date="[^"]*"', "", markup)
    return markup


def localize_links(markup, lang, page):
    urls = {k: v[lang] for k, v in PAGES.items()}
    markup = markup.replace('href="#home"', f'href="{urls["home"]}"')
    markup = markup.replace('href="#about"', f'href="{urls["about"]}"')
    markup = markup.replace('href="#contact"', f'href="{urls["contact"]}"')

    def route(m):
        tag = m.group(0)
        target = m.group(1)
        tag = re.sub(r'\sdata-route="[^"]*"', "", tag)
        if target == page:
            tag = tag[:-1] + ' aria-current="page">'
        return tag

    markup = re.sub(r'<a [^>]*data-route="(\w+)"[^>]*>', route, markup)
    return markup


def lang_switch(lang, page):
    other = "en" if lang == "tr" else "tr"
    label = "Dil" if lang == "tr" else "Language"
    def link(code):
        cur = ' aria-current="true"' if code == lang else ""
        name = "Türkçe" if code == "tr" else "English"
        return f'<a href="{PAGES[page][code]}" hreflang="{code}" lang="{code}" title="{name}"{cur}>{code.upper()}</a>'
    return f'<div class="lang" role="group" aria-label="{label}">{link("tr")}<span aria-hidden="true">/</span>{link("en")}</div>'


def absolutize(markup):
    markup = re.sub(r'(src|href|poster|data-src|data-poster)="assets/', r'\1="/assets/', markup)
    markup = re.sub(r'srcset="([^"]+)"', lambda m: 'srcset="' + re.sub(r"(^|,\s*)assets/", r"\1/assets/", m.group(1)) + '"', markup)
    markup = markup.replace("url(assets/", "url(/assets/")
    return markup


def production_body(lang, page):
    header = HEADER
    menu = MENU.replace('class="nav-link" href="#home"', 'class="nav-link menu-link" href="#home"')
    menu = menu.replace('class="nav-link" href="#about"', 'class="nav-link menu-link" href="#about"')
    menu = menu.replace('class="nav-link" href="#contact"', 'class="nav-link menu-link" href="#contact"')
    for part_name in ("header", "menu"):
        part = header if part_name == "header" else menu
        part = re.sub(r'<div class="lang" role="group".*?</div>', lang_switch(lang, page), part, flags=re.S)
        if part_name == "header":
            header = part
        else:
            menu = part
    t = lambda k: tr_text(lang, k, "")
    open_label = html.escape(t("nav.open") or "Menüyü aç")
    header, n = re.subn(r'aria-label="Menüyü aç"\s+data-i18n-attr="aria-label:nav.open"',
                        lambda m: f'aria-label="{open_label}" data-open="{open_label}" data-close="{html.escape(t("nav.close"))}"', header)
    if not n:
        raise SystemExit("burger label not found")
    main = MAINS[page] if page in MAINS else project_main(lang, page)
    main = main.replace(" hidden>", ">", 1)
    main = main.replace(' tabindex="-1"', "")
    footer = FOOTER.replace(
        'id="copy-email" data-i18n="footer.copy">Kopyala</button>',
        f'id="copy-email" data-copy="{t("footer.copy") or "Kopyala"}" data-copied="{t("footer.copied")}" data-copy-fail="{t("footer.copyFail")}" data-i18n="footer.copy">Kopyala</button>',
    )
    if page == "home":
        main = main.replace('<img src="assets/img/feature-workspace.webp" width="1600" height="1067" loading="lazy"',
                            '<img src="assets/img/feature-workspace.webp" srcset="assets/img/feature-workspace-800.webp 800w, assets/img/feature-workspace.webp 1600w" sizes="(max-width: 1440px) 96vw, 1382px" width="1600" height="1067" loading="lazy" decoding="async"')
        main = main.replace('<img src="assets/img/harpos-pos.webp" width="1600" height="900" loading="lazy"',
                            '<img src="assets/img/harpos-pos.webp" srcset="assets/img/harpos-pos-800.webp 800w, assets/img/harpos-pos.webp 1600w" sizes="(max-width: 767px) 92vw, 44rem" width="1600" height="900" loading="lazy" decoding="async"')
        main = re.sub(r'<img src="assets/img/(svc-[\w-]+)\.webp" width="1600" height="944"( loading="lazy")?',
                      lambda m: f'<img src="assets/img/{m.group(1)}.webp" srcset="assets/img/{m.group(1)}-800.webp 800w, assets/img/{m.group(1)}.webp 1600w" sizes="(max-width: 991px) 92vw, 52vw" width="1600" height="944" loading="lazy" decoding="async"', main)
        main = re.sub(r'(<img src="assets/logos/[^"]+")', r'\1 loading="lazy" decoding="async"', main)
        # Offscreen images are fetched by app.js only when they approach the viewport.
        main = re.sub(r'<img ([^>]*?)loading="lazy"([^>]*)>', lambda m: "<img " + re.sub(r'\b(src|srcset)="', r'data-\1="', m.group(1) + m.group(2)) + ' data-lazy>', main)
    if page == "about":
        tail = "\n    </div>\n  </section>\n</main>"
        if tail not in main:
            raise SystemExit("about tail not found")
        main = main.replace(tail, about_extra(lang) + tail, 1)
    body = "\n".join([SPRITE, header, menu, main, footer])
    body = localize_links(body, lang, page)
    body = translate(body, lang)
    if page == "home" and lang == "en":
        body = re.sub(r'(<h3 class="h4" id="m-title">)[^<]*', lambda m: m.group(1) + html.escape(EN["svc.1.title"]), body)
        body = re.sub(r'(<p id="m-body">)[^<]*', lambda m: m.group(1) + html.escape(EN["svc.1.body"]), body)
    return absolutize(body)


def month_label(ym, lang):
    y, m = (int(x) for x in ym.split("-"))
    names = {"tr": ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"],
             "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]}
    return f"{names[lang][m - 1]} {y}"


def project_time(project, lang):
    """Only render project dates supported by the content source."""
    date = project.get("date")
    return f'<time datetime="{html.escape(date)}">{month_label(date, lang)}</time>' if date else ""


def project_main(lang, page):
    """Markup for /projeler/ and /projeler/<slug>/, in the About page's layout."""
    e = html.escape
    lab = PROJECTS["labels"][lang]
    if page == "projects":
        idx = PROJECTS["index"][lang]
        items = "\n".join(
            f'          <li><a class="r-name" href="{PAGES["p:" + p["slug"]][lang]}">{e(p[lang]["name"])}</a>'
            f'<span class="r-meta">{project_time(p, lang)}</span>'
            f'<p class="proj-sum">{e(p[lang]["summary"])}</p></li>'
            for p in PROJECTS["projects"]
        )
        return f"""<main class="view" id="view-projects">
  <section class="wrap sec-m">
    <div class="container about">
      <div class="arow">
        <div class="a-empty"></div>
        <div><h1 class="about-h1 serif">{e(idx["h1"])}</h1><p class="t-md mt2">{e(idx["lead"])}</p></div>
      </div>
      <hr class="divider">
      <div class="arow">
        <div class="a-left"><h2 class="h5">{e(idx["crumb"])}</h2></div>
        <ul class="rows proj">
{items}
        </ul>
      </div>
    </div>
  </section>
</main>"""
    p = PROJECT_BY_PAGE[page]
    c = p[lang]
    date_label = " · " + project_time(p, lang) if p.get("date") else ""
    paras = "\n".join(f"          <p>{e(t)}</p>" for t in c["paragraphs"])
    facts = "\n".join(f"          <div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>" for k, v in c["facts"])
    links = "\n".join(
        f'          <li><a class="r-name" href="{e(u)}"{"" if u.startswith("/") else " rel=\"noopener\""}>{e(t)}</a></li>'
        for t, u in c["links"]
    )
    return f"""<main class="view" id="view-project">
  <section class="wrap sec-m">
    <div class="container about">
      <p class="eyebrow"><a href="{PAGES["projects"][lang]}">{e(lab["all"])}</a>{date_label}</p>
      <div class="arow mt2">
        <div class="a-empty"></div>
        <h1 class="about-h1 serif">{e(c["name"])}</h1>
      </div>
      <hr class="divider">
      <div class="arow">
        <div class="a-left"><h2 class="h5">{e(lab["about"])}</h2></div>
        <div class="rich">
          <p>{e(c["lead"])}</p>
{paras}
        </div>
      </div>
      <hr class="divider">
      <div class="arow">
        <div class="a-left"><h2 class="h5">{e(lab["facts"])}</h2></div>
        <dl class="facts">
{facts}
        </dl>
      </div>
      <hr class="divider">
      <div class="arow">
        <div class="a-left"><h2 class="h5">{e(lab["links"])}</h2></div>
        <ul class="rows proj">
{links}
          <li><a class="r-name" href="{PAGES["about"][lang]}">Yakup Gündüz</a></li>
        </ul>
      </div>
    </div>
  </section>
</main>"""


def page_modified(page):
    if page in PROJECT_BY_PAGE:
        return PROJECT_BY_PAGE[page].get("modifiedAt", MODIFIED)
    return MODIFIED


def fmt_date(iso, lang):
    y, m, d = (int(x) for x in iso.split("-"))
    names = {"tr": ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"],
             "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]}
    return f"{d} {names[lang][m - 1]} {y}"


def about_extra(lang):
    """Answer-first facts, the real photo and a visible FAQ on the About page."""
    facts = CONTENT["facts"][lang]
    rows = "\n".join(f'          <div><dt>{html.escape(k)}</dt><dd>{html.escape(v)}</dd></div>' for k, v in facts["rows"])
    faq = "\n".join(f'          <div class="faq-item"><h3>{html.escape(q)}</h3><p>{html.escape(a)}</p></div>' for q, a in CONTENT["faq"][lang])
    anchor = "sss" if lang == "tr" else "faq"
    proj_rows = "\n".join(
        f'          <li><a class="r-name" href="{PAGES["p:" + p["slug"]][lang]}">{html.escape(p[lang]["name"])}</a><span class="r-meta">{project_time(p, lang)}</span><p class="proj-sum">{html.escape(p[lang]["summary"])}</p></li>'
        for p in PROJECTS["projects"]
    )
    return f"""
      <hr class="divider">
      <div class="arow" data-reveal>
        <div class="a-left"><h2 class="h5">{html.escape(facts["heading"])}</h2></div>
        <dl class="facts">
{rows}
        </dl>
      </div>
      <hr class="divider">
      <div class="arow" data-reveal>
        <div class="a-left"><h2 class="h5">{html.escape(PROJECTS["index"][lang]["crumb"])}</h2></div>
        <ul class="rows proj">
{proj_rows}
        </ul>
      </div>
      <hr class="divider">
      <div class="arow" id="{anchor}" data-reveal>
        <div class="a-left"><h2 class="h5">{html.escape(CONTENT["faq_heading"][lang])}</h2></div>
        <div class="faq">
{faq}
          <p class="updated">{html.escape(CONTENT["updated_label"][lang])}: <time datetime="{TODAY}">{fmt_date(TODAY, lang)}</time></p>
        </div>
      </div>"""


# ---------------------------------------------------------------- head and data
def jsonld(lang, page):
    p = CONTENT["person"]
    url = BASE + PAGES[page][lang]
    person_id = BASE + "/#person"
    graph = [
        {
            "@type": "Person",
            "@id": person_id,
            "name": p["name"],
            "alternateName": p["alternateName"],
            "givenName": p["givenName"],
            "familyName": p["familyName"],
            "url": BASE + "/",
            "jobTitle": p["jobTitle"][lang],
            "hasOccupation": {"@type": "Occupation", "name": "Full-stack software developer" if lang == "en" else "Full-stack yazılım geliştirici", "sameAs": "https://www.wikidata.org/wiki/Q183888"},
            "description": p["description"][lang],
            "email": "mailto:ykpgunduz@icloud.com",
            "address": {"@type": "PostalAddress", "addressLocality": "İstanbul", "addressCountry": "TR"},
            "nationality": {"@type": "Country", "name": "Türkiye"},
            "knowsLanguage": ["tr", "en"],
            "knowsAbout": p["knowsAbout"][lang],
            "award": p["award"][lang],
            "founder": [{"@id": BASE + "/#harpos"}],
            "alumniOf": [{"@id": BASE + "/#kle"}],
            "affiliation": [{"@id": BASE + "/#42-istanbul"}, {"@id": BASE + "/#istanbul-universitesi"}],
            "sameAs": p["sameAs"],
        },
        {"@type": "Organization", "@id": BASE + "/#harpos", "name": "Harpos Teknoloji", "alternateName": "Harpos", "url": "https://harpos.app", "founder": {"@id": person_id}, "foundingDate": "2024-08", "address": {"@type": "PostalAddress", "addressLocality": "İstanbul", "addressCountry": "TR"}},
        {"@type": "Organization", "@id": BASE + "/#kle", "name": "Kle Bilgi Teknolojileri A.Ş.", "address": {"@type": "PostalAddress", "addressLocality": "İstanbul", "addressCountry": "TR"}},
        {"@type": "CollegeOrUniversity", "@id": BASE + "/#istanbul-universitesi", "name": "İstanbul Üniversitesi", "url": "https://www.istanbul.edu.tr/"},
        {"@type": "EducationalOrganization", "@id": BASE + "/#42-istanbul", "name": "42 İstanbul", "url": "https://42turkiye.com.tr/", "parentOrganization": {"@type": "EducationalOrganization", "name": "42 Türkiye", "url": "https://42turkiye.com.tr/"}},
        {
            "@type": "WebSite",
            "@id": BASE + "/#website",
            "url": BASE + "/",
            "name": "Yakup Gündüz",
            "alternateName": ["Yakup Gunduz"],
            "inLanguage": ["tr-TR", "en"],
            "publisher": {"@id": person_id},
            "author": {"@id": person_id},
        },
    ]
    meta = CONTENT["pages"][page][lang]
    page_node = {
        "@type": {"home": "WebPage", "about": "ProfilePage", "projects": "CollectionPage"}.get(page, "WebPage" if page.startswith("p:") else "ContactPage"),
        "@id": url + "#webpage",
        "url": url,
        "name": meta["title"],
        "description": meta["description"],
        "inLanguage": "tr-TR" if lang == "tr" else "en",
        "isPartOf": {"@id": BASE + "/#website"},
        "about": {"@id": person_id},
        "mainEntity": {"@id": person_id},
        "primaryImageOfPage": BASE + f"/assets/img/og-yakup-gunduz-{lang}.jpg",
        "author": {"@id": person_id},
    }
    if page != "home":
        page_node["dateCreated"] = "2026-10-15T00:00:00+03:00"
        page_node["dateModified"] = page_modified(page)
    if page.startswith("p:"):
        page_node["dateCreated"] = PROJECT_BY_PAGE[page].get("pageCreatedAt", page_node["dateCreated"])
        proj = dict(PROJECT_BY_PAGE[page]["schema"])
        proj.setdefault("@id", url + "#project")
        proj["description"] = meta["description"]
        if proj["@type"] in ("SoftwareApplication", "WebApplication"):
            proj["author"] = {"@id": person_id}
        page_node["about"] = [{"@id": proj["@id"]}, {"@id": person_id}]
        page_node["mainEntity"] = {"@id": proj["@id"]}
        graph.append(proj)
    if page != "home":
        page_node["breadcrumb"] = {"@id": url + "#breadcrumb"}
        crumbs = [{"@type": "ListItem", "position": 1, "name": "Yakup Gündüz", "item": BASE + PAGES["home"][lang]}]
        if page.startswith("p:"):
            crumbs.append({"@type": "ListItem", "position": 2, "name": CONTENT["pages"]["projects"][lang]["crumb"], "item": BASE + PAGES["projects"][lang]})
        crumbs.append({"@type": "ListItem", "position": len(crumbs) + 1, "name": meta["crumb"], "item": url})
        graph.append({"@type": "BreadcrumbList", "@id": url + "#breadcrumb", "itemListElement": crumbs})
    graph.append(page_node)
    faq = None  # visible Q&A only; Google retired FAQ rich results, so no FAQPage markup
    if faq:
        graph.append({
            "@type": "FAQPage",
            "@id": url + "#faq",
            "inLanguage": "tr-TR" if lang == "tr" else "en",
            "isPartOf": {"@id": url + "#webpage"},
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq],
        })
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def head(lang, page):
    meta = CONTENT["pages"][page][lang]
    url = BASE + PAGES[page][lang]
    alt = "en" if lang == "tr" else "tr"
    og_img = BASE + f"/assets/img/og-yakup-gunduz-{lang}.jpg"
    preload = ""
    css = absolutize(CSS)
    css = minify_css(css)
    lines = [
        '<!doctype html>',
        f'<html lang="{"tr" if lang == "tr" else "en"}" data-about="{PAGES["about"][lang]}" data-contact="{PAGES["contact"][lang]}">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
        f"<title>{html.escape(meta['title'])}</title>",
        f'<meta name="description" content="{html.escape(meta["description"])}">',
        '<meta name="author" content="Yakup Gündüz">',
        '<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">',
        f'<link rel="canonical" href="{url}">',
        f'<link rel="alternate" hreflang="tr" href="{BASE + PAGES[page]["tr"]}">',
        f'<link rel="alternate" hreflang="en" href="{BASE + PAGES[page]["en"]}">',
        f'<link rel="alternate" hreflang="x-default" href="{BASE + PAGES[page]["tr"]}">',
        '<link rel="me" href="https://github.com/yakup-gunduz">',
        '<link rel="me" href="https://www.linkedin.com/in/yakupgunduz">',
        f'<link rel="author" href="{PAGES["about"][lang]}">',
        '<link rel="alternate" type="text/plain" href="/llms.txt" title="llms.txt">',
        '<meta name="theme-color" content="#0c0c0c">',
        '<meta name="color-scheme" content="dark">',
        '<link rel="icon" href="/favicon.ico" sizes="32x32">',
        '<link rel="icon" href="/assets/brand/favicon.svg" type="image/svg+xml">',
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
        '<link rel="preload" href="/assets/fonts/manrope-var.woff2" as="font" type="font/woff2" crossorigin>',
        '<link rel="preload" href="/assets/fonts/fraunces-display-300.woff2" as="font" type="font/woff2" crossorigin>' if page not in ("about", "projects") and not page.startswith("p:") else '<link rel="preload" href="/assets/fonts/fraunces-text-300.woff2" as="font" type="font/woff2" crossorigin>',
        preload.rstrip("\n"),
        '<meta property="og:type" content="profile">',
        f'<meta property="og:site_name" content="Yakup Gündüz">',
        f'<meta property="og:title" content="{html.escape(meta["title"])}">',
        f'<meta property="og:description" content="{html.escape(meta["og"])}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:locale" content="{"tr_TR" if lang == "tr" else "en_US"}">',
        f'<meta property="og:locale:alternate" content="{"en_US" if lang == "tr" else "tr_TR"}">',
        f'<meta property="og:image" content="{og_img}">',
        '<meta property="og:image:type" content="image/jpeg">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:image:alt" content="{html.escape(meta["og_alt"])}">',
        '<meta property="profile:first_name" content="Yakup">',
        '<meta property="profile:last_name" content="Gündüz">',
        '<meta property="profile:username" content="yakup-gunduz">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{html.escape(meta["title"])}">',
        f'<meta name="twitter:description" content="{html.escape(meta["og"])}">',
        f'<meta name="twitter:image" content="{og_img}">',
        f'<meta name="twitter:image:alt" content="{html.escape(meta["og_alt"])}">',
        f'<script type="application/ld+json">{jsonld(lang, page)}</script>',
        f"<style>{css}</style>",
        "</head>",
    ]
    return "\n".join(l for l in lines if l)


def minify_css(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};,>])\s*", r"\1", css)
    css = re.sub(r":\s+", ":", css)
    css = css.replace(";}", "}")
    return css.strip()


def minify_js(js):
    js = re.sub(r"^\s*/\*.*?\*/\s*$", "", js, flags=re.S | re.M)
    js = "\n".join(line.strip() for line in js.splitlines() if line.strip())
    return js


def page_html(lang, page):
    body = production_body(lang, page)
    script = f"<script>{minify_js(APP_JS)}</script>"
    return f"{head(lang, page)}\n<body>\n<!--email_off-->\n{body}\n<!--/email_off-->\n{script}\n</body>\n</html>\n"


def not_found(lang):
    c = CONTENT["notfound"][lang]
    nf = f'<main id="view-404" class="wrap sec-m"><div class="container nf"><p class="eyebrow">404</p><h1 class="about-h1 serif">{c["h1"]}</h1><p class="t-md">{c["body"]}</p><p class="mt2"><a class="btn btn-alt" href="{PAGES["home"][lang]}">{c["cta"]}</a></p></div></main>'
    # Same header, menu and footer wiring as the real pages, so the mobile menu and copy button work here too
    body = re.sub(r'<main class="view".*?</main>', lambda m: nf, production_body(lang, "home"), count=1, flags=re.S)
    body = body.replace(' aria-current="page"', "")
    head_html = head(lang, "home")
    head_html = re.sub(r"<title>.*?</title>", f"<title>{html.escape(c['title'])}</title>", head_html)
    head_html = re.sub(r'<meta name="robots"[^>]*>', '<meta name="robots" content="noindex, follow">', head_html)
    head_html = re.sub(r'<link rel="canonical"[^>]*>\n|<link rel="alternate" hreflang[^>]*>\n|<link rel="preload" as="image"[^>]*>\n', "", head_html)
    head_html = re.sub(r'<script type="application/ld\+json">.*?</script>\n', "", head_html)
    script = "<script>" + minify_js(APP_JS) + "</script>"
    return f"{head_html}\n<body>\n<!--email_off-->\n{body}\n<!--/email_off-->\n{script}\n</body>\n</html>\n"


def llms_full():
    """Plain-text profile for language models, generated from the same sources as the pages."""
    e = EN
    ms = re.findall(r'data-i18n="(ms\.\d+)">[^<]*</span><span class="r-meta" data-date="(\d{4})-(\d{2})"', MAINS["about"])
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    lines = [
        "# Yakup Gündüz: full profile",
        "",
        "> " + CONTENT["person"]["description"]["en"],
        "",
        f"Name variants: Yakup Gündüz, Yakup Gunduz. Website: {BASE} (Turkish) and {BASE}/en/ (English).",
        "",
        "## At a glance",
        "",
    ]
    lines += [f"- {k}: {v}" for k, v in CONTENT["facts"]["en"]["rows"]]
    lines += ["", "## Biography", "", CONTENT["person"]["description"]["en"], ""] + sum(([e[f"about.p{i}"], ""] for i in range(1, 6)), [])
    lines += ["", "## Approach", "", e["approach.title"], "", re.sub(r"<[^>]+>", "", e["approach.body"])]
    lines += ["", "## How Yakup works", ""] + [f"{i}. {e[f'process.s{i}']}" for i in range(1, 5)]
    lines += ["", "## Services", ""] + [f"- {e[f'svc.{i}.title']}: {e[f'svc.{i}.body']}" for i in range(1, 5)]
    lines += ["", "## Projects and results", ""] + [f"- {e[f'rec.{i}.stat']}, {e[f'rec.{i}.name']} ({e[f'rec.{i}.role']}): {e[f'rec.{i}.body']}" for i in range(1, 6)]
    lines += ["", "## Featured work: Harpos", "", re.sub(r"<[^>]+>", "", e["feature.body"])]
    lines += ["", "## Projects", ""]
    for p in PROJECTS["projects"]:
        lines += [f"### {p['en']['name']}", "", f"URL: {BASE}{PAGES['p:' + p['slug']]['en']}", "", p["en"]["lead"], ""] + [t + "\n" for t in p["en"]["paragraphs"]]
    lines += ["", "## Milestones", ""] + [f"- {months[int(m) - 1]} {y}: {e[k]}" for k, y, m in ms]
    lines += ["", "## Frequently asked questions", ""]
    for q, a in CONTENT["faq"]["en"]:
        lines += [f"### {q}", "", a, ""]
    lines += ["## Sık sorulanlar (Türkçe)", ""]
    for q, a in CONTENT["faq"]["tr"]:
        lines += [f"### {q}", "", a, ""]
    lines += ["## Contact", "", "- Email: ykpgunduz@icloud.com", "- GitHub: https://github.com/yakup-gunduz", "- LinkedIn: https://www.linkedin.com/in/yakupgunduz", "- Harpos: https://harpos.app", "", f"Last updated: {TODAY}", ""]
    return "\n".join(lines)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


PAGE_IMAGES = {
    "home": ["feature-workspace.webp", "harpos-pos.webp", "svc-app.webp", "svc-web.webp", "svc-db.webp", "svc-automation.webp"],
}


def build_dist():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    for page, urls in PAGES.items():
        for lang, url in urls.items():
            write(DIST / url.strip("/") / "index.html", page_html(lang, page))
    write(DIST / "404.html", not_found("tr"))
    write(DIST / "en" / "404.html", not_found("en"))
    shutil.copytree(ROOT / "assets", DIST / "assets", ignore=shutil.ignore_patterns("*.ai", ".DS_Store"))
    shutil.copy(ROOT / "assets" / "brand" / "favicon.ico", DIST / "favicon.ico")
    shutil.copy(ROOT / "assets" / "brand" / "apple-touch-icon.png", DIST / "apple-touch-icon.png")
    for name in ("robots.txt", "llms.txt"):
        text = (ROOT / "src" / name).read_text(encoding="utf-8").replace("{{DATE}}", TODAY)
        write(DIST / name, text)
    write(DIST / "llms-full.txt", llms_full())
    key = (ROOT / "src" / "indexnow.key").read_text().strip()
    write(DIST / f"{key}.txt", key)
    urls = []
    for page, langs in PAGES.items():
        for lang, path in langs.items():
            alts = "".join(f'\n    <xhtml:link rel="alternate" hreflang="{l}" href="{BASE + langs[l]}"/>' for l in ("tr", "en"))
            alts += f'\n    <xhtml:link rel="alternate" hreflang="x-default" href="{BASE + langs["tr"]}"/>'
            img = "".join(f'\n    <image:image><image:loc>{BASE}/assets/img/{name}</image:loc></image:image>' for name in PAGE_IMAGES.get(page, []))
            urls.append(f"  <url>\n    <loc>{BASE + path}</loc>\n    <lastmod>{page_modified(page)[:10]}</lastmod>{alts}{img}\n  </url>")
    write(DIST / "sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n' + "\n".join(urls) + "\n</urlset>\n")
    sizes = {str(p.relative_to(DIST)): p.stat().st_size for p in DIST.rglob("*.html")}
    print("dist pages:", sizes)


if __name__ == "__main__":
    build_dist()
