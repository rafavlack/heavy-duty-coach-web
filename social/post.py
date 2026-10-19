"""Publica la siguiente entrada de social/posts.json en las redes configuradas.

Lo lanza .github/workflows/social.yml. Cada red se activa si sus variables existen:
  Bluesky: BSKY_HANDLE, BSKY_APP_PASSWORD
  Buffer:  BUFFER_API_KEY (publica en todos los canales conectados en Buffer:
           Instagram, Facebook, Threads...; no hace falta cuenta de desarrollador de Meta)

  python social/post.py --check     valida posts.json sin red
  python social/post.py --dry-run   enseña lo que publicaría
  python social/post.py             publica y avanza social/state.json
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOCIAL = ROOT / "social"
SITE = "https://heavy-duty-coach-web.rafavlack.workers.dev"
BUFFER = "https://api.buffer.com"
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


def request(url, data=None, headers=None):
    if isinstance(data, (dict, list)):
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


def buffer(query, variables=None):
    res = request(BUFFER, {"query": query, "variables": variables or {}},
                  {"Authorization": f"Bearer {os.environ['BUFFER_API_KEY']}"})
    if res.get("errors"):  # GraphQL responde 200 aunque la consulta falle
        raise RuntimeError(f"Buffer: {res['errors'][0].get('message')}")
    return res["data"]


def buffer_channels():
    orgs = buffer("{ account { organizations { id } } }")["account"]["organizations"]
    channels = []
    for org in orgs:
        channels += buffer(f"{{ channels(input: {{organizationId: {json.dumps(org['id'])}}}) "
                           "{ id service isQueuePaused } }")["channels"]
    # Si Bluesky ya va directo, no lo dupliques desde Buffer.
    direct = os.environ.get("BSKY_HANDLE") and os.environ.get("BSKY_APP_PASSWORD")
    return [c for c in channels if not c["isQueuePaused"] and not (direct and c["service"] == "bluesky")]


def post_buffer(post):
    channels = buffer_channels()
    if not channels:
        raise RuntimeError("Buffer: no hay canales activos; conecta Instagram o Facebook en publish.buffer.com")
    # Unos minutos de margen: Buffer descarga la imagen antes de publicar.
    due = datetime.fromtimestamp(time.time() + 300, timezone.utc).isoformat().replace("+00:00", "Z")
    done, errors = [], []
    for c in channels:
        text = {"instagram": instagram_caption, "bluesky": bluesky_text}.get(c["service"], facebook_caption)(post)
        res = buffer("mutation($input: CreatePostInput!) { createPost(input: $input) {"
                     " ... on PostActionSuccess { post { id } } ... on MutationError { message } } }",
                     {"input": {"channelId": c["id"], "text": text, "schedulingType": "automatic",
                                "mode": "customScheduled", "dueAt": due,
                                "assets": [{"image": {"url": card_url(post)}}]}})
        out = res["createPost"]
        (done if "post" in out else errors).append(f"{c['service']}:{out.get('post', {}).get('id') or out.get('message')}")
    if errors:
        raise RuntimeError(f"programados {done}; fallaron {errors}")
    return f"programados para {due}: {', '.join(done)}"


NETWORKS = {
    "bluesky": (("BSKY_HANDLE", "BSKY_APP_PASSWORD"), post_bluesky),
    "buffer": (("BUFFER_API_KEY",), post_buffer),
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
        print(f"\n[Bluesky]\n{bluesky_text(post)}\n\n[Facebook, Threads...]\n{facebook_caption(post)}"
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
