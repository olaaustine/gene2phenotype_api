from rest_framework import generics
from rest_framework.response import Response

from gene2phenotype_app.serializers import (PanelSerializer,
                                            UserSerializer,
                                            PanelDetailSerializer,
                                            AttribTypeSerializer,
                                            AttribSerializer)

from gene2phenotype_app.models import Panel, User, AttribType, Attrib


class PanelList(generics.ListAPIView):
    queryset = Panel.objects.filter()
    serializer_class = PanelSerializer

class PanelDetail(generics.ListAPIView):
    lookup_field = 'name'
    serializer_class = PanelDetailSerializer

    def get_queryset(self):
        name = self.kwargs['name']
        return Panel.objects.filter(name=name)

class UserList(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class AttribTypeList(generics.ListAPIView):
    queryset = AttribType.objects.all()
    serializer_class = AttribTypeSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        code_list = [attrib.code for attrib in queryset]
        return Response(code_list)

class AttribList(generics.ListAPIView):
    lookup_field = 'type'
    serializer_class = AttribSerializer

    def get_queryset(self):
        code = self.kwargs['code']
        return Attrib.objects.filter(type=AttribType.objects.get(code=code))
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        code_list = [attrib.value for attrib in queryset]
        return Response(code_list)
