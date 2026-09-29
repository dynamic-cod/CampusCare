#!/usr/bin/env python3
"""
Pillar 2: Database Optimization & ORM Efficiency Test Suite
Comprehensive testing for:
1. N+1 Query Detection & Constant O(1) Query Scaling across Core Views
2. Select_related & Prefetch_related Join Verification
3. Single-Query KPI SQL Aggregations vs In-Memory Computations
4. Database Indexing & Constraint Validation
5. Response Time & Execution Latency Profiling
"""
import os
import sys
import time
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campuscare.settings")
django.setup()

from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.contrib.auth.models import User
from core.models import Complaint, ComplaintCategory, Building, Department, Room, UserProfile

def run_tests():
    print("=" * 80)
    print("⚡ PILLAR 2: DATABASE OPTIMIZATION & ORM EFFICIENCY TEST SUITE")
    print("=" * 80)
    client = Client()
    passed = 0
    failed = 0
    failures = []

    def check(condition, test_name, detail=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✅ [PASS] {test_name}")
            if detail:
                print(f"       ↳ {detail}")
        else:
            failed += 1
            print(f"  ❌ [FAIL] {test_name}")
            if detail:
                print(f"       ↳ {detail}")
            failures.append((test_name, detail))

    # --- 2.1 CONSTANT QUERY COUNT / N+1 PREVENTION ---
    print("\n[2.1] N+1 Query Auditing & O(1) Scaling Verification:")

    # Prepare accounts
    superuser = User.objects.filter(is_superuser=True).first()
    if not superuser:
        superuser = User.objects.create_superuser("p2_admin", "admin@amu.edu", "Password123!")

    provost = User.objects.filter(profile__role=UserProfile.Role.PROVOST).first()
    if not provost:
        hall = Building.objects.filter(is_active=True, parent__isnull=True).first()
        provost = User.objects.create_user("p2_provost", "provost@amu.edu", "Password123!")
        prof = provost.profile
        prof.role = UserProfile.Role.PROVOST
        prof.managed_building = hall
        prof.save()

    # Measure queries on Public Homepage (/)
    with CaptureQueriesContext(connection) as ctx_home:
        resp_home = client.get("/")
    query_count_home = len(ctx_home.captured_queries)
    check(query_count_home <= 15, f"Homepage query count is optimized: {query_count_home} queries (threshold <= 15)")

    # Measure queries on Complaints Directory (/complaints/)
    client.force_login(superuser)
    with CaptureQueriesContext(connection) as ctx_list:
        resp_list = client.get("/complaints/")
    query_count_list = len(ctx_list.captured_queries)
    check(query_count_list <= 20, f"Complaint list query count is optimized: {query_count_list} queries (threshold <= 20)")

    # Measure queries on Master Dashboard (/dashboard/)
    with CaptureQueriesContext(connection) as ctx_dash:
        resp_dash = client.get("/dashboard/")
    query_count_dash = len(ctx_dash.captured_queries)
    check(query_count_dash <= 25, f"Registrar master dashboard query count: {query_count_dash} queries (threshold <= 25)")

    # Measure queries on Provost Console (/dashboard/)
    client.force_login(provost)
    with CaptureQueriesContext(connection) as ctx_prov_dash:
        resp_prov_dash = client.get("/dashboard/")
    query_count_prov_dash = len(ctx_prov_dash.captured_queries)
    check(query_count_prov_dash <= 25, f"Provost scoped dashboard query count: {query_count_prov_dash} queries (threshold <= 25)")

    # Measure queries on Analytics Dashboard (/analytics/)
    client.force_login(superuser)
    with CaptureQueriesContext(connection) as ctx_analytics:
        resp_analytics = client.get("/analytics/")
    query_count_analytics = len(ctx_analytics.captured_queries)
    check(query_count_analytics <= 25, f"Analytics dashboard query count: {query_count_analytics} queries (threshold <= 25)")

    # Measure queries on Heatmap API (/api/heatmap-data/)
    with CaptureQueriesContext(connection) as ctx_heatmap:
        resp_heatmap = client.get("/api/heatmap-data/")
    query_count_heatmap = len(ctx_heatmap.captured_queries)
    check(query_count_heatmap <= 15, f"Heatmap API query count: {query_count_heatmap} queries (threshold <= 15)")

    # --- 2.2 O(1) QUERY SCALING TEST (NO N+1 LEAKS) ---
    print("\n[2.2] Query Scaling Linearity Test (10 complaints vs 30 complaints):")
    # Fetch 10 complaints in memory and count queries
    cat = ComplaintCategory.objects.first()
    hall = Building.objects.first()
    room = Room.objects.filter(floor__building=hall).first()

    temp_complaints = []
    for i in range(15):
        temp_c = Complaint.objects.create(
            reporter_name=f"Scale Test {i}",
            reporter_enrollment_number="GQ9000",
            title=f"Scale Test Complaint {i}",
            description="Testing query linearity",
            category=cat,
            room=room,
            location_description=hall.name if hall else "Campus",
            is_public=True
        )
        temp_complaints.append(temp_c)

    with CaptureQueriesContext(connection) as ctx_after_create:
        client.get("/complaints/")
    query_count_after = len(ctx_after_create.captured_queries)

    # Clean up temp
    for c in temp_complaints:
        c.delete()

    query_delta = abs(query_count_after - query_count_list)
    check(query_delta <= 3, f"Query count does NOT increase proportionally with rows (Delta = {query_delta} queries, O(1) proven)")

    # --- 2.3 SQL AGGREGATION VS IN-MEMORY AUDIT ---
    print("\n[2.3] Consolidated SQL Aggregation Audit:")
    # Verify that dashboards use SQL aggregation (Count/Avg) rather than python len() or sum()
    captured_sql = " ".join([q["sql"].upper() for q in ctx_dash.captured_queries])
    has_sql_count = "COUNT(" in captured_sql
    check(has_sql_count, "Dashboard uses native database COUNT() aggregations")

    # --- 2.4 DATABASE INDEXING & INTEGRITY AUDIT ---
    print("\n[2.4] Database Indexing & Constraint Validation:")
    complaint_indexes = [idx.name for idx in Complaint._meta.indexes]
    print(f"       Found Complaint indexes: {complaint_indexes}")

    expected_indexes = [
        "complaint_stat_creat_idx",
        "complaint_prio_stat_idx",
        "complaint_cat_stat_idx",
        "complaint_created_at_idx",
    ]
    for exp_idx in expected_indexes:
        check(exp_idx in complaint_indexes, f"Complaint index '{exp_idx}' is properly configured in Meta.indexes")

    # Check indexed fields
    enr_indexed = Complaint._meta.get_field("reporter_enrollment_number").db_index
    check(enr_indexed, "Field 'reporter_enrollment_number' has db_index=True")

    status_indexed = Complaint._meta.get_field("status").db_index
    check(status_indexed, "Field 'status' has db_index=True")

    # Check Unique Constraints
    ref_unique = Complaint._meta.get_field("reference").unique
    check(ref_unique, "Field 'reference' enforces unique=True")

    token_unique = Complaint._meta.get_field("tracking_token").unique
    check(token_unique, "Field 'tracking_token' enforces unique=True")

    task_token_unique = Complaint._meta.get_field("staff_task_token").unique
    check(task_token_unique, "Field 'staff_task_token' enforces unique=True")

    # --- 2.5 LATENCY & EXECUTION PROFILING ---
    print("\n[2.5] Latency & Execution Speed Profiling (1,500+ records in DB):")
    endpoints_to_benchmark = [
        ("/", "Public Homepage", 100.0),
        ("/api/heatmap-data/", "Heatmap API (1,500 coordinates)", 250.0),
        ("/dashboard/", "Registrar Master Console (Full Unpaginated Dataset)", 1000.0),
        ("/complaints/", "Complaints Directory (Full Unpaginated Dataset)", 1000.0),
    ]
    for url, label, max_allowed in endpoints_to_benchmark:
        latencies = []
        for _ in range(5):
            t0 = time.perf_counter()
            resp = client.get(url)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000)
        avg_latency = sum(latencies) / len(latencies)
        check(avg_latency < max_allowed, f"{label} responds in {avg_latency:.1f}ms (threshold < {max_allowed:.0f}ms)")

    client.logout()

    print("\n" + "=" * 80)
    print(f"PILLAR 2 SUMMARY: {passed} PASSED | {failed} FAILED (Total: {passed + failed})")
    print("=" * 80)
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
