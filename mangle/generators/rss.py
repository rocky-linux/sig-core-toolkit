#!/usr/bin/env python3
# -*-:python; coding:utf-8; -*-
# author: Louis Abel <label@rockylinux.org>
# modified version of repo-rss from yum utils

import sys
import os
import argparse
import time
import binascii
import dnf
import dnf.exceptions
#from dnf.comps import Comps
import libxml2

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
        self.link = 'http://dnf.baseurl.org'
        self.title = 'Recent Packages'
        self.do_file(filename)
        self.do_doc()

    def do_doc(self):
        self.doc = libxml2.newDoc('1.0')
        self.xmlescape = self.doc.encodeEntitiesReentrant
        rss = self.doc.newChild(None, 'rss', None)
        rss.setProp('version', '2.0')
        self.rssnode = rss.newChild(None, 'channel', None)

    def do_file(self, filename):
        if filename[0] != '/':
            cwd = os.getcwd()
            self.filename = os.path.join(cwd, filename)
        else:
            self.filename = filename

        try:
            self.file_open = open(self.filename, 'w+')
        except IOError as exc:
            print(f'Error opening file {self.filename}: {exc}', file=sys.stderr)
            sys.exit(1)

    def rsspackage(self, package):
        rfc822_format = "%a, %d %b %Y %X GMT"
        changelog_format = "%a, %d %b %Y GMT"
        package_hex = binascii.hexlify(package.chksum[1]).decode()
        item = self.rssnode.newChild(None, 'item', None)
        title = self.xmlescape(str(package))
        description = package.description
        item.newChild(None, 'title', title)
        date = time.gmtime(float(package.buildtime))
        item.newChild(None, 'pubDate', time.strftime(rfc822_format, date))
        # pylint: disable=line-too-long
        item.newChild(None, 'guid', package_hex).setProp("isPermaLink", "false")
        link = package.remote_location()
        item.newChild(None, 'link', self.xmlescape(link))
        changelog = ''
        cnt = 0
        if package.changelogs is not None:
            changelog_list = package.changelogs
        else:
            changelog_list = []
        for meta in changelog_list:
            count += 1
            if count > 3:
                changelog += '...'
                break
            (date, author, desc) = meta
            date = time.strftime(changelog_format, time.gmtime(float(date)))
            changelog += f'{date} - {author}\n{desc}\n\n'
        # pylint: disable=line-too-long,consider-using-f-string
        description = '<p><strong>{}</strong> - {}</p>\n\n'.format(self.xmlescape(package.name), self.xmlescape(package.summary))
        description += '<p>%s</p>\n\n<p><strong>Change Log:</strong></p>\n\n' % self.xmlescape(description.replace("\n", "<br />\n"))
        description += self.xmlescape('<pre>%s</pre>' % self.xmlescape(changelog))
        item.newChild(None, 'description', description)
        return item

    def start_rss(self):
        """return string representation of rss preamble"""
        rfc822_format = "%a, %d %b %Y %X GMT"
        now = time.strftime(rfc822_format, time.gmtime())
        rssheader = f"""<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0">
      <channel>
        <title>{self.title}</title>
        <link>{self.link}</link>
        <description>{self.description}</description>
        <pubDate>{now}</pubDate>
        <generator>DNF</generator>
        """

        self.file_open.write(rssheader)

    def do_package(self, package):
        item = self.rsspackage(package)
        self.file_open.write(item.serialize("utf-8", 1))
        item.unlinkNode()
        item.freeNode()
        del item

    def close_rss(self):
        end="\n  </channel>\n</rss>\n"
        self.file_open.write(end)
        self.file_open.close()
        del self.file_open
        self.doc.freeDoc()
        del self.doc

def make_rss_feed(filename, title, link, description, recent, dnfobj):
    rssobj = RepoRSS(filename)
    rssobj.title = title
    rssobj.link = link
    rssobj.description = description
    rssobj.start_rss()
    if len(recent) > 0:
        for package in recent:
            rssobj.do_package(package)
    rssobj.close_rss()

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

    print('Getting repo data')
    try:
        dnfobj.fill_sack()
    except:
        print('repo data failure')
        sys.exit(1)

    sack_query = dnfobj.sack.query().available()
    recent = sack_query.filter(latest_per_arch=1)
    sorted_recents = sorted(set(recent.run()), key=lambda pkg: pkg.buildtime)
    sorted_recents.reverse()
    make_rss_feed(options.filename, options.title, options.link, options.description, sorted_recents, dnfobj)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--filename', type=str, default='repo-rss.xml')
    parser.add_argument('--link', type=str, default='http://yum.baseurl.org')
    parser.add_argument('--title', type=str, default='RSS Repository - Recent Packages')
    parser.add_argument('--description', type=str, default='Most recent packages in Repositories')
    parser.add_argument('--days', type=int, default=7)
    parser.add_argument('--tempcache', action='store_true')
    parser.add_argument('--arches', action='append', default=[])
    parser.add_argument('--config', type=str, default='')
    parser.add_argument('repoids', metavar='N', type=str, nargs='+')
    results = parser.parse_args()

    main(results)
