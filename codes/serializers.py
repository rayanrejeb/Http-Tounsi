from rest_framework import serializers

from .models import Slide, StatusCode, find_image


class StatusCodeSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = StatusCode
        fields = ['code', 'nom_officiel', 'titre_derja', 'situation', 'explication_technique',
                  'famille', 'propose_par', 'image_url', 'cree_le']

    def get_image_url(self, obj):
        return find_image('codes', obj.code, self.context.get('request'))


class SlideSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = Slide
        fields = ['numero', 'total', 'titre', 'contenu', 'image', 'image_url']

    def get_image_url(self, obj):
        return find_image('sections', obj.image, self.context.get('request'))

    def get_total(self, obj):
        return Slide.objects.count()
