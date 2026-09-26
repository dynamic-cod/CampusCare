from django.contrib import admin

from .models import (
    Building, Campus, Complaint, ComplaintCategory, ComplaintFeedback, ComplaintStatusHistory, ComplaintSupport, Department, Floor, Room, UserProfile,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "department", "phone")
    list_filter = ("role", "department")
    search_fields = ("user__username", "user__first_name", "user__last_name", "user__email")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "email", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(Campus)
class CampusAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "campus", "is_active")
    list_filter = ("campus", "is_active")
    search_fields = ("name", "code")


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    list_display = ("building", "number", "label")
    list_filter = ("building__campus", "building")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("number", "name", "floor", "is_active")
    list_filter = ("floor__building__campus", "floor__building", "is_active")
    search_fields = ("number", "name")


@admin.register(ComplaintCategory)
class ComplaintCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "default_sla_hours", "is_active")
    list_filter = ("department", "is_active")
    search_fields = ("name", "description")


class ComplaintStatusHistoryInline(admin.TabularInline):
    model = ComplaintStatusHistory
    extra = 0
    readonly_fields = ("status", "note", "changed_by", "created_at")
    can_delete = False


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("reference", "title", "status", "priority", "priority_score", "sla_due_at", "escalation_level", "category", "reporter_display", "assigned_to", "created_at")
    list_filter = ("status", "priority", "resolution_verification", "category", "category__department")
    search_fields = ("reference", "title", "description", "reporter_name", "reporter_enrollment_number", "reporter__username")
    readonly_fields = ("reference", "created_at", "updated_at", "assigned_at", "resolved_at", "priority_score", "priority_reason", "category_detection_confidence", "sla_due_at", "escalated_at", "escalation_level", "resolution_verified_at", "reopened_count")
    autocomplete_fields = ("reporter", "room", "assigned_to", "assigned_by")
    inlines = (ComplaintStatusHistoryInline,)


@admin.register(ComplaintStatusHistory)
class ComplaintStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("complaint", "status", "changed_by", "created_at")
    list_filter = ("status",)
    search_fields = ("complaint__reference", "note")
    readonly_fields = ("complaint", "status", "note", "changed_by", "created_at")


@admin.register(ComplaintSupport)
class ComplaintSupportAdmin(admin.ModelAdmin):
    list_display = ("complaint", "user", "created_at")
    search_fields = ("complaint__reference", "user__username")
    readonly_fields = ("complaint", "user", "created_at")


@admin.register(ComplaintFeedback)
class ComplaintFeedbackAdmin(admin.ModelAdmin):
    list_display = ("complaint", "rating", "created_at")
    list_filter = ("rating",)
    readonly_fields = ("complaint", "rating", "comment", "created_at")
