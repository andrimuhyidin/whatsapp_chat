"""Tagging utilities for WhatsApp contacts."""
import frappe
from frappe.utils import now_datetime


def add_tag(contact_name, tag_name):
    """Add a tag to a contact if not exists."""
    if not frappe.db.exists("WhatsApp Contact Tag", tag_name):
        frappe.log_error(f"Tag {tag_name} does not exist", "WhatsApp Tagging")
        return False
    
    contact = frappe.get_doc("WhatsApp Contact", contact_name)
    
    # Check if tag already assigned
    existing = [t.tag_name for t in contact.tags]
    if tag_name not in existing:
        contact.append("tags", {"tag_name": tag_name})
        contact.save(ignore_permissions=True)
        return True
        
    return False


def remove_tag(contact_name, tag_name):
    """Remove a tag from a contact."""
    contact = frappe.get_doc("WhatsApp Contact", contact_name)
    
    # Filter out the tag
    params_to_keep = [t for t in contact.tags if t.tag_name != tag_name]
    
    if len(params_to_keep) < len(contact.tags):
        contact.tags = params_to_keep
        contact.save(ignore_permissions=True)
        return True
        
    return False


def auto_tag_by_keyword(message_content, contact_name):
    """
    Check message content against Auto Tag Rules and apply tags.
    Should be called on incoming message.
    """
    if not message_content:
        return
        
    active_rules = frappe.get_all(
        "WhatsApp Auto Tag Rule",
        filters={"is_active": 1},
        fields=["name", "target_tag", "keywords", "match_type"]
    )
    
    message_lower = message_content.lower()
    
    for rule in active_rules:
        if not rule.keywords:
            continue
            
        keywords = [k.strip().lower() for k in rule.keywords.split(",")]
        match = False
        
        if rule.match_type == "All":
            # All keywords must be present
            match = all(k in message_lower for k in keywords)
        else:
            # Any keyword present
            match = any(k in message_lower for k in keywords)
            
        if match:
            add_tag(contact_name, rule.target_tag)


def update_contact_dates(contact_name, message_date):
    """Update first/last message date for a contact."""
    contact = frappe.get_doc("WhatsApp Contact", contact_name)
    
    if not contact.first_message_date:
        contact.first_message_date = message_date
    
    contact.last_message_date = message_date
    contact.save(ignore_permissions=True)
