"""Maintenance CRUD for QuarterlyReportItemGroup and QuarterlyReportItem."""
import pytest
from django.urls import reverse
from apps.core.models import QuarterlyReportItemGroup, QuarterlyReportItem


@pytest.mark.django_db
class TestQuarterlyReportItemGroupCRUD:
    def test_list_renders(self, admin_client):
        QuarterlyReportItemGroup.objects.create(name='Financials', order=1)
        resp = admin_client.get(reverse('ui:quarterly_report_item_group_list'))
        assert resp.status_code == 200
        assert b'Financials' in resp.content

    def test_create_group(self, admin_client):
        before = QuarterlyReportItemGroup.objects.count()
        resp = admin_client.post(reverse('ui:quarterly_report_item_group_create'), {
            'name': 'Progress',
            'description': 'Construction progress items',
            'is_active': 'on',
            'order': '1',
        })
        assert resp.status_code == 302
        assert QuarterlyReportItemGroup.objects.count() == before + 1
        assert QuarterlyReportItemGroup.objects.filter(name='Progress').exists()

    def test_edit_group(self, admin_client):
        group = QuarterlyReportItemGroup.objects.create(name='Old Name', order=1)
        resp = admin_client.post(
            reverse('ui:quarterly_report_item_group_edit', args=[group.pk]),
            {'name': 'New Name', 'description': '', 'is_active': 'on', 'order': '2'},
        )
        assert resp.status_code == 302
        group.refresh_from_db()
        assert group.name == 'New Name'

    def test_delete_group(self, admin_client):
        group = QuarterlyReportItemGroup.objects.create(name='ToDelete', order=1)
        resp = admin_client.post(
            reverse('ui:quarterly_report_item_group_delete', args=[group.pk])
        )
        assert resp.status_code == 302
        assert not QuarterlyReportItemGroup.objects.filter(pk=group.pk).exists()


@pytest.mark.django_db
class TestQuarterlyReportItemCRUD:
    def test_create_item(self, admin_client):
        group = QuarterlyReportItemGroup.objects.create(name='Financials', order=1)
        before = QuarterlyReportItem.objects.count()
        resp = admin_client.post(
            reverse('ui:quarterly_report_item_create', kwargs={'group_pk': group.pk}),
            {
                'name': 'Budget spent to date',
                'field_type': 'CURRENCY',
                'order': '1',
                'is_required': 'on',
                'is_active': 'on',
                'help_text': 'Cumulative spend this quarter',
            },
        )
        assert resp.status_code == 302
        assert QuarterlyReportItem.objects.count() == before + 1
        item = QuarterlyReportItem.objects.get(name='Budget spent to date')
        assert item.group == group
        assert item.field_type == 'CURRENCY'

    def test_edit_item(self, admin_client):
        group = QuarterlyReportItemGroup.objects.create(name='G', order=1)
        item = QuarterlyReportItem.objects.create(
            group=group, name='Old', field_type='TEXT', order=1
        )
        resp = admin_client.post(
            reverse('ui:quarterly_report_item_edit', kwargs={'group_pk': group.pk, 'pk': item.pk}),
            {'name': 'Updated', 'field_type': 'DATE', 'order': '2',
             'is_required': 'on', 'is_active': 'on', 'help_text': ''},
        )
        assert resp.status_code == 302
        item.refresh_from_db()
        assert item.name == 'Updated'
        assert item.field_type == 'DATE'

    def test_delete_item(self, admin_client):
        group = QuarterlyReportItemGroup.objects.create(name='G', order=1)
        item = QuarterlyReportItem.objects.create(
            group=group, name='ToDelete', field_type='TEXT', order=1
        )
        resp = admin_client.post(
            reverse('ui:quarterly_report_item_delete', kwargs={'group_pk': group.pk, 'pk': item.pk})
        )
        assert resp.status_code == 302
        assert not QuarterlyReportItem.objects.filter(pk=item.pk).exists()

    def test_items_visible_on_group_list(self, admin_client):
        group = QuarterlyReportItemGroup.objects.create(name='Status', order=1)
        QuarterlyReportItem.objects.create(
            group=group, name='Works completed', field_type='CHECKBOX', order=1
        )
        resp = admin_client.get(reverse('ui:quarterly_report_item_group_list'))
        assert b'Works completed' in resp.content
        assert b'Checkbox' in resp.content

    def test_inactive_group_shows_badge(self, admin_client):
        QuarterlyReportItemGroup.objects.create(name='Archived Section', is_active=False, order=9)
        resp = admin_client.get(reverse('ui:quarterly_report_item_group_list'))
        assert b'Inactive' in resp.content
