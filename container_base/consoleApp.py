from .baseContainer import Container
from IPython import embed

class ConsoleApp:
    def __init__(self, container_class=Container):
        self.container_class = container_class
        self.add_to_namespace = {}

    def open_console(self):
        """Opens an IPython console with access to the GUI's current data and global variables."""
        # Create a combined namespace with the instance variables and the module's global variables
        try:
            console_namespace = {
                "Container": self.container_class,
            }
            console_namespace.update(self.add_to_namespace)
            # add self to the namespace
            console_namespace["self"] = self

        except Exception as e:
            print("Error opening console:", e)
            console_namespace = {}
        embed(user_ns=console_namespace)  # Gives IPython access to both global and instance variables
