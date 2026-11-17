import graphene
from graphene_django import DjangoObjectType

from .models import StatusCode, find_image


class StatusCodeType(DjangoObjectType):
    image_url = graphene.String()

    class Meta:
        model = StatusCode
        fields = ('code', 'nom_officiel', 'titre_derja', 'situation', 'explication_technique',
                  'famille', 'propose_par', 'cree_le')

    def resolve_image_url(self, info):
        return find_image('codes', self.code, info.context)


class Query(graphene.ObjectType):
    codes = graphene.List(graphene.NonNull(StatusCodeType), famille=graphene.String())
    code = graphene.Field(StatusCodeType, code=graphene.Int(required=True))

    def resolve_codes(root, info, famille=None):
        qs = StatusCode.objects.all()
        return qs.filter(famille=famille) if famille else qs

    def resolve_code(root, info, code):
        return StatusCode.objects.filter(code=code).first()


schema = graphene.Schema(query=Query)
