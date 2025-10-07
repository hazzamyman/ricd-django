# Import all models first to ensure they are loaded before forms reference them
import ricd.models

# Import all forms for backward compatibility
from .core import *
from .reporting import *
from .users import *
from .funding import *
from .project import *