import frappe
from frappe_whatsapp.integrations.core import is_app_installed, has_doctype

@frappe.whitelist()
def create_lead_from_chat(mobile_no, contact_name, chat_history=None):
    """Creates a Lead in ERPNext/CRM from WhatsApp Chat."""
    if not is_app_installed("erpnext") or not has_doctype("Lead"):
        frappe.throw("CRM/ERPNext module is not installed.")

    # Check existence
    existing = frappe.db.exists("Lead", {"mobile_no": mobile_no})
    if existing:
        return {"name": existing, "status": "Exists"}

    try:
        lead = frappe.new_doc("Lead")
        lead.mobile_no = mobile_no
        lead.first_name = contact_name
        lead.lead_source = "WhatsApp"
        lead.notes = chat_history
        lead.save(ignore_permissions=True)
        return {"name": lead.name, "status": "Created"}
    except Exception as e:
        frappe.log_error(f"Create Lead Error: {e}")
        frappe.throw("Failed to create Lead. Check logs.")

@frappe.whitelist()
def create_issue_from_chat(mobile_no, description):
    """Creates a Support Issue from WhatsApp Chat."""
    if not has_doctype("Issue"):
        frappe.throw("Support module (Issue) is not installed.")

    # Find Customer
    customer = frappe.db.get_value("Customer", {"mobile_no": mobile_no}, "name")
    
    issue = frappe.new_doc("Issue")
    issue.subject = f"Support Request from {mobile_no}"
    issue.description = description
    if customer:
        issue.customer = customer
    
    try:
        issue.save(ignore_permissions=True)
        return {"name": issue.name, "status": "Created"}
    except Exception as e:
        frappe.log_error(f"Create Issue Error: {e}")
        frappe.throw("Failed to create Issue.")
