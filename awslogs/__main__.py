"""Allow the module to be directly executed with python3 -m"""

import sys

from .bin import main

if __name__ == "__main__":
    sys.exit(main())
