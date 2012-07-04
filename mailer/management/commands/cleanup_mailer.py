from datetime import timedelta

from django.conf import settings
from django.core.management.base import NoArgsCommand

try:
    from django.utils import timezone as datetime
except ImportError:
    from datetime import datetime

# how long to wait (in seconds) before a log entry should be deleted
RETENTION_DELAY = getattr(settings, 'MAILER_RETENTION_DELAY', 60 * 60 * 24 * 7)  # 7 days


class Command(NoArgsCommand):
    help = "Delete old log data from the database)."

    def handle_noargs(self, **options):
        from django.db import transaction
        from mailer.models import MessageLog

        expiration_date = datetime.now() - timedelta(seconds=RETENTION_DELAY)
        MessageLog.objects.filter(when_added__lt=expiration_date).delete()
        transaction.commit_unless_managed()
