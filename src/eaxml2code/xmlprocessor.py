#
# eaxml2code
#
# Copyright 2023 Artur Wisz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from xml.sax.handler import ContentHandler
import json

'''
The class converts the visited XML elements into a dictionary tree.
'''
class XmlProcessor(ContentHandler):

    def __init__(self) -> None:
        super().__init__()
        self._element_stack = []

    @property
    def current_element(self):
        return self._element_stack[-1]

    def endDocument(self):
        print("end of document")

    def startElement(self, name, attrs):
        #print(f"BEGIN: <{name}>, {attrs.keys()}")
        self._element_stack.append({
            "name": name,
            "attributes": dict(attrs),
            "children": [],
            "value": ""
        })

    def endElement(self, name):
        #print(f"END: </{name}>")
        self._clear_element(self.current_element)
        if len(self._element_stack) > 1:
            child = self._element_stack.pop()
            self.current_element["children"].append(child)

    def characters(self, content):
        if content.strip() != "":
            self.current_element["value"] += content

    def _clear_element(self, element):
        element["value"] = element["value"].strip()
        for key in ("attributes", "children", "value"):
            if not element[key]:
                del element[key]