from rest_framework import generics
from rest_framework.response import Response

from gene2phenotype_app.models import Panel

from gene2phenotype_app.serializers import PanelDetailSerializer

from .base import BaseView


class PanelList(generics.ListAPIView):
    """
        Display all panels info.
        The information includes some stats: 
            - total number of records linked to panel
            - total number of genes linked to panel
            - total number of records by confidence

        Returns:
            Response object includes:
                            (list) results: list of panels info
                            (int) count: number of panels
    """

    queryset = Panel.objects.all()
    serializer_class = PanelDetailSerializer

    def list(self, request, *args, **kwargs):
        user = self.request.user
        queryset = self.get_queryset()
        serializer = PanelDetailSerializer()
        panel_list = []

        for panel in queryset:
            panel_info = {}
            if panel.is_visible == 1 or (user.is_authenticated and panel.is_visible == 0):
                stats = serializer.calculate_stats(panel)
                panel_info['name'] = panel.name
                panel_info['description'] = panel.description
                panel_info['stats'] = stats
                panel_list.append(panel_info)

        return Response({'results':panel_list, 'count':len(panel_list)})

class PanelDetail(BaseView):
    """
        Display the panel info.

        Args:
            (str) panel: the panel short name

        Returns:
            Response object includes:
                            (string) panel name
                            (string) panel description: long name
                            (list) curators: list of curators with permission to edit the panel
                            (string) last_updated
                            (dict) stats
    """

    def get(self, request, name, *args, **kwargs):
        user = self.request.user
        queryset = Panel.objects.filter(name=name)

        flag = 0
        for panel in queryset:
            if panel.is_visible == 1 or (user.is_authenticated and panel.is_visible == 0):
                flag = 1

        if flag == 1:
            serializer = PanelDetailSerializer()
            curators = serializer.get_curators(queryset.first())
            last_update = serializer.get_last_updated(queryset.first())
            stats = serializer.calculate_stats(queryset.first())
            response_data = {
                'name': queryset.first().name,
                'description': queryset.first().description,
                'curators': curators,
                'last_updated': last_update,
                'stats': stats,
            }
            return Response(response_data)

        else:
            self.handle_no_permission('Panel', name)

class PanelRecordsSummary(BaseView):
    """
        Display a summary of the latest G2P entries associated with panel.

        Args:
            (str) panel: the panel short name

        Returns:
            Response object includes:
                            (string) panel name
                            (list) records_summary: summary of entries linked to panel
    """

    def get(self, request, name, *args, **kwargs):
        user = self.request.user
        queryset = Panel.objects.filter(name=name)

        flag = 0
        for panel in queryset:
            if panel.is_visible == 1 or (user.is_authenticated and panel.is_visible == 0):
                flag = 1

        if flag == 1:
            serializer = PanelDetailSerializer()
            summary = serializer.records_summary(queryset.first())
            response_data = {
                'panel_name': queryset.first().name,
                'records_summary': summary,
            }
            return Response(response_data)

        else:
            self.handle_no_permission('Panel', name)
