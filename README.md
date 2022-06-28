sig-core-toolkit
================

Release Engineering toolkit for repeatable operations or functionality testing.

Currently mirrored at our [github](https://github.com/rocky-linux), and the
[RESF Git Service](https://git.resf.org). Changes will typically occur at GitHub.

What does this have?
--------------------

* analyze -> Analysis utilities (such as download stats)
* chat -> mattermost related utilities
* func -> (mostly defunct) testing scripts and tools to test base functionality
* iso -> ISO and Compose related utilities, primarily for Rocky Linux 9+
* live -> Live image related utilities
* mangle -> Manglers and other misc stuff
* sync -> Sync tools, primarily for Rocky Linux 8

How can I help?
---------------

Fork this repository and open a PR with your changes. Keep these things in mind
when you make changes:

* Have pre-commit installed
* Have shellcheck installed
* Shell Scripts: These must pass a shellcheck test!
* Python scripts: Try your best to follow PEP8 guidelines

Your PR should be against the devel branch at all times. PR's against the main
branch will be closed.

Will some of this be moved into separate repositories?
------------------------------------------------------

There may be some things that will be moved to its own repository in the near
future. From a SIG/Core standpoint, we believe a good chunk of this should stay
here as it makes it easier for us to maintain and manage.
