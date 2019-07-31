import django_filters
from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import BGPCommunity, BGPCommunityList, RouteMap

from dcim.models import Device


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


class CommunityListFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        method='filter_name',
        field_name='name',
        label='Name',
    )

    class Meta:
        model = BGPCommunityList
        fields = ['name']

    def filter_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(name_icontains=value)


class RouteMapFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(
        method='search',
        label='Search',
    )
    name = django_filters.CharFilter(
        method='filter_name',
        field_name='name',
        label='Name',
    )

    class Meta:
        model = RouteMap
        fields = ['name']

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value)|Q(configuration__icontains=value))

    def filter_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(name_icontains=value)
