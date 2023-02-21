from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from firebase_push.models import FCMDevice


def cleanup_devices(days: int):
    devices = FCMDevice.objects.filter(disabled_at__lt=timezone.now() - timedelta(days=days))
    count = devices.count()
    devices.delete()
    return count


class Command(BaseCommand):
    help = "Cleanup disabled devices from FCM push notification tables"

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            "-s",
            dest="since",
            default=30 * 2,
            type=int,
            help="Device is discarded when it has been disabled for this number of days",
        )

    def handle(self, *args, **options):
        result = cleanup_devices(days=options["since"])
        if result > 0:
            self.stdout.write(self.style.SUCCESS(f"Successfully removed {result} devices!"))
        else:
            self.stdout.write(self.style.SUCCESS(f"No device to remove."))