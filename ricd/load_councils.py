from ricd.models import Council

councils = [
    'Aurukun Shire Council',
    'Cherbourg Aboriginal Shire Council',
    'Doomadgee Aboriginal Shire Council',
    'Hope Vale Aboriginal Shire Council',
    'Kowanyama Aboriginal Shire Council',
    'Lockhart River Aboriginal Shire Council',
    'Mapoon Aboriginal Shire Council',
    'Mornington Shire Council',
    'Napranum Aboriginal Shire Council',
    'Northern Peninsula Area Shire Council',
    'Palm Island Aboriginal Shire Council',
    'Pormpuraaw Aboriginal Shire Council',
    'Torres Strait Island Regional Council',
    'Woorabinda Aboriginal Shire Council',
    'Wujal Wujal Aboriginal Shire Council',
    'Yarrabah Aboriginal Shire Council',
]

for name in councils:
    Council.objects.get_or_create(name=name)
    print(f'Created or found: {name}')