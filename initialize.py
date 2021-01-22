import os
from django.conf import settings
from django.contrib.auth import get_user_model

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

User = get_user_model()
users = User.objects.all()

if len(users) == 0:
	logger.info("No Users Found, Creating Super User with credentials admin/admin.")
	User.objects.create_superuser('admin', 'admin@example.com', 'admin')