"""Les requêtes de la démo, dans l'ordre de la présentation (et du README).

Source unique pour `manage.py check_demo` et pour les tests (un test par étape).
"""
import json

SOAP_ENVELOPE = (
    '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="urn:http-tounsi:codes">'
    '<soap:Body><tns:GetCode><tns:Code>{}</tns:Code></tns:GetCode></soap:Body></soap:Envelope>'
)
PROPOSITION = {  # le code 420 créé puis supprimé pendant la démo des tokens
    'code': 420, 'nom_officiel': 'Enhance Your Calm', 'titre_derja': 'Ched a3sabek',
    'situation': 'Le chauffeur de louage klaxonne depuis dix minutes.', 'propose_par': 'La salle',
}
PUT_404 = {
    'code': 404, 'nom_officiel': 'Not Found', 'titre_derja': 'Mal9itouch',
    'situation': "Le prof cherche ta copie d'examen : elle n'a jamais existé.",
    'explication_technique': 'Aucune ressource ne correspond à cette URL.',
}


def step(expect, method, path, label, body=None, token=None, **opts):
    return {'expect': expect, 'method': method, 'path': path, 'label': label, 'body': body, 'token': token, **opts}


STEPS = [
    step(200, 'GET', '/api/slides/1/', 'Navigation : la présentation est une requête'),
    step(200, 'GET', '/api/codes/', 'GET liste : la galerie', card=True),
    step(200, 'GET', '/api/codes/200/', 'GET détail : Behi, ya3tik essa7a'),
    step(200, 'POST', '/soap/codes/', 'SOAP : vraie enveloppe XML', SOAP_ENVELOPE.format(404)),
    step(500, 'POST', '/soap/codes/', 'SOAP : code introuvable -> soap:Fault (Tay7et)', SOAP_ENVELOPE.format(999)),
    step(404, 'GET', '/api/codes/999/', 'REST : code introuvable -> simple 404 (Mal9itouch)', card=True),
    step(200, 'GET', '/api/codes/404/?format=xml', 'XML vs JSON : même fiche en XML'),
    step(200, 'POST', '/graphql/', 'GraphQL : seulement titreDerja et imageUrl',
         {'query': '{ code(code: 404) { titreDerja imageUrl } }'}),
    step(200, 'PUT', '/api/codes/404/', 'PUT, token admin Alt+A : repeindre tout le mur', PUT_404, token='admin'),
    step(200, 'PATCH', '/api/codes/404/', 'PATCH, token admin Alt+A : retoucher une tache',
         {'titre_derja': 'Mal9itha !'}, token='admin'),
    step(201, 'POST', '/api/codes/', 'POST : proposition (Mabrouk, t3mal !)', PROPOSITION, card=True),
    step(400, 'POST', '/api/codes/', 'POST invalide (Chnowa t9oul enti ?!)', {'code': 'abc'}, card=True),
    step(405, 'DELETE', '/api/codes/', 'DELETE sur la liste (Cash bark)', card=True),
    step(401, 'DELETE', '/api/codes/420/', 'DELETE sans token (Chkoun enti ?)', before=['proposition'], card=True),
    step(403, 'DELETE', '/api/codes/420/', 'DELETE token étudiant, Alt+E (Hedhom lel dhyouf !)',
         token='etudiant', before=['proposition'], card=True),
    step(204, 'DELETE', '/api/codes/420/', 'DELETE token admin, Alt+A (Walou)', token='admin', before=['proposition'], card=True),
    step(304, 'GET', '/api/codes/200/', 'Rejouer avec If-None-Match (Nafs el 7aja)', etag=True, card=True),
    step(301, 'GET', '/api/ancien-codes/', 'Ancienne URL (El 7anout bdal blastou)', card=True),
    step(418, 'GET', '/api/cafe/', 'Ena berrad, mouch machine café', card=True),
    step(429, 'GET', '/api/mama/', '4 clics rapides (Yezzi, ta3abtni !)', repeat=4, card=True),
    step(500, 'GET', '/api/boom/', 'Exception volontaire (Tay7et)', card=True),
    step(502, 'GET', '/api/simulate/502/', 'El samsar ghaltek', card=True),
    step(503, 'GET', '/api/idara/', 'Erja3 ghodwa (Retry-After: 86400)', card=True),
    step(504, 'GET', '/api/simulate/504/', 'El louage mazel ma t3abech (attente)', card=True),
    step(404, 'GET', '/api/n-importe-quoi/', 'URL inconnue (Mal9itouch)'),
    step(204, 'DELETE', '/api/presentation/', 'Fin : Ya3tikom essa7a'),
]


def send(client, tokens, method, path, body=None, token=None, headers=None):
    headers = dict(headers or {})
    if token:
        headers['Authorization'] = f'Token {tokens[token]}'
    kwargs = {}
    if isinstance(body, str):
        kwargs = {'data': body, 'content_type': 'text/xml; charset=utf-8'}
        headers['SOAPAction'] = '"urn:http-tounsi:codes#GetCode"'
    elif body is not None:
        kwargs = {'data': json.dumps(body), 'content_type': 'application/json'}
    return client.generic(method, path, headers=headers, **kwargs)


def run_step(client, tokens, s):
    """Joue une étape (avec ses préparatifs) et renvoie la dernière réponse."""
    if 'proposition' in s.get('before', []):
        send(client, tokens, 'POST', '/api/codes/', PROPOSITION)  # 400 si déjà là : sans importance
    headers = {}
    if s.get('etag'):
        headers['If-None-Match'] = send(client, tokens, s['method'], s['path'])['ETag']
    for _ in range(s.get('repeat', 1)):
        r = send(client, tokens, s['method'], s['path'], s['body'], s['token'], headers)
    return r


def card_triggers():
    """Pour chaque code : la requête de démo qui le déclenche (bouton « Déclencher » de sa fiche)."""
    out = {}
    for s in STEPS:
        if s.get('card'):
            body = s['body'] if s['body'] is None or isinstance(s['body'], str) else json.dumps(s['body'], ensure_ascii=False)
            out[s['expect']] = {'line': f"{s['method']} {s['path']}" + (f' {body}' if body else ''), 'hint': s['label']}
    return out
