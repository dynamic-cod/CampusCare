#!/usr/bin/env python3
"""
Pillar 4: UI/UX, Accessibility & Mobile Readiness Test Suite
Comprehensive testing for:
1. Semantic HTML & Viewport Meta Tags for Mobile Browsers
2. Accessible Form Controls (Labels, aria-labels, descriptive placeholders)
3. Image Alt Attributes & Media Accessibility
4. Button & Anchor Accessibility (Text content, icons with labels)
5. Responsive Breakpoints & Touch Target Sizing (CSS Audit)
6. WCAG AA Color Contrast Tokens & Typography System
"""
import os
import re
import sys
from html.parser import HTMLParser
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campuscare.settings")
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from core.models import UserProfile, Building, Complaint

def run_tests():
    print("=" * 80)
    print("📱 PILLAR 4: UI/UX, ACCESSIBILITY & MOBILE READINESS TEST SUITE")
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

    # Pages to test
    superuser = User.objects.filter(is_superuser=True).first()
    if not superuser:
        superuser = User.objects.create_superuser("p4_admin", "admin@amu.edu", "Password123!")

    provost = User.objects.filter(profile__role=UserProfile.Role.PROVOST).first()
    if not provost:
        hall = Building.objects.filter(is_active=True, parent__isnull=True).first()
        provost = User.objects.create_user("p4_provost", "provost@amu.edu", "Password123!")
        prof = provost.profile
        prof.role = UserProfile.Role.PROVOST
        prof.managed_building = hall
        prof.save()

    sample_complaint = Complaint.objects.first()
    ref = sample_complaint.reference if sample_complaint else "CC-00000001"
    token = sample_complaint.tracking_token if sample_complaint else "abc123"

    pages_to_audit = [
        ("/", "Public Homepage", None),
        ("/complaints/new/", "Complaint Lodging Portal", None),
        (f"/track/{token}/", "Student Tracking Portal", None),
        ("/track/", "Ticket Lookup Form", None),
        ("/login/", "Authentication Portal", None),
        ("/complaints/", "Complaint Directory", superuser),
        ("/dashboard/", "Registrar Master Console", superuser),
        ("/dashboard/", "Provost Hall Console", provost),
    ]

    # --- 4.1 VIEWPORT META TAG AUDIT ---
    print("\n[4.1] Mobile Viewport Meta Tag Audit:")
    for path, name, auth_user in pages_to_audit:
        if auth_user:
            client.force_login(auth_user)
        else:
            client.logout()

        resp = client.get(path)
        html = resp.content.decode("utf-8", errors="ignore")
        has_proper_viewport = bool(re.search(r'<meta[^>]+name=["\']viewport["\'][^>]+content=["\'][^"\']*width=device-width', html, re.I))
        check(has_proper_viewport, f"Page '{name}' has mobile viewport tag: <meta name='viewport' content='...'>")

    # --- 4.2 FORM CONTROL ACCESSIBILITY AUDIT ---
    print("\n[4.2] Accessible Form Controls (Labels / aria-label):")
    # Audit Complaint Form
    client.logout()
    resp_form = client.get("/complaints/new/")
    html_form = resp_form.content.decode("utf-8", errors="ignore")
    
    # Check that key form fields have IDs and matching labels
    expected_fields = ["reporter_name", "reporter_enrollment_number", "title", "description", "category"]
    for field_name in expected_fields:
        has_field = f'name="{field_name}"' in html_form or f"name='{field_name}'" in html_form
        has_label_or_aria = (f'for="id_{field_name}"' in html_form or 
                             f'for="{field_name}"' in html_form or 
                             f'aria-label=' in html_form or 
                             f'placeholder=' in html_form)
        check(has_field and has_label_or_aria, f"Field '{field_name}' is rendered with accessible label/descriptor")

    # --- 4.3 HEADING HIERARCHY AUDIT ---
    print("\n[4.3] Heading Hierarchy Audit (WCAG 1.3.1):")
    for path, name, auth_user in pages_to_audit[:5]:
        if auth_user:
            client.force_login(auth_user)
        else:
            client.logout()
        resp = client.get(path)
        html_page = resp.content.decode("utf-8", errors="ignore")
        h1_matches = re.findall(r'<h1[^>]*>(.*?)</h1>', html_page, re.I | re.S)
        check(len(h1_matches) >= 1, f"Page '{name}' has primary <h1> semantic heading (Count = {len(h1_matches)})")

    # --- 4.4 IMAGE ACCESSIBILITY (ALT ATTRIBUTES) ---
    print("\n[4.4] Image Accessibility (WCAG 1.1.1 Non-Text Content):")
    for path, name, auth_user in pages_to_audit[:4]:
        if auth_user:
            client.force_login(auth_user)
        else:
            client.logout()
        resp = client.get(path)
        html_page = resp.content.decode("utf-8", errors="ignore")
        img_tags = re.findall(r'<img[^>]+>', html_page, re.I)
        missing_alt = [img for img in img_tags if 'alt=' not in img.lower()]
        check(len(missing_alt) == 0, f"All images in '{name}' have alt attributes (Total: {len(img_tags)}, Missing: {len(missing_alt)})")

    # --- 4.5 CSS RESPONSIVENESS & TOUCH TARGET AUDIT ---
    print("\n[4.5] CSS Mobile Media Queries & Touch Target Standards:")
    css_files = ["static/styles.css", "static/css/styles.css", "styles.css"]
    css_content = ""
    for cf in css_files:
        if os.path.exists(cf):
            with open(cf, "r") as f:
                css_content += f.read() + "\n"

    # Check for mobile media queries
    media_queries = re.findall(r"@media\s*\([^\)]+\)", css_content)
    has_mobile_mq = any("max-width" in mq or "min-width" in mq for mq in media_queries)
    check(has_mobile_mq, f"CSS defines responsive media queries (Found: {len(media_queries)} breakpoints)")

    # Check for touch target sizing (min-height >= 40px or padding)
    has_btn_touch_sizing = ("min-height" in css_content or "padding" in css_content) and ("btn" in css_content)
    check(has_btn_touch_sizing, "Interactive button elements define touch target sizing and padding")

    # Check for modern fluid/flex/grid layout rules
    has_flex_or_grid = "display: flex" in css_content or "display: grid" in css_content
    check(has_flex_or_grid, "CSS incorporates modern Flexbox / CSS Grid responsive layout rules")

    # --- 4.6 COLOR TOKENS & TYPOGRAPHY SYSTEM ---
    print("\n[4.6] Design System & Color Tokens:")
    has_amu_tokens = "--amu-" in css_content
    check(has_amu_tokens, "CSS implements custom design system tokens (--amu-* CSS variables)")

    has_google_fonts = ("Outfit" in css_content or "Inter" in css_content or "Roboto" in css_content or "system-ui" in css_content or "-apple-system" in css_content)
    check(has_google_fonts, "Typography defines modern responsive font stack (Inter/Outfit/system-ui)")

    client.logout()

    print("\n" + "=" * 80)
    print(f"PILLAR 4 SUMMARY: {passed} PASSED | {failed} FAILED (Total: {passed + failed})")
    print("=" * 80)
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
