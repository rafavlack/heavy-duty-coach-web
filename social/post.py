"""Publica la siguiente entrada de social/posts.json en las redes configuradas.

Lo lanza .github/workflows/social.yml. Cada red se activa si sus variables existen:
  Bluesky:   BSKY_HANDLE, BSKY_APP_PASSWORD
  Facebook:  FB_PAGE_ID, FB_PAGE_TOKEN
  Instagram: IG_USER_ID, FB_PAGE_TOKEN (cuenta profesional enlazada a esa página)

  python social/post.py --check     valida posts.json sin red
  python social/post.py --dry-run   enseña lo que publicaría
  python social/post.py             publica y avanza social/state.json
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOCIAL = ROOT / "social"
SITE = "https://heavy-duty-coach-web.rafavlack.workers.dev"
GRAPH = "https://graph.facebook.com/v23.0"
BSKY = "https://bsky.social/xrpc"
TAGS = {
    "es": "#HeavyDuty #MikeMentzer #EntrenamientoDeFuerza #Hipertrofia #Gimnasio #HIT",
    "en": "#HeavyDuty #MikeMentzer #HIT #StrengthTraining #Bodybuilding #GymLife",
}
IN_BIO = {"es": "Descárgala gratis: enlace en la bio.", "en": "Free download: link in bio."}


def link(post):
    return SITE + ("/?lang=en" if post["lang"] == "en" else "/")


def card_path(post):
    return SOCIAL / "cards" / f"{post['id']}.jpg"


def card_url(post):
    return f"{SITE}/social/cards/{post['id']}.jpg"


def bluesky_text(post):
    return f"{post['text']}\n\n{link(post)}"


def instagram_caption(post):
    return f"{post['title']}\n\n{post['text']}\n\n{IN_BIO[post['lang']]}\n\n{TAGS[post['lang']]}"


def facebook_caption(post):
    return f"{post['title']}\n\n{post['text']}\n\n{link(post)}"


def check(posts):
    """Límites de cada red; si algo no cabe, falla antes de publicar a medias."""
    errors = []
    ids = [p["id"] for p in posts]
    if len(ids) != len(set(ids)):
        errors.append("ids repetidos")
    for p in posts:
        missing = {"id", "lang", "title", "image", "text", "alt"} - p.keys()
        if missing:
            errors.append(f"{p.get('id')}: faltan {sorted(missing)}")
            continue
        if p["lang"] not in TAGS:
            errors.append(f"{p['id']}: idioma {p['lang']}")
        if not card_path(p).exists():
            errors.append(f"{p['id']}: falta la tarjeta, ejecuta social/make_cards.py")
        # Bluesky cuenta grafemas; los textos no llevan emojis, así que len() basta.
        if len(bluesky_text(p)) > 300:
            errors.append(f"{p['id']}: Bluesky {len(bluesky_text(p))}/300")
        if len(instagram_caption(p)) > 2200 or instagram_caption(p).count("#") > 30:
            errors.append(f"{p['id']}: pie de Instagram demasiado largo")
        if len(p["alt"]) > 1000:
            errors.append(f"{p['id']}: alt demasiado largo")
        if card_path(p).exists() and card_path(p).stat().st_size > 950_000:
            errors.append(f"{p['id']}: la tarjeta pasa del límite de Bluesky (~976 KB)")
    return errors


def request(url, data=None, headers=None, form=None):
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
    elif isinstance(data, (dict, list)):
        data = json.dumps(data).encode()
        headers = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return json.loads(res.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{e.code} {url.split('?')[0]}: {e.read().decode(errors='replace')[:300]}") from None


def post_bluesky(post):
    session = request(f"{BSKY}/com.atproto.server.createSession",
                      {"identifier": os.environ["BSKY_HANDLE"], "password": os.environ["BSKY_APP_PASSWORD"]})
    auth = {"Authorization": f"Bearer {session['accessJwt']}"}
    blob = request(f"{BSKY}/com.atproto.repo.uploadBlob", card_path(post).read_bytes(),
                   {**auth, "Content-Type": "image/jpeg"})["blob"]
    text = bluesky_text(post)
    # Bluesky no enlaza URLs solo: hace falta un facet con su posición en bytes UTF-8.
    start = len(text.encode()) - len(link(post).encode())
    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "langs": [post["lang"]],
        "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "facets": [{"index": {"byteStart": start, "byteEnd": len(text.encode())},
                    "features": [{"$type": "app.bsky.richtext.facet#link", "uri": link(post)}]}],
        "embed": {"$type": "app.bsky.embed.images",
                  "images": [{"alt": post["alt"], "image": blob, "aspectRatio": {"width": 1080, "height": 1350}}]},
    }
    res = request(f"{BSKY}/com.atproto.repo.createRecord",
                  {"repo": session["did"], "collection": "app.bsky.feed.post", "record": record}, auth)
    return res["uri"]


def post_facebook(post):
    res = request(f"{GRAPH}/{os.environ['FB_PAGE_ID']}/photos",
                  form={"url": card_url(post), "caption": facebook_caption(post),
                        "access_token": os.environ["FB_PAGE_TOKEN"]})
    return res.get("post_id") or res["id"]


def post_instagram(post):
    ig, token = os.environ["IG_USER_ID"], os.environ["FB_PAGE_TOKEN"]
    container = request(f"{GRAPH}/{ig}/media", form={
        "image_url": card_url(post), "caption": instagram_caption(post),
        "alt_text": post["alt"], "access_token": token})["id"]
    # Instagram procesa la imagen en segundo plano; publicar antes de FINISHED falla.
    for _ in range(12):
        status = request(f"{GRAPH}/{container}?" + urllib.parse.urlencode(
            {"fields": "status_code", "access_token": token})).get("status_code")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise RuntimeError(f"Instagram no pudo procesar {card_url(post)}")
        time.sleep(5)
    return request(f"{GRAPH}/{ig}/media_publish", form={"creation_id": container, "access_token": token})["id"]


NETWORKS = {
    "bluesky": (("BSKY_HANDLE", "BSKY_APP_PASSWORD"), post_bluesky),
    "facebook": (("FB_PAGE_ID", "FB_PAGE_TOKEN"), post_facebook),
    "instagram": (("IG_USER_ID", "FB_PAGE_TOKEN"), post_instagram),
}


def main(args):
    posts = json.loads((SOCIAL / "posts.json").read_text(encoding="utf-8"))
    errors = check(posts)
    if errors or "--check" in args:
        print("\n".join(errors) or f"OK: {len(posts)} publicaciones válidas")
        return 1 if errors else 0

    state_file = SOCIAL / "state.json"
    state = json.loads(state_file.read_text()) if state_file.exists() else {"next": 0}
    post = posts[state["next"] % len(posts)]
    enabled = {name: fn for name, (keys, fn) in NETWORKS.items() if all(os.environ.get(k) for k in keys)}

    if "--dry-run" in args:
        print(f"Siguiente: #{state['next']} {post['id']} -> {sorted(enabled) or 'ninguna red configurada'}")
        print(f"\n[Bluesky]\n{bluesky_text(post)}\n\n[Facebook]\n{facebook_caption(post)}"
              f"\n\n[Instagram]\n{instagram_caption(post)}\n\nImagen: {card_url(post)}")
        return 0
    if not enabled:
        print("Ninguna red configurada: añade los secrets del repo (ver social/README.md).")
        return 0

    failed = []
    for name, fn in enabled.items():
        try:
            print(f"{name}: publicado {fn(post)}")
        except Exception as e:  # una red caída no debe impedir publicar en las demás
            failed.append(name)
            print(f"{name}: ERROR {e}", file=sys.stderr)

    # Avanza si salió en alguna red, para no repetir la entrada en las que sí funcionaron.
    if len(failed) < len(enabled):
        state_file.write_text(json.dumps({"next": state["next"] + 1, "last": post["id"]}) + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
