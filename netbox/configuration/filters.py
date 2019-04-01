import django_filters
from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import BGPSession, BGPCommunity

from dcim.models import Device

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
    devices = django_filters.ModelMultipleChoiceFilter(
        queryset=Device.objects.all(),
        label='Device (ID)',
    )

    class Meta:
        model = BGPSession
        fields = ['neighbor', 'remote_as', 'devices']

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(neighbor__icontains=value))

    def filter_neighbor(self, queryset, name, value):
        if not value.strip():
            return queryset
        try:
            return queryset.filter(neighbor__contains=value)
        except ValidationError:
            return queryset.none()

    def filter_as(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(remote_as=value)


class CommunityFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(
        method='search',
        label='Search',
    )
    name = django_filters.CharFilter(
        method='filter_name',
        field_name='name',
        label='Name',
    )
    community = django_filters.NumberFilter(
        method='filter_community',
        field_name='community',
        label='Community',
    )

    class Meta:
        model = BGPCommunity
        fields = ['name', 'community']

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value)|Q(description__icontains=value))

    def filter_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(name_icontains=value)

    def filter_community(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(communities__contains=value)
