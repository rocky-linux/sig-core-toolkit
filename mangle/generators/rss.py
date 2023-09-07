#!/usr/bin/env python3
# -*-:python; coding:utf-8; -*-
# author: Louis Abel <label@rockylinux.org>
# modified version of repo-rss from yum utils

import sys
import os
import argparse
import time
import binascii
# The old yum-utils repo-rss used string manipulation. We're instead going to
# use the XML python library to do the work for us. This is cleaner, imo.
from xml.sax.saxutils import escape as xmlescape
from xml.etree.ElementTree import ElementTree, TreeBuilder, tostring
from xml.dom import minidom
import dnf
import dnf.exceptions
#from dnf.comps import Comps
#import libxml2

def to_unicode(string: str) -> str:
    """
    Convert to unicode
    """
    if isinstance(string, bytes):
        return string.decode('utf8')
    if isinstance(string, str):
        return string
    return str(string)

class DnfQuiet(dnf.Base):
    """
    DNF object
    """
    def __init__(self):
        dnf.Base.__init__(self)

    def get_recent(self, days=1):
        """
        Return most recent packages from dnf sack
        """
        recent = []
        now = time.time()
        recentlimit = now-(days*86400)
        ftimehash = {}
        if self.conf.showdupesfromrepos:
            available = self.sack.query().available().filter()
        else:
            available = self.sack.query().available().filter(latest_per_arch=1)

        available.run()

        for package in available:
            ftime = int(package.buildtime)
            if ftime > recentlimit:
                if ftime not in ftimehash:
                    ftimehash[ftime] = [package]
                else:
                    ftimehash[ftime].append(package)

        for sometime in ftimehash.keys():
            for package in ftimehash[sometime]:
                recent.append(package)

        return recent

class RepoRSS:
    def __init__(self, filename='repo-rss.xml'):
        self.description = 'Repository RSS'
        self.link = 'https://github.com/rpm-software-management/dnf'
        self.title = 'Recent Packages'
        if filename[0] != '/':
            cwd = os.getcwd()
            self.filename = os.path.join(cwd, filename)
        else:
            self.filename = filename

    def rsspackage(self, packages):
        file = self.filename
        rfc822_format = "%a, %d %b %Y %X GMT"
        now = time.strftime(rfc822_format, time.gmtime())
        etbobj = TreeBuilder()
        # start rss
        etbobj.start('rss', {'version': '2.0'})
        # start channel
        etbobj.start('channel', {})
        # start title
        etbobj.start('title', {})
        etbobj.data(self.title)
        etbobj.end('title')
        # end title
        # start link
        etbobj.start('link', {})
        etbobj.data(self.link)
        etbobj.end('link')
        # end link
        # start description
        etbobj.start('description', {})
        etbobj.data(self.description)
        etbobj.end('description')
        # end description
        # start pubDate
        etbobj.start('pubDate', {})
        etbobj.data(now)
        etbobj.end('pubDate')
        # end pubDate
        # start generator
        etbobj.start('generator', {})
        etbobj.data('DNF')
        etbobj.end('generator')
        # end generator

        changelog_format = "%a, %d %b %Y GMT"
        for package in packages:
            package_hex = binascii.hexlify(package.chksum[1]).decode()
            title = xmlescape(str(package))
            date = time.gmtime(float(package.buildtime))
            description = package.description
            link = package.remote_location()
            # form description
            changelog = ''
            count = 0
            if package.changelogs is not None:
                changelog_list = package.changelogs
            else:
                changelog_list = []
            for meta in changelog_list:
                count += 1
                if count > 3:
                    changelog += '...'
                    break
                cl_date = meta['timestamp'].strftime(changelog_format)
                author = meta['author']
                desc = meta['text']
                changelog += f'{cl_date} - {author}\n{desc}\n\n'
            description = f'<p><strong>{package.name}</strong> - {package.summary}</p>\n\n'
            description += '<p>%s</p>\n\n<p><strong>Change Log:</strong></p>\n\n' % description.replace("\n", "<br />\n")
            description += f'<pre>{changelog}</pre>'

            # start item
            etbobj.start('item', {})
            # start title
            etbobj.start('title', {})
            etbobj.data(title)
            etbobj.end('title')
            # end title
            # start pubDate
            etbobj.start('pubDate', {})
            etbobj.data(time.strftime(rfc822_format, date))
            etbobj.end('pubDate')
            # end pubDate
            # start guid
            etbobj.start('guid', {'isPermaLink': 'false'})
            etbobj.data(package_hex)
            etbobj.end('guid',)
            # end guid
            # start link
            etbobj.start('link', {})
            etbobj.data(link)
            etbobj.end('link')
            # end link
            # start description
            etbobj.start('description', {})
            etbobj.data(xmlescape(description))
            etbobj.end('description')
            # end description
            etbobj.end('item')
            # end item

        etbobj.end('channel')
        # end channel
        etbobj.end('rss')
        # end rss
        rss = etbobj.close()
        etree = ElementTree(rss)
        some_string = tostring(etree.getroot(), encoding='utf-8')
        xmlstr = minidom.parseString(some_string).toprettyxml(indent="  ")
        #etree.write(file, encoding='utf-8')
        with open(file, 'w+', encoding='utf-8') as f:
            f.write(xmlstr)
            f.close()

def make_rss_feed(filename, title, link, description, recent):
    rssobj = RepoRSS(filename)
    rssobj.title = title
    rssobj.link = link
    rssobj.description = description
    rssobj.rsspackage(recent)

def main(options):
    days = options.days
    repoids = options.repoids
    dnfobj = DnfQuiet()
    if options.config:
        dnfobj.conf.read(filename=options.config)

    if os.geteuid() != 0 or options.tempcache:
        cachedir = dnfobj.conf.cachedir
        if cachedir is None:
            print('Error: Could not make cachedir')
            sys.exit(50)
        dnfobj.conf.cachedir = cachedir

    try:
        dnfobj.read_all_repos()
    except:
        print('Could not read repos', file=sys.stderr)
        sys.exit(1)

    if len(repoids) > 0:
        for repo in dnfobj.repos:
            repoobj = dnfobj.repos[repo]
            if repo not in repoids:
                repoobj.disable()
            else:
                repoobj.enable()
                if options.module_hotfixes:
                    try:
                        repoobj.set_or_append_opt_value('module_hotfixes', '1')
                    except:
                        print('Warning: dnf library is too old to support setting values')

                repoobj.load_metadata_other = True

    print('Getting repo data for requested repos')
    try:
        dnfobj.fill_sack()
    except:
        print('repo data failure')
        sys.exit(1)

    sack_query = dnfobj.sack.query().available()
    #recent = sack_query.filter(latest_per_arch=1)
    recent = dnfobj.get_recent(days=days)
    #sorted_recents = sorted(set(recent.run()), key=lambda pkg: pkg.buildtime)
    sorted_recents = sorted(set(recent), key=lambda pkg: pkg.buildtime)
    sorted_recents.reverse()
    make_rss_feed(options.filename, options.title, options.link,
                  options.description, sorted_recents)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--filename', type=str, default='repo-rss.xml',
                        help='File patch to export to')
    parser.add_argument('--link', type=str, default='https://github.com/rpm-software-management/dnf',
                        help='URL link to repository root')
    parser.add_argument('--title', type=str, default='RSS Repository - Recent Packages',
                        help='Title of the feed')
    parser.add_argument('--description', type=str, default='Most recent packages in Repositories',
                        help='Description of the feed')
    parser.add_argument('--days', type=int, default=7, help='Number of days to look back')
    parser.add_argument('--tempcache', action='store_true',
                        help='Temporary cache location (automatically on if not root)')
    parser.add_argument('--module-hotfixes', action='store_true',
                        help='Only use this to catch all module packages')
    parser.add_argument('--arches', action='append', default=[],
                        help='List of architectures to care about')
    parser.add_argument('--config', type=str, default='',
                        help='A dnf configuration to use if you do not want to use the default')
    parser.add_argument('repoids', metavar='N', type=str, nargs='+')
    results = parser.parse_args()

    main(results)
