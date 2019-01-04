from taggit_serializer.serializers import TaggitSerializer, TagListSerializerField

from extras.api.customfields import CustomFieldModelSerializer
from tenancy.models import Tenant, TenantGroup
from utilities.api import ValidatedModelSerializer
from .nested_serializers import *


#
# Tenants
#

class TenantGroupSerializer(ValidatedModelSerializer):

    class Meta:
        model = TenantGroup
        fields = ['id', 'name', 'slug']


class TenantSerializer(TaggitSerializer, CustomFieldModelSerializer):
    group = NestedTenantGroupSerializer(required=False)
    tags = TagListSerializerField(required=False)

    class Meta:
        model = Tenant
        fields = [
            'id', 'name', 'slug', 'group', 'description', 'comments', 'tags', 'custom_fields', 'created',
            'last_updated',
        ]
