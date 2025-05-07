import sys
import containers.projectContainer
import containers.baseContainer

# Map old root-level names to new module locations
sys.modules["projectContainer"] = containers.projectContainer
sys.modules["baseContainer"] = containers.baseContainer
