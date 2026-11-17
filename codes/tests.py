import re
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

from .demo import STEPS, run_step


class ApiTests(APITestCase):
    fixtures = ['codes', 'slides']

    def setUp(self):
        self.admin = Token.objects.create(user=User.objects.create(username='a', is_staff=True)).key
        self.etudiant = Token.objects.create(user=User.objects.create(username='e')).key

    def test_lecture_et_filtre(self):
        self.assertEqual(len(self.client.get('/api/codes/').json()), 16)
        r = self.client.get('/api/codes/?famille=4xx').json()
        self.assertEqual({c['famille'] for c in r}, {'4xx'})
        self.assertEqual(self.client.get('/api/codes/404/').json()['titre_derja'], 'Mal9itouch')
        self.assertEqual(self.client.get('/api/codes/999/').status_code, 404)
        self.assertEqual(self.client.get('/api/slides/3/').json()['total'], 11)

    def test_post_put_patch(self):
        self.assertEqual(self.client.post('/api/codes/', {'code': 777, 'titre_derja': 'x'}, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/codes/', {'code': 404, 'titre_derja': 'x'}, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/codes/', {'code': 'abc'}, format='json').status_code, 400)
        r = self.client.post('/api/codes/', {'code': 299, 'titre_derja': 'Jdid', 'propose_par': 'Salma'}, format='json')
        self.assertEqual((r.status_code, r.json()['famille']), (201, '2xx'))
        self.assertEqual(self.client.patch('/api/codes/404/', {'titre_derja': 'x'}, format='json').status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.etudiant}')
        self.assertEqual(self.client.put('/api/codes/404/', {'titre_derja': 'x'}, format='json').status_code, 403)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin}')
        self.assertEqual(self.client.put('/api/codes/404/', {'titre_derja': 'x'}, format='json').status_code, 400)
        r = self.client.patch('/api/codes/404/', {'titre_derja': 'Mal9itha !'}, format='json')
        self.assertEqual((r.status_code, r.json()['titre_derja']), (200, 'Mal9itha !'))
        self.assertEqual(self.client.delete('/api/codes/').status_code, 405)

    def test_delete_401_403_204(self):
        self.assertEqual(self.client.delete('/api/codes/404/').status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.etudiant}')
        self.assertEqual(self.client.delete('/api/codes/404/').status_code, 403)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin}')
        self.assertEqual(self.client.delete('/api/codes/404/').status_code, 204)

    def test_xml_soap_graphql(self):
        r = self.client.get('/api/codes/404/?format=xml')
        self.assertIn('<titre_derja>Mal9itouch</titre_derja>', r.content.decode())
        r = self.client.post('/soap/codes/', content_type='text/xml', data=(
            '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="urn:http-tounsi:codes">'
            '<soap:Body><tns:GetCode><tns:Code>418</tns:Code></tns:GetCode></soap:Body></soap:Envelope>'))
        self.assertEqual(r.status_code, 200)
        self.assertIn('<tns:TitreDerja>Ena berrad, mouch machine café</tns:TitreDerja>', r.content.decode())
        self.assertEqual(self.client.get('/soap/codes/?code=999').status_code, 500)  # SOAP Fault
        self.assertEqual(self.client.post('/soap/codes/', content_type='text/xml', data='<pas du xml').status_code, 500)
        r = self.client.post('/graphql/', {'query': '{ code(code: 404) { titreDerja imageUrl } }'}, format='json')
        code = r.json()['data']['code']
        self.assertEqual(set(code), {'titreDerja', 'imageUrl'})  # exactement les champs demandés
        self.assertEqual(code['titreDerja'], 'Mal9itouch')

    def test_image_detectee_sans_toucher_au_code(self):
        f = settings.BASE_DIR / 'static' / 'img' / 'codes' / '599.jpeg'
        self.client.post('/api/codes/', {'code': 599, 'titre_derja': 't'}, format='json')
        self.assertIsNone(self.client.get('/api/codes/599/').json()['image_url'])
        f.write_bytes(b'x')
        try:
            self.assertIn('/static/img/codes/599.jpeg?v=', self.client.get('/api/codes/599/').json()['image_url'])
        finally:
            f.unlink()

    def test_post_limite_par_telephone_pas_pour_le_pc(self):
        cache.clear()
        phone = {'REMOTE_ADDR': '192.168.1.50'}
        codes = [self.client.post('/api/codes/', {'code': 590 + i, 'titre_derja': 't'}, format='json', **phone).status_code
                 for i in range(6)]
        self.assertEqual(codes, [201] * 5 + [429])
        self.assertEqual(self.client.post('/api/codes/', {'code': 597, 'titre_derja': 't'}, format='json').status_code, 201)

    def test_session_admin_sans_csrf_ni_effet(self):
        """Connecté à /admin/ dans le même navigateur : aucun 403 CSRF, et la session ne remplace pas le token."""
        c = APIClient(enforce_csrf_checks=True)
        c.force_login(User.objects.get(username='a'))
        self.assertEqual(c.post('/api/codes/', {'code': 299, 'titre_derja': 't'}, format='json').status_code, 201)
        self.assertEqual(c.delete('/api/codes/299/').status_code, 401)


class DemoTests(TestCase):
    """Un test par étape de la démo (codes/demo.py), dans l'ordre du README."""
    fixtures = ['codes', 'slides']

    def setUp(self):
        cache.clear()
        self.tokens = {name: Token.objects.create(user=User.objects.create(username=name, is_staff=admin)).key
                       for name, admin in (('admin', True), ('etudiant', False))}


def _demo_test(s):
    def test(self):
        with mock.patch('codes.views.time.sleep'):  # pas d'attente réelle pour 502/504
            if s['path'] == '/api/boom/':
                with self.assertLogs('codes.views', 'ERROR'):  # l'exception est bien journalisée
                    r = run_step(self.client, self.tokens, s)
            else:
                r = run_step(self.client, self.tokens, s)
        self.assertEqual(r.status_code, s['expect'], f"{s['method']} {s['path']} : {s['label']}")
    return test


for _i, _s in enumerate(STEPS, 1):
    setattr(DemoTests, f"test_{_i:02d}_{_s['expect']}_{re.sub(r'[^a-z0-9]+', '_', _s['path'].lower()).strip('_')}",
            _demo_test(_s))
