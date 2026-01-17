"""Agent assignment utilities for WhatsApp Chat."""
import frappe
from frappe import _


def auto_assign_agent(contact_name: str) -> str | None:
    """
    Auto-assign an available agent to a WhatsApp Contact.
    
    Args:
        contact_name: Name of the WhatsApp Contact
    
    Returns:
        Assigned agent user ID or None if no agent available
    """
    from whatsapp_chat.whatsapp_chat.doctype.whatsapp_agent_queue.whatsapp_agent_queue import WhatsAppAgentQueue
    
    agent = WhatsAppAgentQueue.get_available_agent()
    
    if not agent:
        return None
    
    # Assign agent to contact
    frappe.db.set_value("WhatsApp Contact", contact_name, {
        "assigned_agent": agent,
        "chat_status": "In Progress"
    })
    
    # Increment agent load
    agent_queue = frappe.get_doc("WhatsApp Agent Queue", agent)
    agent_queue.increment_load()
    
    # Send notification to agent
    notify_agent(agent, contact_name)
    
    return agent


def reassign_agent(contact_name: str, new_agent: str, reason: str = "") -> bool:
    """
    Reassign a contact to a different agent.
    
    Args:
        contact_name: Name of the WhatsApp Contact
        new_agent: User ID of the new agent
        reason: Optional reason for reassignment
    
    Returns:
        True if successful
    """
    contact = frappe.get_doc("WhatsApp Contact", contact_name)
    old_agent = contact.assigned_agent
    
    # Decrement old agent's load
    if old_agent and frappe.db.exists("WhatsApp Agent Queue", old_agent):
        old_queue = frappe.get_doc("WhatsApp Agent Queue", old_agent)
        old_queue.decrement_load()
    
    # Assign new agent
    contact.assigned_agent = new_agent
    contact.save(ignore_permissions=True)
    
    # Increment new agent's load
    if frappe.db.exists("WhatsApp Agent Queue", new_agent):
        new_queue = frappe.get_doc("WhatsApp Agent Queue", new_agent)
        new_queue.increment_load()
    
    # Notify new agent
    notify_agent(new_agent, contact_name, is_transfer=True)
    
    # Log the transfer
    frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Info",
        "reference_doctype": "WhatsApp Contact",
        "reference_name": contact_name,
        "content": f"Chat transferred from {old_agent} to {new_agent}. Reason: {reason or 'Not specified'}"
    }).insert(ignore_permissions=True)
    
    return True


def resolve_chat(contact_name: str) -> bool:
    """
    Mark a chat as resolved and decrement agent load.
    
    Args:
        contact_name: Name of the WhatsApp Contact
    
    Returns:
        True if successful
    """
    contact = frappe.get_doc("WhatsApp Contact", contact_name)
    agent = contact.assigned_agent
    
    contact.chat_status = "Resolved"
    contact.save(ignore_permissions=True)
    
    # Decrement agent load
    if agent and frappe.db.exists("WhatsApp Agent Queue", agent):
        queue = frappe.get_doc("WhatsApp Agent Queue", agent)
        queue.decrement_load()
    
    return True


def notify_agent(agent: str, contact_name: str, is_transfer: bool = False):
    """
    Send notification to agent about new/transferred chat.
    
    Args:
        agent: User ID of the agent
        contact_name: Name of the WhatsApp Contact
        is_transfer: Whether this is a transfer notification
    """
    contact = frappe.get_doc("WhatsApp Contact", contact_name)
    
    # Get agent's notification preference
    pref = frappe.db.get_value("WhatsApp Agent Queue", agent, "notification_preferences") or "Desk"
    
    title = "Chat Transferred" if is_transfer else "New Chat Assigned"
    message = f"You have a new WhatsApp chat from {contact.contact_name or contact.mobile_no}"
    
    if pref in ["Desk", "Both"]:
        # Desk notification
        frappe.publish_realtime(
            "msgprint",
            {
                "message": message,
                "title": title,
                "indicator": "blue"
            },
            user=agent
        )
    
    if pref in ["Email", "Both"]:
        # Email notification
        try:
            frappe.sendmail(
                recipients=[agent],
                subject=f"[WhatsApp] {title}",
                message=f"""
                <p>{message}</p>
                <p><a href="/app/chat?contact={contact_name}">Open Chat</a></p>
                """,
                now=True
            )
        except Exception as e:
            frappe.log_error(f"Failed to send agent notification email: {e}", "WhatsApp Agent Notification")


# API endpoints for frontend
@frappe.whitelist()
def assign_chat_to_me(contact_name: str) -> dict:
    """API endpoint for agent to claim a chat."""
    agent = frappe.session.user
    
    if not frappe.db.exists("WhatsApp Agent Queue", agent):
        frappe.throw(_("You are not registered as a WhatsApp agent"))
    
    contact = frappe.get_doc("WhatsApp Contact", contact_name)
    
    if contact.assigned_agent:
        frappe.throw(_("This chat is already assigned to {0}").format(contact.assigned_agent))
    
    contact.assigned_agent = agent
    contact.chat_status = "In Progress"
    contact.save(ignore_permissions=True)
    
    # Increment load
    queue = frappe.get_doc("WhatsApp Agent Queue", agent)
    queue.increment_load()
    
    return {"status": "success", "agent": agent}


@frappe.whitelist()
def release_chat(contact_name: str) -> dict:
    """API endpoint for agent to release a chat back to queue."""
    agent = frappe.session.user
    contact = frappe.get_doc("WhatsApp Contact", contact_name)
    
    if contact.assigned_agent != agent:
        frappe.throw(_("You are not assigned to this chat"))
    
    contact.assigned_agent = None
    contact.chat_status = "Open"
    contact.save(ignore_permissions=True)
    
    # Decrement load
    if frappe.db.exists("WhatsApp Agent Queue", agent):
        queue = frappe.get_doc("WhatsApp Agent Queue", agent)
        queue.decrement_load()
    
    return {"status": "success"}
