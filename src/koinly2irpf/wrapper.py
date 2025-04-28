   #!/usr/bin/env python
   # -*- coding: utf-8 -*-

   """
   Wrapper module to handle package structure transition.
   This file helps to resolve import issues between old and new package structures.
   """

   import sys
   import os
   import logging

   # Try to add the parent directory to the path so we can import from src
   # This is a fallback mechanism to ensure backwards compatibility
   parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
   if parent_dir not in sys.path:
       sys.path.insert(0, parent_dir)

   def run_main():
       """Run the main application."""
       try:
           # First try the preferred import path
           from koinly2irpf.cli import main
           return main()
       except ImportError as e:
           logging.warning(f"Import error with preferred path: {e}")
           try:
               # Fall back to legacy import paths
               from src.main import main
               logging.warning("Using legacy import path 'src.main'. This will be deprecated in future versions.")
               return main()
           except ImportError as e2:
               logging.error(f"Failed to import using legacy path: {e2}")
               # Try one more approach - direct import assuming we're already in the src directory
               try:
                   from main import main
                   logging.warning("Using direct import 'main'. This will be deprecated in future versions.")
                   return main()
               except ImportError as e3:
                   logging.error(f"All import attempts failed. Last error: {e3}")
                   print("ERROR: Failed to import the main module. Please reinstall the package.")
                   return 1

   if __name__ == "__main__":
       sys.exit(run_main())
