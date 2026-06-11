"""Combined Address + Works editor for a project.

One screen: each address is a card with an inline works table (add / edit /
delete rows), live cost totals, and a single "Save all". The client posts the
whole structure as JSON; the server applies the diff in one transaction.

Editable here: the core address fields (street, lot, plan, suburb, lease) and the
core work fields (type, bedrooms, quantity, estimated cost, status). Deeper work
fields (contractor, dates, materials) keep their dedicated edit page, linked per
row.
"""
import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from apps.core.mixins import WriteRequiredMixin
from apps.core.models import Project, Address, Work, WorkType, Suburb


def _to_int(v, default=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _to_decimal(v):
    try:
        return Decimal(str(v if v not in (None, '') else '0'))
    except (InvalidOperation, ValueError):
        return Decimal('0')


class AddressesWorksEditView(WriteRequiredMixin, View):
    template_name = 'projects/addresses_works_edit.html'

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def _detail_url(self):
        return reverse('ui:project_addresses_works', kwargs={'pk': self.project.pk})

    # ---- GET: render the editor with the current data as JSON ----
    def get(self, request, *args, **kwargs):
        addresses = []
        qs = (self.project.addresses.select_related('suburb')
              .prefetch_related('works__work_type').order_by('street', 'pk'))
        for addr in qs:
            addresses.append({
                'id': addr.pk, 'street': addr.street, 'lot': addr.lot, 'plan': addr.plan,
                'suburb': addr.suburb_id, 'lease_status': addr.lease_status,
                'works': [{
                    'id': w.pk, 'work_type': w.work_type_id,
                    'bedrooms': w.bedrooms or 0, 'quantity': w.quantity or 1,
                    'estimated_cost': str(w.estimated_cost or '0'), 'status': w.status,
                    'edit_url': reverse('ui:work_edit',
                                        kwargs={'project_pk': self.project.pk, 'pk': w.pk}),
                } for w in addr.works.all()],
            })
        data = {
            'addresses': addresses,
            'work_types': [{'id': wt.pk, 'name': wt.name, 'has_bedrooms': wt.has_bedrooms}
                           for wt in WorkType.objects.filter(is_active=True).order_by('category', 'name')],
            'suburbs': [{'id': s.pk, 'name': str(s)} for s in Suburb.objects.order_by('name')],
            'statuses': list(Work.Status.choices),
            'lease_statuses': [['', '— Lease —']] + list(Address.LeaseStatus.choices),
        }
        return render(request, self.template_name, {
            'project': self.project, 'data': data, 'back_url': self._detail_url(),
        })

    # ---- POST: apply the submitted diff in a single transaction ----
    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.POST.get('payload') or '{}')
        except json.JSONDecodeError:
            messages.error(request, 'Could not read the submitted data.')
            return redirect(request.path)

        wt_ids = set(WorkType.objects.values_list('pk', flat=True))
        suburb_ids = set(Suburb.objects.values_list('pk', flat=True))
        valid_status = {c[0] for c in Work.Status.choices}
        valid_lease = {c[0] for c in Address.LeaseStatus.choices}

        deleted_works = [int(x) for x in payload.get('deleted_works', []) if str(x).isdigit()]
        deleted_addrs = [int(x) for x in payload.get('deleted_addresses', []) if str(x).isdigit()]

        try:
            with transaction.atomic():
                # Deletions first (address delete cascades its works).
                if deleted_works:
                    Work.objects.filter(pk__in=deleted_works, project=self.project).delete()
                if deleted_addrs:
                    Address.objects.filter(pk__in=deleted_addrs, project=self.project).delete()

                for a_ in payload.get('addresses', []):
                    aid = a_.get('id')
                    street = (a_.get('street') or '').strip()
                    addr = None
                    if aid:
                        addr = Address.objects.filter(pk=aid, project=self.project).first()
                    if addr is None:
                        if not street:
                            continue  # new card with no street -> ignore
                        addr = Address(project=self.project)
                    if street:
                        addr.street = street
                    addr.lot = (a_.get('lot') or '').strip()
                    addr.plan = (a_.get('plan') or '').strip()
                    sub = a_.get('suburb')
                    addr.suburb_id = sub if sub in suburb_ids else None
                    lease = a_.get('lease_status') or ''
                    addr.lease_status = lease if lease in valid_lease else ''
                    addr.save()

                    for w_ in a_.get('works', []):
                        wt = w_.get('work_type')
                        wid = w_.get('id')
                        work = Work.objects.filter(pk=wid, project=self.project).first() if wid else None
                        if wt not in wt_ids:
                            continue  # a work type is required to create/keep a row
                        if work is None:
                            work = Work(project=self.project)
                        work.address = addr
                        work.work_type_id = wt
                        work.bedrooms = _to_int(w_.get('bedrooms'), 0)
                        work.quantity = max(1, _to_int(w_.get('quantity'), 1))
                        work.estimated_cost = _to_decimal(w_.get('estimated_cost'))
                        st = w_.get('status')
                        work.status = st if st in valid_status else Work.Status.PENDING
                        work.save()

            messages.success(request, 'Addresses & works saved.')
            return redirect(self._detail_url())
        except Exception as exc:  # noqa: BLE001 - surface any save error to the user
            messages.error(request, f'Save failed: {exc}')
            return redirect(request.path)
