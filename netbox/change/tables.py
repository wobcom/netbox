import django_tables2 as tables

from utilities.tables import BaseTable
from .models import ChangeSet, IMPLEMENTED, DRAFT


RECREATE_MR = """
<a href="{{% url "change:mr" pk=record.pk %}}" class="btn btn-primary {{% if record.status == {} %}}disabled{{% endif %}}"><i class="fa fa-play"></i></a>
""".format(IMPLEMENTED)
REACTIVATE = """
<a href="{{% url "change:reactivate" pk=record.pk %}}" class="btn btn-primary {{% if record.status != {} %}}disabled{{% endif %}}"><i class="fa fa-play"></i></a>
""".format(DRAFT)


class ChangeTable(BaseTable):
    pk = tables.LinkColumn('change:detail', args=[tables.A('pk')])
    status = tables.Column()
    changedfield_count = tables.Column(verbose_name='Changed Fields')
    changedobject_count = tables.Column(verbose_name='Changed Objects')
    create_mr = tables.TemplateColumn(verbose_name='Merge Request',
                                      template_code=RECREATE_MR,
                                      orderable=False)
    reactivate = tables.TemplateColumn(verbose_name='Reactivate',
                                      template_code=REACTIVATE,
                                      orderable=False)

    class Meta(BaseTable.Meta):
        model = ChangeSet
        fields = (
            'pk',
            'status',
            'changedfield_count',
            'changedobject_count',
            'create_mr',
            'reactivate',
        )
