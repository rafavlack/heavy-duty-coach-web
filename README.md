# Heavy Duty Coach · web

Landing estática (un `index.html`, sin build). Se publica en Cloudflare Pages y el APK en GitHub Releases de **este** repositorio, que debe ser **público**: los releases de un repo privado no se pueden descargar sin iniciar sesión.

## Publicar la web (una vez)

1. Crea el repo público `heavy-duty-coach-web` en GitHub y sube esta carpeta.
2. Cloudflare → Workers & Pages → Create → Pages → Connect to Git → elige el repo.
3. Framework preset: **None**. Build command: vacío. Build output directory: `/`.
4. Deploy. Queda en `https://heavy-duty-coach-web.pages.dev` (o el nombre que elijas), con HTTPS.

Cada push a la rama de producción vuelve a desplegar.

## Publicar una versión del APK

Los botones apuntan a
`https://github.com/rafavlack/heavy-duty-coach-web/releases/latest/download/heavy-duty-coach.apk`,
que siempre sirve el último release. Por eso el archivo **tiene que llamarse siempre `heavy-duty-coach.apk`**.

```bash
# en android-app/
./gradlew assembleRelease
cp app/build/outputs/apk/release/app-release.apk heavy-duty-coach.apk
gh release create v0.1.0 heavy-duty-coach.apk -R rafavlack/heavy-duty-coach-web \
  --title "v0.1.0" --notes "Primera versión pública"
```

Sube la versión (`versionCode`/`versionName` en `app/build.gradle.kts`) antes de cada release; Android no instala encima un APK con `versionCode` igual o menor.

Si cambias el usuario o el nombre del repo, sustituye la URL en `index.html` (todos los enlaces llevan `data-apk`).
