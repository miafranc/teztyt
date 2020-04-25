# teztyt

Simple one-class multiple choice test generator in Python.

## About

__teztyt__ is a very simple _multiple choice test_ generator written in Python.
It has a simple command-line interface by which _random tests_ can be generated 
in _fillable PDF_ format. 

The program generates LaTeX code, which is in turn compiled to PDF, 
therefore Python and a LaTeX distribution is needed in order to be able to use it
(see the __Requirements__ section below).

The databases containing the problems have to be in JSON format (see the __JSON file format__ section
below). Since LaTeX is involved, math formulae and other LaTeX code can be used in the
problem description (question and answers), but care should be taken in correctly escaping 
the characters (e.g. `$x \\in \\{1,2,3\\}$`).

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
                        Data files. E.g. '-f d1.json d2.json d3.json'
  --problems PROBLEMS, -p PROBLEMS
                        Number of problems to generate from each file in form
                        of a list. E.g. '-p [3, 2, 1]'. If '-n 0' is used
                        (test generation using given problems), this list must
                        contain lists, e.g. [[1], [1,2], [5]].
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

## JSON file format

The input file format containing the problems has to be the following:
```
{
	"unique_integer_problem_key": {
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
The dictionary with key `"A"` can contain an arbitrary number of possible answers.
The keys are important here: all answers are considered to be correct
if the regexp `correct_key_match` (see below) matches it (in this case `"^a.*"`). 

One can create separate data files storing _different_ problems. For example, usually
one would like to generate a set of problems totaling to a given number of points (e.g. 10).
In order to do this efficiently, one can create separate JSON files grouping
problems having the same difficulty, and consequently the same points.

__Example__: Suppose we have 3 files: one with 1-point, another one with 2-point and a third one
with 3-point problems. If one would like to generate a random test totaling to 10 points,
could simply get 3 1-point random problems from the first file, 2 2-point problems from the second
file and 1 3-point problem from the last file (of course, there are other correct combinations).

## Evaluation

It is possible to also evaluate the solved tests (see the `eval` sub-command above).



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
* `newtheorem_string`: Name of the problems, e.g. `"Problem"`.
* `problem_environment`: The LaTeX environment used for the problems. The built-in `problem` environment is recommended.
* `out_file_prefix`: Name prefix of generated files containing the tests.
* `solutions_file`: Name of the text file with the solutions. Format of its content: 
```
===
test_id:
problem_index (data_file_index/problem_key/points): correct_answer_index_1 [, correct_answer_index_2, ...]
...
===
...
```	
* `pdflatex`: Name of `pdflatex` executable (usually `"pdflatex"`).
* `latex_parameters`: If additional parameters are needed; we use `"-interaction=batchmode"` to suppress messages (not the best solution though).
* `max_pages`: Maximum number of pages a test can occupy.
* `same_page_number`: Whether each test should have the same number of pages; `true` or `false`.
* `max_attempts`: Maximum number of attempts for generating a test (it might happen that a test cannot be generated
because of the maximum number of pages constraint).
* `figures_dir`: Folder of the external data used in the problems (e.g. images, tikz, etc.). The path can be used
anywhere in the body of the problems as `%figures_dir%`.
* `evaluation`: Type of evaluation. Three evaluation schemes are defined:
  * `all`: All-or-nothing scheme: The points are given if and only if all the correct answers are checked.
  * `negative`: Proportional negative marking: Incorrect answers are also graded by negative scores. The score is calculated as `((|C /\ A| - |A - C|) / |A|) * p`, where `C` denotes the set of correct answers, `A` is the set of the answers given and `p` is the points assigned to the problem.
  * `semi-negative`: Proportional semi-negative marking: Incorrect answers are also graded by negative scores, but scores obtained for a problem always positive. The score is calculated as `max(0, ((|C /\ A| - |A - C|) / |A|) * p)`, where `C` denotes the set of correct answers, `A` is the set of the answers given and `p` is the points assigned to the problem.
  * `my`: User-defined evaluation scheme. In this case the evaluation is performed evaluating the Python lambda function given by `evaluation_function` (see below).
* `evaluation_function`: The lambda evaluation function having the following 4 parameters: `c`, `a`, `r`, `p`:
  * `c`: List of correct answers.
  * `a`: List of the checked answers.
  * `r`: List of the remaining (unchecked) answers.
  * `p`: Points.  

## Requirements

* Python 3.x (tested on Python 3.6.9)
  * regex https://pypi.org/project/regex/
  * PyPDF2 https://pypi.org/project/PyPDF2/
* LaTeX distribution with pdflatex
  * extsizes https://ctan.org/pkg/extsizes
  * hyperref https://ctan.org/pkg/hyperref

## API

For the API see the source code.
