Empanadas
================

Empanadas is the Rocky Linux Release Engineering toolkit for repeatable operations or functionality testing.

<center><img src='.github/empanadas.png' width=150px /></center>

Currently mirrored at our [github](https://github.com/rocky-linux), and the
[RESF Git Service](https://git.resf.org). Changes will typically occur at the
RESF Git Service.

What does this have?
--------------------

* analyze -> Analysis utilities (such as download stats)
* chat -> mattermost related utilities
* func -> (mostly defunct) testing scripts and tools to test base functionality
* iso -> Contains `empanadas`, which provides ISO, Compose, and Sync related utilities.
* mangle -> Manglers and other misc stuff
* sync -> Sync tools, primarily for Rocky Linux 8 and will eventually be deprecated

How can I help?
---------------

Fork this repository and open a PR with your changes. Keep these things in mind
when you make changes:

* Your PR should be against the devel branch (not optional)
* Have pre-commit installed if possible
* Have shellcheck installed if possible
* Shell Scripts: These must pass a shellcheck test!
* Python scripts: Try your best to follow PEP8 guidelines (even the best linters get things wrong)

  * Note that not everything has to pass. Just try your best.

PR's against the main branch will be closed.

PR's are preferred at the [RESF Git Service](https://git.resf.org).

Will some of this be moved into separate repositories?
------------------------------------------------------

There may be some things that will be moved to its own repository in the near
future. From a SIG/Core standpoint, we believe a good chunk of this should stay
here as it makes it easier for us to maintain and manage.
