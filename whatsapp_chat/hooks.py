app_name = "whatsapp_chat"
app_title = "Whatsapp Chat"
app_publisher = "shridhar patil"
app_description = "Chat app for whatsapp"
app_email = "shridharpatil2792@gmail.com"
app_license = "unlicense"

add_to_apps_screen = [
    {
        "name": "whatsapp_chat",
        "title": "WhatsApp Chat",
        "icon": "/assets/whatsapp_chat/images/whatsapp-logo.png",
        "route": "/app/whatsapp-contact"
    }
]

from frappe import __version__ as frappe_version

is_frappe_above_v13 = int(frappe_version.split('.')[0]) > 13

app_include_css = ['whatsapp_chat.bundle.css'] if is_frappe_above_v13 else [
    '/assets/css/whatsapp_chat.css']

app_include_js = ['whatsapp_chat.bundle.js'] if is_frappe_above_v13 else [
    '/assets/js/whatsapp_chat.js']































doc_events = {
    "WhatsApp Message": {
        "after_insert": "whatsapp_chat.api.message.last_message"
    },
    "Customer": {
        "on_update": "whatsapp_chat.utils.sync_contacts.sync_entity_to_whatsapp_contact",
        "after_insert": "whatsapp_chat.utils.sync_contacts.sync_entity_to_whatsapp_contact"
    },
    "Supplier": {
        "on_update": "whatsapp_chat.utils.sync_contacts.sync_entity_to_whatsapp_contact",
        "after_insert": "whatsapp_chat.utils.sync_contacts.sync_entity_to_whatsapp_contact"
    },
    "User": {
        "on_update": "whatsapp_chat.utils.sync_contacts.sync_entity_to_whatsapp_contact",
        "after_insert": "whatsapp_chat.utils.sync_contacts.sync_entity_to_whatsapp_contact"
    }
}















sounds = [
    {'name': 'chat-notification', 'src': '/assets/frappe/sounds/email.mp3', 'volume': 0.2},
    {'name': 'chat-message-send', 'src': '/assets/frappe/sounds/submit.mp3', 'volume': 0.2},
    {'name': 'chat-message-receive', 'src': '/assets/frappe/sounds/alert.mp3', 'volume': 0.5}
]