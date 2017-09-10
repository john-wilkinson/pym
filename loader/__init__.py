import sys
from .pym import PymLoader

sys.meta_path.insert(0, PymLoader())
