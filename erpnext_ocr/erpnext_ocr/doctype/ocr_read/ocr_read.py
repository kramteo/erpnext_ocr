# -*- coding: utf-8 -*-
# Copyright (c) 2018, John Vincent Fiel and contributors
# Copyright (c) 2020, Monogramm and Contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import io
import os
import re
import time


from spellchecker import SpellChecker

import frappe
from frappe.model.document import Document

from erpnext_ocr.erpnext_ocr.doctype.ocr_language.ocr_language import lang_available

from frappe.utils.csvutils import build_csv_response
from frappe.utils.response import build_response


def get_words_from_text(message):
    """
    This function return only list of words from text. Example: Cat in gloves,
    catches: no mice ->[cat, in, gloves, catches, no, mice]
    """
    message = re.sub(r'\W+', " ", message)
    word_list = list(filter(None, message.split()))
    return word_list


def get_spellchecked_text(message, language):
    """
    :param message: return text with correction:
    Example: Cet in glaves cetches no mice -> Cat in gloves catches no mice
    """
    lang = frappe.get_doc("OCR Language", language).lang
    spell_checker = SpellChecker(lang)
    only_words = get_words_from_text(message)
    misspelled = spell_checker.unknown(only_words)
    # print(only_words)
    # print(misspelled)
    for word in misspelled:
        corrected_word = spell_checker.correction(word)
        # print(word, corrected_word)
        if corrected_word:
            message = message.replace(word, corrected_word)
    return message


class OCRRead(Document):
    def __init__(self, *args, **kwargs):
        self.read_result = None
        self.read_time = None
        self.csv_data = None
        super(OCRRead, self).__init__(*args, **kwargs)

    @frappe.whitelist()
    def read_image(self):
        # text = read_ocr(self)
        # print(text)
        # return text
        read_ocr(self)
        return 

    def read_image_bg(self, is_async=True, now=False):
        return frappe.enqueue("erpnext_ocr.erpnext_ocr.doctype.ocr_read.ocr_read.read_ocr",
                              queue="long", timeout=1500, is_async=is_async,
                              now=now, **{'obj': self})


    @frappe.whitelist()
    def get_columns(self):
        text = self.read_result
        lines = re.split('\n', text)
        line1 = lines[0]
        items = get_elements(line1)
        if not items or len(items)<2:
            frappe.msgprint(frappe._("The read result appears to be empty. Please make sure that the headers are properly separated by spaces."),
                            raise_exception=True)
        
        return items

    @frappe.whitelist()
    def get_rows(self):
        obj = self.ocr_columns
        cols = []
        for i in obj:
            cols.append(i.column_name)
        text = self.read_result
        lines = re.split('\n', text)
        html, csv_data = extract_rows(lines, cols)   

        return html, csv_data     
        

def extract_rows(lines, cols):
    rows = []
    line1 = lines.pop(0)
    col_len = len(cols)
    count = 1
    for i in lines:
        j = get_elements(i)
        if not j:
            break
        if len(j) != col_len:
            frappe.msgprint(frappe._("Data row " + str(count) + " does not contain the required number of items. Have " + str(len(j)) + ", need" + str(col_len) + ". Please rectify"),
                            raise_exception=True)
        count+=1
        rows.append(j)
    
    html = derive_html(cols, rows)
    csv_data = derive_csv(cols, rows)
    print(html, csv_data)
    return html, csv_data


def derive_csv(cols, rows):
    csv_data = ""
    for i in cols:
        csv_data += i + ", "
    
    csv_data = csv_data[0: len(csv_data)-2] + "\n"
    
    for i in rows:
        for j in i:
            csv_data += j + ", "
        csv_data = csv_data[0: len(csv_data)-2] + "\n"
    
    csv_data = csv_data[0: len(csv_data)-2]

    return csv_data


def derive_html(cols, rows):
    html = '<!DOCTYPE html> <table style="width: 100%; border: 1.0px solid black;"> '

    # Set Headers
    html += "<thead> "
    html += "<tr> "
    for i in cols:
        html += '<th style="border: 1.0px solid black;">' + i + '</th> '
    html += "</tr> "
    html += "</thead> "

    # Set Content
    for i in rows:
        html += "<tr> \n"
        for j in i:
            html += '<td style="border: 1.0px solid black;">' + j + '</td> '
        html += "</tr> "

    html += "</table> </html>"

    return html


def get_elements(text):
    items = []
    item = ""
    i=0
    while i<len(text):
        if not item and text[i] != " ":
            if text[i] == "\'" or text[i] == '\"':
                quotechar = text[i]
                found=0
                for j in range(i + 1, len(text)):
                    if text[j] == quotechar:
                        item = text[i+1: j]
                        i=j+1
                        items.append(item)
                        item = ""
                        found=1
                        break
                if not found:
                    frappe.msgprint(frappe._("There is a problem with quotes in the text. Please check and rectify."),
                            raise_exception=True)
            else:
                item = text[i]
        elif item and text[i] != " ":
            item += text[i]
        elif item and text[i] == " ":
            items.append(item)
            item = ""
        i+=1
        if i == len(text) and item:
            items.append(item)
            item = ""

    for i in items:
        if re.search(',', i):
            frappe.msgprint(frappe._("Items cannot contain commas. Please remove them."),
                            raise_exception=True)

    return items




@frappe.whitelist()
def read_ocr(obj):
    """Call Tesseract OCR to extract the text from a OCR Read object."""

    if obj is None:
        frappe.msgprint(frappe._("OCR read requires OCR Read doctype."),
                        raise_exception=True)

    start_time = time.time()
    text = read_document(
        obj.file_to_read, obj.language or 'eng', obj.spell_checker)
    delta_time = time.time() - start_time

    obj.read_time = str(delta_time)
    obj.read_result = text
    obj.save()

    # The following is to test .csv file saving
    # text = 'a, b, c, d' + '\n' + '1, 2, 3, 4' + '\n' + '5, 6, 7, 8'
    # return text
    return



@frappe.whitelist()
def read_document(path, lang='eng', spellcheck=False, event="ocr_progress_bar"):
    """Call Tesseract OCR to extract the text from a document."""
    from PIL import Image
    import requests
    import tesserocr

    if path is None:
        return None

    if not lang_available(lang):
        frappe.msgprint(frappe._
                        ("The selected language is not available. Please contact your administrator."),
                        raise_exception=True)

    frappe.publish_realtime(event, {"progress": "0"}, user=frappe.session.user)

    if path.startswith('/assets/'):
        # from public folder
        fullpath = os.path.abspath(path)
    elif path.startswith('/files/'):
        # public file
        fullpath = frappe.get_site_path() + '/public' + path
    elif path.startswith('/private/files/'):
        # private file
        fullpath = frappe.get_site_path() + path
    elif path.startswith('/'):
        # local file (mostly for tests)
        fullpath = os.path.abspath(path)
    else:
        # external link
        fullpath = requests.get(path, stream=True).raw

    ocr = frappe.get_doc("OCR Settings")

    text = ""
    # print(path, lang)
    # with tesserocr.PyTessBaseAPI(lang=lang, path='/home/mt/frappe-bench/sites/accounting.nprimeintl.com/public/files/') as api:
    with tesserocr.PyTessBaseAPI(lang=lang, path='/usr/share/tesseract-ocr/4.00/tessdata/') as api:

        if path.endswith('.pdf'):
            from wand.image import Image as wi

            # https://stackoverflow.com/questions/43072050/pyocr-with-tesseract-runs-out-of-memory
            with wi(filename=fullpath, resolution=ocr.pdf_resolution) as pdf:
                pdf_image = pdf.convert('png')
                i = 0
                size = len(pdf_image.sequence) * 3

                for img in pdf_image.sequence:
                    with wi(image=img) as img_page:
                        image_blob = img_page.make_blob('png')
                        frappe.publish_realtime(
                            event, {"progress": [i, size]}, user=frappe.session.user)
                        i += 1

                        recognized_text = " "

                        image = Image.open(io.BytesIO(image_blob))
                        api.SetImage(image)
                        frappe.publish_realtime(
                            event, {"progress": [i, size]}, user=frappe.session.user)
                        i += 1

                        recognized_text = api.GetUTF8Text()
                        text = text + recognized_text
                        frappe.publish_realtime(
                            event, {"progress": [i, size]}, user=frappe.session.user)
                        i += 1

        else:
            image = Image.open(fullpath)
            api.SetImage(image)
            frappe.publish_realtime(
                event, {"progress": [33, 100]}, user=frappe.session.user)

            text = api.GetUTF8Text()
            frappe.publish_realtime(
                event, {"progress": [66, 100]}, user=frappe.session.user)

    if spellcheck:
        text = get_spellchecked_text(text, lang)
    
    # print('Start response')
    # build_csv_response([['a','b','c'],[1,2,3],[4,5,6]], 't')
    # # frappe.response.display_content_as = "attachment"
    # # build_response(response_type="download")
    # # frappe.response['message'] = b
    # print('End response')

    frappe.publish_realtime(
        event, {"progress": [100, 100]}, user=frappe.session.user)

    # print(text)
    return text


def download(name):
    file = frappe.get_doc("File", name)
    frappe.response.filename = file.file_name
    frappe.response.filecontent = file.get_content()
    frappe.response.type = "download"
    frappe.response.display_content_as = "attachment"