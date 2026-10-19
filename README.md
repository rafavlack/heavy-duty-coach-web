# Heavy Duty Coach · web

Landing estática (un `index.html`, sin build). Se publica en Cloudflare Pages y el APK en GitHub Releases de **este** repositorio, que debe ser **público**: los releases de un repo privado no se pueden descargar sin iniciar sesión.

## Publicar la web (una vez)

1. Crea el repo público `heavy-duty-coach-web` en GitHub y sube esta carpeta.
2. Cloudflare → Workers & Pages → Create → Pages → Connect to Git → elige el repo.
3. Framework preset: **None**. Build command: vacío. Build output directory: `/`.
4. Deploy. Queda en `https://heavy-duty-coach-web.pages.dev` (o el nombre que elijas), con HTTPS.

Cada push a la rama de producción vuelve a desplegar. La web está desplegada como Worker en
`https://heavy-duty-coach-web.rafavlack.workers.dev`.

## Publicar una versión del APK

Los botones apuntan a
`https://github.com/rafavlack/heavy-duty-coach-web/releases/latest/download/heavy-duty-coach.apk`,
que siempre sirve el último release. Por eso el archivo **tiene que llamarse siempre `heavy-duty-coach.apk`**.

| Versión | versionCode | Release |
|---|---|---|
| 0.1.0 | 1 | v0.1.0, primera versión pública |
| 0.1.1 | 2 | v0.1.1, se instala encima de la 0.1.0 (la actual) |

Pasos, con la 0.1.1 como ejemplo:

1. **Sube la versión** en `android-app/app/build.gradle.kts`. Android no instala encima un APK con un
   `versionCode` igual o menor, así que súbelo siempre en 1:
   ```kotlin
   versionCode = 2
   versionName = "0.1.1"
   ```
   Haz commit y push a `develop` del repo de la app.
2. **Compila el release firmado** (en `android-app/`; necesita `keystore.properties` y `upload-key.jks`, que no están en git):
   ```bash
   ./gradlew :app:assembleRelease
   ```
3. **Comprueba el APK** antes de publicarlo (`apksigner` y `aapt2` están en `build-tools` del SDK):
   ```bash
   apksigner verify --print-certs app/build/outputs/apk/release/app-release.apk
   #   -> certificado SHA-256 b73041cd9769a301ac5afa654652b94cd81e22a9c4e4f0a5b47b203b250ed3aa
   aapt2 dump badging app/build/outputs/apk/release/app-release.apk | head -1
   #   -> versionCode='2' versionName='0.1.1'
   ```
   El certificado tiene que ser siempre el mismo: con otra clave, Android rechaza la actualización.
4. **Publica el release** con el nombre de archivo fijo:
   ```bash
   cp app/build/outputs/apk/release/app-release.apk heavy-duty-coach.apk
   gh release create v0.1.1 heavy-duty-coach.apk -R rafavlack/heavy-duty-coach-web \
     --title "Heavy Duty Coach 0.1.1" --notes "Versión 0.1.1 (versionCode 2). Android 8.0 o superior." --latest
   ```
   `gh` tiene que estar con la cuenta `rafavlack` (`gh auth switch -u rafavlack`).
5. **Verifica la descarga** sin sesión: el enlace de los botones debe devolver el APK nuevo.
   ```bash
   curl -sL -o /tmp/x.apk -w '%{http_code} %{size_download}\n' \
     https://github.com/rafavlack/heavy-duty-coach-web/releases/latest/download/heavy-duty-coach.apk
   ```

Si cambias el usuario o el nombre del repo, sustituye la URL en `index.html` (todos los enlaces llevan `data-apk`).
