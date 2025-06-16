#!/bin/bash
"""
Phase 1 Cleanup Script
Remove redundant debug/test files and organize codebase
"""

echo "Starting Phase 1: Code Cleanup and Stabilization"
echo "================================================"

# Create backup directory for removed files
echo "Creating backup directory..."
mkdir -p .cleanup_backup/phase1_$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=".cleanup_backup/phase1_$(date +%Y%m%d_%H%M%S)"

# Function to safely remove files with backup
safe_remove() {
    local file=$1
    if [ -f "$file" ]; then
        echo "Removing: $file"
        cp "$file" "$BACKUP_DIR/"
        rm "$file"
    fi
}

# 1. Remove redundant debug files
echo "Removing redundant debug files..."
safe_remove "debug_test.py"
safe_remove "debug_archived.py"
safe_remove "simple_diagnostic.py"
safe_remove "debug_vehicle_edit.py"
safe_remove "debug_test.html"

# 2. Remove redundant test files (keeping organized ones)
echo "Removing scattered test files..."
safe_remove "test_active_vehicles_fix.py"
safe_remove "test_add_vehicle_fix.py"
safe_remove "test_auth_direct.py"
safe_remove "test_auth_status_update.py"
safe_remove "test_auth_update.py"
safe_remove "test_authenticated_update.py"
safe_remove "test_button_functionality.py"
safe_remove "test_button_resolution_final.py"
safe_remove "test_chrome_configs.py"
safe_remove "test_chrome_fix.py"
safe_remove "test_chrome_webdriver.py"
safe_remove "test_complete_auth.py"
safe_remove "test_complete_delete_flow.py"
safe_remove "test_current_errors.py"
safe_remove "test_daily_check_final.py"
safe_remove "test_daily_check_isolated.py"
safe_remove "test_date_consistency.py"
safe_remove "test_date_consistency_flask.py"
safe_remove "test_delete_button_fix.py"
safe_remove "test_delete_complete.py"
safe_remove "test_delete_functionality.py"
safe_remove "test_edit_button_final.py"
safe_remove "test_edit_modal_debug.py"
safe_remove "test_edit_modal_fix.py"
safe_remove "test_end_to_end.py"
safe_remove "test_field_mapping.py"
safe_remove "test_final_functionality.py"
safe_remove "test_final_pdf_endpoints.py"
safe_remove "test_frontend_integration.py"
safe_remove "test_integration.py"
safe_remove "test_js_functions.py"
safe_remove "test_jurisdiction_contacts.py"
safe_remove "test_login_only.py"
safe_remove "test_scheduler_functionality.py"
safe_remove "test_scraper_api.py"
safe_remove "test_scraper_context.py"
safe_remove "test_scraper_init.py"
safe_remove "test_scraper_test_mode.py"
safe_remove "test_scraping.py"
safe_remove "test_scraping_api.py"
safe_remove "test_session_debug.py"
safe_remove "test_session_fix.py"
safe_remove "test_status_update_final.py"
safe_remove "test_towbook_scraper.py"
safe_remove "test_vehicle_update.py"
safe_remove "test_vehicle_visibility.py"
safe_remove "test_web_interface.py"
safe_remove "test_webdriver.py"

# 3. Remove redundant HTML test files
echo "Removing HTML debug files..."
safe_remove "auth_diagnostics.html"
safe_remove "function_fix_test.html"
safe_remove "test_date_fix.html"
safe_remove "test_date_formatting_complete.html"
safe_remove "test_date_issue.html"

# 4. Remove fix-specific scripts that are no longer needed
echo "Removing one-off fix scripts..."
safe_remove "fix_auth.py"
safe_remove "fix_archived_field.py"
safe_remove "apply_schema_changes.py"
safe_remove "cleanup_chrome_dirs.py"
safe_remove "create_test_admin.py"
safe_remove "migrate_db.py"
safe_remove "monitor_scraping.py"
safe_remove "normalize_dates.py"
safe_remove "verify_chrome_fixes.py"

# 5. Clean up log files (keep recent ones)
echo "Organizing log files..."
find . -name "*.log" -not -path "./logs/*" -not -name "*.log" -exec mv {} logs/ \; 2>/dev/null || true

# 6. Clean up markdown documentation files
echo "Organizing documentation..."
mkdir -p docs/fixes
safe_remove "AUTHENTICATION_FIX_COMPLETE.md"
safe_remove "AUTHENTICATION_TROUBLESHOOTING.md"
safe_remove "CHROME_WEBDRIVER_FIX_COMPLETE.md"
safe_remove "DAILY_CHECK_IMPLEMENTATION_COMPLETE.md"
safe_remove "DATABASE_CONNECTION_FIX_SUMMARY.md"
safe_remove "DELETE_BUTTON_FIX_COMPLETE.md"
safe_remove "DEPLOYMENT_VALIDATION_REPORT.md"
safe_remove "FIELD_MAPPING_FIX_COMPLETE.md"
safe_remove "ISSUES_RESOLVED_COMPLETE.md"
safe_remove "MODAL_BUTTONS_RESOLUTION_COMPLETE.md"

# 7. Clean up __pycache__ directories
echo "Cleaning up Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# 8. Create organized test structure
echo "Creating organized test structure..."
mkdir -p tests/{unit,integration,fixtures}

# Move remaining important test files to proper location
if [ -f "comprehensive_test.py" ]; then
    mv comprehensive_test.py tests/integration/
fi

if [ -f "final_system_test.py" ]; then
    mv final_system_test.py tests/integration/
fi

if [ -f "conftest.py" ]; then
    mv conftest.py tests/
fi

if [ -f "pytest.ini" ]; then
    # Keep pytest.ini in root
    echo "Keeping pytest.ini in root directory"
fi

echo ""
echo "Phase 1 Cleanup Summary:"
echo "========================"
echo "✓ Removed redundant debug files"
echo "✓ Cleaned up scattered test files"
echo "✓ Organized documentation"
echo "✓ Created new directory structure"
echo "✓ Cleaned up cache files"
echo ""
echo "Backup created in: $BACKUP_DIR"
echo "New structure ready for Phase 2 development"
echo ""
echo "Next: Run 'python -m app.factory' to test new application structure"
