import frappe
from frappe_whatsapp.utils import format_number

def sync_entity_to_whatsapp_contact(doc, method=None):
    """
    Syncs Customer/Supplier/User to WhatsApp Contact.
    Hook this to on_update or on_insert.
    """
    mobile_no = None
    contact_name = None

    if doc.doctype == "User":
        mobile_no = doc.mobile_no
        contact_name = doc.full_name
    elif doc.doctype == "Customer":
        mobile_no = doc.mobile_no
        contact_name = doc.customer_name
    elif doc.doctype == "Supplier":
        mobile_no = doc.mobile_no
        contact_name = doc.supplier_name
    elif doc.doctype == "Contact": # Standard Frappe Contact
        mobile_no = doc.mobile_no
        contact_name = doc.full_name

    if not mobile_no:
        return

    formatted_number = format_number(mobile_no)
    if not formatted_number:
        return

    # Check if exists
    exists = frappe.db.exists("WhatsApp Contact", {"mobile_no": formatted_number})
    if exists:
        # Update name if changed? standard behavior usually avoids overwriting unless empty
        # But let's keep it simple: Ensure it exists.
        return
    
    # Create new
    try:
        new_contact = frappe.new_doc("WhatsApp Contact")
        new_contact.mobile_no = formatted_number
        new_contact.contact_name = contact_name
        if doc.doctype == "User":
            new_contact.email = doc.email
        new_contact.insert(ignore_permissions=True)
    except frappe.DuplicateEntryError:
        pass
    except Exception as e:
        frappe.log_error(f"Failed to sync {doc.doctype} {doc.name}: {e}", "WhatsApp Contact Sync")

def sync_all_contacts():
    """Batch sync all entities."""
    for doctype in ["User", "Customer", "Supplier"]:
        if not frappe.db.exists("DocType", doctype):
            continue
            
        docs = frappe.get_all(doctype, fields=["*"])
        for d in docs:
            doc = frappe.get_doc(doctype, d.name)
            sync_entity_to_whatsapp_contact(doc)
    
    frappe.msgprint("Contacts Synced Successfully")
