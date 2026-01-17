class MessageBuilder {
    constructor(dialog_callback) {
        this.dialog_callback = dialog_callback;
    }

    show_builder_dialog(type = 'buttons') {
        const me = this;
        let fields = [];

        if (type === 'buttons') {
            fields = [
                {
                    label: 'Message Body',
                    fieldname: 'body',
                    fieldtype: 'Small Text',
                    reqd: 1
                },
                {
                    label: 'Buttons',
                    fieldname: 'buttons',
                    fieldtype: 'Table',
                    fields: [
                        { fieldname: 'id', fieldtype: 'Data', label: 'ID', reqd: 1, in_list_view: 1 },
                        { fieldname: 'title', fieldtype: 'Data', label: 'Title', reqd: 1, in_list_view: 1 }
                    ],
                    data: [],
                    get_data: () => { return [] }
                }
            ];
        } else if (type === 'list') {
            fields = [
                {
                    label: 'Message Body',
                    fieldname: 'body',
                    fieldtype: 'Small Text',
                    reqd: 1
                },
                {
                    label: 'Button Text',
                    fieldname: 'button_text',
                    fieldtype: 'Data',
                    default: 'Select Option',
                    reqd: 1
                },
                {
                    label: 'Section Title',
                    fieldname: 'section_title',
                    fieldtype: 'Data',
                    default: 'Options'
                },
                {
                    label: 'List Items',
                    fieldname: 'list_items',
                    fieldtype: 'Table',
                    fields: [
                        { fieldname: 'id', fieldtype: 'Data', label: 'ID', reqd: 1, in_list_view: 1 },
                        { fieldname: 'title', fieldtype: 'Data', label: 'Title', reqd: 1, in_list_view: 1 },
                        { fieldname: 'description', fieldtype: 'Data', label: 'Description' }
                    ]
                }
            ];
        }

        const d = new frappe.ui.Dialog({
            title: `Build ${type} Message`,
            fields: fields,
            primary_action_label: 'Use This Message',
            primary_action(values) {
                let message_payload = {};
                
                if (type === 'buttons') {
                    if (values.buttons.length > 3) {
                        frappe.msgprint('Button message allows max 3 buttons. Use List message instead.');
                        return;
                    }
                    message_payload = {
                        content_type: 'interactive',
                        message: values.body,
                        buttons: values.buttons
                    };
                } else if (type === 'list') {
                     if (values.list_items.length > 10) {
                        frappe.msgprint('List message allows max 10 items.');
                        return;
                    }
                    // Construct list structure for interactive_data
                    // For now, mapping to buttons field which backend handles intelligently
                    // or we pass explicit interactive_data if we updated backend
                    message_payload = {
                        content_type: 'interactive',
                        message: values.body,
                        buttons: values.list_items, // API treats >3 as list automatically
                        // Store full metadata if needed later
                    };
                }

                if (me.dialog_callback) {
                    me.dialog_callback(message_payload);
                }
                d.hide();
            }
        });

        d.show();
    }
}

// Export for usage
window.MessageBuilder = MessageBuilder;
