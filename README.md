# nettool.py
Reimplementation of the Black Hat Python script mentioned in chapter 2 to work with
Python 3. Will add to this as I work through the book. 

## Building
At the moment, it's all vanilla python and should run perfectly fine without
any extra installation

## Running
As explained in the book, use `python nettool.py`

The following switches and inputs are available 
```
-p --port       | Target port
-t --target     | Target host
-c --command    | Used with -l flag, start a command server
-e --echo       | Used with -l flag, start an echo server
-u --upload     | Used with -l flag, start an upload server
-l --listen     | Start a server
```