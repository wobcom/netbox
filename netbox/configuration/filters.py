import django_filters
from django.db.models import Q

from .models import BGPConfiguration

class BGPFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(
        method='search',
        label='Search',
    )
    neighbor = django_filters.CharFilter(
        method='filter_neighbor',
        label='Neighbor IP',
    )
    remote_as = django_filters.NumberFilter(
        method='filter_as',
        field_name='remote_as',
        label='Remote AS',
    )

    class Meta:
        model = BGPConfiguration
        fields = ['neighbor', 'remote_as']

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(neighbor__icontains=value))

    def filter_neighbor(self, queryset, name, value):
        if not value.strip():
            return queryset
        try:
            # Match address and subnet mask
            if '/' in value:
                return queryset.filter(address=value)
            return queryset.filter(address__contains=value)
        except ValidationError:
            return queryset.none()

    def filter_as(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(remote_as=value)
