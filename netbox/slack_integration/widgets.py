from django.forms.widgets import Textarea


class TemplateTextareaWidget(Textarea):
    template_name = 'template-textarea.html'
