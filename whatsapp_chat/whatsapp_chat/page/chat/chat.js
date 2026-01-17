frappe.pages['chat'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'WhatsApp Chat',
		single_column: true
	});

	frappe.require('whatsapp_chat.bundle.js', function() {
		// Initialize chat in the page
		const $container = $(page.body).addClass('chat-page-container');
		$container.css({
            'height': 'calc(100vh - 150px)',
            'display': 'flex',
            'flex-direction': 'column',
            'background': 'var(--card-bg)',
            'border-radius': 'var(--border-radius)',
            'box-shadow': 'var(--card-shadow)',
            'margin': 'var(--margin-sm)'
        });

        // Add some custom styles for the page view
        frappe.dom.set_style(`
            .chat-page-container .chat-list {
                height: 100%;
                border-right: 1px solid var(--border-color);
            }
            .chat-page-container .chat-list-item {
                border-bottom: 1px solid var(--border-color);
            }
        `);

		// We need to fetch settings first similar to how the widget does
        // But since the widget might already be initialized, we can check that
        
        const init_page_chat = async () => {
            try {
                // Determine user details similar to widget
                const token = localStorage.getItem('guest_token') || '';
                // We reuse the verify token logic or just assume logged in user since this is a Desk page
                
                // Call the settings API
                const res = await frappe.call({
                    method: 'whatsapp_chat.api.config.settings',
                    args: { token: token }
                });
                
                const settings = res.message;
                
                if (!settings.is_admin) {
                     page.set_title_sub('You do not have permission to access this page.');
                     return;
                }

                if (frappe.Chat && frappe.Chat.ChatList) {
                    // Initialize ChatList in our container
                    const chat_list = new frappe.Chat.ChatList({
                        $wrapper: $container,
                        user: settings.user,
                        user_email: settings.user_email,
                        is_admin: settings.is_admin,
                        on_load: (list_instance) => {
                             // Check for contact param
                             const params = frappe.utils.get_query_params();
                             if (params.contact) {
                                 // Try to open chat
                                 const found = list_instance.open_chat(params.contact);
                                 if (!found) {
                                     frappe.msgprint(`Contact ${params.contact} not found or no active chat.`);
                                 }
                             }
                        }
                    });
                    chat_list.render();
                    
                } else {
                    frappe.msgprint("Chat components not loaded properly.");
                }

            } catch (err) {
                 console.error("Failed to load chat page", err);
                 frappe.msgprint("Error loading chat.");
            }
        };

        // Initialize socket if not already
        if (!frappe.socketio) {
             frappe.socketio.init(frappe.boot.socketio_port);
        }
        
        init_page_chat();
	});
}
