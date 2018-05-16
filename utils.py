import re
import json
import os
import types
from .gitstatus import git_repo_info

# Converts a dict into a dynamic object
class DictObject(dict):

  def __init__(self, d):
    self.update(d)

  def __getattr__(self, name):
    if not self.has_key(name):
      return None

    return self[name]

def as_object(d):
  if type(d) is types.DictType:
    d = DictObject(d)
    for key in d.iterkeys():
      d[key] = as_object(d[key])
  elif type(d) is types.ListType or type(d) is types.TupleType:
    for idx,elem in enumerate(d):
      d[idx] = as_object(d[idx])

  return d

def read_json(filename):
  with open(filename, 'r') as f:
    try:
      data = f.read()
      return json.JSONDecoder().decode(data)
    except ValueError as ve:
      print("Could not parse file %s"%filename)
      print(ve)
      return None

REPO_ID = "([a-zA-Z0-9_-]+)"
GIT_REPO_EXPRESSION = re.compile(REPO_ID+"/"+REPO_ID+"(?:.git)?"+"(?:#"+REPO_ID+")?")
SHA1_EXPRESSION = re.compile("[a-fA-F0-9]{40}");

PACKAGE_FILE = "package.json"
def package_file(root):
  return os.path.join(root, PACKAGE_FILE)


def find_git_repos(root, config, git_command):
  package_config = read_json(package_file(root))
  deps = {}
  if "dependencies" in package_config:
    for name, version in package_config["dependencies"].iteritems():
      deps[name] = version
  if "devDependencies" in package_config:
    for name, version in package_config["devDependencies"].iteritems():
      deps[name] = version
  for name, version in deps.iteritems():
    match = GIT_REPO_EXPRESSION.match(version)
    if match:
      module_dir = os.path.join(root, 'node_modules', name);
      # only take over modules with a non SHA-1 version
      if os.path.exists(os.path.join(module_dir, '.git')):
        repo = git_repo_info(module_dir, git_command=git_command)
        repo["path"] = module_dir
        config[module_dir] = repo
        find_git_repos(module_dir, config, git_command)

def read_project_config(root, git_command):
  config = {}
  repo = git_repo_info(root, git_command=git_command)
  repo["path"] = root
  find_git_repos(root, config, git_command)
  print(config)
  return config
