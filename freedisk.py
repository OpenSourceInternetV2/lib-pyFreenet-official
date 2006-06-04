#! /usr/bin/env python
#@+leo-ver=4
#@+node:@file freedisk.py
#@@first
#@@language python
#@+others
#@+node:freedisk app
"""
freedisk is a command-line utility for creating,
mounting and synchronising freenet freedisks

Invoke with -h for help
"""
#@+others
#@+node:imports
import sys, os
import getopt
import traceback
import time
import sha
import getpass

try:
    import fcp
    from fcp import node, freenetfs
    from fcp.xmlobject import XMLFile, XMLNode
except:
    print "** PyFCP core module 'fcp' not installed."
    print "** Please refer to the INSTALL file within the PyFCP source package"
    sys.exit(1)

try:
    import SSLCrypto


except:
    SSLCrypto = None
    print "** WARNING! SSLCrypto module not installed"
    print "** Please refer to the INSTALL file within the PyFCP source package"

#@-node:imports
#@+node:globals
# args shorthand
argv = sys.argv
argc = len(argv)
progname = argv[0]

# default config file stuff
homedir = os.path.expanduser("~")
configFile = os.path.join(homedir, ".freediskrc")

defaultMountpoint = os.path.join(homedir, "freedisk")

#@-node:globals
#@+node:class FreediskMgr
class FreediskMgr:
    """
    Freedisk manager class
    """
    #@    @+others
    #@-others

#@-node:class FreediskMgr
#@+node:class FreediskConfig
class FreediskConfig:
    """
    allows for loading/saving/changing freedisk configs
    """
    #@    @+others
    #@+node:attribs
    _intAttribs = ["fcpPort", "fcpVerbosity"]
    
    _strAttribs = ["fcpHost", "mountpoint"]
    
    #@-node:attribs
    #@+node:__init__
    def __init__(self, path, passwd=None):
        """
        Create a config object from file at 'path', if it exists
        """
        #print "FreediskConfig: path=%s" % path
    
        self.path = path
        self.passwd = passwd
        
        if os.path.isfile(path):
            self.load()
        else:
            self.create()
    
        self.root = self.xml.root
    
    #@-node:__init__
    #@+node:load
    def load(self):
        """
        Loads config from self.config
        """
        # get the raw xml, plain or encrypted
        ciphertext = file(self.path, "rb").read()
    
        plaintext = ciphertext
    
        # try to wrap into xml object
        try:
            xml = self.xml = XMLFile(raw=plaintext)
        except:
            i = 0
            while i < 3:
                passwd = self.passwd = getpasswd("Freedisk config password")
                plaintext = decrypt(self.passwd, ciphertext)
                try:
                    xml = XMLFile(raw=plaintext)
                    break
                except:
                    i += 1
                    continue
            if i == 3:
                self.abort()
    
        self.xml = xml
        self.root = xml.root
    
    #@-node:load
    #@+node:create
    def create(self):
        """
        Creates a new config object
        """
        self.xml = XMLFile(root="freedisk")
        root = self.root = self.xml.root
    
        self.fcpHost = fcp.node.defaultFCPHost
        self.fcpPort = fcp.node.defaultFCPPort
        self.fcpVerbosity = fcp.node.defaultVerbosity
        self.mountpoint = defaultMountpoint
    
        self.save()
    
    #@-node:create
    #@+node:save
    def save(self):
    
        plain = self.xml.toxml()
    
        if self.passwd:
            cipher = encrypt(self.passwd, plain)
        else:
            cipher = plain
        
        f = file(self.path, "wb")
        f.write(cipher)
        f.flush()
        f.close()
    
    #@-node:save
    #@+node:abort
    def abort(self):
    
        print "freedisk: Cannot decrypt freedisk config file '%s'" % self.path
        print
        print "If you truly can't remember the password, your only"
        print "option now is to delete the config file and start again"
        sys.exit(1)
    
    #@-node:abort
    #@+node:setPassword
    def setPassword(self, passwd):
        
        self.passwd = passwd
        self.save()
    
    #@-node:setPassword
    #@+node:addDisk
    def addDisk(self, name, uri, privUri, passwd):
    
        d = self.getDisk(name)
        if isinstance(d, XMLNode):
            raise Exception("Disk '%s' already exists" % name)
        
        diskNode = self.root._addNode("disk")
        diskNode.name = name
        diskNode.uri = uri
        diskNode.privUri = privUri
        diskNode.passwd = passwd
        
        self.save()
    
    #@-node:addDisk
    #@+node:getDisk
    def getDisk(self, name):
        """
        Returns a record for a freedisk of name <name>
        """
        disks = self.root._getChild("disk")
        
        for d in disks:
            if d.name == name:
                return d
        
        return None
    
    #@-node:getDisk
    #@+node:getDisks
    def getDisks(self):
        """
        Returns all freedisk records
        """
        return self.root._getChild("disk")
    
    #@-node:getDisks
    #@+node:delDisk
    def delDisk(self, name):
        """
        Removes disk of given name
        """
        d = self.getDisk(name)
        if not isinstance(d, XMLNode):
            raise Exception("No such freedisk '%s'" % name)
        
        self.root._delChild(d)
    
        self.save()
    
    #@-node:delDisk
    #@+node:__getattr__
    def __getattr__(self, attr):
        
        if attr in self._intAttribs:
            try:
                return int(getattr(self.root, attr))
            except:
                raise AttributeError(attr)
    
        elif attr in self._strAttribs:
            try:
                return str(getattr(self.root, attr))
            except:
                raise AttributeError(attr)
    
        else:
            raise AttributeError(attr)
    
    #@-node:__getattr__
    #@+node:__setattr__
    def __setattr__(self, attr, val):
        
        if attr in self._intAttribs:
            val = str(val)
            setattr(self.root, attr, val)
            self.save()
        elif attr in self._strAttribs:
            setattr(self.root, attr, val)
            self.save()
        else:
            self.__dict__[attr] = val
    
    #@-node:__setattr__
    #@-others

#@-node:class FreediskConfig
#@+node:usage
def usage(msg=None, ret=1):
    """
    Prints usage message then exits
    """
    if msg:
        sys.stderr.write(msg+"\n")
    sys.stderr.write("Usage: %s [options] [<command> [<args>]]\n" % progname)
    sys.stderr.write("Type '%s -h' for help\n" % progname)
    sys.exit(ret)

#@-node:usage
#@+node:help
def help():
    """
    Display help info then exit
    """
    print "%s: manage a freenetfs filesystem" % progname
    print "Usage: %s [<options>] <command> [<arguments>]" % progname
    print "Options:"
    print "  -h, --help            Display this help"
    print "  -c, --config=         Specify config file, default ~/.freediskrc"
    print "Commands:"
    print "  init                  Edit configuration interactively"
    print "  mount                 Mount the freenetfs"
    print "  unmount               Unmount the freenetfs"
    print "  new <name>            Create a new freedisk of name <name>"
    print "                        A new keypair will be generated."
    print "  add <name> <URI>      Add an existing freedisk of name <name>"
    print "                        and public key URI <URI>"
    print "  del <name>            Remove freedisk of name <name>"
    print "  update <name>         Sync freedisk <name> from freenet"
    print "  commit <name>         Commit freedisk <name> into freenet"
    print
    print "Environment variables:"
    print "  FREEDISK_CONFIG - set this in place of '-c' argument"

    sys.exit(0)

#@-node:help
#@+node:removeDirAndContents
def removeDirAndContents(path):
    
    files = os.listdir(path)
    
    for f in files:
        fpath = os.path.join(path, f)
        if os.path.isfile(fpath):
            os.unlink(fpath)
        elif os.path.isdir(fpath):
            removeDirAndContents(fpath)
    os.rmdir(path)

#@-node:removeDirAndContents
#@+node:status
def status(msg):
    sys.stdout.write(msg + "...")
    time.sleep(1)
    print


#@-node:status
#@+node:encrypt
def encrypt(passwd, s):

    passwd = sha.new(passwd).digest()

    if SSLCrypto:
        # encrypt with blowfish 256, key=sha(password), IV=00000000
        return SSLCrypto.blowfish(passwd).encrypt(s)
    else:
        # no encyrption available, return plaintext
        return s

#@-node:encrypt
#@+node:decrypt
def decrypt(passwd, s):

    passwd = sha.new(passwd).digest()

    if SSLCrypto:
        # decrypt with blowfish 256, key=sha(password), IV=00000000
        return SSLCrypto.blowfish(passwd).decrypt(s)
    else:
        # no encyrption available, return plaintext
        return s

#@-node:decrypt
#@+node:getpasswd
def getpasswd(prompt="Password", confirm=False):

    if not confirm:
        return getpass.getpass(prompt+": ").strip()

    while 1:
        passwd = getpass.getpass(prompt+": ").strip()
        if passwd:
            passwd1 = getpasswd("Verify password").strip()
            if passwd == passwd1:
                break
            print "passwords do not match, please try again"
        else:
            break

    return passwd

#@-node:getpasswd
#@+node:doFsCommand
def doFsCommand(cmd):
    """
    Executes a command via base64-encoded file
    """
    cmdBase64 = fcp.node.base64encode(cmd)
    path = conf.mountpoint + "/cmds/" + cmdBase64
    return file(path).read()

#@-node:doFsCommand
#@+node:ipython
def ipython(o=None):

    from IPython.Shell import IPShellEmbed

    ipshell = IPShellEmbed()

    ipshell() # this call anywhere in your program will start IPython 

#@-node:ipython
#@+node:getyesno
def getyesno(prmt, dflt=True):
    
    if dflt:
        ynprmt = "[Y/n] "
    else:
        ynprmt = "[y/N] "

    resp = raw_input(prmt + "? " + ynprmt).strip()
    if not resp:
        return dflt
    resp = resp.lower()[0]
    return resp == 'y'

#@-node:getyesno
#@+node:main
def main():
    """
    Front end
    """
    #@    <<global vars>>
    #@+node:<<global vars>>
    # some globals
    
    global Verbosity, verbose, configFile, conf
    
    #@-node:<<global vars>>
    #@nl

    #@    <<set defaults>>
    #@+node:<<set defaults>>
    # create defaults
    
    debug = False
    multithreaded = False
    
    #@-node:<<set defaults>>
    #@nl

    #@    <<process args>>
    #@+node:<<process args>>
    # process args
    
    try:
        cmdopts, args = getopt.getopt(
            sys.argv[1:],
            "?hvc:dm",
            ["help", "verbose",
             "multithreaded",
             "config=", "debug",
             ]
            )
    except getopt.GetoptError:
        # print help information and exit:
        usage()
        sys.exit(2)
    output = None
    verbose = False
    
    #print cmdopts
    for o, a in cmdopts:
    
        if o in ("-?", "-h", "--help"):
            help()
    
        if o in ("-v", "--verbose"):
            verbosity = fcp.node.DETAIL
            opts['Verbosity'] = 1023
            verbose = True
    
        if o in ("-c", "--config"):
            configFile = a
    
        if o in ("-d", "--debug"):
            debug = True
    
        if o in ("-m", "--multithreaded"):
            multithreaded = True
    
    #@-node:<<process args>>
    #@nl

    #@    <<get config>>
    #@+node:<<get config>>
    # load config, if any
    
    #print "loading freedisk config"
    
    conf = FreediskConfig(configFile)
    
    #ipython(conf)
    
    #@-node:<<get config>>
    #@nl
    
    #@    <<validate args>>
    #@+node:<<validate args>>
    # validate args
    
    nargs = len(args)
    if nargs == 0:
        usage("No command given")
    
    cmd = args[0]
    
    # barf if not 'init' and no config
    if cmd != 'init' and not os.path.isfile(configFile):
        usage("Config file %s does not exist\nRun '%s init' to create it" % (
            configFile, progname))
    
    # validate args count for cmds needing diskname arg
    if cmd in ['new', 'add', 'del', 'update', 'commit']:
        if nargs < 2:
            usage("%s: Missing argument <freediskname>" % cmd)
        diskname = args[1]
    
        # get paths to freedisk dir and pseudo-files
        diskPath = os.path.join(conf.mountpoint, "usr", diskname)
        pubKeyPath = os.path.join(diskPath, ".publickey")
        privKeyPath = os.path.join(diskPath, ".privatekey")
        passwdPath = os.path.join(diskPath, ".passwd")
        cmdPath = os.path.join(diskPath, ".cmd")
        statusPath = os.path.join(diskPath, ".status")
    
    #@-node:<<validate args>>
    #@nl

    #@    <<execute command>>
    #@+node:<<execute command>>
    # start a freenetfs mount
    if cmd in ['init', 'setup']:
        #@    <<init>>
        #@+node:<<init>>
        # initialise/change freedisk config
        
        print "Freedisk configuration"
        print
        print "Your freedisk config will normally be stored in the file:"
        print "  %s" % configFile
        
        # allow password change
        if conf.passwd:
            # got a password already
            prmt = "Do you wish to change your config password"
        else:
            # new password
            prmt = "Do you wish to encrypt this file"
        if getyesno(prmt):
            passwd = getpasswd("New Password", True)
            conf.setPassword(passwd)
            print "Password successfully changed"
        
        # host parms
        fcpHost = raw_input("Freenet FCP Hostname: [%s] " % conf.fcpHost).strip()
        if fcpHost:
            conf.fcpHost = fcpHost
        
        fcpPort = raw_input("Freenet FCP Port: [%s] "%  conf.fcpPort).strip()
        if fcpPort:
            conf.fcpPort = fcpPort
        
        print "Freenet verbosity:"
        print "  (0=SILENT, 1=FATAL, 2=CRITICAL, 3=ERROR"
        print "   4=INFO, 5=DETAIL, 6=DEBUG)"
        v = raw_input("[%s] " % conf.fcpVerbosity).strip()
        if v:
            conf.fcpVerbosity = v
        
        while 1:
            m = raw_input("Mountpoint [%s] " % conf.mountpoint).strip() \
                or conf.mountpoint
            if m:
                if not os.path.isdir(m):
                    print "No such directory '%s'" % m
                elif not os.path.exists(m):
                    print "%s is not a directory" % m
                else:
                    conf.mountpoint = m
                    mountpoint = m
                    break
        
        print "Freedisk configuration successfully changed"
        
        #@-node:<<init>>
        #@nl
    
    elif cmd in ['start', 'mount']:
        #@    <<start>>
        #@+node:<<start>>
        print "starting freedisk service..."
        fs = freenetfs.FreenetFS(
                conf.mountpoint,
                fcpHost=conf.fcpHost,
                fcpPort=conf.fcpPort,
                verbosity=conf.fcpVerbosity,
                debug=debug,
                multithreaded=multithreaded,
                )
        
        # spawn a process to run it
        if os.fork() == 0:
            print "Mounting freenet fs at %s" % conf.mountpoint
            fs.run()
        else:
            # parent process
            keyDir = os.path.join(conf.mountpoint, "keys")
            print "Waiting for disk to come up..."
            while not os.path.isdir(keyDir):
                time.sleep(1)
            disks = conf.getDisks()
        
            if disks:
                print "Freenetfs now mounted, adding existing disks..."
            else:
                print "Freenetfs now mounted, no freedisks at present"
        
            for disk in disks:
        
                diskPath = os.path.join(conf.mountpoint, "usr", disk.name)
        
                # barf if a freedisk of that name is already mounted
                if os.path.exists(diskPath):
                    usage("Freedisk %s seems to be already mounted" % disk.name)
                
                # mkdir to create the freedisk dir
                os.mkdir(diskPath)
        
                pubKeyPath = os.path.join(diskPath, ".publickey")
                privKeyPath = os.path.join(diskPath, ".privatekey")
                passwdPath = os.path.join(diskPath, ".passwd")
        
                # wait for the pseudo-files to come into existence
                while not os.path.isfile(privKeyPath):
                    time.sleep(0.1)
        
                # set the key and password
                file(pubKeyPath, "w").write(disk.uri)
                file(privKeyPath, "w").write(disk.privUri)
                file(passwdPath, "w").write(disk.passwd)
                
        #@-node:<<start>>
        #@nl
    
    elif cmd in ['umount', 'unmount', 'stop']:
        #@    <<stop>>
        #@+node:<<stop>>
        os.system("umount %s" % conf.mountpoint)
        
        #@-node:<<stop>>
        #@nl
    
    elif cmd == 'new':
        #@    <<new>>
        #@+node:<<new>>
        #print "new: %s: NOT IMPLEMENTED" % diskname
        
        if os.path.exists(diskPath):
            usage("Freedisk %s seems to be already mounted" % diskname)
        
        # get a password if desired
        passwd = getpasswd("Encrypt disk with password", True)
        
        # get a new private key
        keyDir = os.path.join(conf.mountpoint, "keys")
        if not os.path.isdir(keyDir):
            print "No keys directory %s" % keyDir
            print "Is your freenetfs mounted?"
            usage("Freenetfs not mounted")
        keyName = "freedisk_%s_%s" % (diskname, int(time.time()*1000000))
        keyPath = os.path.join(keyDir, keyName)
        
        keys = file(keyPath).read().strip().split("\n")
        pubKey, privKey = [k.split("/")[0].split("freenet:")[-1] for k in keys]
        
        # mkdir to create the freedisk dir
        os.mkdir(diskPath)
        
        # wait for the pseudo-files to come into existence
        while not os.path.isfile(privKeyPath):
            time.sleep(0.1)
        
        #status("About to write to %s" % privKeyPath)
        
        file(pubKeyPath, "w").write(pubKey)
        file(privKeyPath, "w").write(privKey)
        file(passwdPath, "w").write(passwd)
        
        # and, of course, update config
        conf.addDisk(diskname, pubKey, privKey, passwd)
        
        #@-node:<<new>>
        #@nl
    
    elif cmd == 'add':
        #@    <<add>>
        #@+node:<<add>>
        # get uri
        if nargs < 3:
            usage("add: Missing URI")
        uri = args[2]
        
        #print "add: %s: NOT IMPLEMENTED" % diskname
        
        # barf if a freedisk of that name is already mounted
        if os.path.exists(diskPath):
            usage("Freedisk %s seems to be already mounted" % diskname)
        
        # mkdir to create the freedisk dir
        os.mkdir(diskPath)
        
        # wait for the pseudo-files to come into existence
        while not os.path.isfile(privKeyPath):
            time.sleep(0.1)
        
        # set the keys
        
        if fcp.node.uriIsPrivate(uri):
            path = privKeyPath
        else:
            path = pubKeyPath
        f = file(path, "w")
        f.write(uri)
        f.flush()
        f.close()
        
        #@-node:<<add>>
        #@nl
    
    elif cmd == 'del':
        #@    <<del>>
        #@+node:<<del>>
        disk = conf.getDisk(diskname)
        
        if not isinstance(disk, XMLNode):
            usage("No such disk '%s'" % diskname)
        
        conf.delDisk(diskname)
        
        path = os.path.join(conf.mountpoint, "usr", diskname)
        os.rmdir(path)
        
        #@-node:<<del>>
        #@nl
    
    elif cmd == 'update':
        #@    <<update>>
        #@+node:<<update>>
        print "update: %s: NOT IMPLEMENTED" % diskname
        
        f = file(cmdPath, "w")
        f.write("update")
        f.flush()
        f.close()
        
        #@-node:<<update>>
        #@nl
    
    elif cmd == 'commit':
        #@    <<commit>>
        #@+node:<<commit>>
        print "commit: %s: launching.." % diskname
        
        f = file(cmdPath, "w")
        f.write("commit")
        f.flush()
        f.close()
        
        #@-node:<<commit>>
        #@nl
    
    elif cmd == 'list':
        #@    <<list>>
        #@+node:<<list>>
        disks = conf.getDisks()
        
        if disks:
            print "Currently mounted freedisks:"
            for d in disks:
                print "  %s:" % d.name
                print "    uri=%s" % d.uri
                print "    passwd=%s" % d.passwd
        else:
            print "No freedisks mounted"
        
        #@-node:<<list>>
        #@nl
    
    elif cmd == 'cmd':
        #@    <<cmd>>
        #@+node:<<cmd>>
        # arbitrary command, for testing
        
        cmd = " ".join(args[1:])
        
        print repr(doFsCommand(cmd))
        
        #@-node:<<cmd>>
        #@nl
    
    
    
    
    else:
        usage("Unrecognised command: %s" % cmd)
    
    #@-node:<<execute command>>
    #@nl

#@-node:main
#@+node:mainline
if __name__ == '__main__':
    main()

#@-node:mainline
#@-others

#@-node:freedisk app
#@-others
#@-node:@file freedisk.py
#@-leo