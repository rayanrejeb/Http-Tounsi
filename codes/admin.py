from django.contrib import admin

from .models import Slide, StatusCode

admin.site.register(StatusCode, list_display=('code', 'titre_derja', 'famille', 'propose_par'), list_filter=('famille',))
admin.site.register(Slide, list_display=('numero', 'titre', 'image'))
