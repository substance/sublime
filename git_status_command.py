import sublime, sublime_plugin
import subprocess
import os
import time
import re
from utils import read_project_config
from gitstatus import gitstatus

PACKAGE_SETTINGS = "SubstanceGit.sublime-settings"

MANAGERS = {}
NAME = ".Git.Status"

class GitStatusManager():

  def __init__(self, window, view):
    self.window = window
    self.view = view
    self.short = True
    self.settings = sublime.load_settings(PACKAGE_SETTINGS)
    self.entries = []

  def parse_status_message(self, message):
    output = []

    state = "top"

    PREFIX = '#?\s*'
    RE_STAGED_CHANGES = re.compile('^%sChanges to be committed.*$'%PREFIX)
    RE_UNSTAGED_CHANGES = re.compile('^%sChanges not staged.*$'%PREFIX)
    RE_UNTRACKED_FILES = re.compile('^%sUntracked files.*$'%PREFIX)
    RE_WS = re.compile('^%s$'%PREFIX)
    RE_COMMENT = re.compile('^%s\(.+$'%PREFIX)
    RE_COMMENT2 = re.compile('^%sno changes added to commit'%PREFIX)
    RE_STRIP_PREFIX = re.compile('^%s(.*)$'%PREFIX)

    for line in message.splitlines():
      if RE_WS.match(line):
        continue
      if RE_STAGED_CHANGES.match(line):
        state = "staged"
        output.append("")
        output.append("Staged:")
        continue
      if RE_UNSTAGED_CHANGES.match(line):
        state = "unstaged"
        output.append("")
        output.append("Unstaged:")
        continue
      if RE_UNTRACKED_FILES.match(line):
        state = "untracked"
        continue
      if RE_COMMENT.match(line) or RE_COMMENT2.match(line):
        continue

      stripped = line;
      m = RE_STRIP_PREFIX.match(line)
      if m:
        stripped = m.group(1)

      if state == "top":
        output.append(stripped)
      elif state == "untracked":
        output.append("  new:        %s"%stripped)
      else:
        output.append("  "+stripped)

    return '\n'.join(output)

  def get_status_for_folder(self, folder):
    try:
      git_command = self.settings.get('git_command')
      stat = gitstatus(folder, git_command=git_command, plain_only=True)
      if not stat:
        return None
      if self.short:
        stat['status'] = self.parse_status_message(stat['status']).strip()

      if stat['status'] == "" or stat['status'] == None:
        return None

      if self.short and 'nothing to commit' in stat['status'] and not 'Your branch is ahead' in stat['status'] and not 'Your branch is behind' in stat['status'] and not 'have diverged' in stat['status']:
        return None
      elif self.short:
        return [ folder, stat['status'] ]
      else:
        return [ folder, "sha: %s\n\n%s"%(stat['sha'], stat['status']) ]

    except OSError as err:
      print(err)
      return None

  def process_top_folder(self, folder):
    result = []

    git_folder = os.path.join(folder, ".git")
    if os.path.exists(git_folder):
      item = self.get_status_for_folder(folder)
      if not item == None:
        result.append(item)

    return result

  def get_entry(self, pos):
    pos = pos.begin()
    folder = None

    for entry in self.entries:
      folder = entry[1]
      if (entry[0] > pos):
        break
    return folder

  def update(self):

    if self.view == None:
      return

    view = self.view

    sel = view.sel()
    oldPos = sel[0]

    self.window.focus_view(self.view)

    changes = []
    for folder in self.window.folders():
      changes.extend(self.process_top_folder(folder))

    # begin edit for adding content
    view.set_read_only(False)
    edit = view.begin_edit()

    self.entries = []

    # erase existent content
    all = sublime.Region(0, view.size()+1)
    view.erase(edit, all)

    if len(changes) == 0:
      view.insert(edit, view.size(), "Everything committed. Yeaah!\n")

    else:

      for folder, output in changes:
        entry = {"folder": folder}
        view.insert(edit, view.size(), "- %s:\n"%(folder))
        view.insert(edit, view.size(), "\n")
        view.insert(edit, view.size(), "%s\n"%output)
        view.insert(edit, view.size(), "\n")
        self.entries.append([view.size(), folder])

    view.end_edit(edit)

    # freeze the file
    view.set_read_only(True)
    view.set_scratch(True)

    view.sel().clear()
    view.sel().add(oldPos)
    view.show(oldPos)

class GitStatusCommand(sublime_plugin.WindowCommand):

  def run(self):
    window = self.window
    views = filter(lambda x: x.name() == NAME, window.views())
    if len(views) == 0:
      view = window.new_file()
      view.set_name(NAME)
      view.settings().set('syntax', 'Packages/Substance/Status.tmLanguage')
    else:
      view = views[0]

    view.settings().set('command_mode', True)

    if not view.id() in MANAGERS:
      MANAGERS[view.id()] = GitStatusManager(window, view)

    MANAGERS[view.id()].update()

class GitGuiCommand(sublime_plugin.TextCommand):

  def __init__(self, view):
    self.view = view
    self.settings = sublime.load_settings(PACKAGE_SETTINGS)

  def run(self, edit):
    view = self.view

    if not view.id() in MANAGERS:
      return
    manager = MANAGERS[view.id()]

    pos = view.sel()[0]
    folder = manager.get_entry(pos)
    if folder == None:
      return

    cmd = self.settings.get("git_gui_command")
    # TODO: prepare command?

    print("Running %s in %s"%(str(cmd), folder))
    startupinfo = None
    _env = os.environ.copy()
    if os.name == 'nt':
      startupinfo = subprocess.STARTUPINFO()
      startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    if os.name == 'posix':
      _env['PATH'] = "/usr/bin:/usr/local/bin:" + _env['PATH']
    print("OS NAME: %s"%(str(os.name)))
    p = subprocess.Popen(cmd, cwd=folder, env=_env, startupinfo=startupinfo)

class GitLogCommand(sublime_plugin.TextCommand):

  def __init__(self, view):
    self.view = view
    self.settings = sublime.load_settings(PACKAGE_SETTINGS)

  def run(self, edit):
    view = self.view

    if not view.id() in MANAGERS:
      return
    manager = MANAGERS[view.id()]

    pos = view.sel()[0]
    folder = manager.get_entry(pos)
    if folder == None:
      return

    cmd = self.settings.get("git_log_command")
    # TODO: prepare command?

    print("Running %s in %s"%(str(cmd), folder))
    startupinfo = None
    if os.name == 'nt':
      startupinfo = subprocess.STARTUPINFO()
      startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    p = subprocess.Popen(cmd, cwd=folder, shell=True, startupinfo=startupinfo)

class GitCommand(sublime_plugin.TextCommand):

  def __init__(self, view):
    self.view = view
    self.settings = sublime.load_settings(PACKAGE_SETTINGS)

  def execute(self, command, folders):

    if len(folders) == 0:
      return

    git = self.settings.get("git_command")

    commands = []
    git_command = [git] + command

    for folder in folders:
      commands.append({"cmd": git_command, "working_dir": folder})

    self.view.window().run_command("batch_exec", {
      "commands": commands
      #"callbackCmd": "git_status"
    })

  def run(self, edit, command, all=False):
    view = self.view

    if not view.id() in MANAGERS:
      return
    manager = MANAGERS[view.id()]

    pos = view.sel()[0]

    folders = []
    if all:
      config = manager.load_config()
      for topFolder in config:
        for folder in config[topFolder]["data"].keys():
          folders.append(folder)

    else:
      folder = manager.get_entry(pos)
      if folder != None:
        folders.append(folder)

    self.execute(command, folders)

class GitPush(sublime_plugin.TextCommand):

  def __init__(self, view):
    self.view = view
    self.settings = sublime.load_settings(PACKAGE_SETTINGS)

  def get_selected_module_config(self, project_data, folder):
    for topFolder in project_data:
      if folder in project_data[topFolder]["data"]:
        return project_data[topFolder]["data"][folder]
    return None

  def run(self, edit, command):
    view = self.view

    if not view.id() in MANAGERS:
      return
    manager = MANAGERS[view.id()]

    pos = view.sel()[0]
    folder = manager.get_entry(pos)
    config = manager.load_config()

    repo = self.get_selected_module_config(config, folder)

    if repo != None:
      git = self.settings.get("git_command")
      cmd = [git] + ["push", "origin", repo["branch"]];
      commands = [{"cmd": cmd, "working_dir": repo["path"]}]
      self.view.window().run_command("batch_exec", {
        "commands": commands,
        "callbackCmd": "git_status"
      })

class GitToggleStatusCommand(sublime_plugin.TextCommand):

  def run(self, edit):

    if not self.view.id() in MANAGERS:
      return
    manager = MANAGERS[self.view.id()]

    manager.short = not manager.short
    #self.view.window().run_command("git_status")
    manager.update()

class GitCommitListener(sublime_plugin.EventListener):

  def on_query_context(self, view, key, value, operand, match_all):
    if NAME == view.name() and key == "git_status":
      return True
    return None

  def on_activated(self, view):

    if not view.id() in MANAGERS:
      return

    manager = MANAGERS[view.id()]
    manager.update()
