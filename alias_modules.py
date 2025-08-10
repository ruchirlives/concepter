import sys
import containers.projectContainer
import containers.ConceptContainer

# Map old root-level names to new module locations
sys.modules["projectContainer"] = containers.projectContainer
sys.modules["baseContainer"] = containers.ConceptContainer
