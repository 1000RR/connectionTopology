Switch connection topology explorer for guitar pickup connection scheme visualization, vibe-coded in Python by Gemini 2.5.

data.csv:
can contain
- any number of <STRING/CHAR>:<COLS>x<ROWS> - definition of a pinout surface, like a switch. numbering begins at the top left with pin 1, and goes right, then wraps until pin COLS*ROWS
- 1 of e2epins:<name-of-pin>,<name-of-pin-2>..... - pins to show in the end to end topology
- tuples of pins of <STRING><NUMBER>, or more generically, <pin-name>
- comment lines starting with the # char

state files (.csv)
that contain k n-tuples of numbers in the following format, tuple per line: <number>, <number2>, <number3>,...

Running
Execute with python3 with the number of parameters being equal to the number of disparate switch definitions.
Each param should be the extension-free name of the csv file containing the tuples reflecting the interconnected pins of that switch.

For the case of
A:3x4
B:4x8

The correct way to execute is ```python switchTopology.py left right```

where left.csv:
#DPDT switch set to left
1,2
4,5

and right.csv:
#DPDT switch set to right
2,3
5,6
