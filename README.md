Substance Sublime
=================


This custom Sublime integration helps us to deal with our many modules.
It has a very simple git status panel which makes it easier to commit and push.
Although, being open-source it is probably not generally interesting, as it depends on our custom project
configuration files.

How to install
--------------

Go into the Sublime Application folder (location depends on operating system).

MacOSX:

    $ cd $HOME/Library/Application Support/Sublime Text 2/Packages
    $ git clone https://github.com/substance/sublime.git Substance

Linux (Ubuntu):
```
$ cd ~/.config/sublime-text-2/Packages
$ git clone https://github.com/substance/sublime.git Substance
```

Status Page
-----------

You can open a page showing the collated git status for all sub-modules using `Ctrl-Shift-s`.

Sub-modules need to be specified in a `.screwdriver/project.json`

Example:

```
{
  "modules": [
    {
      "repository": "git@github.com:substance/sublime.git",
      "folder": ".",
      "branch": "master"
    }
  ]
}
```

`repository`, where to pull the sub-module from, folder where to put the sub-module relative to the root folder, and `branch`, which branch to use.

This approach is a bit more general than with Git sub-modules, in that you still need to create a commit to change a sub-module's branch, but not for updates.
