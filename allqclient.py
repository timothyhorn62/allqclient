#!/usr/pypy2.7/bin/pypy
import subprocess
import re
import pylibmc
import fcntl
import json
import os
import time
import getpass


def getServerName():
        out = subprocess.check_output('hostname | cut -d . -f 1 ', shell=True)
        hostname = out.rstrip()
        envir = hostname[3:5]
        servernum = re.findall(r'\d+', hostname)
        numeric = ''.join(servernum)
        prefix = ''
        if envir == 'pp':
                prefix = 'pp'
        servername = prefix + 'nggf' + numeric
        return (servername)

def getMemcacheValue(client, hostname):
	keyname = hostname + '.processcounts'
	result = client.get(keyname)
	return result

def setMemcacheValue(client, hostname, value):
	keyname = hostname + '.processcounts'
	client.set(keyname, value);
	return

def getSicstus():
	cmd1 = subprocess.Popen(['ps', '-ef'],stdout=subprocess.PIPE)
	cmd2 = subprocess.Popen(['grep', 'sicstus'],stdin=cmd1.stdout,stdout=subprocess.PIPE)
	cmd3 = subprocess.Popen(['grep','-v', 'grep'],stdin=cmd2.stdout,stdout=subprocess.PIPE)
	cmd4 = subprocess.Popen(['grep', '-v','defunct'],stdin=cmd3.stdout,stdout=subprocess.PIPE)
	cmd5 = subprocess.Popen(['awk', '{print $16}'],stdin=cmd4.stdout,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	cmd1.stdout.close()
	out,err = cmd5.communicate()
	print(out)

def getProcessCounts(pname):
        out = subprocess.check_output('ps -ef | grep ' + pname + ' | grep -v grep | grep -v defunct | wc -l', shell=True)
        return(out)

def getConfigParm(path, cparm):
        out = subprocess.check_output('grep ' + cparm + ' ' + path + ' | awk \'{print $2}\'', shell=True)
        return(out.replace(',',''))

def getExpectedCounts(path):
	escount = getConfigParm(path,'server_count').rstrip()
	ercount = getConfigParm(path,'mq_reader_count').rstrip()
	ewcount = getConfigParm(path,'mq_writer_count').rstrip()
	earray = [escount, ercount, ewcount]
	return(earray)

def getLock(filename):
	fp = os.open(filename, os.O_CREAT | os.O_TRUNC | os.O_WRONLY)
	try:
		fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
	except IOError:
		return False
	return True

def getVersion(verpath):
	last = ''
	if os.path.islink(verpath):
		st = os.readlink(verpath)
		pathparts = st.split("/")
		last = pathparts[-1]
	return last

def getRegion(envdir,server):
	fullpath = envdir + "/" + server
	return os.listdir(fullpath)[0]

me = getpass.getuser()
if me != 'efare':
	print("You must be logged in as efare")
	exit()
jsonname = 'allqclient.json'
with open(jsonname,'r') as confile:
	data = confile.read()
parms = json.loads(data)
lockfile = parms['lockfile']
logfile = parms['logfile']
envdir = parms['envdir']
memcachehost = parms['memcachehost']
memcacheport = parms['memcacheport']
memcachepath = memcachehost + ':' + memcacheport
servername = getServerName()
region = getRegion(envdir, servername)
regionpath = '/efare1/dist/conf/regions/' + region + '/systems.d/' + servername + region[4:] + '.json'
versionpath = '/efare1/dist/src/prodcode' + region[4:]
if getLock(lockfile):
	print("Retrieved the lock...continuing")
	while (True):
		scount = getProcessCounts('sicstus').rstrip()
		rcount = getProcessCounts('mq_reader').rstrip()
		wcount = getProcessCounts('mq_writer').rstrip()
		expectedcounts = getExpectedCounts(regionpath)
		version = getVersion(versionpath)
		client = pylibmc.Client([memcachepath])
		newkey = version + ':' + version + ':' + expectedcounts[0] + ':' + expectedcounts[1] + ':' + expectedcounts[2] + ':' + scount + ':' + rcount + ':' + wcount + ':0:0'
		print(newkey)
		setMemcacheValue(client, servername, newkey.rstrip())
		time.sleep(5)
else :
	print("Could not get the lock")
