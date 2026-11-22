# cs-image-system-okta

The Okta identity plugin for
[cs-image-system](https://github.com/infrastructurebuilder/cs-image-system-3).
A configuration's groups become managed Okta Privileged Access (OPA) groups,
with their resource groups, login projects, security policies and enrollment
tokens. Its users become lookups of people already in Okta. The plugin bakes
the OPA server agent into a base image, activates it for an instance's owning
group, and keeps the server registry and the CI login policy. It moved here,
with its history, from the system's repository (spec 008), and releases on
its own version line from 0.2.0.

## The plugin

One distribution:

| Distribution | Import package | Provides | Entry points |
| --- | --- | --- | --- |
| [`cs-image-system-okta-opa-plugin`](packages/okta-opa-plugin/README.md) | `cs_image_system.okta_opa_plugin` | the `okta-tf` and `okta-tf-ro` group and user builders, the `okta` identity type and its enrollment, the gid shim, the OPA server registry, the login proof and the CI login policy; the Okta section of the bootstrap; its Terraform module, as package data | `cs_image_system.plugins.group`: `okta_opa_plugin`; `cs_image_system.bootstrap`: `okta`; `cs_image_system.commands`: `okta_opa_plugin` (`workload`, `verify login`); `cs_image_system.modules`: `modules` |

It depends on the parts of the system's SDK it uses (the contract, the kit
and the Terraform libraries) by range, never on an exact release.

## Installing

An operator installs the plugin through the system's own `okta` extra,
beside the extras of the tree's runtimes:

```sh
uv tool install 'cs-image-system[okta]'
```

The extra names the plugin by a range on its releases. The system's
operations guide states the install once, with every provider's extra:
[OPERATIONS.md, "Installing a release"](https://github.com/infrastructurebuilder/cs-image-system-3/blob/develop/docs/OPERATIONS.md#installing-a-release).

## Building and testing

The [`Justfile`](Justfile) is the one entry point; `just --list` names
every target.

```sh
just init         # once, idempotent: the environment exactly as uv.lock has it
just test         # lint, the type check, the surface check, the plugin's own tests, the instance tests and the golden
just full-test    # `test`, then the low end of the SDK ranges and the standard-aws starter rendered, validated and dry-run
```

Everything of the system the plugin needs comes from the package index
by range. The SDK comes as the plugin's own dependencies. The command line,
its test kit and the core plugins the fixture declares make up the
workspace's `dev` group ([pyproject.toml](pyproject.toml)). Nothing here
reads another repository's checkout.

The tests run under the test kit's strict session: a run that collects
nothing or skips anything fails. The plugin's own tests
([packages/okta-opa-plugin/tests](packages/okta-opa-plugin/tests)) need
nothing but the SDK and the test kit. The instance tests
([tests/instance](tests/instance)) drive stubbed runs over the suite's own
fixture ([tests/instance/fixture](tests/instance/fixture)) and compare the
emission with its golden ([tests/instance/golden](tests/instance/golden)).
After an intended change to the emission, `just golden-regen` rewrites the
golden; read every rewritten file before committing it.

### Why the instance tests need the AWS family

An identity's work on a machine can only be shown on a machine: the
enrollment at launch, the activation in the bake, the login proof. So the
instance suite declares a cloud for its machines to run on. Today that is
the AWS family, installed from the index by the workspace's `instance`
dependency group, and nowhere else: the plugin itself never depends on it,
and [tests/test_aws_only_in_instance.py](tests/test_aws_only_in_instance.py)
holds it there. The cloud may change. The AWS stubs in
[tests/instance/aws_stubs.py](tests/instance/aws_stubs.py) are temporary
and will be replaced by the AWS family's own once it publishes them.

Nothing in these tests reaches Okta, OPA or AWS. The Okta credentials a
load checks for are dummies, since a load only reads that they are set.
CI's dispatched `lookup` job is the one exception: a read-only lookup
against the OPA team, run by hand, with the team's key pair as secrets.

## Releasing

```sh
just release <part> pypi            # full-test, then a commit and the tag v<version>
git push origin HEAD v<version>     # the tag's push publishes it
```

`<part>` is `major`, `minor`, `patch` or an explicit version. The release
moves the plugin's number, refuses any version either index ever held for
the plugin (every 0.1.x, released from cs-image-system-3, among them), runs
`full-test`, builds, then commits and tags `v<version>`. `yes` as a third
argument is the dry form: the plan, with nothing changed.

Pushing the tag publishes the release: the `Publish` workflow uploads it to
TestPyPI and then, for a final version, PyPI, by trusted publishing, so no
upload token is stored anywhere. [docs/RELEASING.md](docs/RELEASING.md) says
how that trust is set up on each index and in the repository, and what a
fork must change to publish under a name of its own.

## Documents

- [docs/CONFIGURATION.md](docs/CONFIGURATION.md): the fields of the Okta
  group and user builders, the one source for them.
- [docs/RELEASING.md](docs/RELEASING.md): how a release is cut and
  published, setting up trusted publishing, and releasing a fork.
- The [plugin's README](packages/okta-opa-plugin/README.md): the plugin
  in depth, from what it registers to how it fails.
- The system's documents for everything else: the
  [operations guide](https://github.com/infrastructurebuilder/cs-image-system-3/blob/develop/docs/OPERATIONS.md),
  the rest of the
  [configuration reference](https://github.com/infrastructurebuilder/cs-image-system-3/blob/develop/docs/CONFIGURATION.md),
  and how a provider depends on the SDK
  ([WRITING_A_PROVIDER.md](https://github.com/infrastructurebuilder/cs-image-system-3/blob/develop/docs/WRITING_A_PROVIDER.md#how-it-depends-on-the-sdk)).

## Licence

Apache-2.0 ([LICENSE](LICENSE)). Every file carries an SPDX header or is
declared in [REUSE.toml](REUSE.toml); `just lint` runs `reuse lint`.
