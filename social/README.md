# Publicación automática en redes

GitHub Actions (`.github/workflows/social.yml`) publica lunes, miércoles y viernes la siguiente entrada de `posts.json`, en rotación, en las redes configuradas. Coste cero: Actions es gratis en repos públicos y las tres API lo son.

Cada red se activa sola al añadir sus secrets en GitHub → repo → Settings → Secrets and variables → Actions.

## Bluesky (5 minutos)
1. Crea la cuenta en bsky.app.
2. Settings → Privacy and security → App passwords → Add.
3. Secrets: `BSKY_HANDLE` (p. ej. `heavydutycoach.bsky.social`) y `BSKY_APP_PASSWORD`.

## Instagram, Facebook y más, vía Buffer (sin cuenta de desarrollador de Meta)
Buffer publica con su propia app de Meta ya aprobada. Plan gratuito: 3 canales y API incluida.
1. Pasa Instagram a **cuenta profesional** (Creador o Empresa). Para Facebook, crea una **página**.
2. Crea la cuenta en buffer.com y conecta los canales (Instagram, página de Facebook, Threads...).
3. publish.buffer.com/settings/api → *Create a new API key*.
4. Secret: `BUFFER_API_KEY`. No hacen falta IDs: el script publica en todos los canales activos de Buffer
   (salvo Bluesky si ya va directo). Pausa la cola de un canal en Buffer para excluirlo.

## Uso
- Probar sin publicar: `python social/post.py --dry-run`
- Publicar ya: GitHub → Actions → *Publicar en redes* → Run workflow.
- Añadir publicaciones: edita `posts.json`, ejecuta `python social/make_cards.py` (necesita Pillow) y sube los cambios. Las tarjetas deben estar desplegadas antes de publicar, porque Instagram y Facebook las descargan desde la web.
- `state.json` guarda cuál toca; se actualiza solo.
