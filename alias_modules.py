import sys
import containers.projectContainer
import containers.neo4jContainer
import containers.baseContainer

# Map old root-level names to new module locations
sys.modules["projectContainer"] = containers.projectContainer
sys.modules["neo4jContainer"] = containers.neo4jContainer
sys.modules["baseContainer"] = containers.baseContainer
