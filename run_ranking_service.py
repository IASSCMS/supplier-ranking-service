#!/usr/bin/env python
"""
Run script for the Supplier Ranking Service on port 8001
"""
import os
import sys

if __name__ == "__main__":
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'supplier_ranking_service.settings')
    
    # Import Django's runserver command
    from django.core.management import execute_from_command_line
    
    # Run the server on port 8001 (hardcoded)
    execute_from_command_line(['manage.py', 'runserver', '0.0.0.0:8001']) 