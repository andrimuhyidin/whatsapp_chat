import frappe

def after_migrate():
    """Run post-migration tasks."""
    create_agent_role()

def create_agent_role():
    """Create WhatsApp Agent role if it doesn't exist."""
    if not frappe.db.exists("Role", "WhatsApp Agent"):
        role = frappe.get_doc({
            "doctype": "Role",
            "role_name": "WhatsApp Agent",
            "desk_access": 1,
            "is_custom": 0 
        })
        role.insert(ignore_permissions=True)
        frappe.db.commit()
