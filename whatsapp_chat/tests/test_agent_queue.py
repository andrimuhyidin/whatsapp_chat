import frappe
from frappe.tests.utils import FrappeTestCase

class TestAgentQueue(FrappeTestCase):
    def setUp(self):
        # Create test users/agents
        self.agent1 = "agent1@example.com"
        self.agent2 = "agent2@example.com"
        
        self._create_user(self.agent1)
        self._create_user(self.agent2)
        
        # Create Queues
        self.queue1 = self._create_queue(self.agent1, 5)
        self.queue2 = self._create_queue(self.agent2, 5)

    def _create_user(self, email):
        if not frappe.db.exists("User", email):
            u = frappe.new_doc("User")
            u.email = email
            u.first_name = email.split("@")[0]
            u.save(ignore_permissions=True)

    def _create_queue(self, agent, capacity):
        if frappe.db.exists("WhatsApp Agent Queue", agent):
            frappe.db.delete("WhatsApp Agent Queue", agent)
            
        q = frappe.new_doc("WhatsApp Agent Queue")
        q.agent = agent
        q.status = "Available"
        q.max_capacity = capacity
        q.current_load = 0
        q.auto_assign = 1
        q.insert(ignore_permissions=True)
        return q

    def tearDown(self):
        frappe.db.delete("WhatsApp Agent Queue", self.agent1)
        frappe.db.delete("WhatsApp Agent Queue", self.agent2)

    def test_increment_decrement_load(self):
        q = frappe.get_doc("WhatsApp Agent Queue", self.agent1)
        initial = q.current_load
        
        # Test Increment
        q.increment_load()
        q.reload()
        self.assertEqual(q.current_load, initial + 1)
        
        # Test Decrement
        q.decrement_load()
        q.reload()
        self.assertEqual(q.current_load, initial)
        
        # Test Decrement below zero (should stay 0)
        q.current_load = 0
        q.decrement_load()
        q.reload()
        self.assertEqual(q.current_load, 0)

    def test_get_available_agent(self):
        from whatsapp_chat.whatsapp_chat.doctype.whatsapp_agent_queue.whatsapp_agent_queue import WhatsAppAgentQueue
        
        # Set agent1 load to 1, agent2 load to 0
        q1 = frappe.get_doc("WhatsApp Agent Queue", self.agent1)
        q1.current_load = 1
        q1.save()
        
        q2 = frappe.get_doc("WhatsApp Agent Queue", self.agent2)
        q2.current_load = 0
        q2.save()
        
        # Should pick agent2 (lowest load)
        selected = WhatsAppAgentQueue.get_available_agent()
        self.assertEqual(selected, self.agent2)
        
        # Set agent2 to max capacity
        q2.current_load = 5
        q2.save()
        
        # Should pick agent1 now
        selected = WhatsAppAgentQueue.get_available_agent()
        self.assertEqual(selected, self.agent1)
        
        # Set agent1 to max capacity
        q1.current_load = 5
        q1.save()
        
        # Should return None (all full)
        selected = WhatsAppAgentQueue.get_available_agent()
        self.assertIsNone(selected)
