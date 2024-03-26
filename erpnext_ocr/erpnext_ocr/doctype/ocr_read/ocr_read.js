frappe.ui.form.on('OCR Read', {
    setup: function (frm) {
        frappe.call({
            method: "erpnext_ocr.erpnext_ocr.doctype.ocr_language.ocr_language.get_current_language",
            args: {
                'user': frappe.user['name']
            },
            callback: function (r) {
                cur_frm.set_value("language", r.message);
            }
        })
    },
    read_image: function (frm) {
        frappe.hide_msgprint(true);
        frappe.realtime.on("ocr_progress_bar", function (data) {
            frappe.hide_msgprint(true);
            frappe.show_progress(__("Reading the file"), data.progress[0], data.progress[1]);
        });
        frappe.call({
            method: "read_image",
            doc: cur_frm.doc,
            // args: {
            //     "spell_checker": frm.doc.spell_checker
            // },
            callback: function(r) {
                // cur_dialog.hide();
                // // console.log("Message: ", r);
                // // download("test.csv", r.message);
                cur_frm.refresh();
            }
        });
    },
    generate_columns: function (frm) {
        frm.set_value('ocr_columns', []);
        frappe.call({
            method: "get_columns",
            doc: cur_frm.doc,
            // args: {
            //     doc: frm.doc.read_result
            // },
        callback: function(r) {
                console.log(r.message[0])
                for (let i = 0; i < r.message.length; i++) {
                    let row = frm.add_child('ocr_columns', {
                        column_name: r.message[i]
                    });
                }
                cur_frm.refresh();
            }
        });
    },
    generate_rows: function (frm) {
        frm.set_value('generated_table', '');
        frappe.call({
            method: "get_rows",
            doc: cur_frm.doc,
            // args: {
            //     doc: frm.doc.read_result
            // },
        callback: function(r) {
                console.log(r.message)
                cur_frm.refresh();
            }
        });
    },
    import: function (frm) {
        if (typeof frm.doc.ocr_import != "undefined" && frm.doc.ocr_import !== '') {
            frappe.call({
                method: "erpnext_ocr.erpnext_ocr.doctype.ocr_import.ocr_import.generate_doctype",
                args: {
                    "doctype_import_link": frm.doc.ocr_import,
                    "read_result": frm.doc.read_result
                },
                callback: function (r) {
                    console.log(r.message);
                    frappe.show_alert({
                        message: __('Doctype {0} generated',
                            ['<a href="#Form/' + r.message.doctype + '/' + r.message.name + '">' + r.message.name + '</a>']),
                        indicator: 'green'
                    });
                }
            })
        }
        else {
            frappe.throw("Field Template is None");
        }
    }
});


function download(filename, content) {
    var element = document.createElement('a');
    element.setAttribute('href', 'data:application/octet-stream;charset=utf-8,' + encodeURIComponent(content));
    element.setAttribute('download', filename);
  
    element.style.display = 'none';
    document.body.appendChild(element);
  
    element.click();
  
    document.body.removeChild(element);
  }
  