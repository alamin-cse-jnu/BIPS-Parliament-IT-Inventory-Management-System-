"""
Views for Vendors app in PIMS (Parliament IT Inventory Management System)
Bangladesh Parliament Secretariat

This module defines views for vendor management including CRUD operations,
search functionality, reporting, and status management.
"""

# Standard library imports
import csv
import json
from datetime import datetime, timedelta

# Django core imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q, Count, Avg, Case, When, IntegerField
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Local app imports
from .models import Vendor
from .forms import VendorForm, VendorSearchForm, VendorQuickAddForm


# ============================================================================
# Vendor CRUD Views
# ============================================================================

class VendorListView(LoginRequiredMixin, ListView):
    """Display list of all vendors with search and filtering."""
    model = Vendor
    template_name = 'vendors/list.html'
    context_object_name = 'vendors'
    paginate_by = 20
    
    def get_queryset(self):
        """Filter vendors based on search parameters."""
        queryset = Vendor.objects.select_related('created_by', 'updated_by')
        
        # Apply search form filters
        form = VendorSearchForm(self.request.GET)
        if form.is_valid():
            queryset = form.filter_queryset(queryset)
        
        return queryset.order_by('vendor_code', 'name')
    
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        context['search_form'] = VendorSearchForm(self.request.GET)
        context['total_vendors'] = Vendor.objects.count()
        context['active_vendors'] = Vendor.objects.filter(is_active=True).count()
        context['preferred_vendors'] = Vendor.objects.filter(is_preferred=True).count()
        context['suppliers'] = Vendor.objects.filter(vendor_type='SUPPLIER').count()
        context['service_providers'] = Vendor.objects.filter(
            vendor_type__in=['MAINTENANCE', 'SUPPORT', 'INSTALLATION']
        ).count()
        return context


class VendorDetailView(LoginRequiredMixin, DetailView):
    """Display detailed information about a vendor."""
    model = Vendor
    template_name = 'vendors/detail.html'
    context_object_name = 'vendor'
    
    def get_queryset(self):
        """Optimize queryset with select_related."""
        return Vendor.objects.select_related('created_by', 'updated_by')
    
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        vendor = self.object
        
        # Get related counts
        context['device_count'] = vendor.get_device_count()
        context['maintenance_count'] = vendor.get_maintenance_count()
        context['service_categories'] = vendor.get_service_categories_list()
        
        return context


class VendorCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create a new vendor."""
    model = Vendor
    form_class = VendorForm
    template_name = 'vendors/create.html'
    permission_required = 'vendors.add_vendor'
    success_url = reverse_lazy('vendors:list')
    
    def form_valid(self, form):
        """Handle successful form submission."""
        # Set created_by to current user
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'Vendor "{self.object.name}" created successfully!'
        )
        return response
    
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Create New Vendor'
        context['form_action'] = 'Create'
        return context


class VendorUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Update an existing vendor."""
    model = Vendor
    form_class = VendorForm
    template_name = 'vendors/edit.html'
    permission_required = 'vendors.change_vendor'
    
    def get_success_url(self):
        return reverse('vendors:detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        """Handle successful form submission."""
        # Set updated_by to current user
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'Vendor "{self.object.name}" updated successfully!'
        )
        return response
    
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Edit Vendor - {self.object.name}'
        context['form_action'] = 'Update'
        return context


class VendorDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Delete a vendor."""
    model = Vendor
    template_name = 'vendors/delete.html'
    permission_required = 'vendors.delete_vendor'
    success_url = reverse_lazy('vendors:list')
    
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        vendor = self.object
        context['device_count'] = vendor.get_device_count()
        context['maintenance_count'] = vendor.get_maintenance_count()
        return context
    
    def delete(self, request, *args, **kwargs):
        """Handle vendor deletion."""
        vendor = self.get_object()
        vendor_name = vendor.name
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Vendor "{vendor_name}" deleted successfully!')
        return response


# ============================================================================
# Vendor Search and Filtering Views
# ============================================================================

class VendorSearchView(LoginRequiredMixin, ListView):
    """Advanced vendor search view."""
    model = Vendor
    template_name = 'vendors/search.html'
    context_object_name = 'vendors'
    paginate_by = 20
    
    def get_queryset(self):
        """Apply search filters."""
        queryset = Vendor.objects.select_related('created_by', 'updated_by')
        form = VendorSearchForm(self.request.GET)
        
        if form.is_valid():
            queryset = form.filter_queryset(queryset)
        
        return queryset.order_by('vendor_code', 'name')
    
    def get_context_data(self, **kwargs):
        """Add search form to context."""
        context = super().get_context_data(**kwargs)
        context['search_form'] = VendorSearchForm(self.request.GET)
        return context


class VendorActiveListView(LoginRequiredMixin, ListView):
    """Display only active vendors."""
    model = Vendor
    template_name = 'vendors/active.html'
    context_object_name = 'vendors'
    paginate_by = 20
    
    def get_queryset(self):
        """Return only active vendors."""
        return Vendor.objects.filter(is_active=True).order_by('name')
    
    def get_context_data(self, **kwargs):
        """Add additional context."""
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Active Vendors'
        context['total_count'] = self.get_queryset().count()
        return context


class VendorInactiveListView(LoginRequiredMixin, ListView):
    """Display only inactive vendors."""
    model = Vendor
    template_name = 'vendors/inactive.html'
    context_object_name = 'vendors'
    paginate_by = 20
    
    def get_queryset(self):
        """Return only inactive vendors."""
        return Vendor.objects.filter(is_active=False).order_by('name')
    
    def get_context_data(self, **kwargs):
        """Add additional context."""
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Inactive Vendors'
        context['total_count'] = self.get_queryset().count()
        return context


class VendorPreferredListView(LoginRequiredMixin, ListView):
    """Display only preferred vendors."""
    model = Vendor
    template_name = 'vendors/preferred.html'
    context_object_name = 'vendors'
    paginate_by = 20
    
    def get_queryset(self):
        """Return only preferred vendors."""
        return Vendor.objects.filter(is_preferred=True, is_active=True).order_by('name')
    
    def get_context_data(self, **kwargs):
        """Add additional context."""
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Preferred Vendors'
        context['total_count'] = self.get_queryset().count()
        return context


class VendorSupplierListView(LoginRequiredMixin, ListView):
    """Display only supplier vendors."""
    model = Vendor
    template_name = 'vendors/suppliers.html'
    context_object_name = 'vendors'
    paginate_by = 20
    
    def get_queryset(self):
        """Return only suppliers."""
        return Vendor.objects.filter(
            vendor_type__in=['SUPPLIER', 'MANUFACTURER']
        ).order_by('name')
    
    def get_context_data(self, **kwargs):
        """Add additional context."""
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Equipment Suppliers'
        context['total_count'] = self.get_queryset().count()
        return context


class VendorServiceProviderListView(LoginRequiredMixin, ListView):
    """Display only service provider vendors."""
    model = Vendor
    template_name = 'vendors/service_providers.html'
    context_object_name = 'vendors'
    paginate_by = 20
    
    def get_queryset(self):
        """Return only service providers."""
        return Vendor.objects.filter(
            vendor_type__in=['MAINTENANCE', 'SUPPORT', 'INSTALLATION', 'CONSULTANT']
        ).order_by('name')
    
    def get_context_data(self, **kwargs):
        """Add additional context."""
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Service Providers'
        context['total_count'] = self.get_queryset().count()
        return context


# ============================================================================
# Reports and Export Views
# ============================================================================

class VendorReportsView(LoginRequiredMixin, TemplateView):
    """Vendor reports dashboard."""
    template_name = 'vendors/reports.html'
    
    def get_context_data(self, **kwargs):
        """Add report statistics."""
        context = super().get_context_data(**kwargs)
        
        # Basic statistics
        context['total_vendors'] = Vendor.objects.count()
        context['active_vendors'] = Vendor.objects.filter(is_active=True).count()
        context['inactive_vendors'] = Vendor.objects.filter(is_active=False).count()
        context['preferred_vendors'] = Vendor.objects.filter(is_preferred=True).count()
        
        # Vendor type breakdown
        context['suppliers'] = Vendor.objects.filter(vendor_type='SUPPLIER').count()
        context['manufacturers'] = Vendor.objects.filter(vendor_type='MANUFACTURER').count()
        context['maintenance_providers'] = Vendor.objects.filter(vendor_type='MAINTENANCE').count()
        context['support_providers'] = Vendor.objects.filter(vendor_type='SUPPORT').count()
        context['installation_providers'] = Vendor.objects.filter(vendor_type='INSTALLATION').count()
        context['consultants'] = Vendor.objects.filter(vendor_type='CONSULTANT').count()
        
        # Performance statistics
        context['rated_vendors'] = Vendor.objects.filter(performance_rating__isnull=False).count()
        context['average_rating'] = Vendor.objects.filter(
            performance_rating__isnull=False
        ).aggregate(avg=Avg('performance_rating'))['avg']
        
        # Location statistics
        context['dhaka_vendors'] = Vendor.objects.filter(city__icontains='dhaka').count()
        context['international_vendors'] = Vendor.objects.exclude(country__iexact='bangladesh').count()
        
        return context


class VendorSummaryView(LoginRequiredMixin, TemplateView):
    """Vendor summary statistics view."""
    template_name = 'vendors/summary.html'
    
    def get_context_data(self, **kwargs):
        """Add summary data."""
        context = super().get_context_data(**kwargs)
        
        # Monthly vendor creation statistics
        six_months_ago = timezone.now() - timedelta(days=180)
        monthly_stats = []
        
        for i in range(6):
            month_start = six_months_ago + timedelta(days=30*i)
            month_end = month_start + timedelta(days=30)
            count = Vendor.objects.filter(
                created_at__gte=month_start,
                created_at__lt=month_end
            ).count()
            monthly_stats.append({
                'month': month_start.strftime('%B %Y'),
                'count': count
            })
        
        context['monthly_stats'] = monthly_stats
        
        # Top performing vendors
        context['top_vendors'] = Vendor.objects.filter(
            performance_rating__isnull=False,
            is_active=True
        ).order_by('-performance_rating')[:10]
        
        # Recent vendors
        context['recent_vendors'] = Vendor.objects.order_by('-created_at')[:10]
        
        return context


class VendorExportCSVView(LoginRequiredMixin, View):
    """Export vendors to CSV file."""
    
    def get(self, request):
        """Generate CSV export."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="vendors_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'Vendor Code', 'Name', 'Trade Name', 'Type', 'Status',
            'Contact Person', 'Designation', 'Phone Primary', 'Email Primary',
            'Address', 'City', 'District', 'Country',
            'Performance Rating', 'Is Preferred', 'Is Active', 'Created At'
        ])
        
        # Apply filters from request
        queryset = Vendor.objects.all()
        form = VendorSearchForm(request.GET)
        if form.is_valid():
            queryset = form.filter_queryset(queryset)
        
        # Write vendor data
        for vendor in queryset:
            writer.writerow([
                vendor.vendor_code,
                vendor.name,
                vendor.trade_name,
                vendor.get_vendor_type_display(),
                vendor.get_status_display(),
                vendor.contact_person,
                vendor.contact_designation,
                vendor.phone_primary,
                vendor.email_primary,
                vendor.address,
                vendor.city,
                vendor.district,
                vendor.country,
                vendor.performance_rating,
                'Yes' if vendor.is_preferred else 'No',
                'Yes' if vendor.is_active else 'No',
                vendor.created_at.strftime('%Y-%m-%d %H:%M:%S') if vendor.created_at else ''
            ])
        
        return response


class VendorContactExportView(LoginRequiredMixin, View):
    """Export vendor contact information to CSV."""
    
    def get(self, request):
        """Generate contact list CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="vendor_contacts_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'Vendor Code', 'Company Name', 'Contact Person', 'Designation',
            'Phone Primary', 'Phone Secondary', 'Email Primary', 'Email Secondary',
            'Address', 'Website'
        ])
        
        # Write contact data for active vendors only
        for vendor in Vendor.objects.filter(is_active=True).order_by('name'):
            writer.writerow([
                vendor.vendor_code,
                vendor.name,
                vendor.contact_person,
                vendor.contact_designation,
                vendor.phone_primary,
                vendor.phone_secondary,
                vendor.email_primary,
                vendor.email_secondary,
                vendor.full_address,
                vendor.website
            ])
        
        return response


# ============================================================================
# Quick Actions and Status Management
# ============================================================================

@login_required
@permission_required('vendors.change_vendor', raise_exception=True)
def vendor_activate(request, pk):
    """Activate a vendor."""
    vendor = get_object_or_404(Vendor, pk=pk)
    vendor.is_active = True
    vendor.status = 'ACTIVE'
    vendor.updated_by = request.user
    vendor.save()
    
    messages.success(request, f'Vendor "{vendor.name}" activated successfully!')
    return redirect('vendors:detail', pk=pk)


@login_required
@permission_required('vendors.change_vendor', raise_exception=True)
def vendor_deactivate(request, pk):
    """Deactivate a vendor."""
    vendor = get_object_or_404(Vendor, pk=pk)
    vendor.is_active = False
    vendor.status = 'INACTIVE'
    vendor.updated_by = request.user
    vendor.save()
    
    messages.success(request, f'Vendor "{vendor.name}" deactivated successfully!')
    return redirect('vendors:detail', pk=pk)


@login_required
@permission_required('vendors.change_vendor', raise_exception=True)
def vendor_toggle_preferred(request, pk):
    """Toggle vendor preferred status."""
    vendor = get_object_or_404(Vendor, pk=pk)
    vendor.is_preferred = not vendor.is_preferred
    vendor.updated_by = request.user
    vendor.save()
    
    status = "marked as preferred" if vendor.is_preferred else "removed from preferred"
    messages.success(request, f'Vendor "{vendor.name}" {status}!')
    return redirect('vendors:detail', pk=pk)


# ============================================================================
# AJAX API Endpoints
# ============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def vendor_validate_code(request):
    """AJAX endpoint to validate vendor code uniqueness."""
    vendor_code = request.POST.get('vendor_code', '').upper().strip()
    vendor_id = request.POST.get('vendor_id')  # For edit forms
    
    if not vendor_code:
        return JsonResponse({'valid': False, 'message': 'Vendor code is required.'})
    
    # Check uniqueness
    queryset = Vendor.objects.filter(vendor_code=vendor_code)
    if vendor_id:
        queryset = queryset.exclude(pk=vendor_id)
    
    if queryset.exists():
        return JsonResponse({'valid': False, 'message': 'Vendor code already exists.'})
    
    return JsonResponse({'valid': True, 'message': 'Vendor code is available.'})


@csrf_exempt
@require_http_methods(["GET"])
def vendor_search_api(request):
    """AJAX endpoint for vendor search."""
    query = request.GET.get('q', '')
    limit = int(request.GET.get('limit', 10))
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    vendors = Vendor.objects.filter(
        Q(vendor_code__icontains=query) |
        Q(name__icontains=query) |
        Q(contact_person__icontains=query)
    ).filter(is_active=True)[:limit]
    
    results = []
    for vendor in vendors:
        results.append({
            'id': vendor.pk,
            'vendor_code': vendor.vendor_code,
            'name': vendor.name,
            'contact_person': vendor.contact_person,
            'phone': vendor.phone_primary,
            'email': vendor.email_primary,
            'type': vendor.get_vendor_type_display(),
            'url': reverse('vendors:detail', kwargs={'pk': vendor.pk})
        })
    
    return JsonResponse({'results': results})