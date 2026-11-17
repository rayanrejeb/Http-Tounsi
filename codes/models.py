from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.templatetags.static import static

IMAGE_EXTS = ('webp', 'png', 'jpg', 'jpeg')
SECTION_NAMES = ('hero', 'services-web', 'api', 'soap-rest', 'xml-json', 'verbes', 'token',
                 'graphql', '2xx', '3xx', '4xx', '5xx', 'fin')


def find_image(folder, name, request=None):
    """URL de static/img/<folder>/<name>.<ext> (première extension trouvée), ou None.

    Cherché à chaque appel : une image déposée apparaît sans redémarrer.
    ?v=<mtime> force le navigateur à recharger une image remplacée.
    """
    if not name:
        return None
    for ext in IMAGE_EXTS:
        f = settings.BASE_DIR / 'static' / 'img' / folder / f'{name}.{ext}'
        if f.is_file():
            url = f'{static(f"img/{folder}/{name}.{ext}")}?v={int(f.stat().st_mtime)}'
            return request.build_absolute_uri(url) if request else url
    return None


class StatusCode(models.Model):
    code = models.PositiveSmallIntegerField(unique=True, validators=[MinValueValidator(100), MaxValueValidator(599)])
    nom_officiel = models.CharField(max_length=80, blank=True)
    titre_derja = models.CharField(max_length=120)
    situation = models.TextField(blank=True)
    explication_technique = models.TextField(blank=True)
    famille = models.CharField(max_length=3, editable=False)  # déduite du code : 404 -> "4xx"
    propose_par = models.CharField(max_length=60, blank=True, null=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']

    def save(self, *args, **kwargs):
        self.famille = f'{str(self.code)[0]}xx'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.code} — {self.titre_derja}'


class Slide(models.Model):
    numero = models.PositiveSmallIntegerField(unique=True)
    titre = models.CharField(max_length=120)
    contenu = models.TextField(blank=True, help_text='"- " puce, **gras**, `code`, "> GET /api/x/ {body}" requête cliquable')
    image = models.CharField(max_length=40, blank=True, help_text='Nom dans static/img/sections/ sans extension, ou "familles"')

    class Meta:
        ordering = ['numero']

    def __str__(self):
        return f'{self.numero}. {self.titre}'
