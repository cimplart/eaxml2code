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

from copy import deepcopy

class ModelBuilder:

    def __init__(self, verbose=False):
        self._model = {}    #intermediate model
        self._id_map = {}
        self._model['elements'] = []
        self._model['dependencies'] = []
        self._model['attributes'] = []
        self._model['operations'] = []
        self._model['literals'] = []
        self._model['component'] = ''
        self._cur_element_id = None

        self._headers = {}  #main entry point to final model

    @property
    def current_element(self):
        if self._model['elements']:
            if self._cur_element_id is not None:
                return self._id_map[self._cur_element_id]
            else:
                return self._model['elements'][-1]
        else:
            return None

    def walk_raw_model_subtree(self, node: dict):
        '''
        node is from a raw model converted from xml.
        '''
        method_map = {
            'packagedElement': self.visit_packaged_element,
            'ownedAttribute': self.visit_owned_attribute,
            'ownedOperation': self.visit_owned_operation,
            'ownedLiteral': self.visit_owned_literal,
            'element': self.visit_ea_element,
            'attribute': self.visit_ea_attribute,
            'operation': self.visit_ea_operation
        }

        skip_nodes = [ 'diagrams' ]

        if node['name'] in method_map.keys():
            if "attributes" in node:
                attr = node["attributes"]
                if "xmi:type" in attr:
                    method_map[node['name']](node, attr['xmi:type'])
                else:
                    method_map[node['name']](node)
            else:
                print(f"WARNING: {node['name']} without attributes, ignored")
                return

        if node['name'] in skip_nodes:
            return

        if "children" in node:
            for ch in node["children"]:
                self.walk_raw_model_subtree(ch)


    def visit_packaged_element(self, node: dict, xmi_type: str):
        if xmi_type == 'uml:Package' and node['attributes']['xmi:id'].startswith('EAPK_'):
            self._model['component'] = node['attributes']['name']
        elif xmi_type in [ 'uml:Class', 'uml:Interface', 'uml:Artifact', 'uml:Enumeration' ]:
            model_el = {
                'name': node['attributes']['name'],
                'xmi:type': xmi_type,
                'xmi:id': node['attributes']['xmi:id']
            }
            self._model['elements'] += [ model_el ]
            self._id_map[model_el['xmi:id']] = self._model['elements'][-1]
        elif xmi_type in [ 'uml:Dependency' ]:
            model_el = {
                'xmi:type': xmi_type,
                'xmi:id': node['attributes']['xmi:id'],
                'supplier': node['attributes']['supplier'],
                'client': node['attributes']['client']
            }
            self._model['dependencies'] += [ model_el ]
            self._id_map[model_el['xmi:id']] = self._model['dependencies'][-1]

    def visit_owned_attribute(self, node: dict, xmi_type: str):
        model_el = {
            'name': node['attributes']['name'],
            'xmi:id': node['attributes']['xmi:id'],
            'owner': self.current_element['xmi:id']
        }
        self._model['attributes'] += [ model_el ]
        self._id_map[model_el['xmi:id']] = self._model['attributes'][-1]

    def visit_owned_operation(self, node: dict):
        model_el = {
            'name': node['attributes']['name'],
            'xmi:id': node['attributes']['xmi:id'],
            'owner': self.current_element['xmi:id'],
            'parameters': []
        }

        for c in node['children']:
            assert c['name'] == 'ownedParameter'
            param_el = {
                'name': c['attributes']['name'],
                'xmi:id': c['attributes']['xmi:id'],
                'direction': c['attributes']['direction']
            }
            model_el['parameters'] += [ param_el ]
            self._id_map[param_el['xmi:id']] = model_el['parameters'][-1]

        self._model['operations'] += [ model_el ]
        self._id_map[model_el['xmi:id']] = self._model['operations'][-1]

    def visit_owned_literal(self, node: dict, xmi_type: str):
        model_el = {
            'name': node['attributes']['name'],
            'xmi:id': node['attributes']['xmi:id'],
            'owner': self.current_element['xmi:id']
        }
        self._model['literals'] += [ model_el ]
        self._id_map[model_el['xmi:id']] = self._model['literals'][-1]

    def visit_ea_element(self, node: dict, xmi_type: str):
        if xmi_type not in [ 'uml:Class', 'uml:Interface', 'uml:Artifact', 'uml:Enumeration' ]:
            print('Ignore node ' + xmi_type)
            return

        self._cur_element_id = node['attributes']['xmi:idref']
        try:
            found = self._id_map[node['attributes']['xmi:idref']]
        except KeyError as e:
            return
        for c in node['children']:
            if c['name'] == 'properties' and "attributes" in c:
                if 'documentation' in c['attributes']:
                    found['description'] = c['attributes']['documentation']
                    if xmi_type != 'uml:Artifact':
                        found['header'] = self._extract_header(found['name'], found['description'])
                    else:
                        found['generated'] = self._extract_generated(found['name'], found['description'])
                if 'stereotype' in c['attributes']:
                    found['stereotype'] = c['attributes']['stereotype']

    def _extract_header(self, el_name, notes):
        for line in notes.split('\n'):
            if 'Declared in:' in line:
                return line.replace('Declared in:', '').strip()
        else:
            raise Exception(f"Missing 'Declared in:' in notes of {el_name}")

    def _extract_generated(self, el_name, notes):
        for line in notes.split('\n'):
            if 'Generated:' in line:
                return 'Yes' in line or 'YES' in line or 'yes' in line
        else:
            raise Exception(f"Missing 'Generated:' in notes of {el_name}")

    def visit_ea_attribute(self, node:dict):
        found = self._id_map[node['attributes']['xmi:idref']]
        assert found['name'] == node['attributes']['name']

        for c in node['children']:
            if c['name'] == 'initial' and "attributes" in c:
                found['initial'] = c["attributes"]['body']
            elif c['name'] == 'documentation' and "attributes" in c:
                found['description'] = c['attributes']['value']
            elif c['name'] == 'properties' and 'attributes' in c:
                if 'type' in c['attributes']:
                    found['type'] = c['attributes']['type']

    def visit_ea_operation(self, node:dict):
        found = self._id_map[node['attributes']['xmi:idref']]
        assert found['name'] == node['attributes']['name']

        for c in node['children']:
            if c['name'] == 'stereotype' and 'attributes' in c:
                found['stereotype'] = c['attributes']['stereotype']
            elif c['name'] == 'type':
                found['static'] = c['attributes']["static"]
                found.setdefault('return-value', {})
                if "type" in c['attributes']:
                    found['return-value']['type'] = c['attributes']['type']
                else:
                    found['return-value']['type'] = 'void'
            elif c['name'] == 'documentation':
                found['description'] = c['attributes']['value']
                if found['return-value']['type'] != 'void':
                    found['return-value']['description'] = self._extract_return_value_description(found['description'])
            elif c['name'] == 'parameters':
                self._collect_parameters(c, found['parameters'])

    def _extract_return_value_description(self, description):
        for line in description.split('\n'):
            if 'Return value:' in line:
                return line.replace('Return value:', '').strip()
        return ''

    def _collect_parameters(self, node:dict, params: list):
        for c in node['children']:
            assert c['name'] == 'parameter'
            assert "attributes" in c
            if c['attributes']['xmi:idref'].startswith('EAID_RETURNID_'):
                #Skip return parameters
                continue
            for p in params:
                if p['xmi:id'] == c['attributes']['xmi:idref']:
                    found_param = p
                    break
            else:
                print(f"WARNING: parameter {c['attributes']['xmi:idref']} was not found")
                found_param = None
                continue
            for cc in c['children']:
                if cc['name'] == 'properties':
                    found_param['type'] = cc['attributes']['type']
                    found_param['position'] = cc['attributes']['pos']
                    found_param['const'] = cc['attributes']['const']
                elif cc['name'] == 'documentation' and 'attributes' in cc:
                    found_param['description'] = cc['attributes']['value']

    _default_header_content = {
        'functions': list(),
        'types': list(),
        'variables': list(),
        'macro-constants': list(),
        'includes': list(),
        'file-name': '',
        'description': '',
        'generated': False
    }

    #Create the final model for use in the code template.
    def post_process(self):
        self._create_headers()
        self._arrange_function_groups()

    def _create_headers(self):
        for el in self._model['elements']:
            if el['xmi:type'] == 'uml:Artifact':
                if el['stereotype'] == 'header':
                    self._headers.setdefault(el['name'], deepcopy(self._default_header_content))
                    header_ref = self._headers[el['name']]
                    header_ref['file-name'] = el['name']
                    header_ref['description'] = el['description']
                    header_ref['generated'] = el['generated']
                    header_ref['component'] = self._model['component']

    def _arrange_function_groups(self):
        for el in self._model['elements']:
            if el['xmi:type'] == 'uml:Interface':
                functions_group = {
                    'functions-group': el['name'],
                    'functions': [ ]
                }
                #add functions for this owner
                for f in self._model['operations']:
                    if f['owner'] == el['xmi:id']:
                        functions_group['functions'] += [ f ]
                    #supplement missing keys
                    f.setdefault('in-params', [])
                    f.setdefault('out-params', [])
                    f.setdefault('inout-params', [])
                    f.setdefault('return-value', { 'type': 'void', 'description': '' })
                    self._set_func_syntax(f)

                self._headers[el['header']]['functions'] += [ functions_group ]

    def _set_func_syntax(self, func):
        syntax = func['return-value']['type'] + ' ' + func['name'] + '('
        for p in func['parameters']:
            if p['name'] != 'return':
                syntax += p['type'] + ' ' + p['name'] + ', '
        syntax = syntax[:-2] + ')'
        func['syntax'] = syntax
