from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from firebase_push.models import FCMHistoryBase
from firebase_push.utils import get_history_model


def cleanup_history(days: int):
    FCMHistory = get_history_model()
    entries = FCMHistory.objects.filter(updated_at__lt=timezone.now() - timedelta(days=days))
    pending = entries.filter(status=FCMHistoryBase.Status.PENDING).count()
    sent = entries.filter(status=FCMHistoryBase.Status.SENT).count()
    failed = entries.filter(status=FCMHistoryBase.Status.FAILED).count()
    entries.delete()
    return pending, sent, failed


class Command(BaseCommand):
    help = "Cleanup history from FCM push notification tables"

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            "-s",
            dest="since",
            default=30 * 6,
            type=int,
            help="History is discarded when it is older than this number of days",
        )

    def handle(self, *args, **options):
        pending, sent, failed = cleanup_history(days=options["since"])
        if (pending + sent + failed) > 0:
            self.stdout.write(self.style.SUCCESS(f"Successfully removed {pending + sent + failed} history entries"))
            self.stdout.write(self.style.NOTICE(f"(sent: {sent}, failed: {failed}, still pending: {pending})"))
        else:
            self.stdout.write(self.style.SUCCESS("No history to remove."))
