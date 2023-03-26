###
<%!                                             \
    def make_include_guard(file):               \
        return file.upper().replace('.', '_')   \
%>                                              \
###
<%!                                             \
    def make_include_guard(file):               \
        return file.upper().replace('.', '_')   \
%>                                              \
###
<%!                                             \
    def get_group(content,item):                \
        return content['component']             \
%>                                                                      \
###
<%!                                                                                 \
    def get_enum_initializer(item):                                                 \
        return bool(item.get('value', '').strip()) * ' = ' + item.get('value', '')  \
%>                                                                                  \
###
### render_macro_constant()
###
<%def name="render_macro_constant(const_item)" filter="trim">           \
% if 'definition' in const_item:
/**
%    for line in const_item['description'].split('\n'):
 * ${line}
%    endfor
 */
${const_item['definition']}
% else:
#define ${const_item['name']} (${const_item['value']})    ///< ${const_item['description']}
% endif
</%def>                                                                 \
###
### render_macro_function()
###
<%def name="render_macro_function(func_item)" filter="trim" >

/**
 * @brief ${func_item['brief']}
 *
% for line in func_item['description'].split('\n'):
 * ${line}
% endfor
 *
% for ipar in func_item['in-params']:
 * @param[in] ${ipar['name']} - ${ipar['description']}
% endfor
% for opar in func_item['out-params']:
 * @param[out] ${opar['name']} - ${opar['description']}
% endfor
% for iopar in func_item['inout-params']:
 * @param[in-out] ${iopar['name']} - ${iopar['description']}
% endfor
% if func_item['return-value']['type'] != "void":
 * @return ${func_item['return-value']['type']} - ${func_item['return-value']['description']}
% endif
 */
${func_item['definition']}
</%def>
### render_type() ###
<%def name="render_type(type_item)">            \

/**
 * ${type_item['brief']}
 * @ingroup ${content['component']}
 *
% for line in type_item['description'].split('\n'):
 * ${line}
% endfor
 */
% if type_item['kind'] == 'Typedef':
${type_item['declaration']};
% elif type_item['kind'] == 'Structure':
typedef struct ${type_item['type-name']} {
% for sel in type_item['elements']:
    /** ${sel['description']} */
    ${sel['type']} ${sel['field']};
% endfor
} ${type_item['type-name']};
% elif type_item['kind'] == 'Enumeration':
typedef enum ${type_item['type-name']} {
% for item in type_item['constants']:
    ${item['name']}${get_enum_initializer(item)},       ///< ${item['description']}
% endfor
} ${type_item['type-name']};
% endif
</%def>                                         \
###
### render_variable()
###
<%def name="render_variable(var_item)" filter="trim">                   \
${var_item['syntax']};      ///< ${var_item['description']}
</%def>                                                                 \
### render_function() ###
<%def name="render_function(func_item)">        \

/**
 * @brief ${func_item['brief']}
 * @ingroup ${content['component']}
 *
% for line in func_item['description'].split('\n'):
 * ${line}
% endfor
% for ipar in func_item['in-params']:
 * @param[in] ${ipar['name']} - ${ipar['description']}
% endfor
% for opar in func_item['out-params']:
 * @param[out] ${opar['name']} - ${opar['description']}
% endfor
% for iopar in func_item['inout-params']:
 * @param[in-out] ${iopar['name']} - ${iopar['description']}
% endfor
% if func_item['return-value']['type'] != "void":
 * @return ${func_item['return-value']['type']} - ${func_item['return-value']['description']}
% endif
 */
${func_item['syntax']};
</%def>                                         \
###

/**!
 *
 * ${content['description']}
 *
 * Copyright ...
 *
 */

#ifndef TEST_${make_include_guard(file)}
#define TEST_${make_include_guard(file)}
##
% if content['file-name'] == content['component'].lower() + '.h':

/*!
 * @defgroup ${content['component']} ${content['component']}
 */

% elif content['file-name'] == content['component'].lower() + '_priv.h':

/*!
 * @defgroup ${content['component']+'Private'} ${content['component']+'Private'}
 */

% endif
##

% for i in content['includes']:
#include "${i}"
% endfor

% for cg in content['macro-constants']:
/**
 *  ${cg['constants-group']}
 *  @addtogroup ${get_group(content, cg)} @{
 */
%    for c in cg['constants']:
${render_macro_constant(c)}
%    endfor
/** @} */

% endfor
##
% for t in content['types']:
${render_type(t)}
% endfor

% for vg in content['variables']:
/**
 * @brief ${vg['variables-group']}
 * @addtogroup ${get_group(content, vg)} @{
 */
%    for v in vg['variables']:
${render_variable(v)}
%    endfor
/** @} */

%endfor
##
% for fg in content['functions']:
/**
 * @brief ${fg['functions-group']}
 * @addtogroup ${get_group(content, fg)} @{
 */
%     for f in fg['functions']:
%        if f['is-macro']:
${render_macro_function(f)}

%        else:
${render_function(f)}

%        endif
%    endfor
/** @} */

% endfor
##

#endif //TEST_${make_include_guard(file)}