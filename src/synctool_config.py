#! /usr/bin/env python
#
#	synctool-config	WJ109
#
#   synctool Copyright 2013 Walter de Jong <walter@heiho.net>
#
#   synctool COMES WITH NO WARRANTY. synctool IS FREE SOFTWARE.
#   synctool is distributed under terms described in the GNU General Public
#   License.
#

import os
import sys
import string
import getopt
import errno

import synctool.config
import synctool.configparser
from synctool.configparser import stderr
import synctool.param

ACTION = 0
ACTION_OPTION = None
ARG_NODENAMES = None
ARG_GROUPS = None
ARG_CMDS = None

# these are enums for the "list" command-line options
ACTION_LIST_NODES = 1
ACTION_LIST_GROUPS = 2
ACTION_NODES = 3
ACTION_GROUPS = 4
ACTION_CMDS = 5
ACTION_NUMPROC = 6
ACTION_VERSION = 7
ACTION_PREFIX = 8
ACTION_LOGFILE = 9
ACTION_NODENAME = 10
ACTION_LIST_DIRS = 11
ACTION_PKGMGR = 12

# optional: do not list hosts/groups that are ignored
OPT_FILTER_IGNORED = False
# optional: list ipaddresses of the selected nodes
OPT_IPADDRESS = False
# optional: list hostnames of the selected nodes
OPT_HOSTNAME = False
# optional: list rsync yes/no qualifier
OPT_RSYNC = False


def list_all_nodes():
	nodes = synctool.config.get_all_nodes()
	nodes.sort()

	for node in nodes:
		ignored = set(synctool.config.get_groups(node))
		ignored &= synctool.param.IGNORE_GROUPS

		if OPT_FILTER_IGNORED and len(ignored) > 0:
			continue

		if OPT_IPADDRESS:
			node += ' ' + synctool.config.get_node_ipaddress(node)

		elif OPT_HOSTNAME:
			node += ' ' + synctool.config.get_node_hostname(node)

		elif OPT_RSYNC:
			if node in synctool.param.NO_RSYNC:
				node += ' no'
			else:
				node += ' yes'

		if len(ignored) > 0:
			node += ' (ignored)'

		print node


def list_all_groups():
	groups = synctool.param.GROUP_DEFS.keys()
	groups.sort()

	for group in groups:
		if OPT_FILTER_IGNORED and group in synctool.param.IGNORE_GROUPS:
			continue

		if group in synctool.param.IGNORE_GROUPS:
			group += ' (ignored)'

		print group


def list_nodes(nodenames):
	groups = []

	for node in nodenames:
		if not synctool.param.NODES.has_key(node):
			stderr("no such node '%s' defined" % node)
			sys.exit(1)

		if OPT_IPADDRESS or OPT_HOSTNAME or OPT_RSYNC:
			out = ''

			if OPT_IPADDRESS:
				out += ' ' + synctool.config.get_node_ipaddress(node)

			if OPT_HOSTNAME:
				out += ' ' + synctool.config.get_node_hostname(node)

			if OPT_RSYNC:
				if node in synctool.param.NO_RSYNC:
					out += ' no'
				else:
					out += ' yes'

			print out[1:]

		else:
			for group in synctool.config.get_groups(node):
				# extend groups, but do not have duplicates
				if not group in groups:
					groups.append(group)

	# group order is important, so don't sort
	# however, when you list multiple nodes at once, the groups will have
	# been added to the end
	# So the order is important, but may be incorrect when listing
	# multiple nodes at once
#	groups.sort()

	for group in groups:
		if OPT_FILTER_IGNORED and group in synctool.param.IGNORE_GROUPS:
			continue

		if group in synctool.param.IGNORE_GROUPS:
			group += ' (ignored)'

		print group


def list_nodegroups(groups):
	groups = set(groups)

	unknown = groups - synctool.param.ALL_GROUPS
	for g in unknown:
		stderr("no such group '%s' defined" % g)
		sys.exit(1)

	arr = list(synctool.config.get_nodes_in_groups(groups))
	arr.sort()

	for node in arr:
		ignored = set(synctool.config.get_groups(node))
		ignored &= synctool.param.IGNORE_GROUPS

		if OPT_FILTER_IGNORED and len(ignored) > 0:
			continue

		if OPT_IPADDRESS:
			node += ' ' + synctool.config.get_node_ipaddress(node)

		elif OPT_HOSTNAME:
			node += ' ' + synctool.config.get_node_hostname(node)

		elif OPT_RSYNC:
			if node in synctool.param.NO_RSYNC:
				node += ' no'
			else:
				node += ' yes'

		if len(ignored) > 0:
			node += ' (ignored)'

		print node


def list_commands(cmds):
	'''display command setting'''

	for cmd in cmds:
		if cmd == 'diff':
			(ok, a) = synctool.config.check_cmd_config('diff_cmd',
						synctool.param.DIFF_CMD)
			if ok:
				print synctool.param.DIFF_CMD

		if cmd == 'ping':
			(ok, a) = synctool.config.check_cmd_config('ping_cmd',
						synctool.param.PING_CMD)
			if ok:
				print synctool.param.PING_CMD

		elif cmd == 'ssh':
			(ok, a) = synctool.config.check_cmd_config('ssh_cmd',
						synctool.param.SSH_CMD)
			if ok:
				print synctool.param.SSH_CMD

		elif cmd == 'scp':
			(ok, a) = synctool.config.check_cmd_config('scp_cmd',
						synctool.param.SCP_CMD)
			if ok:
				print synctool.param.SCP_CMD

		elif cmd == 'rsync':
			(ok, a) = synctool.config.check_cmd_config('rsync_cmd',
						synctool.param.RSYNC_CMD)
			if ok:
				print synctool.param.RSYNC_CMD

		elif cmd == 'synctool':
			(ok, a) = synctool.config.check_cmd_config('synctool_cmd',
						synctool.param.SYNCTOOL_CMD)
			if ok:
				print synctool.param.SYNCTOOL_CMD

		elif cmd == 'pkg':
			(ok, a) = synctool.config.check_cmd_config('pkg_cmd',
						synctool.param.PKG_CMD)
			if ok:
				print synctool.param.PKG_CMD

		else:
			stderr("no such command '%s' available in synctool" % cmd)


def list_dirs():
	'''display directory settings'''

	print 'rootdir', synctool.param.ROOTDIR
	print 'overlaydir', synctool.param.OVERLAY_DIR
	print 'deletedir', synctool.param.DELETE_DIR
	print 'scriptdir', synctool.param.SCRIPT_DIR
	print 'tempdir', synctool.param.TEMP_DIR


def set_action(a, opt):
	global ACTION, ACTION_OPTION

	if ACTION > 0:
		stderr('options %s and %s can not be combined' % (ACTION_OPTION, opt))
		sys.exit(1)

	ACTION = a
	ACTION_OPTION = opt


def usage():
	print 'usage: %s [options] [<argument>]' % os.path.basename(sys.argv[0])
	print 'options:'
	print '  -h, --help               Display this information'
	print '  -c, --conf=dir/file      Use this config file'
	print ('                           (default: %s)' %
		synctool.param.DEFAULT_CONF)

	print '''  -l, --list-nodes         List all configured nodes
  -L, --list-groups        List all configured groups
  -n, --node=nodelist      List all groups this node is in
  -g, --group=grouplist    List all nodes in this group
  -i, --ipaddress          List selected nodes' IP address
  -H, --hostname           List selected nodes' hostname
  -r, --rsync              List selected nodes' rsync qualifier
  -f, --filter-ignored     Do not list ignored nodes and groups

  -C, --command=command    Display setting for command
  -P, --package-manager    Display configured package manager
  -p, --numproc            Display numproc setting
  -d, --list-dirs          Display directory settings
      --prefix             Display installation prefix
      --logfile            Display configured logfile
      --nodename           Display my nodename
  -v, --version            Display synctool version

A node/group list can be a single value, or a comma-separated list
A command is a list of these: diff,ping,ssh,scp,rsync,synctool,pkg
'''


def get_options():
	global ARG_NODENAMES, ARG_GROUPS, ARG_CMDS
	global OPT_FILTER_IGNORED, OPT_IPADDRESS, OPT_HOSTNAME, OPT_RSYNC

	progname = os.path.basename(sys.argv[0])

	if len(sys.argv) <= 1:
		usage()
		sys.exit(1)

	try:
		opts, args = getopt.getopt(sys.argv[1:], 'hc:lLn:g:iHrfC:Ppdv',
			['help', 'conf=', 'list-nodes', 'list-groups', 'node=', 'group=',
			'ipaddress', 'hostname', 'rsync', 'filter-ignored',
			'command', 'package-manager', 'numproc', 'list-dirs',
			'prefix', 'logfile', 'nodename', 'version'])

	except getopt.error, (reason):
		print
		print '%s: %s' % (progname, reason)
		print
		usage()
		sys.exit(1)

	except getopt.GetoptError, (reason):
		print
		print '%s: %s' % (progname, reason)
		print
		usage()
		sys.exit(1)

	except:
		usage()
		sys.exit(1)

	if args != None and len(args) > 0:
		stderr('error: excessive arguments on command-line')
		sys.exit(1)

	errors = 0

	for opt, arg in opts:
		if opt in ('-h', '--help', '-?'):
			usage()
			sys.exit(1)

		if opt in ('-c', '--conf'):
			synctool.param.CONF_FILE = arg
			continue

		if opt in ('-l', '--list-nodes'):
			set_action(ACTION_LIST_NODES, '--list-nodes')
			continue

		if opt in ('-L', '--list-groups'):
			set_action(ACTION_LIST_GROUPS, '--list-groups')
			continue

		if opt in ('-n', '--node'):
			set_action(ACTION_NODES, '--node')
			ARG_NODENAMES = string.split(arg, ',')
			continue

		if opt in ('-g', '--group'):
			set_action(ACTION_GROUPS, '--group')
			ARG_GROUPS = string.split(arg, ',')
			continue

		if opt in ('-i', 'ipaddress'):
			OPT_IPADDRESS = True
			continue

		if opt in ('-H', '--hostname'):
			OPT_HOSTNAME = True
			continue

		if opt in ('-r', '--rsync'):
			OPT_RSYNC = True
			continue

		if opt in ('-f', '--filter-ignored'):
			OPT_FILTER_IGNORED = True
			continue

		if opt in ('-C', '--command'):
			set_action(ACTION_CMDS, '--command')
			ARG_CMDS = string.split(arg, ',')
			continue

		if opt in ('-P', '--package-manager'):
			set_action(ACTION_PKGMGR, '--package-manager')
			continue

		if opt in ('-p', '--numproc'):
			set_action(ACTION_NUMPROC, '--numproc')
			continue

		if opt in ('-d', '--list-dirs'):
			set_action(ACTION_LIST_DIRS, '--list-dirs')
			continue

		if opt == '--prefix':
			set_action(ACTION_PREFIX, '--prefix')
			continue

		if opt == '--logfile':
			set_action(ACTION_LOGFILE, '--logfile')
			continue

		if opt == '--nodename':
			set_action(ACTION_NODENAME, '--nodename')
			continue

		if opt in ('-v', '--version'):
			set_action(ACTION_VERSION, '--version')
			continue

		stderr("unknown command line option '%s'" % opt)
		errors += 1

	if errors:
		usage()
		sys.exit(1)

	if not ACTION:
		usage()
		sys.exit(1)


def main():
	synctool.param.init()

	get_options()

	if ACTION == ACTION_VERSION:
		print synctool.param.VERSION
		sys.exit(0)

	synctool.config.read_config()

	if ACTION == ACTION_LIST_NODES:
		list_all_nodes()

	elif ACTION == ACTION_LIST_GROUPS:
		list_all_groups()

	elif ACTION == ACTION_NODES:
		if not ARG_NODENAMES:
			stderr("option '--node' requires an argument; the node name")
			sys.exit(1)

		list_nodes(ARG_NODENAMES)

	elif ACTION == ACTION_GROUPS:
		if not ARG_GROUPS:
			stderr("option '--node-group' requires an argument; "
				"the node group name")
			sys.exit(1)

		list_nodegroups(ARG_GROUPS)

	elif ACTION == ACTION_CMDS:
		list_commands(ARG_CMDS)

	elif ACTION == ACTION_NUMPROC:
		print synctool.param.NUM_PROC

	elif ACTION == ACTION_PREFIX:
		print synctool.param.PREFIX

	elif ACTION == ACTION_LOGFILE:
		print synctool.param.LOGFILE

	elif ACTION == ACTION_NODENAME:
		synctool.config.init_mynodename()

		if not synctool.param.NODENAME:
			stderr('unable to determine my nodename (%s)' %
					synctool.param.HOSTNAME)
			stderr('please check %s' % synctool.param.CONF_FILE)
			sys.exit(1)

		print synctool.param.NODENAME

	elif ACTION == ACTION_LIST_DIRS:
		list_dirs()

	elif ACTION == ACTION_PKGMGR:
		print synctool.param.PACKAGE_MANAGER

	else:
		raise RuntimeError, 'bug: unknown ACTION code %d' % ACTION


if __name__ == '__main__':
	try:
		main()
	except IOError, ioerr:
		if ioerr.errno == errno.EPIPE:		# Broken pipe
			pass
		else:
			print ioerr

	except KeyboardInterrupt:		# user pressed Ctrl-C
		print

# EOB
