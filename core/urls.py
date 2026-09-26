from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.SubAdminLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("api/suggest-category/", views.suggest_category_api, name="suggest_category_api"),
    path("api/suggest-category/", views.suggest_category_api, name="suggest_category"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("campus-directory/", views.campus_directory, name="campus_directory"),
    path("complaints/", views.complaint_list, name="complaint_list"),
    path("complaints/new/", views.complaint_create, name="complaint_create"),
    path("track/", views.tracking_form, name="tracking_form"),
    path("track/<str:tracking_token>/", views.complaint_tracking, name="complaint_tracking"),
    path("task/<uuid:task_token>/", views.technician_task_view, name="technician_task_view"),
    path("complaints/<str:reference>/", views.complaint_detail, name="complaint_detail"),
    path("complaints/<str:reference>/assign/", views.complaint_assign, name="complaint_assign"),
    path("complaints/<str:reference>/status/", views.complaint_update_status, name="complaint_update_status"),
    path("complaints/<str:reference>/support/", views.complaint_toggle_support, name="complaint_toggle_support"),
    path("complaints/<str:reference>/verify-resolution/", views.complaint_verify_resolution, name="complaint_verify_resolution"),
    path("complaints/<str:tracking_token>/confirm/", views.student_confirm_resolution, name="student_confirm_resolution"),
    path("complaints/<str:tracking_token>/reopen/", views.student_reopen_complaint, name="student_reopen_complaint"),
    path("complaints/<str:reference>/reopen-legacy/", views.complaint_reopen, name="complaint_reopen"),
    path("complaints/<str:reference>/feedback/", views.complaint_feedback, name="complaint_feedback"),
    path("analytics/", views.analytics_dashboard, name="analytics_dashboard"),
    path("reports/complaints.csv", views.complaint_report_csv, name="complaint_report_csv"),
    path("api/analyze-urgency/", views.analyze_urgency_api, name="analyze_urgency_api"),
    path("api/room-lookup/", views.room_lookup_api, name="room_lookup_api"),
]
