###
<%!                                             \
    def make_include_guard(file):               \
        return file.upper().replace('.', '_')   \
%>                                              \
###
<%!                                             \
    def get_brief(descr):                       \
        return descr[:descr.index("\n")]        \
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
<%!                                                                     \
    def get_enum_initializer(item):                                     \
        return ' = ' + item['value'] if 'value' in item else ''         \
%>                                                                      \
###
### render_macro_constant()
###
<%def name="render_macro_constant(const_item)" filter="trim">           \
#define ${const_item['name']} (${const_item['value']})    ///< ${const_item['description']}
</%def>                                                                 \
###
### render_macro_function()
###
<%def name="render_macro_function(func_item)" filter="trim" >

/**
 * @brief ${get_brief(func_item['description'])}
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
% for def_item in func_item['definition']:
% if def_item['prepro-conditional'] != '':
${def_item['prepro-conditional']} ${def_item['condition']}
% endif
${func_item['syntax']}   <%text>\</%text>
%for line in def_item['code']:
    ${line}
% endfor
% endfor
% if func_item['definition'][0]['prepro-conditional'] != '':
#endif
% endif
</%def>
### render_type() ###
<%def name="render_type(type_item)">            \

/**
 * ${type_item['description']}
 * @ingroup ${content['component']}
 */
% if type_item['kind'] == 'Typedef':
typedef ${type_item['type']};
% elif type_item['kind'] == 'Structure':
typedef struct ${type_item['type-name']} {
% for sel in type_item['elements']:
    /** ${sel['description']} */
    ${sel['type']} ${sel['field']};
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
 * @brief ${get_brief(func_item['description'])}
 * @ingroup ${content['component']}
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
/** ${cg['constants-group']} */
%    for c in cg['constants']:
${render_macro_constant(c)}
%    endfor

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
${render_function(f)}
%    endfor
/** @} */

% endfor
##

#endif //TEST_${make_include_guard(file)}