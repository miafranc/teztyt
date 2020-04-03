# -*- coding: utf-8 -*-

import codecs
import json
import random
import regex

from distutils.spawn import find_executable
from subprocess import call
from os.path import join, isfile, isdir
from os import listdir, unlink
import shutil

from PyPDF2.pdf import PdfFileReader, PdfFileWriter


class OneClassMultipleChoiceTest:
    """Class for generating multiple choice tests from a given set of problems
    stored in JSON files. 
    Generates and compiles LaTeX code and outputs PDFs.
    """
        
    def __init__(self, config_file):
        """Constructor of class `OneClassMultipleChoiceTest`.
        
        Parameters:
            config_file (str or unicode): Path to the JSON configuration file.
        """
        self.config = self.load_json(config_file)
        self.data = []

    @staticmethod
    def load_json(json_filename):
        """Returns the content of a JSON file.
        
        Parameters:
            json_filename (str or unicode): Path to the filename.
        
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
            *filenames (strs or unicodes): Paths to the JSON data files.
        """
        self.data = []
        for f in filenames:
            self.data.append(self.load_json(f))

    def generate_tests(self, num_tests, out_dir, *num_problems):
        """Generates a given a number of tests and outputs the generated PDF
        files to a directory.
        
        Parameters:
            num_tests (int): Number of tests to generate.
            out_dir (str or unicode): Path to output directory.
            *num_problems (ints): Number of problems to generate from each data file.
        """
        map(lambda x: shutil.rmtree(x) if isdir(x) else unlink(x), (join(out_dir, f) for f in listdir(out_dir)))

        solutions = u'===\n'
        
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
            
            solutions += sol + u'===\n'
            
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
            unicode: LaTeX code for one test.
            unicode: Solution of the test.
        """
        if len(num_problems) > len(self.data):
            raise Exception('Too few data files!')
    
        all_keys = [self.data[i].keys() for i in range(len(self.data))]
#         print all_keys
        selected_keys = []
        problem_num = 0
        
        test_code = u''
        test_solution = u''
        
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
            
#         print selected_keys
#         print test_code
#         print test_solution
        
        test_code = self._generate_code_prologue(test_id) + test_code + self._generate_code_epilogue()
        test_solution = unicode(test_id) + u':\n' + test_solution
        
#         print test_code
#         print test_solution
        
        return (test_code, test_solution)

    def _generate_code(self, test_id, problem_num, i, k, answers):
        """Generates LaTeX code for a given test problem.
        
        Parameters:
            test_id (int): Unique ID (usually index) of test. 
            problem_num (int): Index of problem.
            i (int): Index of data file.
            k (str or unicode): Key of the problem.
            answers (list of strs/unicodes): Shuffled keys of the problem.
            
        Returns:
            unicode: LaTeX code of a problem.
        """
        code = u'%{}:\n'.format(problem_num)
        code += u'\\begin{{{}}}[{}p]%{}/{}\n'.format(self.config['problem_environment'], self.data[i][k]['P'], i, k)
        code += self.data[i][k]['Q'].replace('%figures_dir%', self.config['figures_dir']) + '\n'
        code += u'\\begin{itemize}\n'
        code += u'\\setlength{{\\itemsep}}{{{}}}\n'.format(self.config['itemsep'])
        
        for ind_a, a in enumerate(answers):
            ans = self.data[i][k]['A'][a].replace('%figures_dir%', self.config['figures_dir'])
#             code += u'\\item[{}] {}'.format(self.config['checkbox'], ans)
            code += u'\\item[\\checkBoxHref{{{}}}] {}'.format(u'{}:{}:{}:{}'.format(test_id, i, k, ind_a), ans)
            code += u' %\n' if regex.match(self.config['correct_key_match'], a) else u'\n'
         
        code += u'\\end{itemize}\n'
        code += u'\\end{{{}}}\n'.format(self.config['problem_environment'])
        
#         print code
    
        return code

    def _generate_code_prologue(self, test_id):
        """Generates LaTeX code prologue.
        
        Parameters:
            test_id (int): Unique ID (usually index) of test.
            
        Returns:
            unicode: The LaTeX code prologue.
        """
        prologue = u'\n'.join(self.config['prologue']) + u'\n\n'
        
        prologue += u'\\title{{{}\\\\\n'.format(self.config['title'])
        if self.config['subtitle'] != '':
            prologue += u'{}\\\\\n'.format(self.config['subtitle'])
        prologue += u'{}\\\\\n'.format(test_id)
        prologue += u'}'
        
        prologue += u'\n\\date{}\\author{}\n\n'
        
        prologue += u'\\usepackage{hyperref}\n'
        prologue += u'\\newcommand\\checkBoxHref[1]{\\mbox{\\CheckBox[width=3mm, height=3mm, checkboxsymbol=\\ding{110}, bordercolor=0 0 0]{#1}}}\n'
        prologue += u'\\renewcommand\\LayoutCheckField[2]{#2}\n\n'

        prologue += u'\\pagenumbering{{{}}}\n'.format(self.config['pagenumbering'])
        prologue += u'\\newcounter{{fel}}\n\\newtheorem{{problem}}[fel]{{{}}}\n'.format(self.config['newtheorem_string'])  # "built-in"/default problem environment
        prologue += u'\\renewcommand{{\\baselinestretch}}{{{}}}\n\n'.format(self.config['baselinestretch'])
        prologue += u'\\begin{document}\n\n\\maketitle\\sloppy\n\n'
        
#         prologue += u'\\begin{Form}[action={}]\n\n'
        prologue += u'\\begin{Form}\n\n'

        for ind_f, field in enumerate(self.config['name_and_stuff']):
            prologue += u'\\noindent\\TextField[name={},width={}]{{{}:}}{}\n'.format(u't{}:{}'.format(test_id, ind_f), 
                                                                                     self.config['name_and_stuff_widths'][ind_f], 
                                                                                     field,
                                                                                     u'\\\\\\\\' if ind_f < len(self.config['name_and_stuff']) -1 else u'')
        
#         print prologue
    
        return prologue
    
    def _generate_code_epilogue(self):
        """Generates LaTeX code epilogue.
        
        Returns:
            unicode: The LaTeX code epilogue.
        """
        epilogue = u'\n\\end{Form}\n\n'
        epilogue += u'\n\\end{document}'
        return epilogue
    
    def _generate_solution(self, problem_num, i, k, answers):
        """Generates text describing the solution of a given problem.
        
        Parameters:
            problem_num (int): Index of problem.
            i (int): Index of data file.
            k (str or unicode): Key of the problem.
            answers (list of strs/unicodes): Shuffled keys of the problem.
            
        Returns:
            unicode: Text describing the solution of a given problem.
        """
        sol = u'{} ({}/{}): '.format(problem_num, i + 1, k)
        first_correct_answer = True
        for ind, a in enumerate(answers):
            if first_correct_answer:
                if regex.match(self.config['correct_key_match'], a):
                    sol += u'{}'.format(ind + 1)
                    first_correct_answer = False
            else:
                if regex.match(self.config['correct_key_match'], a):
                    sol += u', {}'.format(ind + 1)
         
#         print sol
         
        return sol + u'\n'
    
    def _shuffle_answers(self, problem):
        """Shuffles the answers of a given problem.
        
        Parameters:
            problem (dict): Problem as a dictionary.
            
        Returns:
            list of strs/unicodes: Shuffled keys of the problem.
        """
        keys = random.sample(problem['A'].keys(), len(problem['A']))
#         print keys
        return keys

    def _write_latex(self, test_id, test_code, out_dir):
        """Writes out the generated LaTeX code to a file.
        
        Parameters:
            test_id (int): Unique ID (usually index) of test.
            test_code (str or unicode): Generated LaTeX code of test.
            out_dir (str or unicode): Path to output directory.
        """
        fname = '{}{}.tex'.format(self.config['out_file_prefix'], test_id)
        f = codecs.open(join(out_dir, fname), 'w', 'utf-8')
        f.write(test_code)
        f.close()

    def _compile_latex(self, test_id, out_dir):
        """Compiles the LaTeX source code generating PDF.
        
        Parameters:
            test_id (int): Unique ID (usually index) of test.
            out_dir (str or unicode): Path to output directory.
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
            out_dir (str or unicode): Path to output directory.
            
        Returns:
            int: Number of pages in PDF.
        """
        f = codecs.open(join(out_dir, '{}{}.log'.format(self.config['out_file_prefix'], test_id)))
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
            in_dir (str or unicode): Path to the input directory containing the PDF files to be merged.
            out_file (str or unicode): Path to the merged PDF.
        """
        pw = PdfFileWriter()
        
        for f in sorted(listdir(in_dir)):
            if isfile(join(in_dir, f)) and regex.match('^test.*\.pdf$', f, flags=regex.IGNORECASE):
                pr = PdfFileReader(join(in_dir, f))
                pw.appendPagesFromReader(pr)
                if self.config['same_page_number'] and pr.getNumPages() < self.config['max_pages']:
                    for i in range(self.config['max_pages'] - pr.getNumPages()):
                        pw.addBlankPage()
        
        f = codecs.open(out_file, 'wb')
        pw.write(f)
        f.close()



if __name__ == "__main__":
    # MEGOLDANI:
    # ----------
    # requirements.txt
    
    mct = OneClassMultipleChoiceTest('config.json')
    
    mct.read('data_OK/t1.json',
             'data_OK/t2.json',
             'data_OK/t3.json')
      
#     mct.generate_tests(1, 'gen', 1, 1, 1)
    mct.generate_tests(1, 'gen', 2, 4, 2)
#     mct.generate_tests(1, 'gen', 40, 49, 46)
  
    mct._merge_pdfs('gen', 'gen/all.pdf')

#     mct.read('data_OK/uj.json')
#   
#     mct.generate_tests(1, 'gen', 5)
#       
#     mct._merge_pdfs('gen', 'gen/all.pdf')
    