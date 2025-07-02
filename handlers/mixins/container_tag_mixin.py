from containers.projectContainer import ProjectContainer


class ContainerTagMixin:
    """Mixin for handling container tagging operations."""
    
    def add_child_with_tags(self, container: ProjectContainer, child):
        """Add a child container and inherit parent tags."""
        container.add_container(child)
        # For each tag in the parent's Tags array, add it to the child unless it already exists
        parent_tags = container.getValue("Tags", [])
        child.append_tags(parent_tags)
