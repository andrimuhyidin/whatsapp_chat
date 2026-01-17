// Copyright (c) 2024, shridhar patil and contributors
// For license information, please see license.txt

frappe.ui.form.on("WhatsApp Contact", {
	refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__("Open Chat"), () => {
                // Open Chat interface
                // We can try to open the global chat or a specific dialog
                // Since ChatSpace is not globally exposed easily, let's try to trigger the global chat open
                
                // Option A: Trigger global chat to open this room
                // Accessing the global instance if available
                // Usually stored in frappe.chat_app or similar if standard pattern, but here it is new frappe.Chat()
                
                // Alternative: Render a dialog using the same logic as ChatSpace
                // But we need to load dependencies.
                
                // Simplest fallback: If the global widget exists, try to show it.
                // But specifically for this contact.
                
                // Let's rely on the routing or a direct dialog if we can find the component.
                // Given the complexity of isolating ChatSpace without imports, 
                // let's try to redirect to the Desk Page if it existed, but it doesn't.
                
                // Let's implement a clean dialog loader by dynamically importing the component if possible
                // or just standard Frappe routing if we had a page.
                
                // Since we don't have a page, let's forcefully show the global chat widget and try to switch room.
                // This assumes the global widget is present (Task bar).
                
                if ($('.chat-app').length > 0) {
                     $('.chat-navbar-icon').click();
                     // TODO: Switch to specific room logic which might need more internal access
                     frappe.msgprint("Please select the contact in the chat list.");
                } else {
                    frappe.msgprint("Chat Widget not loaded. Please check integration settings.");
                }
            });
        }
	},
});
