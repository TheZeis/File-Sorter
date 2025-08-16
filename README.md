# File-Sorter
Take ref file, find sibling files in subfolder(s), move ref file

Let's say you have these 4 files:

Degree.png
Degree.pdf
Degree.docx
Degree.dong

And you starting sorting your files. You're left with "Degree.pdf" in the main folder, but you forgot in which subfolder you sorted the other 3 files.

The script will look for the siblings of "Degree.pdf" in all available subfolders. When it finds them, it gives you the option to move the pdf there.

It also includes a nifty Orphan search to automate that even more; makes the script look for lonesome files that have siblings in subfolders, which you can then move there with another button click.

You also have the option to skip, rename, or overwrite in case of conflicts.

And you can simply write which file extensions the script should consider.
