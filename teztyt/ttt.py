# -*- coding: utf-8 -*-

import codecs
import json
import random
from distutils.spawn import find_executable
from subprocess import call
from os.path import join, isfile
from os import listdir
import argparse
import sys

import regex
from PyPDF2.pdf import PdfFileReader, PdfFileWriter
from PyPDF2.generic import BooleanObject, NameObject
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


class OneClassMultipleChoiceTest:
    """Class for generating multiple choice tests from a given set of problems
    stored in JSON files. 
    Generates and compiles LaTeX code and outputs PDFs.
    """
        
    def __init__(self, config_file):
        """Constructor of class `OneClassMultipleChoiceTest`.
        
        Parameters:
            config_file (str): Path to the JSON configuration file.
        """
        self.config_type = 'yaml'
        if config_file.endswith('.json'):
            self.config_type = 'json'
        self.config = self._load_yaml(config_file)  # can handle json too
        self.data = []
        
        self.solutions = {}
        
        self.YES = '/Yes'
        self.NO = '/Off'
        
    @staticmethod
    def _check_duplicate_keys(fname, ordered_pairs):
        """Checking for duplicate keys
        """
        d = {}
        for k, v in ordered_pairs:
            if k in d:
                raise Exception('Duplicate keys: {} ({})'.format(k, fname))
            else:
                d[k] = v
        return d

    class UniqueKeyLoader(Loader):
        """From: https://gist.github.com/pypt/94d747fe5180851196eb
        """
        def construct_mapping(self, node, deep=False):
            mapping = []
            for key_node, value_node in node.value:  # pylint: disable=unused-variable 
                key = self.construct_object(key_node, deep=deep)
                if key in mapping:
                    raise Exception('Duplicate keys: {}'.format(key))
                mapping.append(key)
            return super().construct_mapping(node, deep)
    
    @staticmethod
    def _load_yaml(yaml_filename, load_all=False):
        """Returns the content of a YAML file.
        
        Parameters:
            yaml_filename (str): Path to the filename.
        
        Returns:
            data: Data read from file in a Python data structure.
        """
        f = codecs.open(yaml_filename, 'r', 'utf-8')
        if load_all:
            data = list(yaml.load_all(f, Loader=OneClassMultipleChoiceTest.UniqueKeyLoader))
        else:
            data = yaml.load(f, Loader=OneClassMultipleChoiceTest.UniqueKeyLoader)
        f.close()
        return data

    @staticmethod
    def _dump_yaml(yaml_filename, data, dump_all=False):
        """Dumps the content of a YAML file.
        
        Parameters:
            yaml_filename (str): Path to the filename.
        """
        f = codecs.open(yaml_filename, 'w', 'utf-8')
        if dump_all:
#             yaml.dump_all(data, f, Dumper=Dumper, indent=2, default_flow_style=False, allow_unicode=True)
            yaml.dump_all(data, f, Dumper=Dumper, indent=2, allow_unicode=True)
        else:
            yaml.dump(data, f, Dumper=Dumper, indent=2, allow_unicode=True)
        f.close()

    @staticmethod
    def _load_json(json_filename):
        """Returns the content of a JSON file.
        
        Parameters:
            json_filename (str): Path to the filename.
        
        Returns:
            dict: JSON as a dictionary.
        """
        f = codecs.open(json_filename, 'r', 'utf-8')
        data = json.load(f, object_pairs_hook=lambda pairs: OneClassMultipleChoiceTest._check_duplicate_keys(json_filename, pairs))
        f.close()
        return data
    
    def read(self, *filenames):
        """Reads the problems given in JSON format.
        Must be called before any other method.
        
        Parameters:
            *filenames (strs): Paths to the JSON data files.
        
        (The format of the YAML file slightly differs from the JSON: in JSON there is one dictionary
        containing all the problems, while in YAML each document (dictionary) represent one document.)
        """
        self.data = []
        for f in filenames:
            if f.endswith('.json'):  # JSON
                self.data.append(self._load_json(f))
            elif f.endswith('.yaml'):  # YAML
                data = self._load_yaml(f, load_all=True)
                ddata = {}
                for d in data:
                    if len(d.keys()) > 1:
                        raise Exception('Wrong YAML format: more than one problem in one document!')
                    if list(d.keys())[0] in ddata.keys():
                        raise Exception('Duplicate keys: {} ({})'.format(list(d.keys())[0], f))
                    ddata.update(d)
                self.data.append(ddata)

    def generate_tests(self, num_tests, out_dir, *num_problems):
        """Generates a given a number of tests and outputs the generated PDF
        files to a directory.
        
        Parameters:
            num_tests (int): Number of tests to generate.
            out_dir (str): Path to output directory.
            *num_problems (ints): Number of problems to generate from each data file.
        """
        solutions = []
        
        for test_id in range(num_tests):
            (code, sol) = self.generate_test(test_id + 1, *num_problems)
            self._write_latex(test_id + 1, code, out_dir)
            self._compile_latex(test_id + 1, out_dir)
            page_num = self._check_pagenumber(test_id + 1, out_dir)
            
            attempts = 0
            
            while page_num > self.config['max_pages'] and attempts < self.config['max_attempts']:
                print('Test {}: attempt {}'.format(test_id + 1, attempts))
                
                (code, sol) = self.generate_test(test_id + 1, *num_problems)
                self._write_latex(test_id + 1, code, out_dir)
                self._compile_latex(test_id + 1, out_dir)
                page_num = self._check_pagenumber(test_id + 1, out_dir)
                attempts += 1
            
            if page_num > self.config['max_pages']:
                raise Exception('Could not generate tests: could not fit into given number of pages!')
            
            solutions.append(sol)
            
        self._dump_yaml(join(out_dir, self.config['solutions_file']), solutions, dump_all=True)

    def generate_test(self, test_id, *num_problems):
        """Generates a test with a given `test_id` containing `num_problems`
        problems from each data file.
        
        Parameters:
            test_id (int): Unique ID (usually index) of test.
            *num_problems (ints): Number of problems to generate from each data file.
        
        Returns:
            str: LaTeX code for one test.
            str: Solution of the test.
        """
        if len(num_problems) != len(self.data):
            raise Exception('Number of data files and number of problems must be equal!')
    
        all_keys = [self.data[i].keys() for i in range(len(self.data))]
        selected_keys = []
        problem_num = 0
        
        test_code = ''
        test_solution = {}
        
        for i in range(len(num_problems)):
            if num_problems[i] > len(all_keys[i]):
                raise Exception('Too few problems in one of the data files!')
            
            sel_keys = random.sample(all_keys[i], num_problems[i])
            selected_keys.append(sel_keys)
            
            for k in sel_keys:
                problem_num += 1
                answers = self._shuffle_answers(self.data[i][k])
                code = self._generate_code(test_id, problem_num, i, k, answers)
                sol = self._generate_solution(problem_num, i, k, answers, self.data[i][k]['P'])
                test_code += code
                test_solution.update(sol)
        
        test_code = self._generate_code_prologue(test_id) + test_code + self._generate_code_epilogue()
        test_solution = {test_id: test_solution}
        
        return (test_code, test_solution)

    def generate_test_with_problems(self, test_id, problems, out_dir):
        """Generates a test with the given problems.
        
        Parameters:
            test_id (int): Unique ID (usually index) of test.
            problems (list): Exact problems to generate from each data file (IDs).
            out_dir (str): Path to output directory.
        
        Returns:
            str: LaTeX code for one test.
            str: Solution of the test.
        """
        if len(problems) != len(self.data):
            raise Exception('Number of data files and number of problems must be equal!')
    
        problem_num = 0
        
        test_code = ''
        test_solution = {}
        
        for i in range(len(problems)):
            for k in problems[i]:
                problem_num += 1
                answers = self._shuffle_answers(self.data[i][str(k)])  # conversion is needed in order to simplify command-line stuff (str(k))
                code = self._generate_code(test_id, problem_num, i, str(k), answers)
                sol = self._generate_solution(problem_num, i, str(k), answers, self.data[i][str(k)]['P'])
                test_code += code
                test_solution.update(sol)
        
        test_code = self._generate_code_prologue(test_id) + test_code + self._generate_code_epilogue()
        test_solution = [{test_id: test_solution}]

        self._write_latex(test_id, test_code, out_dir)
        self._compile_latex(test_id, out_dir)
        
        self._dump_yaml(join(out_dir, self.config['solutions_file']), test_solution, dump_all=True)

    def _generate_code(self, test_id, problem_num, i, k, answers):
        """Generates LaTeX code for a given test problem.
        
        Parameters:
            test_id (int): Unique ID (usually index) of test. 
            problem_num (int): Index of problem.
            i (int): Index of data file.
            k (str): Key of the problem.
            answers (list of strs): Shuffled keys of the problem.
            
        Returns:
            str: LaTeX code of a problem.
        """
        code = '%{}:\n'.format(problem_num)
        code += '\\begin{{{}}}[{}p]%{}/{}\n'.format(self.config['problem_environment'], self.data[i][k]['P'], i, k)
        code += self.data[i][k]['Q'].replace('%figures_dir%', self.config['figures_dir']) + '\n'
        code += '\\begin{itemize}\n'
        code += '\\setlength{{\\itemsep}}{{{}}}\n'.format(self.config['itemsep'])
        
        for ind_a, a in enumerate(answers):
            ans = self.data[i][k]['A'][a].replace('%figures_dir%', self.config['figures_dir'])
            code += '\\item[\\checkBoxHref{{{}}}] {}'.format('{}:{}:{}:{}:{}'.format(test_id, problem_num, i+1, k, ind_a+1), ans)
            code += ' %\n' if regex.match(self.config['correct_key_match'], a) else '\n'
         
        code += '\\end{itemize}\n'
        code += '\\end{{{}}}\n'.format(self.config['problem_environment'])
        
        return code

    def _generate_code_prologue(self, test_id):
        """Generates LaTeX code prologue.
        
        Parameters:
            test_id (int): Unique ID (usually index) of test.
            
        Returns:
            str: The LaTeX code prologue.
        """
        prologue = '\\documentclass[{}pt,oneside,{}]{{extarticle}}\n'.format(self.config['fontsize'], 
                                                                             self.config['columns'])
        if self.config_type == 'json':
            prologue += '\n'.join(self.config['prologue']) + '\n\n'
        else:
            prologue += '\n' + self.config['prologue'] + '\n\n'
        
        prologue += '\\title{{{}\\\\\n'.format(self.config['title'])
        if self.config['subtitle'] != '':
            prologue += '{}\\\\\n'.format(self.config['subtitle'])
        prologue += '{}\\\\\n'.format(test_id)
        prologue += '}'
        
        prologue += '\n\\date{}\\author{}\n\n'

        prologue += '\\usepackage{hyperref}\n'
        prologue += '\\newcommand\\checkBoxHref[1]{\\mbox{\\CheckBox[width=3mm, height=3mm, checkboxsymbol=\\ding{110}, bordercolor=0 0 0]{#1}}}\n'
        prologue += '\\renewcommand\\LayoutCheckField[2]{#2}\n\n'

        prologue += '\\pagenumbering{{{}}}\n'.format(self.config['pagenumbering'])
        prologue += '\\newcounter{{fel}}\n\\newtheorem{{problem}}[fel]{{{}}}\n'.format(self.config['newtheorem_string'])  # "built-in"/default problem environment
        prologue += '\\renewcommand{{\\baselinestretch}}{{{}}}\n\n'.format(self.config['baselinestretch'])
        prologue += '\\begin{document}\n\n\\maketitle\\sloppy\n\n'
        
        # prologue += '\\begin{Form}[action={}]\n\n'
        prologue += '\\begin{Form}\n\n'

        for ind_f, field in enumerate(self.config['name_and_stuff']):
            prologue += '\\noindent\\TextField[name={},width={}]{{{}:}}{}\n'.format('t{}:{}'.format(test_id, ind_f), 
                                                                                     self.config['name_and_stuff_widths'][ind_f], 
                                                                                     field,
                                                                                     '\\\\\\\\' if ind_f < len(self.config['name_and_stuff'])-1 else '')
        
        return prologue
    
    def _generate_code_epilogue(self):
        """Generates LaTeX code epilogue.
        
        Returns:
            str: The LaTeX code epilogue.
        """
        epilogue = '\n\\end{Form}\n\n'
        epilogue += '\n\\end{document}'
        return epilogue
    
    def _generate_solution(self, problem_num, i, k, answers, points):
        """Generates text describing the solution of a given problem.
        
        Parameters:
            problem_num (int): Index of problem.
            i (int): Index of data file.
            k (str): Key of the problem.
            answers (list of strs): Shuffled keys of the problem.
            
        Returns:
            dict: Dictionary describing the information about a problem,
                  including the correct answers (see the return statement below).
        """
        corr_ans = []
        for ind, a in enumerate(answers):
            if regex.match(self.config['correct_key_match'], a):
                corr_ans.append(ind + 1)
        
        return {problem_num: [[i+1, k, points], corr_ans]}
    
    def _shuffle_answers(self, problem):
        """Shuffles the answers of a given problem.
        
        Parameters:
            problem (dict): Problem as a dictionary.
            
        Returns:
            list of strs: Shuffled keys of the problem.
        """
        keys = random.sample(problem['A'].keys(), len(problem['A']))
        return keys

    def _write_latex(self, test_id, test_code, out_dir):
        """Writes out the generated LaTeX code to a file.
        
        Parameters:
            test_id (int): Unique ID (usually index) of test.
            test_code (str): Generated LaTeX code of test.
            out_dir (str): Path to output directory.
        """
        fname = '{}{}.tex'.format(self.config['out_file_prefix'], test_id)
        f = codecs.open(join(out_dir, fname), 'w', 'utf-8')
        f.write(test_code)
        f.close()

    def _compile_latex(self, test_id, out_dir):
        """Compiles the LaTeX source code generating PDF.
        
        Parameters:
            test_id (int): Unique ID (usually index) of test.
            out_dir (str): Path to output directory.
        """
        fname = '{}{}.tex'.format(self.config['out_file_prefix'], test_id)
        
        if not find_executable(self.config['pdflatex']):
            raise Exception('{} cannot be found!'.format(self.config['pdflatex']))
         
        if self.config['latex_parameters'] != '':
            call([self.config['pdflatex'], self.config['latex_parameters'], '-output-directory', out_dir, join(out_dir, fname)])
        else:
            call([self.config['pdflatex'], '-output-directory', out_dir, join(out_dir, fname)])

    def _check_pagenumber(self, test_id, out_dir):
        """Returns the number of pages of the generated PDF file based on the content of the log file.
        
        Parameters:
            test_id (int): Unique ID (usually index) of test.
            out_dir (str): Path to output directory.
            
        Returns:
            int: Number of pages in PDF.
        """
        f = codecs.open(join(out_dir, '{}{}.log'.format(self.config['out_file_prefix'], test_id)), 'r', 'utf-8', errors='ignore')  # sometimes utf-8 decode error occurs; did not happen in Python 2.7
        data = f.read()
        f.close()
        
        r = '{}{}\.pdf \(([0-9]+) page'.format(self.config['out_file_prefix'], test_id)
        m = regex.findall(r, data)
        
        return int(m[0])

    def _merge_pdfs(self, in_dir, out_file):
        """Merges PDFs in a given directory and outputs it to a single PDF file.
        If `same_page_number` is set to true in the config file, all tests will have `max_pages` number of pages.
        
        Parameters:
            in_dir (str): Path to the input directory containing the PDF files to be merged.
            out_file (str): Path to the merged PDF.
        """
        pw = PdfFileWriter()
        
        firstPDF = True
        for f in sorted(listdir(in_dir)):
            if isfile(join(in_dir, f)) and regex.match('^test.*\.pdf$', f, flags=regex.IGNORECASE):
                pr = PdfFileReader(join(in_dir, f), strict=False)
                
                form = pr.trailer["/Root"]["/AcroForm"]  # see: https://stackoverflow.com/questions/47288578/pdf-form-filled-with-pypdf2-does-not-show-in-print
                
                pw.appendPagesFromReader(pr)
                if self.config['same_page_number'] and pr.getNumPages() < self.config['max_pages']:
                    for i in range(self.config['max_pages'] - pr.getNumPages()):  # pylint: disable=unused-variable
                        pw.addBlankPage()
                
                if firstPDF:
                    pw._root_object.update({NameObject("/AcroForm"): form})
                    firstPDF = False
                else:
                    pw._root_object["/AcroForm"]["/Fields"].extend(form["/Fields"])
                
        pw._root_object["/AcroForm"].update({NameObject("/NeedAppearances"): BooleanObject(True)})
        
        f = codecs.open(out_file, 'wb')
        pw.write(f)
        f.close()

    def _extract_pdf_forms(self, fname):
        """Extracts interactive form fields data from a PDF file.
        
        Parameters:
            fname (str): Path to PDF file.
        
        Returns:
            dict: Form fields data extracted.
        """
        f = PdfFileReader(fname)
        return f.getFields()

    def load_solutions(self, fname):
        """Loads solutions file.
        
        Parameters:
            fname (str): Path to solutions file.
        
        Returns:
            dict: Solutions in a dict: {test_id: {problem_id: [[datafile_index, problem_key, problem_points], [correct_answer_index1, correct_answer_index2, ...]], ... } ... }
                  (Also sets `self.solutions`)
        """
        solutions = self._load_yaml(fname, load_all=True)
        
        sols = {}
        for s in solutions:
            sols.update(s)
        
        self.solutions = sols
        return sols

    def evaluate_test(self, fname):
        """Evaluate a test (a PDF file) given a solution file and an evaluation scheme.
        Solutions have to be loaded first.
        
        Parameters:
            fname (str): Path to PDF file.
        
        Returns:
            str: Test ID.
            dict: Dictionary of text data extracted: {text_key: text_value, ...}
            float: Points collected.
            list (of strs): List of correct indices.
            list (of strs): List of checked indices.
        """
        fields = self._extract_pdf_forms(fname)
        
        all_keys = list(fields.keys())
        problem_keys = list(filter(lambda x: x[0] != 't', all_keys))
        text_keys = list(filter(lambda x: x[0] == 't', all_keys))
        test_id = int(problem_keys[0][:problem_keys[0].index(':')])
        
        problem_solution = self.solutions[test_id]
        
        points = 0.
        correct_indices = []
        checked_indices = []
        
        if self.config['evaluation'] == 'regular': # regular (all-or-nothing) scheme
            schema = lambda c, a, r, p: p if set(c) == set(a) else 0  # pylint: disable=unused-variable
        elif self.config['evaluation'] == 'negative':  # proportional negative marking
            schema = lambda c, a, r, p: ((len(c.intersection(a)) - len(a.difference(c))) / float(len(c))) * p  # pylint: disable=unused-variable
        elif self.config['evaluation'] == 'positive':  # error-retaliatory positive marking
            schema = lambda c, a, r, p: (max(0, len(c.intersection(a)) - len(a.difference(c))) / float(len(c))) * p  # pylint: disable=unused-variable
        elif self.config['evaluation'] == 'my':  # user-defined
            schema = eval(self.config['evaluation_function'])
        else:
            raise Exception('Unknown evaluation scheme: {}'.format(self.config['evaluation']))
        
        for problem_id in problem_solution.keys():
            correct_answers = problem_solution[problem_id][1]
            # In some cases (e.g. using Acrobat Reader in Windows, version 2019.012.20040) it happens, that the '/V' fields becomes missing if a checkbox is not checked.
            # (This is why '/V' is checked if it exists.)
            checked_answers = [int(x[str.rindex(x, ':') + 1:]) for x in filter(lambda x: x.startswith('{}:{}'.format(test_id, problem_id)) 
                                                                          and fields[x].get('/V', -1) != -1 
                                                                          and fields[x]['/V'] == self.YES, problem_keys)]
            rest_answers = [int(x[str.rindex(x, ':') + 1:]) for x in filter(lambda x: x.startswith('{}:{}'.format(test_id, problem_id)) 
                                                                       and (fields[x].get('/V', -1) == -1 or fields[x]['/V'] == self.NO), problem_keys)]
            correct_indices.append(correct_answers)
            checked_indices.append(checked_answers)
            points += schema(set(correct_answers), set(checked_answers), set(rest_answers), float(problem_solution[problem_id][0][2]))
    
        return (test_id, {x:fields[x]['/V'] for x in text_keys}, points, correct_indices, checked_indices)
    
    def generate_report(self, test_id, text_data, points, correct_indices, checked_indices):
        """Generating evaluation reports. 
        Its parameters are exactly the ones returned by `evaluate_test`. 
        
        Parameters:
            test_id (str): Test ID.
            text_data (dict): Dictionary of text data extracted: {text_key: text_value, ...}
            points (float): Points collected.
            correct_indices (list of strs): List of correct indices.
            checked_indices (list of strs): List of checked indices.
        
        Returns:
            dict: Generated report.
        """
        # Sometimes it happens that a string becomes a byte string (in case of text fields).
        report = {test_id: {}}
        tt = {}
        for i, t in enumerate(text_data.keys()):
            st = str(t)
            tt[str(i+1) + '. ' + self.config['name_and_stuff'][int(st[st.rindex(':')+1:])]] = str(text_data[t])
        report[test_id]['_'] = tt
        report[test_id]['ans'] = {}
        for i in range(len(checked_indices)):
            report[test_id]['ans'][i+1] = [checked_indices[i], correct_indices[i]]
        report[test_id]['points'] = points
        
        return report
    
    def evaluate_tests(self, in_dir, out_file):
        """Evaluates test PDFs from a given input directory and writes out the evaluation report.
        Solutions have to be loaded first.
        
        Parameters:
            in_dir (str): Directory containing the test PDFs.
            out_file (str): Path to output report file.
        """
        reports = []
        for f in sorted(listdir(in_dir)):
            fname = join(in_dir, f)
            if isfile(fname) and regex.match('^.*\.pdf$', f, flags=regex.IGNORECASE):
                try:
                    (test_id, text_data, points, correct_indices, checked_indices) = self.evaluate_test(fname)
                    reports.append(self.generate_report(test_id, text_data, points, correct_indices, checked_indices))
                except:
                    print('ERROR ({}): {}'.format(fname, str(sys.exc_info())))  # do not raise exception, just report the error
        
        self._dump_yaml(out_file, reports, dump_all=True)
    

def main(args):
    if len(args) == 0:
        args = ['--help']
    
    parser = argparse.ArgumentParser()
    
    subparsers = parser.add_subparsers(help='sub-command help')
    
    # Generate tests:
    parser_gen = subparsers.add_parser('gen', help='Generate tests')
    parser_gen.add_argument('--config', '-c', type=str, required=True, help="Configuration file.")
    parser_gen.add_argument('--number', '-n', type=int, required=True, help="Number of tests to generate.")
    parser_gen.add_argument('--files', '-f', type=str, nargs='+', required=True, help="Data files. E.g. '-f d1.json d2.json d3.json'")
    parser_gen.add_argument('--problems', '-p', type=str, required=True, 
                        help="""Number of problems to generate from each file in form of a list. E.g. '-p [3,2,1]'.
                                If '-n 0' is used (test generation using given problems), this list must contain
                                lists, e.g. [[1],[1,2],[5]].
                                Spaces are not allowed in the above form, only if using aposthrophes or quotes,
                                e.g. "[1, 2, 3]".""")
    parser_gen.add_argument('--out', '-o', type=str, required=True, help="Output directory.")
    parser_gen.add_argument('--merge', '-m', type=str, required=False, help="Optional, the name of the merged tests' file.")
    parser_gen.set_defaults(which='gen')
    
    # Evaluate tests:
    parser_eval = subparsers.add_parser('eval', help='Evaluate tests')
    parser_eval.add_argument('--config', '-c', type=str, required=True, help="Configuration file.")
    parser_eval.add_argument('--solutions', '-s', type=str, required=True, help="Solutions file.")
    parser_eval.add_argument('--dir', '-d', type=str, required=True, help="Input directory.")
    parser_eval.add_argument('--out', '-o', type=str, required=True, help="Output filename.")
    parser_eval.set_defaults(which='eval')

    args = parser.parse_args(args)

    mct = OneClassMultipleChoiceTest(args.config)
    
#     print(args)
    
    if args.which == 'gen':
        mct.read(*args.files)
        
        if args.number == 0:  # given problems
            mct.generate_test_with_problems(1, json.loads(args.problems), args.out)
        else:
            mct.generate_tests(args.number, args.out, *json.loads(args.problems))
            if args.merge:
                mct._merge_pdfs(args.out, args.merge)
    elif args.which == 'eval':
        mct.load_solutions(args.solutions)
        mct.evaluate_tests(args.dir, args.out)

        
if __name__ == "__main__":
    main(sys.argv[1:])
