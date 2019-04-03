import django_tables2 as tables

from utilities.tables import BaseTable
from .models import ChangeSet, IMPLEMENTED


RECREATE_MR = """
<a href="{{% url "change:change_mr" pk=record.pk %}}" class="btn btn-primary {{% if record.status == {} %}}disabled{{% endif %}}">Recreate Merge Request</a>
""".format(IMPLEMENTED)
RECREATE_TOPDESK = """
<a href="{% url "change:change_topdesk" pk=record.pk %}" class="btn btn-primary">Recreate TOPdesk Ticket</a>
"""


class ChangeTable(BaseTable):
    pk = tables.LinkColumn('change:change_detail', args=[tables.A('pk')])
    status = tables.Column()
    changedfield_count = tables.Column(verbose_name='Changed Fields')
    changedobject_count = tables.Column(verbose_name='Changed Objects')
    create_mr = tables.TemplateColumn(verbose_name='Recreate Merge Request',
                                      template_code=RECREATE_MR,
                                      orderable=False)
    create_topdesk = tables.TemplateColumn(
        verbose_name='Recreate TOPdesk ticket',
        template_code=RECREATE_TOPDESK,
        orderable=False
    )

    class Meta(BaseTable.Meta):
        model = ChangeSet
        fields = (
            'pk',
            'status',
            'changedfield_count',
            'changedobject_count',
            'create_mr',
            'create_topdesk',
        )
