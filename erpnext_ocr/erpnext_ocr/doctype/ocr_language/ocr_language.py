# -*- coding: utf-8 -*-
# Copyright (c) 2020, Monogramm and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import os
import requests

import frappe
from frappe import _
from frappe.model.document import Document

import tesserocr


@frappe.whitelist()
def check_language(lang):
    """Check a language availability. Returns a user friendly text."""
    return _("Yes") if lang_available(lang) else _("No")


@frappe.whitelist()
def lang_available(lang):
    """Call Tesseract OCR to verify language is available."""
    # print(tesserocr.get_languages(), len(tesserocr.get_languages()))
    # l = len(tesserocr.get_languages()[1][0])
    # print(tesserocr.get_languages()[1][0][l-3:l])
    list_of_languages = tesserocr.get_languages(path='/usr/share/tesseract-ocr/4.00/tessdata/')[1]
    # list_of_languages=[]
    # for i in list_of_languages2:
    #     l2 = len(i)
    #     list_of_languages.append(i[l2-3:l2])
    if len(lang) == 2:
        return frappe.get_doc("OCR Language", {"lang": lang}).code in list_of_languages

    return lang in list_of_languages


@frappe.whitelist()
def get_current_language(user):
    """Get Tesseract language matching current user or system settings."""
    user = frappe.get_doc("User", user)
    language = user.language
    if not language:
        settings = frappe.get_doc("System Settings")
        language = settings.language
    #print(language)
    lang_code = frappe.get_doc("OCR Language", {"lang": language}).name
    return lang_code if lang_code is not None else "eng"


class OCRLanguage(Document):
    def __init__(self, *args, **kwargs):
        super(OCRLanguage, self).__init__(*args, **kwargs)
        # self.TESSDATA_LINK = "https://github.com/tesseract-ocr/tessdata{}/blob/master/{}.traineddata?raw=true"
        self.TESSDATA_LINK = "https://github.com/tesseract-ocr/tessdata/blob/master/eng.traineddata?raw=true"
        print(self, self.code, self.TESSDATA_LINK)
        if self.code:
            self.is_supported = check_language(self.code)

    @frappe.whitelist()
    def download_tesseract(self):
        print(self.type_of_ocr)
        if self.type_of_ocr == 'Default' or not self.type_of_ocr:
            path = self.TESSDATA_LINK.format("", self.name)
        else:
            path = self.TESSDATA_LINK.format(
                "_" + self.type_of_ocr.lower(), self.name)
        print('Path: ' + path)

        res = requests.get(path)
        #print(res.content)
        dest = os.getenv("TESSDATA_PREFIX", "/usr/share/tesseract-ocr/tessdata") + \
            "/" + self.name + ".traineddata"

        if self.type_of_ocr == 'Custom':
            frappe.throw(
                _("Download is not available for custom OCR data."))
        with open(dest, "wb") as file:
            file.write(res.content)

        if os.path.exists(dest):
            self.is_supported = check_language(self.code)
            self.save()
        else:
            frappe.throw(_("File could not be downloaded."))
