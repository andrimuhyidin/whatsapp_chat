import frappe
from frappe.model.document import Document


class WhatsAppAgentQueue(Document):
    """
    WhatsApp Agent Queue for workload management.
    
    Manages agent availability, capacity, and automatic chat
    assignment with load balancing for customer support.
    """

    def validate(self):
        if self.current_load < 0:
            self.current_load = 0
        if self.current_load > self.max_capacity:
            self.status = "Busy"

    def increment_load(self):
        """Increment current load when a new chat is assigned."""
        self.current_load = (self.current_load or 0) + 1
        if self.current_load >= self.max_capacity:
            self.status = "Busy"
        self.save(ignore_permissions=True)

    def decrement_load(self):
        """Decrement current load when a chat is resolved."""
        self.current_load = max(0, (self.current_load or 0) - 1)
        if self.current_load < self.max_capacity and self.status == "Busy":
            self.status = "Available"
        self.save(ignore_permissions=True)

    @staticmethod
    def get_available_agent():
        """Get the next available agent using round-robin with load balancing."""
        agents = frappe.get_all(
            "WhatsApp Agent Queue",
            filters={
                "status": "Available",
                "auto_assign": 1
            },
            fields=["name", "agent", "current_load", "max_capacity"],
            order_by="current_load asc, modified asc"
        )

        for agent in agents:
            if agent.current_load < agent.max_capacity:
                return agent.agent

        return None
