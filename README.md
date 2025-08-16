# File-Sorter
Take ref file, find sibling files in subfolder(s), move ref file

# What does it do

Let's say you have these 4 files:

Degree.preview.png

Degree.pdf

Degree.docx

Degree.dong

And you starting sorting your files. You're left with "Degree.pdf" in the main folder, but you forgot in which subfolder you sorted the other 3 files.

The script will look for the siblings of "Degree.pdf" in all available subfolders. When it finds them, it gives you the option to move the pdf there.

It also includes a nifty Orphan search to automate that even more; makes the script look for lonesome files that have siblings in subfolders, which you can then move there with another button click.

You also have the option to skip, rename, or overwrite in case of conflicts.

And you can simply write which file extensions the script should consider.

# Install

1. If not already installed, [install python](https://www.python.org/downloads/)
2. Download the script from here
3. Slap the script into a folder
4. Open Terminal
5. run ```python lora_sorter_gui_enhanced_v15.py``` (or whatever you rename the script to)

# Run

1. Pick a file you want to move
2. Pick a base folder that contains the subfolders the script should look through
3. Update the file extensions it should consider (e.g. .docx,.txt,.png)
4. Click "Preview Matches"
5. If you're satisfied, click "Move"

# Help

I'm not a coder, can't really help ya. This thing is completely coded by ChatGPT, so just give it to Chat and ask it for help if you run into any issues.
