from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from firebase_push.utils import get_device_model


FCMDevice = get_device_model()


def age_devices(days: int):
    devices = FCMDevice.objects.filter(updated_at__lt=timezone.now() - timedelta(days=days))
    count = devices.count()
    devices.update(disabled_at=timezone.now())
    return count


class Command(BaseCommand):
    help = "Disable old devices that have not been seen in a pre-defined time"

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            "-s",
            dest="since",
            default=30 * 2,
            type=int,
            help="Device is disabled when it has not been seen for this number of days",
        )

    def handle(self, *args, **options):
        result = age_devices(days=options["since"])
        if result > 0:
            self.stdout.write(self.style.SUCCESS(f"Successfully disabled {result} devices!"))
        else:
            self.stdout.write(self.style.SUCCESS("No devices to disable."))
