"""Seed 53 QLD suburbs + their electorate / QHIGI region lookups.

Source: user-provided table referencing the QLD Electoral Commission's electoral
district lookup and the AEC's locality search.
Lookups (StateElectorate, FederalElectorate, QhigiRegion) are created on
demand via get_or_create. Suburb rows are upserted on (name, postcode, state).
Idempotent — safe to re-run.
"""
from django.db import migrations


SUBURBS = [
    # (name, state_electorate, federal_electorate, council_name, postcode, qhigi_region)
    ('Aurukun', 'Cook', 'Leichhardt', 'Aurukun Shire Council', '4892', 'Cape York'),
    ('Badu Island', 'Cook', 'Leichhardt', 'Torres Strait Island Regional Council', '4875', 'Cape York'),
    ('Bamaga', 'Cook', 'Leichhardt', 'Northern Peninsula Area Regional Council', '4876', 'Cape York'),
    ('Birdsville', 'Gregory', 'Maranoa', 'Diamantina Shire Council', '4482', 'Outback - South West'),
    ('Boigu Island', 'Cook', 'Leichhardt', 'Torres Strait Island Regional Council', '4875', 'Cape York'),
    ('Cairns City', 'Cairns', 'Leichhardt', 'Cairns Regional Council', '4870', 'Far North Queensland'),
    ('Camooweal', 'Traeger', 'Kennedy', 'Mount Isa City Council', '4828', 'Outback - North West'),
    ('Charleville', 'Gregory', 'Maranoa', 'Murweh Shire Council', '4470', 'Outback - South West'),
    ('Cherbourg', 'Nanango', 'Wide Bay', 'Cherbourg Aboriginal Shire Council', '4605', 'Wide Bay Burnett'),
    ('Coen', 'Cook', 'Leichhardt', 'Cook Shire Council', '4892', 'Cape York'),
    ('Cooktown', 'Cook', 'Leichhardt', 'Cook Shire Council', '4895', 'Cape York'),
    ('Dauan Island', 'Cook', 'Leichhardt', 'Torres Strait Island Regional Council', '4875', 'Cape York'),
    ('Doomadgee', 'Traeger', 'Kennedy', 'Doomadgee Aboriginal Shire Council', '4830', 'Outback - North West'),
    ('Erub (Darnley) Island', 'Cook', 'Leichhardt', 'Torres Strait Island Regional Council', '4875', 'Cape York'),
    ('Hammond Island', 'Cook', 'Leichhardt', 'Torres Strait Island Regional Council', '4875', 'Cape York'),
    ('Hope Vale', 'Cook', 'Leichhardt', 'Hope Vale Aboriginal Shire Council', '4895', 'Cape York'),
    ('Horn Island (Wasaga)', 'Cook', 'Leichhardt', 'Torres Shire Council', '4875', 'Cape York'),
    ('Iama (Yam) Island', 'Cook', 'Leichhardt', 'Torres Strait Island Regional Council', '4875', 'Cape York'),
    ('Injinoo', 'Cook', 'Leichhardt', 'Northern Peninsula Area Regional Council', '4876', 'Cape York'),
    ('Innisfail', 'Hill', 'Kennedy', 'Cassowary Coast Regional Council', '4860', 'Far North Queensland'),
    ('Kowanyama', 'Cook', 'Leichhardt', 'Kowanyama Aboriginal Shire Council', '4892', 'Cape York'),
    ('Kubin (Moa) Island', 'Cook', 'Leichhardt', 'Torres Strait Island Regional Council', '4875', 'Cape York'),
    ('Laura', 'Cook', 'Leichhardt', 'Cook Shire Council', '4892', 'Cape York'),
    ('Lockhart River', 'Cook', 'Leichhardt', 'Lockhart River Aboriginal Shire Council', '4892', 'Cape York'),
    ('Longreach', 'Gregory', 'Maranoa', 'Longreach Regional Council', '4730', 'Outback - Central'),
    ('Mabuiag Island', 'Cook', 'Leichhardt', 'Torres Strait Island Regional Council', '4875', 'Cape York'),
    ('Mapoon', 'Cook', 'Leichhardt', 'Mapoon Aboriginal Shire Council', '4874', 'Cape York'),
    ('Masig (Yorke) Island', 'Cook', 'Leichhardt', 'Torres Strait Island Regional Council', '4875', 'Cape York'),
    ('Mer (Murray) Island', 'Cook', 'Leichhardt', 'Torres Strait Island Regional Council', '4875', 'Cape York'),
    ('Mitchell', 'Warrego', 'Maranoa', 'Maranoa Regional Council', '4465', 'Darling Downs'),
    ('Moranbah', 'Burdekin', 'Capricornia', 'Isaac Regional Council', '4744', 'Mackay-Whitsunday'),
    ('Mornington Island', 'Traeger', 'Kennedy', 'Mornington Shire Council', '4871', 'Outback - North West'),
    ('Napranum', 'Cook', 'Leichhardt', 'Napranum Aboriginal Shire Council', '4874', 'Cape York'),
    ('New Mapoon', 'Cook', 'Leichhardt', 'Northern Peninsula Area Regional Council', '4876', 'Cape York'),
    ('Northern Peninsula', 'Cook', 'Leichhardt', 'Northern Peninsula Area Regional Council', '4876', 'Cape York'),
    ('Palm Island', 'Townsville', 'Herbert', 'Palm Island Aboriginal Shire Council', '4816', 'North Queensland'),
    ('Pormpuraaw', 'Cook', 'Leichhardt', 'Pormpuraaw Aboriginal Shire Council', '4892', 'Cape York'),
    ('Poruma (Coconut) Island', 'Cook', 'Leichhardt', 'Torres Strait Island Regional Council', '4875', 'Cape York'),
    ('Saibai (Kaumag) Island', 'Cook', 'Leichhardt', 'Torres Strait Island Regional Council', '4875', 'Cape York'),
    ('Seisia', 'Cook', 'Leichhardt', 'Northern Peninsula Area Regional Council', '4876', 'Cape York'),
    ('St George', 'Warrego', 'Maranoa', 'Balonne Shire Council', '4487', 'Darling Downs'),
    ('St Pauls (Moa) Island', 'Cook', 'Leichhardt', 'Torres Strait Island Regional Council', '4875', 'Cape York'),
    ('Thursday Island', 'Cook', 'Leichhardt', 'Torres Shire Council', '4875', 'Cape York'),
    ('Torres Strait', 'Cook', 'Leichhardt', 'Torres Strait Island Regional Council', '4875', 'Cape York'),
    ('Townsville City', 'Townsville', 'Herbert', 'Townsville City Council', '4810', 'North Queensland'),
    ('Ugar (Stephen) Island', 'Cook', 'Leichhardt', 'Torres Strait Island Regional Council', '4875', 'Cape York'),
    ('Umagico', 'Cook', 'Leichhardt', 'Northern Peninsula Area Regional Council', '4876', 'Cape York'),
    ('Warraber (Sue) Island', 'Cook', 'Leichhardt', 'Torres Strait Island Regional Council', '4875', 'Cape York'),
    ('Woorabinda', 'Gregory', 'Flynn', 'Woorabinda Aboriginal Shire Council', '4713', 'Central Queensland'),
    ('Wujal Wujal', 'Cook', 'Leichhardt', 'Wujal Wujal Aboriginal Shire Council', '4895', 'Cape York'),
    ('Yarrabah', 'Mulgrave', 'Kennedy', 'Yarrabah Aboriginal Shire Council', '4871', 'Far North Queensland'),
    ('NPARC', 'Cook', 'Leichhardt', 'Northern Peninsula Area Regional Council', '4876', 'Cape York'),
    ('TSIRC', 'Cook', 'Leichhardt', 'Torres Strait Island Regional Council', '4875', 'Cape York'),
]


def seed_suburbs(apps, schema_editor):
    Suburb = apps.get_model('core', 'Suburb')
    StateElectorate = apps.get_model('core', 'StateElectorate')
    FederalElectorate = apps.get_model('core', 'FederalElectorate')
    QhigiRegion = apps.get_model('core', 'QhigiRegion')

    state_el_cache = {}
    fed_el_cache = {}
    qhigi_cache = {}

    def _get_state_el(name):
        if name not in state_el_cache:
            obj, _ = StateElectorate.objects.get_or_create(
                name=name, defaults={'is_active': True},
            )
            state_el_cache[name] = obj
        return state_el_cache[name]

    def _get_fed_el(name):
        if name not in fed_el_cache:
            obj, _ = FederalElectorate.objects.get_or_create(
                name=name, defaults={'is_active': True},
            )
            fed_el_cache[name] = obj
        return fed_el_cache[name]

    def _get_qhigi(name):
        if name not in qhigi_cache:
            obj, _ = QhigiRegion.objects.get_or_create(
                name=name, defaults={'is_active': True},
            )
            qhigi_cache[name] = obj
        return qhigi_cache[name]

    for name, state_el, fed_el, _council_name, postcode, qhigi in SUBURBS:
        Suburb.objects.update_or_create(
            name=name, postcode=postcode, state='QLD',
            defaults={
                'state_electorate_link': _get_state_el(state_el),
                'federal_electorate_link': _get_fed_el(fed_el),
                'qhigi_region_link': _get_qhigi(qhigi),
                'is_active': True,
            },
        )


def unseed_suburbs(apps, schema_editor):
    Suburb = apps.get_model('core', 'Suburb')
    names = [row[0] for row in SUBURBS]
    Suburb.objects.filter(name__in=names, state='QLD').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0023_cofunding_payment_allocation'),
    ]
    operations = [
        migrations.RunPython(seed_suburbs, unseed_suburbs),
    ]
