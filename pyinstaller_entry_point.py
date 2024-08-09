# Pyinstaller breaks relative imports (i.e. from .filter import Filter) unless the program itself
# is included as a dependency. This is a dummy program whos only job is to import flump.

from flump.flump import main

main()