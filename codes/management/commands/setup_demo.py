import secrets

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from rest_framework.authtoken.models import Token

from codes.models import StatusCode


class Command(BaseCommand):
    help = ("Recharge les 16 codes et les slides, (re)crée l'admin et l'étudiant non admin, "
            "puis affiche leurs tokens. Relance-la juste avant la présentation pour tout remettre à zéro.")

    def handle(self, *args, **options):
        StatusCode.objects.all().delete()  # efface aussi les propositions des répétitions
        call_command('loaddata', 'codes', 'slides', verbosity=0)
        User = get_user_model()
        out = []
        # Mots de passe et tokens neufs à chaque lancement : le token tapé devant
        # la salle (et photographié) ne sert plus après la présentation.
        for username, is_admin in (('admin', True), ('etudiant', False)):
            user, _ = User.objects.get_or_create(username=username)
            user.is_staff = user.is_superuser = is_admin
            password = secrets.token_urlsafe(6)
            user.set_password(password)
            user.save()
            Token.objects.filter(user=user).delete()
            out.append((username, password, Token.objects.create(user=user).key, is_admin))

        w = self.stdout.write
        w(self.style.SUCCESS('16 codes et slides rechargés (propositions effacées).\n'))
        for username, password, key, is_admin in out:
            role = 'ADMIN : DELETE -> 204' if is_admin else 'NON ADMIN : DELETE -> 403'
            w(self.style.MIGRATE_HEADING(f'{username}  ({role})'))
            w(f'  token        : {key}')
            if is_admin:
                w(f'  mot de passe : {password}   (pour /admin/)')
            w('')
        w('Sans token : DELETE -> 401.\n')
        w('Raccourcis : Alt+A token admin · Alt+E token étudiant · ← → slides · ↑ remonter')
