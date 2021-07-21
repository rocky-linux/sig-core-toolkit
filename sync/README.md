sync
====

These scripts assist in syncing to staging and to prod for releases, whether
they are full point releases, simple update releases, or a brand new repository
being added. Each script here has a specific purpose.

What to do?
-----------

When the scripts are being ran, they are usually ran with a specific purpose or
a reason. They are also ran in a certain order.

The below are common vars files. common_X will override what's in common.

```
.
├── common
├── common_8
```

These are for the releases in general. What they do is noted below.

```
├── gen-torrents.sh                  -> Generates torrents for images
├── minor-release-sync-to-staging.sh -> Syncs a minor release to staging
├── prep-staging-8.sh                -> Preps staging updates and signs repos
├── sign-repos-only.sh               -> Signs the repomd (only)
├── sync-to-prod.sh                  -> Syncs staging to production
├── sync-to-staging.sh               -> Syncs a provided compose to staging
├── sync-to-staging-sig.sh           -> Syncs a sig provided compose to staging
```

Generally, you will only run `minor-release-sync-to-staging.sh` when a full
minor release is being produced. So for example, if 8.5 has been built out, you
would run that after a compose. `gen-torrents.sh` would be ran shortly after.

When doing updates, the order of operations (preferably) would be:

* `sync-to-staging.sh`
* `sync-to-staging-sig.sh` Only if sigs are updated
* `prep-staging-X.sh`  -> This is required to ensure the groups, compos, and
                          module data stay sane. This helps us provide older
                          packages in the repos.
* `sync-to-prod.sh`    -> After the initial testing, it is sent to prod.
