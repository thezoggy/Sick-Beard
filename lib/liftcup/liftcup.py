# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://github.com/midgetspy/Lift-Cup
#
# This file is part of Lift Cup (adapted from Sick Beard)
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import os
import re
import subprocess
import shlex
import shutil

import liftcup

try:
    from conf import *
except ImportError:
    print "No config found, check that you have a conf.py file"
    sys.exit(1)

import sickbeard
from sickbeard import logger
from sickbeard.common import Quality

scene_qualities = {Quality.SDTV: "HDTV.XviD",
           Quality.SDDVD: "DVDRip.XviD",
           Quality.HDTV: "720p.HDTV.x264",
           Quality.HDWEBDL: "720p.WEB-DL",
           Quality.HDBLURAY: "720p.BluRay.x264",
           Quality.FULLHDBLURAY: "1080p.BluRay.x264",
          }

#------------------------------------------------------------------------
# Taken from sabnzbd
# Figure out which OS the user is running and if x64
# Note: windows python installs tend to just do 32bit for stability

# In their infinitive wisdom Microsoft has decided to make the 'long' C
# type always a 32 bit signed integer - even on 64bit systems.
# On most Unix systems a long is at least 32 bit but usually sizeof(ptr).
# Some 64-bit systems (notably Win64) leave C longs as 32-bit. The LLP64 data model.

WIN32 = DARWIN = DARWIN_INTEL = POSIX = WIN64 = False

if os.name == 'nt':
    from win32api import GetVersionEx
    import _winreg
    WINmaj, WINmin, WINbuildno, WINplat, WINcsd = GetVersionEx()
    if(WINmaj > 5):
        # Must be done the hard way, because the Python runtime lies to us.
        # This does *not* work:
        #     return os.environ['PROCESSOR_ARCHITECTURE'] == 'AMD64'
        # because the Python runtime returns 'X86' even on an x64 system!
        key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")
        for n in xrange(_winreg.QueryInfoKey(key)[1]):
            name, value, val_type = _winreg.EnumValue(key, n)
            if name == 'PROCESSOR_ARCHITECTURE':
                WIN64 = value.upper() == u'AMD64'
                break
        _winreg.CloseKey(key)
    else:
        # Due to LLP64 data model this 64bit check generally will not work
        import struct
        if(8 * struct.calcsize("P")) == 64:
            WIN64 = True
        # Give up and just assume 32 bit only
        WIN32 = True
elif os.name == 'posix':
    ORG_UMASK = os.umask(18)
    os.umask(ORG_UMASK)
    POSIX = True
    import platform
    if platform.system().lower() == 'darwin':
        DARWIN = True
        if platform.machine() == 'i386':
            DARWIN_INTEL = True
#------------------------------------------------------------------------

PAR2_BINARY = None
RAR_BINARY = None
RAR_PROBLEM = False


def find_programs(curdir):
    def find_on_path(targets):
        """ Search the PATH for a program and return full path """
        if WIN32:
            paths = os.getenv('PATH').split(';')
        else:
            paths = os.getenv('PATH').split(':')

        if isinstance(targets, basestring):
            targets = ( targets, )

        for path in paths:
            for target in targets:
                target_path = os.path.abspath(os.path.join(path, target))
                if os.path.isfile(target_path) and os.access(target_path, os.X_OK):
                    return target_path
        return None

    def check(path, program):
        p = os.path.abspath(os.path.join(path, program))
        if os.access(p, os.X_OK):
            return p
        else:
            return None

    def rar_check(rar):
        """ Return True if correct version of rar is found """
        if rar:
            try:
                version = subprocess.Popen(rar, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).stdout.read()
            except:
                return False
            m = re.search("RAR\s(\d+)\.(\d+)\s+.*Alexander Roshal", version)
            if m:
                return (int(m.group(1)), int(m.group(2))) >= (3, 80)
        return False

    if DARWIN:
        try:
            os_version = subprocess.Popen("sw_vers -productVersion", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).stdout.read()
            #par2-sl from Macpar Deluxe 4.1 is only 10.6 and later
            if int(os_version.split('.')[1]) >= 6:
                liftcup.PAR2_BINARY = check(curdir, 'osx/par2/par2-sl')
            else:
                liftcup.PAR2_BINARY = check(curdir, 'osx/par2/par2-classic')
        except:
            liftcup.PAR2_BINARY = check(curdir, 'osx/par2/par2-classic')

        liftcup.RAR_BINARY = check(curdir, 'osx/rar/rar')

    if WIN64:
        liftcup.PAR2_BINARY = check(curdir, 'win/par2/x64/par2.exe')
        liftcup.RAR_BINARY = check(curdir, 'win/rar/x64/Rar.exe')

    if WIN32:
        liftcup.PAR2_BINARY = check(curdir, 'win/par2/par2.exe')
        liftcup.RAR_BINARY = check(curdir, 'win/rar/Rar.exe')
    else:
        if not liftcup.PAR2_BINARY:
            liftcup.PAR2_BINARY = find_on_path('par2')
        if not liftcup.RAR_BINARY:
            liftcup.RAR_BINARY = find_on_path('rar')
            print "find_on_path('rar'): " + str(find_on_path('rar'))

    if not (WIN32 or DARWIN):
        liftcup.RAR_PROBLEM = not rar_check(liftcup.RAR_BINARY)


class LiftCup(object):

    def __init__(self, full_file_path, quality):
        #original_tv_dir = os.path.dirname(full_file_path)
        original_file = os.path.basename(full_file_path)
        #TODO: What if they don't define the variables in the config?
        self.test = LC_TEST
        self.debug = LC_DEBUG
        self.cleanup = LC_CLEANUP
        self.upload = LC_UPLOAD
        # do we really want them to skip quality check? if it's coming from sb
        self.skip_quality = LC_QUALITY

        logger.log(u"LC: Starting Lift-Cup module.")

        if self.debug:
            print "Debug info:"
            print "original_file: " + str(original_file)
            print "quality: " + str(quality)
            print "self.test: " + str(self.test)
            print "self.debug: " + str(self.debug)
            print "self.cleanup: " + str(self.cleanup)
            print "self.upload: " + str(self.upload)
            print "self.skip_quality: " + str(self.skip_quality)
            print " "

        if not self.skip_quality:
            if quality == Quality.UNKNOWN:
                logger.log(u"LC: Quality for show is Unknown, aborting process for the good of others.")
                return

        # setup env : use/create release folder per user config
        logger.log(u"LC: Config.py TEMP_DIR: " + str(TEMP_DIR))
        sickbeard.helpers.makeDir(TEMP_DIR)

        # determine tools : figure out which rar/par utility to use
        find_programs(os.path.dirname(__file__))
        if RAR_PROBLEM == True:
            logger.log(u"LC: Rar problem detected, aborting. Do you have rar installed?")
            return

        # copy episode to temp folder -- prevent problems due to network / remote storage
        # faster to create rarset off local file, also in case we want to modify the file
        scene_file_path = os.path.join(TEMP_DIR, original_file)
        if os.path.isfile(scene_file_path):
            logger.log(u"LC: File " + str(scene_file_path) + " already exists, skipping this release")
            return
        logger.log(u"LC: Copying " + str(full_file_path) + " to " + str(scene_file_path))
        sickbeard.helpers.copyFile(full_file_path, scene_file_path)

        # generate rarset : put rarset in a subfolder (filename without extension) inside of the temp_dir
        scene_base_name = os.path.splitext(original_file)[0]
        rar_base_name = os.path.join(TEMP_DIR, scene_base_name, scene_base_name)
        files_to_rar = [scene_file_path]
        if not self.rar_release(files_to_rar, rar_base_name, self.find_rar_size(files_to_rar)):
            logger.log(u"LC: Problem during RAR creation.")
            return

        # generate nfo for rarset : use original nfo as base
        cur_file_name = os.path.splitext(full_file_path)[0]
        cur_file_nfo = cur_file_name + '.nfo'
        nfo_file_path = rar_base_name + '.nfo'
        if os.path.isfile(cur_file_nfo):
            logger.log(u"LC: Existing .nfo found, using " + str(cur_file_nfo) + " as a base")
            sickbeard.helpers.copyFile(cur_file_nfo, nfo_file_path)
        # append liftcup related info to existing nfo / create nfo
        self.create_nfo(nfo_file_path, original_file)

        # generate pars : put pars with rarset
        if not self.par_release(rar_base_name):
            logger.log(u"LC: Problem during PAR creation.")
            return

        #print sickbeard.helpers.listMediaFiles(self.tv_dir) # show contents in dir -- batch?
        #self.quality = sickbeard.common.Quality.nameQuality(full_file_path)
        #print "scene_name: " + self.make_scene_name(self.file)

        # upload release : start upload routine
        if self.upload and not self.upload_release(os.path.dirname(rar_base_name)):
            logger.log(u"LC: Problem during upload process.")
            # because this process fails for windows users the cleanup process does not run
            return

        # clean up : removed the current session of generated files
        if self.cleanup:
            logger.log(u"LC: Start post upload cleanup process.")
            os.remove(scene_file_path)
            os.remove(nfo_file_path)
            if os.path.isdir(os.path.join(TEMP_DIR, scene_base_name)):
                shutil.rmtree(os.path.join(TEMP_DIR, scene_base_name))

        logger.log(u"LC: Lift-Cup module completed.")

    def make_scene_name(self, name):
        """
        Tries to inject the appropriate quality into the name and "scenifies" it a little bit
        name: The original filename of the release
        Returns: A string containing the scenified version of the name
        """

        if sickbeard.common.Quality.nameQuality(name) != sickbeard.common.Quality.UNKNOWN or self.skip_quality:
            scene_name = name
        else:
            if not self.quality:
                cur_quality = sickbeard.common.Quality.assumeQuality(name)
            else:
                cur_quality = self.quality

            base_name, extension = os.path.splitext(name)

            scene_match = re.match('(.*\S)\-(\S + )', base_name)

            if not scene_match:
                scene_name = base_name + '.' + scene_qualities[cur_quality] + extension
            else:
                scene_name = scene_match.group(1) + '.' + scene_qualities[cur_quality] + '-' + scene_match.group(2) + extension

        scene_name = re.sub("[_ !() + '.-] + ", '.', scene_name)
        return scene_name

    def find_rar_size(self, file_list):
        """
        Picks the optimal size the release rarset should use with a target of 30 parts in mind.
        Returns: the number of megabytes the rars should be
        """
        #TODO: check for empty file_list
        rar_sizes = (15, 20, 50, 100)

        size = sum([os.path.getsize(x) for x in file_list]) / 1024 / 1024
        ideal_size = size / 30

        rar_size = min((abs(ideal_size - x), x) for x in rar_sizes)[1]

        return rar_size

    def rar_release(self, path_to_files, rar_dest, rar_size):
        """
        Rars up the provided files to the given folder.

        path_to_files: A list of full paths to files
        rar_dest: The destination path  +  base name for the rar set

        Returns: True for success or False for failure
        """
        print "RAR_BINARY: " + str(RAR_BINARY)

        common_root_path = os.path.dirname(os.path.commonprefix(path_to_files))
        short_file_list = [x[len(common_root_path) + 1:] for x in path_to_files]
        logger.log(u"LC: Creating " + str(rar_size) + "m rarset for " + str(short_file_list) + " at " + rar_dest)
        rar_dest = os.path.abspath(rar_dest)
        rar_dir = os.path.dirname(rar_dest)
        sickbeard.helpers.makeDir(rar_dir)
        cmd = [str(liftcup.RAR_BINARY), 'a', rar_dest, ' '.join(short_file_list), '-v' + str(rar_size) + 'm', '-m0']

        return self.execute_command(cmd, common_root_path)

    def create_nfo(self, nfo_path, old_name):
        """
        Generates an NFO file at the given path.
        Includes the original name of the file for reference.

        nfo_path: Full path of the file we should create
        old_name: The original name of this release before we scenified it
        """
        logger.log(u"LC: Creating NFO at " + str(nfo_path))
        nfo = open(nfo_path, 'a')
        nfo.write('Original name: ' + old_name + '\n')
        if nfo_string:
            nfo.write(nfo_string + '\n')
        nfo.write('Lift Cup 0.1' + '\n')
        #TODO: Need to use __version__ instead of hardcoding
        nfo.close

    def par_release(self, path_to_rars):
        """
        Generate 10% recovery parset for rarset.

        path_to_rars: The path  +  base name for the rar set
        Returns: True for success or False for failure
        """
        print "PAR2_BINARY: " + str(PAR2_BINARY)
        logger.log(u"LC: Creating pars for rarset at " + path_to_rars + "*.rar")
        cmd = [str(liftcup.PAR2_BINARY), 'c', '-r10', '-n7', path_to_rars, path_to_rars + '*.rar', path_to_rars + '.nfo']

        return self.execute_command(cmd)

    def upload_release(self, release_path):
        """
        Non-Windows: Uses newsmangler to upload a set of rars/pars to usenet.

        release_path: The path to the folder containing the rars/pars to upload
        Returns: True for success or False for failure
        """

        print "Config.py POSTER_PY: " + str(POSTER_PY)
        print "Config.py POSTER_CONF: " + str(POSTER_CONF)
        logger.log(u"LC: Uploading the files in " + str(release_path))
        if(WIN32 or WIN64):
            logger.log(u"LC: Upload process not supported for Windows, aborting process.")
            return False
        cmd = [POSTER_PY, '-c', POSTER_CONF, release_path + os.sep]

        return self.execute_command(cmd)

    def execute_command(self, command, cwd=None):
        """
        Executes the given shell command and returns bool representing success.

        command: A string containing the command (with parameters) to execute
        cwd: Optional parameter that gets passed to Popen as the cwd

        Returns: True for success, False for failure.
        """

        # if we have a string turn it into a command list
        if type(command) in (str, unicode):
            # kludge for shlex.split
            if os.sep == '\\':
                command = command.replace(os.sep, os.sep + os.sep)
            script_cmd = shlex.split(command)
        else:
            script_cmd = command

        try:
            if not self.test:
                logger.log(u"LC: Executing command " + str(script_cmd))
                p = subprocess.Popen(script_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd)
                out, err = p.communicate()
                logger.log(u"LC: Command output: " + out)
        except OSError, e:
            logger.log(u"LC: Error:", e)
            return False

        return True
