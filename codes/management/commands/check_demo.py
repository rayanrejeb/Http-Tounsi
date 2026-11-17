import logging
import sys

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction
from django.test import Client
from rest_framework.authtoken.models import Token

from codes.demo import STEPS, run_step
from codes.models import SECTION_NAMES, StatusCode, find_image


class Command(BaseCommand):
    help = ("Rejoue toutes les requêtes de la démo dans l'ordre du README et affiche attendu / obtenu / OK-KO. "
            "Tout se passe dans une transaction annulée : la base n'est pas modifiée.")

    def handle(self, *args, **options):
        w, ok_style, ko_style = self.stdout.write, self.style.SUCCESS, self.style.ERROR
        User = get_user_model()
        ready = all(Token.objects.filter(user__username=u).exists() for u in ('admin', 'etudiant'))
        failures = 0
        with transaction.atomic():
            # Utilisateurs jetables : le check ne dépend pas des tokens réels (ni ne les change).
            tokens = {}
            for name, admin in (('admin', True), ('etudiant', False)):
                u = User.objects.create(username=f'_check_{name}', is_staff=admin, is_superuser=admin)
                tokens[name] = Token.objects.create(user=u).key
            cache.clear()  # compteur du throttling de /api/mama/ (cache de ce processus seulement)
            client = Client(raise_request_exception=False)
            logging.disable(logging.CRITICAL)  # les 4xx/5xx voulus ne doivent pas noyer le tableau

            w(f"{'#':>2}  {'requête':<34} {'attendu':>7} {'obtenu':>6}       étape")
            for i, s in enumerate(STEPS, 1):
                got = run_step(client, tokens, s).status_code
                ok = got == s['expect']
                failures += not ok
                req = f"{s['method']} {s['path']}"
                tag = ok_style(' OK ') if ok else ko_style(' KO ')
                w(f"{i:>2}  {req[:34]:<34} {s['expect']:>7} {got:>6}  {tag}  {s['label']}")
            transaction.set_rollback(True)
        logging.disable(logging.NOTSET)

        w('')
        w(ok_style(f'Démo : {len(STEPS)}/{len(STEPS)} OK') if not failures
          else ko_style(f'Démo : {failures} KO sur {len(STEPS)}. Lance "python manage.py setup_demo" puis réessaie.'))
        if not ready:
            w(ko_style("Tokens admin/etudiant absents : lance \"python manage.py setup_demo\" (Alt+A / Alt+E en dépendent)."))

        codes = list(StatusCode.objects.values_list('code', flat=True))
        missing_codes = [c for c in codes if not find_image('codes', c)]
        missing_sections = [n for n in SECTION_NAMES if not find_image('sections', n)]
        w(f'Images : {len(codes) - len(missing_codes)}/{len(codes)} codes, '
          f'{len(SECTION_NAMES) - len(missing_sections)}/{len(SECTION_NAMES)} sections.')
        if missing_codes:
            w(f'  manquent dans static/img/codes/    : {", ".join(map(str, missing_codes))}')
        if missing_sections:
            w(f'  manquent dans static/img/sections/ : {", ".join(missing_sections)}')
        if missing_codes or missing_sections:
            w('  (placeholder affiché à la place ; .webp, .png, .jpg ou .jpeg)')
        if failures:
            sys.exit(1)
