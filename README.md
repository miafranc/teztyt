# teztyt

Simple one-class multiple choice test generator in Python.

## About

## Requirements

## JSON file format

The input file format containing the problems has to be the following:
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
The dictionary with key `"A"` can contain an arbitrary number of possible answers.
The structure of the keys are important here: all answers are considered to be correct
if the regexp `correct_key_match` (see below) matches it (in this case `"^a.*"`). 

One can create separate data files storing _different_ problems. For example, usually
one would like to generate a set of problems totaling to a given number of points (e.g. 10).
In order to do this efficiently, one can create separate JSON files grouping
problems having the same difficulty, and consequently the same points.

__Example__: Suppose we have 3 files: one with 1-point, another one with 2-point and a third one
with 3-point problems. If one would like to generate a random test totaling to 10 points,
could simply get 3 1-point random problems from the first file, 2 2-point problems from the second
file and 1 3-point problem from the last file (of course, there are other correct combinations).

## Command-line interface



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
problem_index (data_file_index/problem_key): correct_answer_index_1 [, correct_answer_index_2, ...]
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

## API

For the API see the source code.
