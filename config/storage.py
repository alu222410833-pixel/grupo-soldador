from whitenoise.storage import CompressedManifestStaticFilesStorage


class NonStrictManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """Manifest storage que no tumba el sitio si falta un archivo en el manifiesto.

    Con manifest_strict=True (el default), un {% static %} sin entrada en
    staticfiles.json lanza ValueError y la página entera da error 500. Con esto
    cae a la URL sin hash y WhiteNoise igual la sirve desde STATIC_ROOT.
    """

    manifest_strict = False
