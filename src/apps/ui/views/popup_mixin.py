"""PopupAwareCreateMixin — drop-in CreateView mixin for the lookup-popup pattern.

Apply to any CreateView whose object should be creatable inline from another
form (e.g. add a Suburb while filling in an Address form). When the view is
hit with `?_popup=1`, it renders a minimal template (no nav/breadcrumbs) and,
on successful save, returns a tiny HTML page that posts a `postMessage` to
`window.opener` and closes itself.

The site-wide JS handler in base.html listens for these messages and appends
the new option to the parent form's <select> + selects it.
"""
from django.shortcuts import render


class PopupAwareCreateMixin:
    """Mix into a CreateView. Adds `?_popup=1` support."""

    popup_template_name = 'crud/popup_form.html'
    popup_response_template = 'crud/popup_response.html'

    def is_popup(self):
        return (
            self.request.GET.get('_popup') == '1'
            or self.request.POST.get('_popup') == '1'
        )

    def get_template_names(self):
        if self.is_popup():
            return [self.popup_template_name]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['is_popup'] = self.is_popup()
        ctx['popup_target_field'] = self.request.GET.get('field') or self.request.POST.get('field') or ''
        return ctx

    def form_valid(self, form):
        if self.is_popup():
            self.object = form.save()
            return render(self.request, self.popup_response_template, {
                'pk': self.object.pk,
                'name': str(self.object),
                'field': self.request.GET.get('field') or self.request.POST.get('field') or '',
            })
        return super().form_valid(form)
