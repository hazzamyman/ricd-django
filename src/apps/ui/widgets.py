"""Form widgets for the UI app.

PopupAddSelect — a Select widget that renders the dropdown followed by a small
"+ Add" button. Clicking the button opens a popup window pointing at a model's
create view (with ?_popup=1&field=<id>). When the popup saves, it sends a
postMessage back to this window; the listener in base.html appends a new
<option> and selects it.
"""
from django import forms
from django.utils.safestring import mark_safe
from django.utils.html import format_html


class PopupAddSelect(forms.Select):
    """Select widget with a sibling '+ Add' button that launches a popup.

    Usage:
        suburb = forms.ModelChoiceField(
            queryset=Suburb.objects.all(),
            widget=PopupAddSelect(add_url='/suburbs/create/', add_label='Add suburb'),
        )

    The receiver (popup create view) must implement the popup protocol
    (see apps.ui.views.popup_mixin.PopupAwareCreateMixin).
    """
    template_name = 'django/forms/widgets/select.html'

    def __init__(self, add_url=None, add_label='Add', popup_width=720, popup_height=640, **kwargs):
        super().__init__(**kwargs)
        self.add_url = add_url
        self.add_label = add_label
        self.popup_width = popup_width
        self.popup_height = popup_height
        existing = self.attrs.get('class', '')
        self.attrs['class'] = (existing + ' form-select').strip()

    def render(self, name, value, attrs=None, renderer=None):
        select_html = super().render(name, value, attrs=attrs, renderer=renderer)
        if not self.add_url:
            return select_html
        field_id = (attrs or {}).get('id') or f'id_{name}'
        button = format_html(
            '<button type="button" class="btn btn-outline-secondary btn-sm popup-add-btn" '
            'data-popup-add-url="{url}" data-popup-add-field="{fid}" '
            'data-popup-width="{w}" data-popup-height="{h}" '
            'title="{label}">'
            '<i class="bi bi-plus-lg"></i> Add'
            '</button>',
            url=self.add_url, fid=field_id, w=self.popup_width, h=self.popup_height,
            label=self.add_label,
        )
        return mark_safe(
            f'<div class="d-flex align-items-stretch gap-2 popup-add-wrapper">{select_html}{button}</div>'
        )
