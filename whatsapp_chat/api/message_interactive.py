@frappe.whitelist()
def send_interactive(room, user_no, message_payload):
    """
    Send interactive messages (buttons/list).
    message_payload should be a dict conforming to WhatsApp interactive spec structure,
    or at least containing keys we map in DocType.
    """
    if isinstance(message_payload, str):
        message_payload = frappe.parse_json(message_payload)
        
    content_type = message_payload.get("content_type", "interactive")
    message_text = message_payload.get("message")
    buttons = message_payload.get("buttons") # Using 'buttons' field for list items too temporarily or mapping to interactive_data
    
    doc = frappe.get_doc({
        "doctype": "WhatsApp Message",
        "type": "Outgoing",
        "to": user_no,
        "message": message_text,
        "content_type": content_type,
        "buttons": frappe.as_json(buttons) if buttons else None,
        # "interactive_data": frappe.as_json(message_payload) # For full fidelity later
    })
    doc.insert(ignore_permissions=True)
    return "ok"
