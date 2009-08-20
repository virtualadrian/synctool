#! /usr/bin/env python
#
#	synctool_core.py	WJ109
#
#	The core holds the 'overlay' function
#

import synctool_config
from synctool_lib import verbose,stdout,stderr

import os
import sys
import string


GROUPS = None
ALL_GROUPS = None

# treewalk() sets the current source dir (used for error reporting from filter() functions)
CURR_DIR = None

# array of .post scripts in current dir
POST_SCRIPTS = []

# this is an enum; return values for dir_has_group_ext()
DIR_EXT_NO_GROUP = 1
DIR_EXT_IS_GROUP = 2
DIR_EXT_INVALID_GROUP = 3

# used for find_synctree()
FIND_SYNCTREE = None
FOUND_SYNCTREE = None



def file_has_group_ext(filename):
	'''filter function; see if the group extension applies'''

	global POST_SCRIPTS

	arr = string.split(filename, '.')

	if len(arr) < 2:
		stderr('no group extension on %s/%s, skipped' % (CURR_DIR, filename))
		return False

	group = arr[-1]

# check for .post script; keep it for now
# .post scripts are processed in overlay_callback()
	if group == 'post':
		POST_SCRIPTS.append(filename)
		return False

	if group[0] != '_':
		stderr('no underscored group extension on %s/%s, skipped' % (CURR_DIR, filename))
		return False

	group = group[1:]
	if not group:
		stderr('no group extension on %s/%s, skipped' % (CURR_DIR, filename))
		return False

	if group in GROUPS:				# got a file for one of our groups
		return True

	if not group in ALL_GROUPS:
		stderr('unknown group on file %s/%s, skipped' % (CURR_DIR, filename))
		return False

	verbose('%s/%s is not one of my groups, skipped' % (CURR_DIR, filename))
	return False


def dir_has_group_ext(dirname):
	'''see if the group extension on a directory applies'''
	'''NB. this is not a filter() function'''

	arr = string.split(dirname, '.')

	if len(arr) < 2:
		return DIR_EXT_NO_GROUP

	group = arr[-1]

	if group[0] != '_':
		return DIR_EXT_NO_GROUP

	group = group[1:]
	if not group:
		return DIR_EXT_NO_GROUP

	if group in GROUPS:				# got a directory for one of our groups
		return DIR_EXT_IS_GROUP

	if not group in ALL_GROUPS:
		stderr('unknown group on directory %s/%s/, skipped' % (CURR_DIR, dirname))
		return DIR_EXT_INVALID_GROUP

	verbose('%s/%s/ is not one of my groups, skipped' % (CURR_DIR, dirname))
	return DIR_EXT_INVALID_GROUP


def filter_overrides(files):
	'''return a dict with {base filename:extension}'''

	stripped = {}

	for filename in files:
		arr = string.split(filename, '.')

		if len(arr) < 2:
			raise RuntimeError, 'bug! There should have been a good valid extension on this filename: %s' % filename

		stripped_name = string.join(arr[:-1], '.')
		ext = arr[-1]

		if ext[0] != '_':
			raise RuntimeError, 'bug! The extension should have started with an underscore: %s' % filename

		ext = ext[1:]

		if not stripped.has_key(stripped_name):
			stripped[stripped_name] = ext
		else:
# choose most important group
# the most important group is the one that is listed earlier in the GROUPS array, so it has a smaller index
			a = GROUPS.index(ext)
			b = GROUPS.index(stripped[stripped_name])
			if a < b:
				verbose('%s/%s._%s overrides %s._%s' % (CURR_DIR, stripped_name, ext, stripped_name, stripped[stripped_name]))
				stripped[stripped_name] = ext

	return stripped


def overlay_callback(src_dir, dest_dir, filename, ext):
	'''compare files and run post-script if needed'''

# TODO efficiently handle .post scripts
#	if filename[-5:] == 'post': return True

	src = os.path.join(src_dir, '%s._%s' % (filename, ext))
	dest = os.path.join(dest_dir, filename)

	print 'TD cmp %s <-> %s' % (src, dest)

#
#	TODO .post scripts worden op Huygens op een andere manier gebruikt;
#
#	bijv. scr1.post._computenodes
#
#	if filename in POST_SCRIPTS:
#		...
#
#

	post_script = os.path.join(src_dir, '%s.post' % filename)
	if os.path.exists(post_script):
		print 'TD on_update', post_script

	return True


def treewalk(src_dir, dest_dir, callback):
	'''walk the repository tree, either under overlay/, delete/, or tasks/'''
	'''and call the callback function for relevant files'''

	global CURR_DIR

	CURR_DIR = src_dir				# stupid global for filter() functions

	try:
		files = os.listdir(src_dir)
	except OSError, err:
		stderr('error: %s' % err)
		return

	all_dirs = []
	group_ext_dirs = []

	n = 0
	while n < len(files):
		filename = files[n]
		full_path = os.path.join(src_dir, filename)

# do not follow symlinked directories
		if os.path.islink(full_path):
			n = n + 1
			continue

		if os.path.isdir(full_path):

# it's a directory

# remove all dirs from files[] and put them in all_dirs[] or group_ext_dirs[]

			files.remove(filename)

# check ignore_dotdirs
			if filename[0] == '.' and synctool_config.IGNORE_DOTDIRS:
				continue

			if string.find(filename, '_') >= 0:				# first a quick check for group extension
				ret = dir_has_group_ext(filename)

				if ret == DIR_EXT_NO_GROUP:
					all_dirs.append(filename)

				elif ret == DIR_EXT_IS_GROUP:
					group_ext_dirs.append(filename)

				elif ret == DIR_EXT_INVALID_GROUP:
					pass

				else:
					raise RuntimeError, 'bug: unknown return value %d from dir_has_group_ext()' % ret
			else:
				all_dirs.append(filename)

			continue

# check ignore_dotfiles
		else:
			if filename[0] == '.' and synctool_config.IGNORE_DOTFILES:
				files.remove(filename)
				continue

		n = n + 1

# handle all files with group extensions that apply
	files = filter(file_has_group_ext, files)

	if len(files) > 0:
		stripped = filter_overrides(files)

		for filename in stripped.keys():
			if filename in synctool_config.IGNORE_FILES:
				continue

			if not callback(src_dir, dest_dir, filename, stripped[filename]):
				return

# now handle directories

# recursively visit all directories
	for dirname in all_dirs:
		if dirname in synctool_config.IGNORE_FILES:
			continue

		new_src_dir = os.path.join(src_dir, dirname)
		new_dest_dir = os.path.join(dest_dir, dirname)
		treewalk(new_src_dir,  new_dest_dir, callback)

# visit all directories with group extensions that apply
	if len(group_ext_dirs) > 0:
		stripped = filter_overrides(group_ext_dirs)

		for dirname in stripped.keys():
			if dirname in synctool_config.IGNORE_FILES:
				continue

			new_src_dir = os.path.join(src_dir, '%s._%s' % (dirname, stripped[dirname]))
			new_dest_dir = os.path.join(dest_dir, dirname)
			treewalk(new_src_dir, new_dest_dir, callback)


def overlay():
	'''run the overlay function'''

	base_path = os.path.join(synctool_config.MASTERDIR, 'overlay')
	if not os.path.isdir(base_path):
		stderr('error: $masterdir/overlay/ not found')
		return

	treewalk(base_path, '/', overlay_callback)


def find_callback(src_dir, dest_dir, filename, ext):
	'''callback function for find_synctree()'''

	global FOUND_SYNCTREE

	dest = os.path.join(dest_dir, filename)

	if dest == FIND_SYNCTREE:
		FOUND_SYNCTREE = os.path.join(src_dir, '%s._%s' % (filename, ext))
		return False			# terminate the treewalk()

	return True


def find_synctree(subdir, pathname):
	'''find the source of a full destination path'''

	global FIND_SYNCTREE, FOUND_SYNCTREE

	base_path = os.path.join(synctool_config.MASTERDIR, subdir)
	if not os.path.isdir(base_path):
		stderr('error: $masterdir/%s/ not found' % subdir)
		return

	FIND_SYNCTREE = pathname
	FOUND_SYNCTREE = None

	treewalk(base_path, '/', find_callback)

	if not FOUND_SYNCTREE:
		print 'TD find_synctree(): %s not found' % pathname
	else:
		print 'TD %s <-> %s' % (FOUND_SYNCTREE, pathname)

	return FOUND_SYNCTREE


def read_config():
	global GROUPS, ALL_GROUPS

	synctool_config.read_config()
	synctool_config.add_myhostname()

	if synctool_config.NODENAME == None:
		stderr('unable to determine my nodename, please check %s' % synctool_config.CONF_FILE)
		sys.exit(1)

#	if synctool_config.NODENAME in synctool_config.IGNORE_GROUPS:
#		stderr('%s: node %s is disabled in the config file' % (synctool_config.CONF_FILE, synctool_config.NODENAME))
#		sys.exit(1)

	synctool_config.remove_ignored_groups()
	GROUPS = synctool_config.get_my_groups()
	print 'TD GROUPS ==', GROUPS
	ALL_GROUPS = synctool_config.make_all_groups()


if __name__ == '__main__':
	read_config()
	overlay()

	print
	find_synctree('overlay', '/usr/sara/acct/sbin/accup')
	find_synctree('tasks', '/scr1')


# EOB
