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

from argparse import ArgumentParser
import json
from mako.template import Template
from mako.runtime import Context
from mako import exceptions
from io import StringIO
import pkg_resources
import os
import xml.sax

try:
    from .xmlprocessor import XmlProcessor
    from .modelbuilder import ModelBuilder
    from .__init__ import __version__
except:
    from xmlprocessor import XmlProcessor
    from modelbuilder import ModelBuilder
    from __init__ import __version__


def main():
    try:
        version = pkg_resources.get_distribution('eaxml2code').version
    except pkg_resources.DistributionNotFound as e:
        version = __version__
    print("eaxml2code version ", version)
    parser = ArgumentParser()
    parser.add_argument("-i", "--input", dest="input", help="xml input file", metavar="INPUT-FILE", required=True, nargs='+')
    parser.add_argument("-e", "--encoding", dest="encoding", help="XML encoding", required=False, default="windows-1252")
    parser.add_argument("-t", "--template", dest="templ", help="header template", metavar="TEMPLATE", required=True)
    parser.add_argument("-o", "--odir", dest="odir", help="output folder", metavar="OUTPUT-DIR", required=True)
    parser.add_argument("-d", "--dump", dest="dump", help="dump content dictionary", default=False, required=False, action='store_true')
    parser.add_argument("-v", "--verbose", dest="verbose", help="Be more verbose about what is going on",
                        default=False, required=False, action='store_true')

    args = vars(parser.parse_args())

    with open(args['templ'], 'r') as f:
        templ_str = f.read()

    if args['verbose']:
        print("Analyzing code template...")
    try:
        header_templ = Template(templ_str)
    except:
        print(exceptions.text_error_template().render())
        raise

    builder = ModelBuilder(args['verbose'])

    for input in args['input']:
        with open(input, 'r', encoding=args['encoding']) as f:
            text = f.read()
            if args['verbose']:
                print("Parsing input file...")
            handler = XmlProcessor()
            xml.sax.parse(input, handler)
            root = handler.current_element

            if not os.path.exists(args['odir']):
                if args['verbose']:
                    print("Creating output directory...")
                os.mkdir(args['odir'])
            elif not os.path.isdir(args['odir']):
                print("ERROR: ", args['odir'], " is not a directory")

            if args['verbose']:
                print("Dumping raw model dict...")
                js = json.dumps(root, indent=3)
                with open(args['odir'] + os.sep + os.path.basename(input) + '_rawmodeldump.json', 'w') as fdump:
                    fdump.write(js)

            builder.walk_raw_model_subtree(root)

    if args['verbose']:
        print("Dumping model dict...")
        js = json.dumps(builder._model, indent=3)
        with open(args['odir'] + os.sep + 'modeldump.json', 'w') as fdump:
            fdump.write(js)

    builder.post_process()

    print("Generated headers:")
    for header in builder._headers:
        if builder._headers[header]['generated']:
            print('   ' + header)

    for header in builder._headers:
        try:
            if args['dump']:
                print('------ Dump content for header: ', header, ' ------')
                dump = json.dumps(builder._headers[header], indent=3)
                print(dump)
            if builder._headers[header]['generated']:
                buf = StringIO()
                ctx = Context(buf, file=header, content=builder._headers[header])
                header_templ.render_context(ctx)
                if args['verbose']:
                    print("Writing ", header)
                with open(args['odir'] + '/' + header, "w") as outf:
                    outf.write(buf.getvalue())
            else:
                if args['verbose']:
                    print("Skip writing ", header)
        except:
            print('Exception while rendering ' + header + ': ' + exceptions.text_error_template().render())

    if args['verbose']:
        print("Done.")

if __name__ == "__main__":
    main()