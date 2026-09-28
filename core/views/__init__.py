"""
CampusCare Core Views Package.
Exposes all view modules and backward-compatible view aliases.
"""

from .helpers import *
from .public import *
from .complaints import *
from .tasks import *
from .dashboards import *
from .api import *
from .auth import *

# Backward compatibility aliases
track_complaint = complaint_tracking
admin_dashboard = dashboard
provost_dashboard = dashboard
hod_dashboard = dashboard
dashboard_view = dashboard
admin_complaint_detail = complaint_detail
admin_update_status = complaint_update_status
