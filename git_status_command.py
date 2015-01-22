import sublime, sublime_plugin
import subprocess
import os
import time
import re
from utils import read_config, MODULES_CONFIG, MODULES_CONFIG_LEGACY
from gitstatus import gitstatus

PACKAGE_SETTINGS = "SubstanceGit.sublime-settings"

MANAGERS = {}
NAME = ".Git.Status"

class GitStatusManager():

  def __init__(self, window, view):
    self.window = window
    self.view = view
    self.config = {}
    self.short = True
    self.settings = sublime.load_settings(PACKAGE_SETTINGS)
    self.entries = []

  def get_status_for_folder(self, folder):

    try:
      git_command = self.settings.get('git_command')
      stat = gitstatus(folder, git_command=git_command, plain_only=True)

      if not stat:
        return None

      print('Status for %s: %s'%(folder, stat))

      # if self.short:
      #   if stat['clean'] and not stat['ahead'] and not stat['behind']:
      #     return None
      #   else:
      #     s = []
      #     s.append("Remote: %s, Branch: %s"%(stat['remote'], stat['branch']))
      #     if stat['ahead']:
      #       s.append("%s commits ahead"%(stat['ahead']))
      #     if stat['behind']:
      #       s.append("%s commits behind"%(stat['behind']))

      #     return [ folder, '\n'.join([', '.join(s), stat['status']]) ]
      # else:
      if self.short and 'nothing to commit' in stat['status'] and not 'Your branch is ahead' in stat['status'] and not 'Your branch is behind' in stat['status']:
          return None
      else:
        return [ folder, stat['status'] ]

    except OSError as err:
      print(err)
      return None

  def process_top_folder(self, folder):
    result = []

    item = self.get_status_for_folder(folder)
    if not item == None:
      result.append(item)

    if folder in self.config:
      config = self.config[folder]
      for m in config['data'].modules:
        module_dir = os.path.join(folder, m.folder)
        if not os.path.exists(module_dir):
          continue
        item = self.get_status_for_folder(module_dir)
        if not item == None:
          result.append(item)

    return result

  def load_config(self):
    # Check if we have to reload the config file
    for folder in self.window.folders():
      config_file = os.path.join(folder, MODULES_CONFIG)
      if not os.path.exists(config_file):
        config_file = os.path.join(folder, MODULES_CONFIG_LEGACY)
        if os.path.exists(config_file):
          print('DEPRECATED: please move "project.json" to ".screwdriver/project.json"')
        else:
          continue

      if not folder in self.config or self.config[folder]['timestamp'] < os.path.getmtime(config_file):
        print("Loading config: %s"%config_file)
        self.config[folder] = {
          "timestamp": os.path.getmtime(config_file),
          "data": read_config(config_file)
        }

    return self.config

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

    self.load_config()
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
    if os.name == 'nt':
      startupinfo = subprocess.STARTUPINFO()
      startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    p = subprocess.Popen(cmd, cwd=folder, startupinfo=startupinfo)

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
        for m in config[topFolder]['data'].modules:
          folders.append(os.path.join(topFolder, m.folder))

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
      if folder.startswith(topFolder):
        folder = folder[len(topFolder)+1:]
        project_config = project_data[topFolder]["data"]
        found = [m for m in project_config["modules"] if m["folder"] == folder]
        if len(found) != 1:
          return None
        return {
          "root_dir": topFolder,
          "module": found[0]
        };

    return None

  def run(self, edit, command):
    view = self.view

    if not view.id() in MANAGERS:
      return
    manager = MANAGERS[view.id()]

    pos = view.sel()[0]
    folder = manager.get_entry(pos)
    config = manager.load_config()

    module_config = self.get_selected_module_config(config, folder)

    if module_config != None:
      module = module_config["module"]
      git = self.settings.get("git_command")
      cmd = [git] + ["push", "origin", module["branch"]];
      commands = [{"cmd": cmd, "working_dir": os.path.join(module_config["root_dir"], module["folder"])}]
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
