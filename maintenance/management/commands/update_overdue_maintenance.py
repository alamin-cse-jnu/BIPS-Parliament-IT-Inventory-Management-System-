from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from maintenance.models import Maintenance


class Command(BaseCommand):
    help = 'Update overdue maintenance status'
    
    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Find overdue maintenance
        overdue_maintenance = Maintenance.objects.filter(
            expected_end_date__lt=today,
            status__in=['SCHEDULED', 'IN_PROGRESS'],
            is_active=True
        )
        
        count = overdue_maintenance.count()
        
        self.stdout.write(f'Found {count} overdue maintenance records')
        
        for maintenance in overdue_maintenance:
            days_overdue = (today - maintenance.expected_end_date).days
            self.stdout.write(
                f'  - {maintenance.maintenance_id}: {days_overdue} days overdue'
            )
        
        self.stdout.write(self.style.SUCCESS('Update completed'))

# ============================================================================
# ESSENTIAL Helper Functions
# ============================================================================

def get_maintenance_summary():
    """
    Get simple maintenance summary for dashboard.
    """
    total = Maintenance.objects.count()
    
    summary = {
        'total': total,
        'scheduled': Maintenance.objects.filter(status='SCHEDULED').count(),
        'in_progress': Maintenance.objects.filter(status='IN_PROGRESS').count(),
        'completed': Maintenance.objects.filter(status='COMPLETED').count(),
        'overdue': 0
    }
    
    # Count overdue (simple way)
    today = timezone.now().date()
    overdue_qs = Maintenance.objects.filter(
        expected_end_date__lt=today,
        status__in=['SCHEDULED', 'IN_PROGRESS']
    )
    summary['overdue'] = overdue_qs.count()
    
    return summary


def export_maintenance_simple_csv(request):
    """
    Simple CSV export for maintenance records.
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="maintenance_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Maintenance ID', 'Device ID', 'Type', 'Status', 
        'Start Date', 'Expected End', 'Cost'
    ])
    
    maintenance_records = Maintenance.objects.select_related('device').order_by('-start_date')
    
    for maintenance in maintenance_records:
        writer.writerow([
            maintenance.maintenance_id,
            maintenance.device.device_id if maintenance.device else '',
            maintenance.get_maintenance_type_display(),
            maintenance.get_status_display(),
            maintenance.start_date,
            maintenance.expected_end_date,
            maintenance.actual_cost or maintenance.estimated_cost or 0
        ])
    
    return response


def check_device_maintenance_conflicts(device, start_date, end_date, exclude_maintenance_id=None):
    """
    Simple conflict checker for device maintenance scheduling.
    """
    conflicts = Maintenance.objects.filter(
        device=device,
        status__in=['SCHEDULED', 'IN_PROGRESS'],
        start_date__lte=end_date,
        expected_end_date__gte=start_date
    )
    
    if exclude_maintenance_id:
        conflicts = conflicts.exclude(id=exclude_maintenance_id)
    
    return conflicts.exists()


def get_next_maintenance_date(device, maintenance_type='PREVENTIVE'):
    """
    Simple calculation for next maintenance date.
    """
    # Simple intervals (in days)
    intervals = {
        'PREVENTIVE': 90,    # 3 months
        'INSPECTION': 180,   # 6 months
        'CLEANING': 30,      # 1 month
        'CALIBRATION': 365,  # 1 year
    }
    
    interval_days = intervals.get(maintenance_type, 90)
    
    # Get last maintenance of this type
    last_maintenance = Maintenance.objects.filter(
        device=device,
        maintenance_type=maintenance_type,
        status='COMPLETED'
    ).order_by('-actual_end_date').first()
    
    if last_maintenance and last_maintenance.actual_end_date:
        base_date = last_maintenance.actual_end_date.date()
    else:
        base_date = timezone.now().date()
    
    return base_date + timedelta(days=interval_days)