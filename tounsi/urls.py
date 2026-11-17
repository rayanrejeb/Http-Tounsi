from django.contrib import admin
from django.urls import include, path, re_path
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import RedirectView
from graphene_django.views import GraphQLView
from rest_framework.routers import DefaultRouter

from codes import views

router = DefaultRouter()
router.register('codes', views.StatusCodeViewSet, basename='code')
router.register('slides', views.SlideViewSet, basename='slide')

urlpatterns = [
    path('', views.index, name='home'),
    # démos de codes
    path('api/boom/', views.boom),
    path('api/idara/', views.idara),
    path('api/cafe/', views.cafe),
    path('api/mama/', views.mama),
    path('api/ancien-codes/', RedirectView.as_view(url='/api/codes/', permanent=True, query_string=True)),
    path('api/simulate/<int:code>/', views.simulate),
    path('api/presentation/', views.presentation),
    path('api/', include(router.urls)),
    re_path(r'^api/', views.api_not_found),  # toute autre URL /api/... -> 404 JSON
    path('soap/codes/', views.soap_codes, name='soap-codes'),
    path('graphql/', csrf_exempt(GraphQLView.as_view(graphiql=True)), name='graphql'),
    path('admin/', admin.site.urls),
]
