Release Engineering Core Functionality Testing
==============================================

These are a set of scripts that are designed to test the core functionality
of a Rocky Linux system. They are designed to work on current versions of
Rocky and are used to test a system as a Release Engineering self-QA but
can be used by others for their own personal testing (under the assumption
that you just want to see what happens, we don't judge :).

These tests *must* pass for a release to be considered "Core Validated"
Checking against the upstream repositories for package matches are not enough
and are/will be addressed by other tools.

* common  -> Functions that our scripts and tests may or may not use. Templates
             and other files should come here too under common/files and
             scripts that use them should reference them as `./common/files/...`
* core    -> Core functionality and testing. For example, packages and service
             functionality.
* lib     -> Library tests (these may be done elsewhere)
* log     -> Log output. This repository has example logs of running on Rocky
             Linux.
* modules -> Tests for module streams and their basic tests
* stacks  -> Software stacks, think like LAMP.

How to Run
----------

There are two ways to run through the tests:

* By running `/bin/bash runtests.sh`
  * Runs all tests
* By running `/bin/bash monotests.sh`
  * Runs all tests one by one to help identify failures as they happen

Adding Tests
------------

So you want to add a few tests. Great! Before you add them, I want you to ask
yourself the following questions:

* Are my test(s) brand new?
* Are my test(s) actually for the "core" functionality of the system?
* Will my test(s) be going through a shellcheck?
* Were my tests running with SELinux enforcing?

If you've answered no to any of the above, the test may not be valid for this
project. If you are planning on changing a test or fixing a test to look or
work better, then a PR is more than welcome. Some things could definitely
use some touching up or improvements.

When creating tests, the below should be followed (at a minimum):

* Use functions from `./common/imports.sh`
* Global variables should be in `./common/exports.sh`
* Reusable files should be in `./common/files`
* Logging is enforced; use `r_log` where ever necessary
* Exits and status checks should be against `r_checkExitStatus`
* Place comments where `r_log` won't be descriptive enough
* With some exceptions, keep lines to a maximum of 80 characters
* Use fullpath to binaries when necessary
* Use shellcheck to verify the scripts are valid and compliant (some stuff that
  shellcheck reports could be false - Just use a comment to turn off that test
  for that particular line, but you need to ensure it's a false positive.)
* All filenames should start with a number and end with `.sh` (eg `00-foo.sh`)
* The executable bit should be set (except for scripts that are sourced)

**Note**: that if tests should be skipped, they should be placed into the
`skip.list` file so that way they won't run during the test phase. The file will
get a -x placed on it. Note that this is generally OK, since this repo will just
be cloned when being used anyway and won't be committed back. It is just
expected that all scripts are +x to begin with unless there's a valid reason.
There are a few tests we already have disabled because they're either not done
or they are acting strangely.

**Note**: If a package required additional modification (eg, dotnet) and it
it has a `.rocky` on the release tag, then it should be noted in the mods.list.
The same thing goes for the debrand list. Additionally, if certain patches
can change the output, it would be good to test for this (see `core/pkg_httpd`)
for an example.

Core Functionality
------------------

Everyone has their own idea of "core functionality." In the case of Release
Engineering, core functionality is simply us saying that with a basic
installation of Rocky Linux, we can run basic commands that any system admin,
developer, or casual user would run and expect to work on a regular basis.

Think about the software you probably use fairly regularly on any Linux system
that you've installed, ran, or are currently running. Now think about the
commands that you run day in, and day out. Now consider that what you're
running isn't niche and it's highly likely others use them too. If something
goes wrong with the build of your distribution, your tools might not work as
expected. Which is why the idea of doing basic testing of most, if not all of
the common stuff is a good thing to do.

While writing this, the things that come to mind are:

* archiving: zip, tar, gzip, etc
* file: head, tail, less, cat, diff, find, grep, vim, git
* network: ping, ip, ssh, wget, curl
* packaging: rpm, dnf
* system utilities: systemctl, top, sudo, ps
* web (packaging): httpd

Those are just off the top of my head. There's obviously a lot more, but with
that in mind, you now have the idea of what we're trying to accomplish with
this set of tests.

With that being said, there are obviously other tests being employed for things
that people may or may not use (LAMP stacks for example). It's not a core
function by any means, but it at least validates that a common thing or set of
things works as intended without extending the system or fixing the baseline
set of packages.

FAQ
---

### How do I know what some of these scripts do?
You can view the script and look at the various `r_log` lines or the comments
if they happen to be there. If you don't see a comment, look for an `r_log`.

### How do I disable a test?
A test can be disabled by running `chmod -x` on any given test. It's also
recommended to add it to `skip.list`

### Won't some of the tests have to change on (insert major release here)?
Yes and no. There are some tests will have to be altered to deal with it, but
the only way to really find out is to run the tests on a new major release
and see what happens.

### A test failed, what do I do?
Run a test manually to get the error. (Most) errors are not sent to the logs
as the logs are mainly to say if something was "PASSED", "FAILED", or "SKIPPED".

### A test isn't descriptive enough on r_log or comments, can I PR for that?
Absolutely - If you feel there is a gap, please fork and change what you feel
needs more information!

### Do I really need SELinux enforcing to run/add tests?
Yes.

### Why though?
Ensuring the tests work and operate under default conditions (firewall and 
selinux are up) helps those who use our distribution in environments where
security is important, actually work and function correctly.

With that said, There is no reason to disable integral security layers on your
system.

Current Tree
------------
```
.
├── common
│   ├── exports.sh
│   ├── files
│   │   ├── correct-passwd
│   │   ├── correct-shadow
│   │   ├── dovecot-test-sasl
│   │   ├── hello.c
│   │   ├── hello.cpp
│   │   ├── incorrect-passwd
│   │   ├── incorrect-shadow
│   │   ├── lamp-sql
│   │   ├── lamp-sql-php
│   │   ├── malform-group
│   │   ├── malform-gshadow
│   │   ├── openssl-answers
│   │   ├── postfix-test-sasl
│   │   ├── postfix-test-tls
│   │   └── smb.conf
│   └── imports.sh
├── core
│   ├── pkg_acl
│   │   ├── 00-install-acl.sh
│   │   ├── 10-test-acl-functions.sh
│   │   └── README.md
│   ├── pkg_archive
│   │   ├── 00-install-formats.sh
│   │   ├── 10-bzip.sh
│   │   ├── 20-gzip-bin-test.sh
│   │   ├── 21-gzip-test.sh
│   │   ├── 22-gzexe.sh
│   │   ├── 23-zcmp-zdiff.sh
│   │   ├── 24-zforce.sh
│   │   ├── 25-zgrep.sh
│   │   ├── 25-zless.sh
│   │   ├── 26-zmore.sh
│   │   ├── 27-znew.sh
│   │   ├── 30-tar.sh
│   │   ├── 40-xzcmp-xzdiff.sh
│   │   ├── 40-zip.sh
│   │   ├── 50-lzop.sh
│   │   └── README.md
│   ├── pkg_attr
│   │   ├── 00-install-attr.sh
│   │   ├── 10-check-attr.sh
│   │   └── README.md
│   ├── pkg_auditd
│   │   ├── 00-install-auditd.sh
│   │   ├── 10-auditd-logs.sh
│   │   ├── 11-generate-events.sh
│   │   └── README.md
│   ├── pkg_bash
│   │   ├── 00-bash-version.sh
│   │   └── README.md
│   ├── pkg_bc
│   │   ├── 00-install-bc.sh
│   │   ├── 10-test-calculation.sh
│   │   └── README.md
│   ├── pkg_bind
│   │   ├── 00-install-bind.sh
│   │   ├── 10-test-lookup.sh
│   │   └── README.md
│   ├── pkg_coreutils
│   │   ├── 00-install-coreutils.sh
│   │   ├── 10-arch.sh
│   │   ├── 11-basename.sh
│   │   ├── 12-cat.sh
│   │   ├── 13-cut.sh
│   │   ├── 14-bool.sh
│   │   ├── 15-heads-tails.sh
│   │   ├── 16-pathchk.sh
│   │   ├── 17-readlink.sh
│   │   ├── 18-seq.sh
│   │   ├── 19-timeout.sh
│   │   ├── 20-hash.sh
│   │   ├── 21-touch-ls.sh
│   │   ├── 22-uniq.sh
│   │   ├── 23-wc.sh
│   │   ├── 24-yes.sh
│   │   └── README.md
│   ├── pkg_cpio
│   │   ├── 00-install-cpio.sh
│   │   ├── 10-cpio.sh
│   │   └── README.md
│   ├── pkg_cracklib
│   │   ├── 00-install-cracklib.sh
│   │   ├── 10-test-passwords.sh
│   │   └── README.md
│   ├── pkg_cron
│   │   ├── 00-install-cron.sh
│   │   ├── 10-dot-cron.sh
│   │   └── README.md
│   ├── pkg_curl
│   │   ├── 00-install-curl.sh
│   │   ├── 10-test-curl.sh
│   │   └── README.md
│   ├── pkg_diffutils
│   │   ├── 00-install-diff.sh
│   │   └── README.md
│   ├── pkg_dnf
│   │   ├── 10-remove-package.sh
│   │   └── README.md
│   ├── pkg_dovecot
│   │   ├── 00-install-dovecot.sh
│   │   ├── 01-configure-dovecot.sh
│   │   ├── 10-pop3-test.sh
│   │   ├── 11-imap-test.sh
│   │   ├── 12-dovecot-clean.sh
│   │   └── README.md
│   ├── pkg_file
│   │   ├── 00-install-file.sh
│   │   ├── 10-mime-check.sh
│   │   ├── 20-mime-image.sh
│   │   ├── 30-mime-symlink.sh
│   │   └── README.md
│   ├── pkg_findutils
│   │   ├── 00-install-findutils.sh
│   │   ├── 10-find.sh
│   │   └── README.md
│   ├── pkg_firefox
│   │   ├── 00-install-firefox.sh
│   │   ├── 10-check-firefox-start-page.sh
│   │   └── README.md
│   ├── pkg_firewalld
│   │   ├── 00-install-firewalld.sh
│   │   ├── 10-firewalld-check-rule.sh
│   │   └── README.md
│   ├── pkg_freeradius
│   │   ├── 00-install-freeradius.sh
│   │   ├── 10-test-freeradius.sh
│   │   └── README.md
│   ├── pkg_gcc
│   │   ├── 00-install-gcc.sh
│   │   ├── 10-gcc-build-simple.sh
│   │   ├── 11-gcc-build-cpp.sh
│   │   ├── 20-annobin-test-gcc.sh
│   │   ├── 21-annobin-test-gplusplus.sh
│   │   └── README.md
│   ├── pkg_git
│   │   ├── 00-install-git.sh
│   │   ├── 10-test-git.sh
│   │   ├── 11-test-clone-log.sh
│   │   └── README.md
│   ├── pkg_httpd
│   │   ├── 00-install-httpd.sh
│   │   ├── 10-httpd-branding.sh
│   │   ├── 20-test-basic-http.sh
│   │   ├── 21-test-basic-https.sh
│   │   ├── 30-test-basic-auth.sh
│   │   ├── 40-test-basic-vhost.sh
│   │   ├── 50-test-basic-php.sh
│   │   └── README.md
│   ├── pkg_kernel
│   │   ├── 10-test-kernel-keyring.sh
│   │   ├── 11-test-secure-boot.sh
│   │   ├── 12-test-debrand.sh
│   │   └── README.md
│   ├── pkg_lsb
│   │   ├── 00-install-lsb.sh
│   │   ├── 10-test-branding.sh
│   │   └── README.md
│   ├── pkg_lsof
│   │   ├── 00-install-lsof.sh
│   │   ├── 10-test-lsof.sh
│   │   └── README.md
│   ├── pkg_network
│   │   ├── 00-install-packages.sh
│   │   ├── 10-tracepath.sh
│   │   ├── 11-traceroute.sh
│   │   ├── 12-mtr.sh
│   │   ├── 13-iptraf.sh
│   │   ├── 20-configure-bridge.sh
│   │   ├── 30-test-arpwatch.sh
│   │   ├── imports.sh
│   │   └── README.md
│   ├── pkg_nfs
│   │   ├── 00-install-nfs.sh
│   │   ├── 10-prepare-nfs-ro.sh
│   │   ├── 11-prepare-nfs-rw.sh
│   │   ├── 12-prepare-autofs.sh
│   │   └── README.md
│   ├── pkg_openssl
│   │   ├── 00-install-openssl.sh
│   │   ├── 10-test-openssl.sh
│   │   └── README.md
│   ├── pkg_perl
│   │   ├── 00-install-perl.sh
│   │   ├── 10-test-perl.sh
│   │   ├── 11-test-perl-script.sh
│   │   └── README.md
│   ├── pkg_postfix
│   │   ├── 00-install-postfix.sh
│   │   ├── 10-test-helo.sh
│   │   ├── 20-mta.sh
│   │   ├── 30-postfix-sasl.sh
│   │   ├── 40-postfix-tls.sh
│   │   └── README.md
│   ├── pkg_python
│   │   ├── 00-install-python.sh
│   │   ├── 10-test-python3.sh
│   │   └── README.md
│   ├── pkg_release
│   │   ├── 00-install-file.sh
│   │   ├── 10-name-sanity-check.sh
│   │   ├── 20-check-gpg-keys.sh
│   │   ├── 30-os-release.sh
│   │   ├── 40-system-release.sh
│   │   └── README.md
│   ├── pkg_rootfiles
│   │   ├── 00-install-rootfiles.sh
│   │   └── 10-test-rootfiles.sh
│   ├── pkg_rsyslog
│   │   ├── 00-install-rsyslog.sh
│   │   ├── 10-test-syslog.sh
│   │   └── README.md
│   ├── pkg_samba
│   │   ├── 00-install-samba.sh
│   │   ├── 10-test-samba.sh
│   │   └── README.md
│   ├── pkg_secureboot
│   │   ├── 10-test-grub-secureboot.sh
│   │   ├── 11-test-shim-certs.sh
│   │   └── README.md
│   ├── pkg_selinux
│   │   ├── 00-install-selinux-tools.sh
│   │   ├── 10-check-alerts.sh
│   │   └── 20-check-policy-mismatch.sh
│   ├── pkg_setup
│   │   ├── 00-test-shells.sh
│   │   ├── 10-test-group-file.sh
│   │   ├── 20-test-passwd-file.sh
│   │   └── README.md
│   ├── pkg_shadow-utils
│   │   ├── 00-install.sh
│   │   ├── 10-files-verify.sh
│   │   ├── 20-user-tests.sh
│   │   ├── 30-group-tests.sh
│   │   ├── 40-pw.sh
│   │   ├── 90-clean.sh
│   │   └── README.md
│   ├── pkg_snmp
│   │   ├── 00-install-snmp.sh
│   │   ├── 10-test-snmp-1.sh
│   │   ├── 11-test-snmp-2.sh
│   │   ├── 12-test-snmp-3.sh
│   │   └── README.md
│   ├── pkg_sqlite
│   │   ├── 00-install-sqlite.sh
│   │   ├── 10-sqlite-tables.sh
│   │   ├── 20-sqlite-dump.sh
│   │   └── README.md
│   ├── pkg_strace
│   │   ├── 00-install-strace.sh
│   │   ├── 10-test-strace.sh
│   │   └── README.md
│   ├── pkg_sysstat
│   │   ├── 00-install-sysstat.sh
│   │   ├── 10-iostat.sh
│   │   ├── 11-cpu.sh
│   │   ├── 12-cpu-io.sh
│   │   └── README.md
│   ├── pkg_systemd
│   │   ├── 00-systemd-list-services.sh
│   │   ├── 10-systemd-list-non-native-sevices.sh
│   │   ├── 11-systemd-service-status.sh
│   │   ├── 20-systemd-journald.sh
│   │   └── README.md
│   ├── pkg_tcpdump
│   │   └── README.md
│   ├── pkg_telnet
│   │   ├── 00-install-telnet.sh
│   │   └── 10-test-telnet.sh
│   ├── pkg_vsftpd
│   │   ├── 00-install-vsftpd.sh
│   │   ├── 10-anonymous-vsftpd.sh
│   │   ├── 20-local-login.sh
│   │   ├── 30-cleanup.sh
│   │   └── README.md
│   ├── pkg_wget
│   │   ├── 00-install-wget.sh
│   │   ├── 10-test-wget.sh
│   │   └── README.md
│   └── pkg_which
│       ├── 00-install-which.sh
│       ├── 10-test-which.sh
│       └── README.md
├── debrand.list
├── lib
├── log
│   └── README.md
├── mods.list
├── modules
├── monotests.sh
├── README.md
├── runtests.sh
├── skip.list
└── stacks
    ├── ipa
    │   ├── 00-ipa-pregame.sh
    │   ├── 10-install-ipa.sh
    │   ├── 11-configure-ipa.sh
    │   ├── 12-verify-ipa.sh
    │   ├── 20-ipa-user.sh
    │   ├── 21-ipa-service.sh
    │   ├── 22-ipa-dns.sh
    │   ├── 23-ipa-sudo.sh
    │   ├── 50-cleanup-ipa.sh
    │   └── README.md
    └── lamp
        ├── 00-install-lamp.sh
        ├── 01-verification.sh
        └── 10-test-lamp.sh
```
