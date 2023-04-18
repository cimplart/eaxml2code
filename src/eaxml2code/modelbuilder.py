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
import sys

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

        self._headers = {}  #main entry point to final model

    @property
    def current_element(self):
        if self._model['elements']:
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
            'connector': self.visit_ea_connector,
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
            if not 'component' in self._model:
                self._model['component'] = node['attributes']['name']
        elif xmi_type in [ 'uml:Class', 'uml:Interface', 'uml:Artifact', 'uml:Enumeration', 'uml:Component' ]:
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
            'name': node['attributes'].get('name', ''),
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
            # 'return' is not really a parameter, just ignore it
            if param_el['name'] != 'return':
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

        try:
            found = self._id_map[node['attributes']['xmi:idref']]
        except KeyError as e:
            return
        for c in node['children']:
            if c['name'] == 'properties' and "attributes" in c:
                if 'documentation' in c['attributes']:
                    found['description'] = self._clear_formatting(c['attributes']['documentation'])
                    if xmi_type != 'uml:Artifact':
                        found['header'] = self._extract_header(found['name'], found['description'])
                    else:
                        found['generated'] = self._extract_generated(found['name'], found['description'])
                if 'stereotype' in c['attributes']:
                    found['stereotype'] = c['attributes']['stereotype']
            elif c['name'] == 'links' and found.get('stereotype', '') == 'typedef':
                for cc in c['children']:
                    #Only consider outgoing links.
                    if cc['name'] == 'Generalization' and cc['attributes']['end'] != found['xmi:id']:
                        found['base:id'] = cc['attributes']['end']

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
            if c['name'] == 'initial':
                found.setdefault('initial', '')
                if "attributes" in c:
                    found['initial'] = c["attributes"]['body']
            elif c['name'] == 'documentation':
                found.setdefault('description', '')
                if "attributes" in c:
                    found['description'] = self._clear_formatting(c['attributes']['value'])
            elif c['name'] == 'properties' and 'attributes' in c:
                found['type'] = c['attributes'].get('type', '')
                found['static'] = 'static' if c['attributes'].get('static', '') == '1' else ''


    def visit_ea_operation(self, node:dict):
        found = self._id_map[node['attributes']['xmi:idref']]
        assert found['name'] == node['attributes']['name']

        for c in node['children']:
            if c['name'] == 'stereotype' and 'attributes' in c:
                found['stereotype'] = c['attributes']['stereotype']
            elif c['name'] == 'type':
                found['static'] = c['attributes']["static"]
                found.setdefault('return-value', {})
                found['return-value'].setdefault('description', '')
                if "type" in c['attributes']:
                    found['return-value']['type'] = c['attributes']['type']
                else:
                    found['return-value']['type'] = 'void'
            elif c['name'] == 'documentation':
                if 'attributes' in c:
                    found['description'] = self._clear_formatting(c['attributes']['value'])
                    if found['return-value']['type'] != 'void':
                        found['return-value']['description'] = self._extract_return_value_description(found['name'], found['description'])
                elif found.get('return-value', {}).get('type', 'void') != 'void':
                    print(f"WARNING: operation {found['name']} returning non-void is missing return value description")
            elif c['name'] == 'parameters':
                self._collect_parameters(c, found['parameters'])

    def _extract_return_value_description(self, op_name, description):
        for line in description.split('\n'):
            if 'Return value:' in line:
                return line.replace('Return value:', '').strip()
        print(f"WARNING: return value of {op_name} is missing description")
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
            found_param.setdefault('description', '')
            for cc in c['children']:
                if cc['name'] == 'properties':
                    found_param['type'] = cc['attributes'].get('type', '')
                    found_param['position'] = cc['attributes']['pos']
                    found_param['const'] = cc['attributes']['const']
                elif cc['name'] == 'documentation' and 'attributes' in cc:
                    found_param['description'] = self._clear_formatting(cc['attributes']['value'])

    def visit_ea_connector(self, node:dict):
        found = self._id_map.get(node['attributes']['xmi:idref'], None)
        if found is None:
            return

        for c in node['children']:
            if c['name'] == 'properties':
                found['stereotype'] = c['attributes'].get('stereotype', '')
                found['type'] = c['attributes']['ea_type']

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
        self._arrange_types()
        self._arrange_variables()
        self._arrange_macro_constants()

    def _create_headers(self):
        for el in self._model['elements']:
            if el['xmi:type'] == 'uml:Artifact':
                if not 'stereotype' in el:
                    print(f"WARNING: artifact {el['name']} has no stereotype, ignoring")
                elif el['stereotype'] == 'header':
                    self._headers.setdefault(el['name'], deepcopy(self._default_header_content))
                    header_ref = self._headers[el['name']]
                    header_ref['file-name'] = el['name']
                    if not 'description' in el:
                        print(f"WARNING: artifact {el['name']} is missing description")
                    header_ref['description'] = self._clean_el_description(el.get('description', ''))
                    header_ref['generated'] = el.get('generated', False)
                    header_ref['component'] = self._model['component']
                    header_ref['includes'] = []
                    self._get_includes(el, header_ref)

    def _get_includes(self, artifact, header_ref):
        for dep in self._model['dependencies']:
            if dep['client'] == artifact['xmi:id'] and dep.get('stereotype', 'include'):
                if dep['supplier'] in self._id_map:
                    supplier_el = self._id_map[dep['supplier']]
                    header_ref['includes'] += [ supplier_el['name'] ]
                else:
                    print(f"WARNING: artifact {dep['supplier']} not found in the model, ignoring")

    def _get_brief(self, descr: str):
        p_dot = descr.find('.')
        p_newl = descr.find('\n')
        if p_dot < 0:
            p_dot = sys.maxsize
        if p_newl < 0:
            p_newl = sys.maxsize
        cut_point = min([ p_dot, p_newl ])
        if cut_point < sys.maxsize:
            return descr[:cut_point]
        else:
            return "GO FIX THIS DESCRIPTION"

    #
    # Post-process operations
    #
    def _arrange_function_groups(self):
        for el in self._model['elements']:
            if el['xmi:type'] == 'uml:Interface':
                functions_group = {
                    'functions-group': el['name'],
                    'functions': [ ]
                }
                if 'header' not in el:
                    print(f"WARNING: interface {el['name']} not assigned to any header file, will not be generated")
                    continue
                if el['header'] not in self._headers:
                    print(f"WARNING: interface {el['name']} assigned to undefined header file {el['header']}, will not be generated")
                    continue
                self._headers[el['header']]['functions'] += [ functions_group ]
                #add functions for this owner
                for f in self._model['operations']:
                    if f['owner'] == el['xmi:id']:
                        functions_group['functions'] += [ f ]
                        #supplement missing keys
                        f.setdefault('in-params', [])
                        f.setdefault('out-params', [])
                        f.setdefault('inout-params', [])
                        f.setdefault('return-value', { 'type': 'void', 'description': '' })
                        f['description'] = self._clean_el_description(f.get('description', ''))
                        f['brief'] = self._get_brief(f['description'])

                        self._set_func_params(f)
                        if 'stereotype' in f and f['stereotype'] == "macro":
                            f['is-macro'] = True
                            self._set_func_macro_syntax(f)
                            self._set_func_macro_definition(f)
                        else:
                            f['is-macro'] = False
                            self._set_func_syntax(f)

    def _set_func_syntax(self, func):
        syntax = ''
        if func['static'] == 'true':
            syntax = 'static '
        syntax += func['return-value']['type'] + ' ' + func['name'] + '('
        for p in func['parameters']:
            if p['name'] == "...":
                syntax += p['name'] + ', '
            else:
                type = p['type']
                if p['const'] == 'true' and not type.startswith('const'):
                    type = 'const ' + type
                syntax += type + ' ' + p['name'] + ', '
        if syntax.endswith(', '):
            syntax = syntax[:-2]
        syntax += ')'
        func['syntax'] = syntax

    def _set_func_params(self, func):
        for p in func['parameters']:
            key = p['direction'] + '-params'
            func[key] += [
                {
                    'name': p['name'],
                    'description': p['description']
                }
            ]

    def _set_func_macro_syntax(self, func):
        syntax = func['name'] + '('
        for p in func['parameters']:
            syntax += p['name'] + ', '
        if syntax.endswith(', '):
            syntax = syntax[:-2]
        syntax += ')'
        func['syntax'] = syntax

    def _set_func_macro_definition(self, func):
        code = ''
        descr = ''
        add_to_code = False
        leading_spaces = None
        for line in func['description'].split('\n'):
            if add_to_code:
                if line.strip():
                    if leading_spaces is None:
                        leading_spaces = len(line) - len(line.lstrip(' '))
                    code += line[leading_spaces:] + '\n'
            elif 'Definition:' in line:
                add_to_code = True
            else:
                descr += line.strip() + '\n'
        func['definition'] = code.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        # Remove Definition: from description.
        func['description'] = descr.strip()

    #
    # Post-process types
    #
    def _arrange_types(self):
        for el in self._model['elements']:
            if el['xmi:type'] == 'uml:Class' and el.get('stereotype', '') == 'struct':
                type = {
                    'brief': self._get_brief(el['description']),
                    'description': self._clean_el_description(el['description']),
                    'kind': 'Structure',
                    'type-name': el['name'],
                    'elements': []
                }
                self._add_struct_fields(el, type)
                self._headers[el['header']]['types'] += [ type ]
            elif el['xmi:type'] == 'uml:Enumeration' and not 'stereotype' in el:
                type = {
                    'brief': self._get_brief(el['description']),
                    'description': self._clean_el_description(el['description']),
                    'kind': 'Enumeration',
                    'type-name': el['name'],
                    'constants': []
                }
                self._add_enums(el, type)
                self._headers[el['header']]['types'] += [ type ]
            elif el['xmi:type'] == 'uml:Class' and el.get('stereotype', '') == 'typedef':
                #Generalization has priority over containment.
                if 'base:id' in el:
                    found_base_type_el = self._id_map.get(el['base:id'], None)
                    declaration = self._make_typedef_from_base(el, found_base_type_el)
                else:
                    found_feature = self._find_typedef_feature(el['xmi:id'])
                    if found_feature != None:
                        declaration = self._make_typedef_from_feature(el, found_feature)
                    else:
                        print(f"WARNING: insufficient information for typedef declaration of {el['name']}, ignoring")
                        return
                type = {
                    'brief': self._get_brief(el['description']),
                    'description': self._clean_el_description(el['description']),
                    'kind': 'Typedef',
                    'type-name': el['name'],
                    'declaration': declaration
                }
                self._headers[el['header']]['types'] += [ type ]

    def _find_typedef_feature(self, owner):
        for attr in self._model['attributes']:
            if attr['owner'] == owner:
                return attr
        for op in self._model['operations']:
            if op['owner'] == owner:
                return op
        return None

    def _make_typedef_from_feature(self, el, feat):
        if 'parameters' in feat and 'return-value' in feat:
            if not feat['name'].startswith('(*') or not feat['name'].endswith(')'):
                print(f"WARNING: invalid declaration information for typedef f{el['name']} - expecting pointer to function")
                return ''
            decl = 'typedef ' + feat['return-value']['type'] + ' ' + feat['name'] + '('
            if len(feat['parameters']):
                for p in feat['parameters']:
                    decl += p['type'] + ', '
                decl = decl[:-2]
            decl += ')'
        else:
            if not 'type' in feat or not feat['type']:
                print("WARNING: missing or invalid type for typedef declaration")
            decl = 'typedef ' + feat['type'] + ' ' + el['name']
        return decl

    def _make_typedef_from_base(self, el, base):
        return 'typedef ' + base['name'] + ' ' + el['name']

    def _clear_formatting(self, descr):
        cleaned = ''
        for line in descr.split('\n'):
            l = line.replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')
            cleaned += l + '\n'
        return cleaned.strip()


    def _clean_el_description(self, descr):
        unformatted = self._clear_formatting(descr)
        cleaned = ''
        for line in unformatted.split('\n'):
            if 'Declared in:' not in line and 'Generated:' not in line:
                cleaned += line + '\n'
        return cleaned.strip()

    def _add_struct_fields(self, el, type):
        for a in self._model['attributes']:
            if a['owner'] == el['xmi:id']:
                struct_el = {
                    'description': a['description'],
                    'type': a['type'],
                    'field': a['name']
                }
                type['elements'].append(struct_el)

    def _add_enums(self, el, type):
        for l in self._model['literals']:
            if l['owner'] == el['xmi:id']:
                constant = {
                    'name': l['name'],
                    'description': l['description'],
                    'value': l["initial"]
                }
                type['constants'].append(constant)

    #
    # Post-process variables
    #
    def _arrange_variables(self):
        for el in self._model['elements']:
            if el['xmi:type'] == 'uml:Class' and el.get('stereotype', '') == 'variables':
                variables_group = {
                    'variables-group': el['name'],
                    'variables':  [ ]
                }
                self._headers[el['header']]['variables'] += [ variables_group ]
                #add attributes for this owner
                for a in self._model['attributes']:
                    if a['owner'] == el['xmi:id']:
                        variables_group['variables'] += [ a ]
                        # description is already set
                        a['syntax'] = a['static'] + bool(a['static']) * ' ' + a['type'] + ' ' + a['name']
                        if a['initial']:
                            a['syntax'] += ' = ' + a['initial']

    #
    # Post-process macro constants
    #
    def _arrange_macro_constants(self):
        for el in self._model['elements']:
            if el['xmi:type'] == 'uml:Enumeration' and el.get('stereotype', '') == 'macros':
                macro_constants_group = {
                    'constants-group': el['name'],
                    'constants': []
                }
                self._headers[el['header']]['macro-constants'] += [ macro_constants_group ]
                #add constants for this owner
                for c in self._model['literals']:
                    if c['owner'] == el['xmi:id']:
                        macro_constants_group['constants'] += [ c ]
                        # name and description are already set
                        if not c['initial'] and 'Definition:' in c['description']:
                            self._set_func_macro_definition(c)
                        else:
                            c['value'] = c['initial']


