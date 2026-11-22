# The instance suite's fixture

This tree is **owned by the tests** and is not a live configuration. Its
layout is that of a real configuration root; nothing here changes because
a cloud changed, and no run ever commits into it.

It is cs-image-system-3's frozen fixture (`tests/fixtures/config`, at the
commit spec 008 moved the plugin from, `0e73dedc`) with its docker parts
taken out, since this repository installs no docker family: the
`docker-fixture` runtime, the `tofu-docker` instance builder, the
`docker-volume` storage builder, the `pckr-docker` image builder, the
`rh10-container` OS builder, `images/image5.yaml` (`imgfile-container`),
`storages/container.yaml` and the `container-test` instance. Everything
else stays as it was there, so the Okta emission is the one the system's
suite pinned: the identity roots in [../golden](../golden) are byte for byte
the ones cs-image-system-3's shared golden held.

- **The identity is Okta's**: `cfg/group-builders.yml` declares the managed
  group builder `oktagroups` (with `posix-local` as its POSIX delegate), the
  read-only `okta-groups-ro` and the read-only user builder `okta-tf-users`.
  `groups/` holds the groups on them (`basic`, `coops`, `tcmet`, `stofs`,
  `secofs`; `readers` on the read-only builder) and one POSIX group
  (`pxgroup`) beside them.
- **The machines run on AWS**, the cloud the instance suite needs for an
  identity's work on a machine (the repository's README says why). Nothing
  reaches AWS: the suite's stubs answer it.
- It carries **no `meta-state/`** and no generated output; the harness's
  `copy_config` copies it into a temporary directory for every test. Its
  instance subjects (`test`, `test2`) are declared in
  `instances/instances.yaml`; none is ephemeral here.
- `../golden/` is exactly what a run of every lifecycle emits over it; a
  change here moves the golden (`just golden-regen`, then read every
  rewritten file).
- The overlays under `overlays/` are test devices: nothing reads them
  unless an invocation names one with `--overlay`.
- The four modification files at the root (`setup_dask.yml`,
  `setup_data_science.yml`, `modify_image.yml`, `mod_image.sh`) are
  provisioned content whose hash is part of image lineage: editing even a
  comment in them moves the golden.

The rosters (`groups/users.yaml`, `groups/group-*.yaml`) are encrypted entry
by entry as `ENC[age:...]` values to the fixture's own TEST identity,
`.age-identity` (committed on purpose; its public key is `.age-recipient` and
`cfg/_config.yml` `encryption.recipients`). The harness hands it to the
load, so the suite needs nothing from the environment. Encrypting with a
committed key protects nothing (it exercises the mechanism), so the people
are **synthetic**: personas with phonetic-alphabet surnames, explicit
addresses on example domains and derived ones on `@example.invalid`. No real
person and no real domain is in this tree.
