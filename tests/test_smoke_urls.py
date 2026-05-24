"""
Smoke test: GET every reversible URL in the ``ui:`` namespace and assert
no view returns HTTP 5xx.

This catches a whole class of regressions without needing detailed fixtures:

  * Missing imports (e.g. ``NameError: name 'render' is not defined``)
  * Broken templates referencing removed URL names
  * Undefined template tags / filters
  * Views that crash on a fresh DB (e.g. accessing a removed model field)
  * Stale ``{% url 'foo' %}`` tags in side templates

We accept 200 (rendered OK), 302 (redirect), 400 (bad request), 403 (forbidden),
404 (object not found, the view ran fine) and 405 (POST-only endpoint hit with
GET). Anything 5xx fails the test with the URL name and status code so the
fix is obvious from the test output.
"""
import pytest
from django.urls import NoReverseMatch, get_resolver, reverse
from django.contrib.auth import get_user_model


# Placeholder values used to fabricate URL kwargs. Stub IDs that don't exist
# in the DB will just return 404 from get_object_or_404, which is fine.
DUMMY_KWARGS = {
    'pk': 1,
    'project_pk': 1,
    'wt_pk': 1,
    'council_pk': 1,
    'program_pk': 1,
    'group_pk': 1,
    'notice_pk': 1,
    'rule_pk': 1,
    'item_pk': 1,
    'claim_pk': 1,
    'variation_pk': 1,
    'work_pk': 1,
    'pay_pk': 1,
    'address_pk': 1,
    'stage_type': 'STAGE1',
}


def _required_kwarg_names(pattern):
    """Return the set of kwarg names the URL pattern needs."""
    p = pattern.pattern
    if hasattr(p, 'converters'):
        return set(p.converters.keys())
    if hasattr(p, 'regex') and hasattr(p.regex, 'groupindex'):
        return set(p.regex.groupindex.keys())
    return set()


def _ui_namespace_patterns():
    """Yield every URLPattern registered under the ``ui:`` namespace."""
    resolver = get_resolver()
    ns_entry = resolver.namespace_dict.get('ui')
    if ns_entry is None:
        return
    _prefix, ns_resolver = ns_entry
    for pattern in ns_resolver.url_patterns:
        if getattr(pattern, 'name', None):
            yield pattern


@pytest.mark.django_db
def test_no_5xx_on_any_ui_url(client):
    """Every reversible GET URL in the ``ui:`` namespace must not 5xx."""
    User = get_user_model()
    # Smoke-test as a superuser so RBAC gates don't hide failures
    user = User.objects.create_user(
        username='smoke_admin', password='pass', is_staff=True, is_superuser=True,
    )
    client.force_login(user)

    failed = []
    skipped = []
    checked = 0

    for pattern in _ui_namespace_patterns():
        name = pattern.name
        kwarg_names = _required_kwarg_names(pattern)
        unknown = kwarg_names - DUMMY_KWARGS.keys()
        if unknown:
            skipped.append(f"{name} (missing dummy values for {sorted(unknown)})")
            continue
        kwargs = {k: DUMMY_KWARGS[k] for k in kwarg_names}
        try:
            url = reverse(f'ui:{name}', kwargs=kwargs)
        except NoReverseMatch:
            skipped.append(f"{name} (NoReverseMatch with kwargs={kwargs})")
            continue

        try:
            response = client.get(url)
        except Exception as exc:
            failed.append(f"{name} GET {url}: EXCEPTION {type(exc).__name__}: {exc}")
            continue

        checked += 1
        if response.status_code >= 500:
            failed.append(f"{name} GET {url}: HTTP {response.status_code}")

    # If the resolver introspection is broken we want to know
    assert checked > 50, (
        f"Only smoke-checked {checked} URLs (expected 50+). "
        f"Skipped: {skipped[:10]}"
    )

    if failed:
        msg = "\n  ".join(failed)
        if skipped:
            msg += "\n\nSkipped (likely fine, but worth a look):\n  " + "\n  ".join(skipped[:20])
        pytest.fail(f"{len(failed)} URL(s) returned 5xx or raised:\n  {msg}")
