import logging
import time

from defusedxml import ElementTree
from django.core.exceptions import BadRequest, PermissionDenied, SuspiciousOperation
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import Resolver404, resolve
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from .demo import card_triggers
from .models import SECTION_NAMES, Slide, StatusCode, find_image
from .serializers import SlideSerializer, StatusCodeSerializer

logger = logging.getLogger(__name__)


# ---------- pages ----------
def index(request):
    # Tokens pour Alt+A / Alt+E : seulement pour le PC du présentateur, jamais pour la salle.
    tokens = dict(Token.objects.filter(user__username__in=['admin', 'etudiant'])
                  .values_list('user__username', 'key')) if is_local(request) else {}
    return render(request, 'index.html', {'config': {
        'sections': {name: find_image('sections', name, request) for name in SECTION_NAMES},
        'tokens': tokens,
        'triggers': card_triggers(),
    }})


# ---------- API REST ----------
class AdminForChanges(permissions.BasePermission):
    """Lecture et POST ouverts. PUT, PATCH, DELETE : token admin.
    Sans token -> 401 (TokenAuthentication envoie WWW-Authenticate), token non admin -> 403."""
    message = "Hedhom lel dhyouf : réservé à l'admin."

    def has_permission(self, request, view):
        # Par action, pas par méthode : DELETE /api/codes/ (liste) doit rester un 405, pas un 401.
        if view.action not in ('update', 'partial_update', 'destroy'):
            return True
        return bool(request.user and request.user.is_staff)


def is_local(request):
    return request.META.get('REMOTE_ADDR') in ('127.0.0.1', '::1')


class ProposeThrottle(SimpleRateThrottle):
    """POST : 5 par minute et par appareil (IP) du réseau. Le PC du présentateur n'est jamais limité."""
    rate = '5/m'

    def allow_request(self, request, view):
        if request.method != 'POST' or is_local(request):
            return True
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': 'propose', 'ident': self.get_ident(request)}


class StatusCodeViewSet(viewsets.ModelViewSet):
    serializer_class = StatusCodeSerializer
    permission_classes = [AdminForChanges]
    throttle_classes = [ProposeThrottle]
    lookup_field = 'code'

    def get_queryset(self):
        famille = self.request.query_params.get('famille')
        qs = StatusCode.objects.all()
        return qs.filter(famille=famille) if famille else qs


class SlideViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Slide.objects.all()
    serializer_class = SlideSerializer
    lookup_field = 'numero'


# ---------- endpoints de démo ----------
@api_view(['GET'])
def boom(request):
    return Response({'resultat': 1 / 0})  # vrai 500 : ZeroDivisionError


@api_view(['GET'])
def idara(request):
    return Response({'detail': 'El guichet msaker. Erja3 ghodwa.'}, status=503, headers={'Retry-After': '86400'})


@api_view(['GET'])
def cafe(request):
    return Response({'detail': 'Ena berrad, mouch machine café.'}, status=418)


class MamaThrottle(SimpleRateThrottle):
    """3 appels par fenêtre de 10 s et par IP : le 4e clic rapide donne 429, et 10 s
    plus tard tout est oublié (pas de blocage après une répétition).
    DRF ne lit que la 1re lettre de la période ("3/10s" = 3/s) : on lit "10s" nous-mêmes."""
    rate = '3/10s'

    def parse_rate(self, rate):
        num, period = rate.split('/')
        return int(num), int(period[:-1] or 1) * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[period[-1]]

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': 'mama', 'ident': self.get_ident(request)}


@api_view(['GET'])
@throttle_classes([MamaThrottle])
def mama(request):
    return Response({'mama': 'Na3em ?'})


SIMULATE_DELAYS = {502: 1, 504: 4}  # secondes


@api_view(['GET'])
def simulate(request, code):
    if code not in SIMULATE_DELAYS:
        raise NotFound('Seuls 502 et 504 sont simulés.')
    time.sleep(SIMULATE_DELAYS[code])
    detail = {502: 'El samsar ghaltek : réponse invalide du serveur amont.',
              504: 'El louage mazel ma t3abech : le serveur amont a mis trop de temps.'}[code]
    return Response({'detail': detail}, status=code)


@api_view(['DELETE'])
def presentation(request):
    return Response(status=204)


@csrf_exempt  # un POST vers une URL inconnue doit donner 404, pas un 403 CSRF
def api_not_found(request):
    detail = 'Mal9itouch : aucune route ne correspond à cette URL.'
    if not request.path.endswith('/'):
        try:
            if resolve(request.path + '/').func is not api_not_found:
                detail += f' Il manque le slash final : {request.path}/'
        except Resolver404:
            pass
    return JsonResponse({'detail': detail}, status=404)


class ApiErrorsMiddleware:
    """Sous /api/, une exception devient un 500 JSON, même avec DEBUG=True
    (sinon Django renvoie sa page HTML de debug)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not request.path.startswith('/api/') or isinstance(
                exception, (Http404, PermissionDenied, BadRequest, SuspiciousOperation)):
            return None
        logger.exception('Tay7et sur %s', request.path)
        return JsonResponse({'detail': f'Tay7et : {type(exception).__name__}: {exception}'}, status=500)


# ---------- Mini service SOAP 1.1 : opération GetCode ----------
TNS = 'urn:http-tounsi:codes'


def _xml(template, context, status=200):
    return HttpResponse(render_to_string(template, context), status=status,
                        content_type='text/xml; charset=utf-8')


@csrf_exempt
def soap_codes(request):
    """POST : vraie enveloppe SOAP avec <tns:GetCode><tns:Code>404</tns:Code></tns:GetCode>.
    GET ?wsdl : le contrat WSDL. GET ?code=404 : raccourci de secours seulement."""
    if 'wsdl' in request.GET:
        return _xml('soap/codes.wsdl', {'url': request.build_absolute_uri(request.path)})

    def fault(code, msg):  # SOAP 1.1 : toute Fault part en HTTP 500
        return _xml('soap/envelope.xml', {'fault': {'code': code, 'message': msg}}, status=500)

    if request.method == 'POST':
        try:
            raw = ElementTree.fromstring(request.body).find(f'.//{{{TNS}}}Code').text
        except Exception:  # XML cassé, entités interdites, élément absent...
            return fault('soap:Client', 'Enveloppe invalide : il faut <tns:Code> dans <tns:GetCode>.')
    elif request.method == 'GET':
        raw = request.GET.get('code', '200')
    else:
        return fault('soap:Client', 'SOAP passe par POST (ou GET ?code= / ?wsdl).')

    try:
        c = StatusCode.objects.get(code=int(raw))
    except (ValueError, TypeError, StatusCode.DoesNotExist):
        return fault('soap:Client', f'Mal9itouch : aucun code « {raw} ».')
    return _xml('soap/envelope.xml', {'c': c, 'image_url': find_image('codes', c.code, request)})
