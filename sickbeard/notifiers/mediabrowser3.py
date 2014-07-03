# Author: Jonathon Saine <thezoggy@gmail.com>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

from httplib import HTTPConnection
from urllib import urlencode
from socket import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_REUSEADDR, SO_BROADCAST, SHUT_RDWR

import sickbeard

from sickbeard.exceptions import ex
from sickbeard import common
from sickbeard import logger


class MediaBrowser3Notifier:

    def server_broadcast(self):
        cs = socket(AF_INET, SOCK_DGRAM)
        cs.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        cs.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        cs.settimeout(3)
        try:
            assert cs.sendto('who is MediaBrowserServer?', ('255.255.255.255', 7359)) == 26, "Not all data was sent through the socket!"
            message, address = cs.recvfrom(1024)
            cs.shutdown(SHUT_RDWR)
            if message:
                logger.log(u"MEDIABROWSER3: UDP query returned (%s) from : %s" % (str(message), address[0]))
                return message.split('|')[1]
        except:
            return ''

    def _send_to_mb3(self, method, title, message, host, username, password):

        if not host:
            logger.log(u"MEDIABROWSER3: No host specified, check your settings", logger.ERROR)
            return False

        try:

            http_handler = HTTPConnection(host)

            data = {'Name': title.encode('utf-8'),
                    'Description': message.encode('utf-8'),
                    'Source': 'SickBeard'
                    }

            http_handler.request("POST", "/mediabrowser/" + method,
                                 headers={'Content-type': "application/x-www-form-urlencoded"},
                                 body=urlencode(data)
                                 )

            response = http_handler.getresponse()
            print response.status, response.reason
            data = response.read()
            print data
            http_handler.close()

        except Exception, e:
            logger.log(u"MEDIABROWSER3: Notification failed: " + ex(e), logger.ERROR)
            return False

        return True

    def _notify(self, title, message, host=None, username=None, password=None, force=False):

        # suppress notifications if the notifier is disabled but the notify options are checked
        if not sickbeard.USE_MEDIABROWSER3 and not force:
            return False

        # fill in omitted parameters
        if not host:
            host = sickbeard.MEDIABROWSER3_HOST
        if not username:
            username = sickbeard.MEDIABROWSER3_USERNAME
        if not password:
            password = sickbeard.MEDIABROWSER3_PASSWORD

        method = "Notifications/Admin"
        result = ''
        for curHost in [x.strip() for x in host.split(",")]:
            logger.log(u"MEDIABROWSER3: Sending notification to '" + curHost + "' - " + message, logger.MESSAGE)

            notifyResult = self._send_to_mb3(method, title, message, curHost, username, password)
            if notifyResult:
                result += curHost + ':' + str(notifyResult)

        return result

##############################################################################
# Public functions
##############################################################################

    def notify_snatch(self, ep_name):
        if sickbeard.MEDIABROWSER3_NOTIFY_ONSNATCH:
            self._notify(common.notifyStrings[common.NOTIFY_SNATCH], ep_name)

    def notify_download(self, ep_name):
        if sickbeard.MEDIABROWSER3_NOTIFY_ONDOWNLOAD:
            self._notify(common.notifyStrings[common.NOTIFY_DOWNLOAD], ep_name)

    def test_notify(self, host, username, password):
        return self._notify("Test", "This is a test notification from Sick Beard", host, username, password, force=True)

    def update_library(self, ep_obj=None, show_obj=None, tvdbid=None):

        if sickbeard.USE_MEDIABROWSER3 and sickbeard.MEDIABROWSER3_UPDATE_LIBRARY:
            if not sickbeard.MEDIABROWSER3_HOST:
                logger.log(u"MEDIABROWSER3: No host specified, check your settings", logger.DEBUG)
                return False

            if sickbeard.MEDIABROWSER3_UPDATE_ONLYFIRST:
                # only send update to first host in the list if requested
                host = sickbeard.MEDIABROWSER3_HOST.split(",")[0].strip()
            else:
                host = sickbeard.MEDIABROWSER3_HOST

            if tvdbid:
                tvdb_id = tvdbid
            elif ep_obj:
                tvdb_id = ep_obj.show.tvdbid
            elif show_obj:
                tvdb_id = show_obj.tvdbid
            else:
                logger.log(u"MEDIABROWSER3: Unable to update show due to missing tvdbid.", logger.DEBUG)
                return False

            method = "Library/Series/Updated?tvdbid=" + str(tvdb_id)

            result = 0
            for curHost in [x.strip() for x in host.split(",")]:
                logger.log(u"MEDIABROWSER3: Updating library for host: " + curHost, logger.MESSAGE)
                logger.log(u"MEDIABROWSER3: Updating show: " + str(tvdb_id), logger.MESSAGE)
            # needed for the 'update mb3' submenu command
            # as it only cares of the final result vs the individual ones
            if result == 0:
                return True
            else:
                return False

        pass

notifier = MediaBrowser3Notifier
