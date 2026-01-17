"""Chat history timeline component for WhatsApp Contact form."""
frappe.provide("whatsapp_chat.components");

whatsapp_chat.components.ChatHistory = class ChatHistory {
    constructor(parent, contact_name) {
        this.parent = parent;
        this.contact_name = contact_name;
        this.messages = [];
        this.page_length = 20;
        this.render();
    }

    render() {
        this.wrapper = $(`
            <div class="chat-history-wrapper">
                <div class="chat-history-toolbar" style="padding: 10px; border-bottom: 1px solid var(--border-color);">
                    <button class="btn btn-xs btn-default refresh-btn">
                        <i class="fa fa-refresh"></i> Refresh
                    </button>
                    <span class="text-muted float-right message-count"></span>
                </div>
                <div class="chat-history-container" style="max-height: 400px; overflow-y: auto; padding: 10px;">
                    <div class="messages-list"></div>
                    <div class="loading-indicator text-center text-muted" style="display: none;">
                        <i class="fa fa-spinner fa-spin"></i> Loading...
                    </div>
                </div>
            </div>
        `).appendTo(this.parent);

        this.setup_events();
        this.load_messages();
    }

    setup_events() {
        this.wrapper.find('.refresh-btn').on('click', () => {
            this.load_messages();
        });
    }

    async load_messages() {
        this.wrapper.find('.loading-indicator').show();
        this.wrapper.find('.messages-list').empty();

        try {
            const result = await frappe.call({
                method: 'whatsapp_chat.api.message.get_all',
                args: {
                    room: this.contact_name,
                    limit: this.page_length
                }
            });

            this.messages = result.message || [];
            this.render_messages();
            this.wrapper.find('.message-count').text(`${this.messages.length} messages`);
        } catch (error) {
            frappe.msgprint(__('Failed to load chat history'));
            console.error(error);
        } finally {
            this.wrapper.find('.loading-indicator').hide();
        }
    }

    render_messages() {
        const container = this.wrapper.find('.messages-list');
        
        if (this.messages.length === 0) {
            container.html(`
                <div class="text-center text-muted" style="padding: 40px;">
                    <i class="fa fa-comments-o fa-3x"></i>
                    <p style="margin-top: 10px;">No messages yet</p>
                </div>
            `);
            return;
        }

        this.messages.forEach(msg => {
            const is_outgoing = msg.type === 'Outgoing';
            const time = frappe.datetime.prettyDate(msg.creation);
            const status_icon = this.get_status_icon(msg.status);
            
            const message_html = `
                <div class="message-item ${is_outgoing ? 'outgoing' : 'incoming'}" 
                     style="display: flex; flex-direction: column; margin-bottom: 10px; 
                            align-items: ${is_outgoing ? 'flex-end' : 'flex-start'};">
                    <div class="message-bubble" 
                         style="max-width: 80%; padding: 8px 12px; border-radius: 12px;
                                background: ${is_outgoing ? 'var(--primary)' : 'var(--bg-light-gray)'};
                                color: ${is_outgoing ? 'white' : 'inherit'};">
                        ${frappe.utils.escape_html(msg.message || '[Media]')}
                    </div>
                    <div class="message-meta text-muted" style="font-size: 11px; margin-top: 2px;">
                        ${time} ${is_outgoing ? status_icon : ''}
                    </div>
                </div>
            `;
            container.append(message_html);
        });

        // Scroll to bottom
        const scrollContainer = this.wrapper.find('.chat-history-container');
        scrollContainer.scrollTop(scrollContainer[0].scrollHeight);
    }

    get_status_icon(status) {
        const icons = {
            'sent': '<i class="fa fa-check text-muted"></i>',
            'delivered': '<i class="fa fa-check-double text-muted"></i>',
            'read': '<i class="fa fa-check-double text-primary"></i>',
            'failed': '<i class="fa fa-exclamation-triangle text-danger"></i>'
        };
        return icons[status] || '';
    }
};
