import frappe
from frappe.tests.utils import FrappeTestCase
from whatsapp_chat.utils.tagging import add_tag, remove_tag, auto_tag_by_keyword


class TestTagging(FrappeTestCase):
    def setUp(self):
        # Create test contact
        self.contact = frappe.new_doc("WhatsApp Contact")
        self.contact.contact_name = "Test User"
        self.contact.mobile_no = "1234567890"
        self.contact.save(ignore_permissions=True)
        
        # Create test tags
        self.tag1 = frappe.new_doc("WhatsApp Contact Tag")
        self.tag1.tag_name = "TestTag1"
        self.tag1.save(ignore_permissions=True)
        
        self.tag2 = frappe.new_doc("WhatsApp Contact Tag")
        self.tag2.tag_name = "TestTag2"
        self.tag2.save(ignore_permissions=True)

    def tearDown(self):
        frappe.db.delete("WhatsApp Contact", self.contact.name)
        frappe.db.delete("WhatsApp Contact Tag", self.tag1.name)
        frappe.db.delete("WhatsApp Contact Tag", self.tag2.name)
        frappe.db.sql("DELETE FROM `tabWhatsApp Auto Tag Rule`")

    def test_add_remove_tag(self):
        # Test add
        add_tag(self.contact.name, "TestTag1")
        contact = frappe.get_doc("WhatsApp Contact", self.contact.name)
        self.assertEqual(len(contact.tags), 1)
        self.assertEqual(contact.tags[0].tag_name, "TestTag1")
        
        # Test add duplicate (should not duplicate)
        add_tag(self.contact.name, "TestTag1")
        contact = frappe.get_doc("WhatsApp Contact", self.contact.name)
        self.assertEqual(len(contact.tags), 1)
        
        # Test add second tag
        add_tag(self.contact.name, "TestTag2")
        contact = frappe.get_doc("WhatsApp Contact", self.contact.name)
        self.assertEqual(len(contact.tags), 2)
        
        # Test remove
        remove_tag(self.contact.name, "TestTag1")
        contact = frappe.get_doc("WhatsApp Contact", self.contact.name)
        self.assertEqual(len(contact.tags), 1)
        self.assertEqual(contact.tags[0].tag_name, "TestTag2")

    def test_auto_tag_rule(self):
        # Create rule
        rule = frappe.new_doc("WhatsApp Auto Tag Rule")
        rule.rule_name = "Price Rule"
        rule.target_tag = "TestTag1"
        rule.keywords = "price, cost"
        rule.match_type = "Any"
        rule.insert(ignore_permissions=True)
        
        # Test match
        auto_tag_by_keyword("What is the price?", self.contact.name)
        contact = frappe.get_doc("WhatsApp Contact", self.contact.name)
        self.assertEqual(len(contact.tags), 1)
        self.assertEqual(contact.tags[0].tag_name, "TestTag1")
        
        # Test no match
        auto_tag_by_keyword("Hello there", self.contact.name)
        contact = frappe.get_doc("WhatsApp Contact", self.contact.name)
        self.assertEqual(len(contact.tags), 1) # Should not change
