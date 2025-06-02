# conftest.py
import pytest
import os

def pytest_ignore_collect(path, config):
    # Determine the file path as string
    try:
        path_str = path.strpath
    except AttributeError:
        path_str = str(path)

    # Skip the standalone final test scripts
    if os.path.basename(path_str) in ("final_system_test.py", "test_complete_delete_flow.py", "test_jurisdiction_contacts.py"):
        return True

    # Skip any files under a virtual environment directory
    if "venv" in path_str.split(os.sep):
        return True

    return False
