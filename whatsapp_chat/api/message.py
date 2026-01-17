import frappe
import mimetypes



@frappe.whitelist()
def get_all(room: str, user_no: str):
    """Get all the messages of a particular room

    Args:
        room (str): Room's name.

    """
    # Refactored to QueryBuilder
    wm = frappe.qb.DocType("WhatsApp Message")
    
    sender_user_no = (
        frappe.qb.terms.Case()
        .when(wm.to != "", wm.to)
        .else_("Administrator")
    ).as_("sender_user_no")

    content_type_coalesced = frappe.qb.functions.Coalesce(wm.content_type, "text")
    
    content = (
        frappe.qb.terms.Case()
        .when(content_type_coalesced == "text", frappe.qb.functions.Coalesce(wm.message, ""))
        .else_(frappe.qb.functions.Coalesce(wm.attach, wm.message, ""))
    ).as_("content")

    caption = (
        frappe.qb.terms.Case()
        .when(content_type_coalesced != "text", wm.message)
        .else_(None)
    ).as_("caption")

    content_type = content_type_coalesced.as_("content_type")

    return (
        frappe.qb.from_(wm)
        .select(wm.creation, sender_user_no, content, caption, content_type)
        .where(
            (wm.to == user_no) | (wm["from"] == user_no)
        )
        .where(frappe.qb.functions.Coalesce(wm.message_type, "") != "Template")
        .orderby(wm.creation, order=frappe.query_builder.Order.asc)
    ).run(as_dict=True)


@frappe.whitelist()
def mark_as_read(room):
    """Mark messages as read in local DB and optionally send read receipts to WhatsApp."""
    try:
        # Update local contact status
        frappe.db.set_value("WhatsApp Contact", room, "is_read", 1, update_modified=False)
        frappe.db.commit()

        # Send read receipts to WhatsApp if enabled
        send_whatsapp_read_receipts(room)
    except Exception:
        pass  # Ignore concurrent update errors
    return "ok"


def send_whatsapp_read_receipts(room):
    """Send read receipts to WhatsApp for unread incoming messages."""
    try:
        # Get the contact's mobile number
        contact = frappe.get_doc("WhatsApp Contact", room)
        if not contact.mobile_no:
            return

        # Find unread incoming messages for this contact
        unread_messages = frappe.get_all(
            "WhatsApp Message",
            filters={
                "from": contact.mobile_no,
                "type": "Incoming",
                "status": ["not in", ["marked as read"]]
            },
            fields=["name", "whatsapp_account"],
            order_by="creation desc",
            limit=10
        )

        if not unread_messages:
            return

        # Check if auto read receipt is enabled for the account
        for msg in unread_messages:
            if not msg.whatsapp_account:
                continue

            allow_auto_read = frappe.db.get_value(
                "WhatsApp Account",
                msg.whatsapp_account,
                "allow_auto_read_receipt"
            )

            if allow_auto_read:
                try:
                    msg_doc = frappe.get_doc("WhatsApp Message", msg.name)
                    msg_doc.send_read_receipt()
                except Exception as e:
                    frappe.log_error(f"Failed to send read receipt for {msg.name}: {str(e)}", "WhatsApp Chat Read Receipt")
    except Exception as e:
        frappe.log_error(f"send_whatsapp_read_receipts error: {str(e)}", "WhatsApp Chat Read Receipt")



@frappe.whitelist()
def send(content, user, room, user_no, attachment=None):
    content_type = "text"
    if attachment:
        file_type = mimetypes.guess_type(content)[0]
        if file_type in ["image/apng","image/avif","image/gif","image/jpeg","image/png","image/svg","image/webp"]:
            content_type = 'image'
        elif file_type in ["application/pdf", "application/vnd.ms-powerpoint", "application/msword", "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
            content_type = "document"
        elif file_type in ["audio/aac", "audio/mp4", "audio/mpeg", "audio/amr", "audio/ogg"]:
            content_type = 'audio'
        elif file_type in ["video/mp4", "video/3gp"]:
            content_type = "video"

        frappe.get_doc({
            "doctype": "WhatsApp Message",
            "to": user_no,
            "type": "Outgoing",
            "attach": content,
            "content_type": content_type
        }).save()
    else:
        frappe.get_doc({
            "doctype": "WhatsApp Message",
            "to": user_no,
            "type": "Outgoing",
            "message": content,
            "content_type": content_type
        }).save()

    return "ok"


def last_message(doc, method):
    if doc.type == 'Outgoing':
        mobile_no = doc.to
    else:
        mobile_no = doc.get("from")


    contact_name = frappe.db.get_value("WhatsApp Contact", filters={"mobile_no": mobile_no})
    if contact_name:
        chat_doc = frappe.get_doc("WhatsApp Contact", contact_name)
        chat_doc.last_message = doc.message
        chat_doc.is_read = 0
        chat_doc.save(ignore_permissions=True)
    else:
        chat_doc = frappe.get_doc({
            "doctype": "WhatsApp Contact",
            "mobile_no": mobile_no,
            "last_message": doc.message,
            "contact_name": mobile_no,
            "is_read": 0
        })
        chat_doc.save(ignore_permissions=True)

    if chat_doc.email and doc.type != 'Outgoing':
        message_data = {
            "content": doc.message or doc.attach or '',
            "creation": frappe.utils.now(),
            "room": chat_doc.name,
            "contact_name": chat_doc.contact_name,
            "sender_user_no": mobile_no,
            "user": "Guest"
        }
        # Notify chat list
        frappe.publish_realtime(
            "latest_chat_updates",
            message_data,
            user=chat_doc.email
        )
        # Notify open chat room
        frappe.publish_realtime(
            chat_doc.name,
            message_data,
            user=chat_doc.email
        )

    return "ok"
