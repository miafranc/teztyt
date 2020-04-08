# -*- coding: utf-8 -*-

import codecs
import json
import random
from distutils.spawn import find_executable
from subprocess import call
from os.path import join, isfile, isdir
from os import listdir, unlink
import shutil
import argparse
import sys

import regex
from PyPDF2.pdf import PdfFileReader, PdfFileWriter


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
        self.config = self.load_json(config_file)
        self.data = []

    @staticmethod
    def load_json(json_filename):
        """Returns the content of a JSON file.
        
        Parameters:
            json_filename (str): Path to the filename.
        
        Returns:
            dict: JSON as a dictionary.
        """
        f = codecs.open(json_filename, 'r', 'utf-8')
        data = json.load(f)
        f.close()
        return data
    
    def read(self, *filenames):
        """Reads the problems given in JSON format.
        Must be called before any other method.
        
        Parameters:
            *filenames (strs): Paths to the JSON data files.
        """
        self.data = []
        for f in filenames:
            self.data.append(self.load_json(f))

    def generate_tests(self, num_tests, out_dir, *num_problems):
        """Generates a given a number of tests and outputs the generated PDF
        files to a directory.
        
        Parameters:
            num_tests (int): Number of tests to generate.
            out_dir (str): Path to output directory.
            *num_problems (ints): Number of problems to generate from each data file.
        """
        map(lambda x: shutil.rmtree(x) if isdir(x) else unlink(x), (join(out_dir, f) for f in listdir(out_dir)))

        solutions = '===\n'
        
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
            
            solutions += sol + '===\n'
            
        f = codecs.open(join(out_dir, self.config['solutions_file']), 'w', 'utf-8')
        f.write(solutions)
        f.close()

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
        test_solution = ''
        
        for i in range(len(num_problems)):
            if num_problems[i] > len(all_keys[i]):
                raise Exception('Too few problems in one of the data files!')
            
            sel_keys = random.sample(all_keys[i], num_problems[i])
            selected_keys.append(sel_keys)
            
            for k in sel_keys:
                problem_num += 1
                answers = self._shuffle_answers(self.data[i][k])
                code = self._generate_code(test_id, problem_num, i, k, answers)
                sol = self._generate_solution(problem_num, i, k, answers)
                test_code += code
                test_solution += sol
            
        test_code = self._generate_code_prologue(test_id) + test_code + self._generate_code_epilogue()
        test_solution = str(test_id) + ':\n' + test_solution
        
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
        test_solution = ''
        
        for i in range(len(problems)):
            for k in problems[i]:
                problem_num += 1
                answers = self._shuffle_answers(self.data[i][str(k)])  # conversion is needed in order to simplify command-line stuff (str(k))
                code = self._generate_code(test_id, problem_num, i, str(k), answers)
                sol = self._generate_solution(problem_num, i, str(k), answers)
                test_code += code
                test_solution += sol
            
        test_code = self._generate_code_prologue(test_id) + test_code + self._generate_code_epilogue()
        test_solution = str(test_id) + ':\n' + test_solution
        
        self._write_latex(test_id, test_code, out_dir)
        self._compile_latex(test_id, out_dir)
        f = codecs.open(join(out_dir, self.config['solutions_file']), 'w', 'utf-8')
        f.write(test_solution)
        f.close()

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
#             code += '\\item[{}] {}'.format(self.config['checkbox'], ans)
            code += '\\item[\\checkBoxHref{{{}}}] {}'.format('{}:{}:{}:{}'.format(test_id, i, k, ind_a), ans)
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
        prologue += '\n'.join(self.config['prologue']) + '\n\n'
        
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
        
#         prologue += '\\begin{Form}[action={}]\n\n'
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
    
    def _generate_solution(self, problem_num, i, k, answers):
        """Generates text describing the solution of a given problem.
        
        Parameters:
            problem_num (int): Index of problem.
            i (int): Index of data file.
            k (str): Key of the problem.
            answers (list of strs): Shuffled keys of the problem.
            
        Returns:
            str: Text describing the solution of a given problem.
        """
        sol = '{} ({}/{}): '.format(problem_num, i + 1, k)
        first_correct_answer = True
        for ind, a in enumerate(answers):
            if first_correct_answer:
                if regex.match(self.config['correct_key_match'], a):
                    sol += '{}'.format(ind + 1)
                    first_correct_answer = False
            else:
                if regex.match(self.config['correct_key_match'], a):
                    sol += ', {}'.format(ind + 1)
         
        return sol + '\n'
    
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
        Be careful: if `same_page_number` is set to true in the config file, all tests
        will have `max_pages` number of pages.
        
        Parameters:
            in_dir (str): Path to the input directory containing the PDF files to be merged.
            out_file (str): Path to the merged PDF.
        """
        pw = PdfFileWriter()
        
        for f in sorted(listdir(in_dir)):
            if isfile(join(in_dir, f)) and regex.match('^test.*\.pdf$', f, flags=regex.IGNORECASE):
                pr = PdfFileReader(join(in_dir, f))
                pw.appendPagesFromReader(pr)
                if self.config['same_page_number'] and pr.getNumPages() < self.config['max_pages']:
                    for i in range(self.config['max_pages'] - pr.getNumPages()):  # pylint: disable=unused-variable
                        pw.addBlankPage()
        f = codecs.open(out_file, 'wb')
        pw.write(f)
        f.close()


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c', type=str, required=True, help="Configuration file.")
    parser.add_argument('--number', '-n', type=int, required=True, help="Number of tests to generate.")
    parser.add_argument('--files', '-f', type=str, nargs='+', required=True, help="Data files. E.g. '-f d1.json d2.json d3.json'")
#     parser.add_argument('--problems', '-p', type=int, nargs='+', required=True, help="Number of problems to generate from each file. E.g. '-p 3 2 1'")
    parser.add_argument('--problems', '-p', type=str, required=True, 
                        help="""Number of problems to generate from each file in form of a list. E.g. '-p [3, 2, 1]'.
                                If '-n 0' is used (test generation using given problems), this list must contain
                                lists, e.g. [[1], [1,2], [5]].""")
    parser.add_argument('--out', '-o', type=str, required=True, help="Output directory.")
    parser.add_argument('--merge', '-m', type=str, required=False, help="Optional, the name of the merged tests' file.")
    
    args = parser.parse_args(args)

    mct = OneClassMultipleChoiceTest(args.config)
    mct.read(*args.files)
    
    if args.number == 0:  # given problems
        print(json.loads(args.problems))
        mct.generate_test_with_problems(1, json.loads(args.problems), args.out)
#         mct.generate_test_with_problems(1, [[2],[2],[2]], args.out)
    else:
#         mct.generate_tests(args.number, args.out, *args.problems)
        print(json.loads(args.problems))
        mct.generate_tests(args.number, args.out, *json.loads(args.problems))
        if args.merge:
            mct._merge_pdfs(args.out, args.merge)
        

if __name__ == "__main__":
#     main(sys.argv[1:])

    main("-h".split())
    
#     main("-c ./config.json -n 0 -f ./data_OK/t1.json ./data_OK/t2.json ./data_OK/t3.json -p [[1,1],[1],[1]] -o ./ooo".split())
#     main("-c ./config.json -n 0 -f ./data_OK/t1.json ./data_OK/t2.json ./data_OK/t3.json -p [[1,1],[],[2]] -o ./ooo".split())
#     main("-c ./config.json -n 1 -f ./data_OK/t1.json ./data_OK/t2.json ./data_OK/t3.json -p [1,0,0] -o ./ooo".split())
#     main("-c ./config.json -n 1 -f ./data_OK/t1.json ./data_OK/t2.json ./data_OK/t3.json -p [0,0,0] -o ./ooo".split())


if __name__ == "__main__1":
    # TODO:
    # ----------
    # - README.md

    mct = OneClassMultipleChoiceTest('config.json')
    
    mct.read('data_OK/t1.json',
             'data_OK/t2.json',
             'data_OK/t3.json')

#     test_id = 100
#     mct.generate_test_with_problems(test_id, [['2'], ['2'], ['2']], './ooo')
#     exit(0)
    
#     mct.generate_tests(1, 'gen', 1, 1, 1)
    mct.generate_tests(5, 'gen', 2, 4, 2)
    mct._merge_pdfs('gen', 'gen/all.pdf')
    