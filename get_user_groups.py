from django.contrib.auth import get_user_model
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testproj.settings')
import django
django.setup()
User = get_user_model()
user = User.objects.get(username='harry')
print('Harry groups:', [g.name for g in user.groups.all()])