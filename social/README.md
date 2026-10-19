# Publicación automática en redes

GitHub Actions (`.github/workflows/social.yml`) publica lunes, miércoles y viernes la siguiente entrada de `posts.json`, en rotación, en las redes configuradas. Coste cero: Actions es gratis en repos públicos y las tres API lo son.

Cada red se activa sola al añadir sus secrets en GitHub → repo → Settings → Secrets and variables → Actions.

## Bluesky (5 minutos)
1. Crea la cuenta en bsky.app.
2. Settings → Privacy and security → App passwords → Add.
3. Secrets: `BSKY_HANDLE` (p. ej. `heavydutycoach.bsky.social`) y `BSKY_APP_PASSWORD`.

## Facebook e Instagram (una sola app de Meta)
1. Crea una **página de Facebook** y pasa Instagram a **cuenta profesional** (Creador o Empresa) enlazada a esa página.
2. developers.facebook.com → Create app → tipo Business. Añade los productos *Facebook Login for Business* e *Instagram*. Para publicar en tus propias cuentas no hace falta App Review: tú eres administrador de la app.
3. Graph API Explorer → elige la app → pide `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`, `business_management` → Generate Access Token.
4. Cambia ese token por uno de larga duración (Access Token Debugger → Extend) y pide `GET /me/accounts`: el `access_token` de tu página **no caduca**. Ese es `FB_PAGE_TOKEN`, y el `id`, `FB_PAGE_ID`.
5. `GET /{FB_PAGE_ID}?fields=instagram_business_account` → el `id` es `IG_USER_ID`.

## Uso
- Probar sin publicar: `python social/post.py --dry-run`
- Publicar ya: GitHub → Actions → *Publicar en redes* → Run workflow.
- Añadir publicaciones: edita `posts.json`, ejecuta `python social/make_cards.py` (necesita Pillow) y sube los cambios. Las tarjetas deben estar desplegadas antes de publicar, porque Instagram y Facebook las descargan desde la web.
- `state.json` guarda cuál toca; se actualiza solo.
