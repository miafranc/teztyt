# teztyt

Simple one-class multiple choice test/quiz generator in Python. 
Automatic evaluation of saved filled-out forms is also possible.
The generated tests can be used for online exams but can also
be printed out.

## About

__teztyt__ is a simple _multiple choice test_ generator written in Python.
It has a simple command-line interface by which _random tests_ can be generated 
in _fillable PDF_ format.

The program generates LaTeX code, which is in turn compiled to PDF, 
therefore Python and a LaTeX distribution is needed in order to be able to use it 
(see the [Requirements](#requirements) section below).

The databases containing the problems have to be in JSON or YAML formats (see the [JSON and YAML data file formats](#json-and-yaml-data-file-formats) section
below). Since LaTeX is involved, math formulae and other LaTeX code can be used in the
problem description (question and answers), but care should be taken in correctly escaping 
the characters when using JSON (e.g. `$x \\in \\{1,2,3\\}$`). YAML, although not developed
for this purpose, is more comfortable: no LaTeX escaping is needed, has multi-line string and commenting support.

Given an _evaluation scheme_, one can also automatically grade the filled-out and then saved PDF
forms. 

The generated test can also be printed out for written exams. 
The `merge` option and the `same_page_number` configuration field can be useful in this case.

## Command-line interface

```
usage: ttt.py [-h] {gen,eval} ...

positional arguments:
  {gen,eval}  sub-command help
    gen       Generate tests
    eval      Evaluate tests

optional arguments:
  -h, --help  show this help message and exit


usage: ttt.py gen [-h] --config CONFIG --number NUMBER --files FILES
                  [FILES ...] --problems PROBLEMS --out OUT [--merge MERGE]

optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG, -c CONFIG
                        Configuration file.
  --number NUMBER, -n NUMBER
                        Number of tests to generate.
  --files FILES [FILES ...], -f FILES [FILES ...]
                        Data files. E.g. '-f d1.yaml d2.json d3.json'
  --problems PROBLEMS, -p PROBLEMS
                        Number of problems to generate from each file in form
                        of a list. E.g. '-p [3,2,1]'. If '-n 0' is used (test
                        generation using given problems), this list must
                        contain lists, e.g. [[1],[1,2],[5]]. Spaces are not
                        allowed in the above form, only if using aposthrophes
                        or quotes, e.g. "[1, 2, 3]".
  --out OUT, -o OUT     Output directory.
  --merge MERGE, -m MERGE
                        Optional, the name of the merged tests' file.


usage: ttt.py eval [-h] --config CONFIG --solutions SOLUTIONS --dir DIR --out
                   OUT

optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG, -c CONFIG
                        Configuration file.
  --solutions SOLUTIONS, -s SOLUTIONS
                        Solutions file.
  --dir DIR, -d DIR     Input directory.
  --out OUT, -o OUT     Output filename.
```

## JSON and YAML data file formats

The JSON file format containing the problems is the following:
```
{
	"unique_problem_key": {
		"P": points,
		"Q": "Question?",
		"A": {
			"a1": "1st correct answer.",
			"a2": "2nd correct answer.",
			"b": "3rd answer.",
			"c": "4th answer."
		}
	},
...
}
```
Similarly, the YAML file format is as follows:
```
unique_problem_key:
	P: points
	Q: Question?
	A:
		a1: |
			1st correct
			answer.
		a2: 2nd correct answer.
		b: 3rd answer.
		c: 4th answer.
---
...
```
The dictionary with key `"A"` can contain an arbitrary number of possible answers.
The keys are important here: all answers are considered to be correct
if the regexp `correct_key_match` (see below) matches it (in this case `"^a.*"`). 

One can create separate data files storing _different_ problems. For example, usually
one would like to generate a set of problems totaling to a given number of points (e.g. 10).
In order to do this efficiently, one can create separate JSON/YAML files grouping
problems having the same difficulty, and consequently the same points.

If using YAML, we recommend to use strings for the problem IDs, i.e. put the problem keys between
quotation marks (because in case of JSON it is of type string).

__Example__: Suppose we have 3 files: one with 1-point, another one with 2-point, and a third one
with 3-point problems. If one would like to generate a random test totaling 10 points,
could simply get 3 1-point random problems from the first file, 2 2-point problems from the second
file, and 1 3-point problem from the last file (of course, there exist other correct combinations as well).

## Solutions, evaluation

In order to be able to (automatically) evaluate the filled-out PDFs, 
the solutions (i.e. the correct answer(s) for every problem) need to be output.
The solutions are output in YAML format as follows:
```
test_id:
  problem_index:
  - [input_file_index, problem_key, points]
  - [indices_of_correct_answers]
...
```
Evaluation of the solved tests can be done using the `eval` sub-command.
The format of the YAML output file produced is the following:
```
test_id:
  text_field_1: value_1
  text_field_2: value_2
  ...
  ans:
    problem_index:
    - [answers]
    - [correct_answers]
    ...
...
```
where `answers` and `correct_answers` are lists containing the indices of the checked answers
and of the correct answers, respectively.

The evaluation scheme to be used can be set using the `evaluation` key in the config file. 
The currently built-in schemes include all-or-nothing and proportional negative marking 
(see the __Config file__ section below). It is also possible to define and use a new scheme setting `"evaluation": "my"`
and giving the evaluation function as a Python lambda function in `evaluation_function`.

## Config file

* `title`
* `subtitle`
* `correct_key_match`: Regular expression for correct keys. E.g. `"^ok.*"`.
* `pagenumbering`: `"gobble"` (no page numbers), `"arabic"`, `"roman"`.
* `points_format_string`: Format of the string showing the points for a given problem.
* `itemsep`: Since `itemize` is used for showing the possible answers, the distance between the items can be set by this.
* `baselinestretch`
* `fontsize`: Size of the base font (`extarticle` documentclass is used).
* `columns`: `"onecolumn"` or `"twocolumn"`
* `prologue`: In case other packages or settings are needed.
* `name_and_stuff`: Name and other text fields to appear at the beginning of the document; array containing the corresponding strings.
* `name_and_stuff_widths`: Widths of the text fields; array of the same size as `name_and_stuff`.
* `newtheorem_string`: Name/title of the problems, e.g. `"Problem"`.
* `problem_environment`: The LaTeX environment used for the problems. The built-in `problem` environment is recommended.
* `out_file_prefix`: Name prefix of generated files containing the tests.
* `solutions_file`: Name of the text file with the solutions.
* `pdflatex`: Name of `pdflatex` executable (usually `"pdflatex"`).
* `latex_parameters`: If additional parameters are needed; we use `"-interaction=batchmode"` to suppress messages (not the best solution though).
* `max_pages`: Maximum number of pages a test can occupy.
* `same_page_number`: Whether each test should have the same number of pages; `true` or `false`.
* `max_attempts`: Maximum number of attempts for generating a test (it might happen that a test cannot be generated
because of the maximum number of pages constraint).
* `figures_dir`: Folder of the external data used in the problems (e.g. images, tikz, etc.). The path can be used
anywhere in the body of the problems as `%figures_dir%`.
* `evaluation`: Type of evaluation. Three evaluation schemes are defined (two + user-defined):
  * `all`: All-or-nothing scheme: The points are given if and only if all the correct answers are checked.
  * `negative`: Proportional negative marking: incorrect answers are also graded by negative scores. The score is calculated as `((|intersection(C, A)| - |A - C|) / |C|) * p`, where `C` denotes the set of correct answers, `A` is the set of the answers given, and `p` is the points assigned to the problem. Thus, this scheme punishes incorrect answers by subtracting the number of wrong answers from the number of correct answers given. It is proportional, the difference of correct - incorrect answers is divided by the number of correct answers.
  * `positive`: Error-retaliatory positive marking: the same as the previous scheme, but because of the `max` function, the score will always be positive.
  * `my`: User-defined evaluation scheme. In this case the evaluation is performed evaluating the Python lambda function given by `evaluation_function` (see below).
* `evaluation_function`: The lambda evaluation function having the following 4 parameters: `c`, `a`, `r`, `p`:
  * `c`: Set of correct answers.
  * `a`: Set of the checked answers.
  * `r`: Set of the remaining (unchecked) answers.
  * `p`: Points.
For example, `lambda c, a, r, p: ((len(c.intersection(a)) - len(a.difference(c))) / float(len(c))) * p` is equivalent to the proportional negative marking scheme discussed above.

## Requirements

* Python 3.x (tested on Python 3.6.9)
  * regex https://pypi.org/project/regex/
  * PyPDF2 https://pypi.org/project/PyPDF2/
  * PyYAML https://pypi.org/project/PyYAML/
* LaTeX distribution with pdflatex
  * extsizes https://ctan.org/pkg/extsizes
  * hyperref https://ctan.org/pkg/hyperref

## API

For the API see the source code.
